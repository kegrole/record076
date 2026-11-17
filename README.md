# urlnorm

仅使用 Python 标准库实现的 URL 规范化与去重工具。判断两个字符串形式不同的
URL 是否指向同一资源时，不做裸字符串比较，而是按 RFC 3986 逐段解析、解析相对
引用、再对规范化结果逐字节比较。

## 目录结构

- `urlnorm/parser.py`：RFC 3986 分段解析、§5.2.3 merge、§5.2.4
  `remove_dot_segments`、§5.3 recompose、§5.2.2 完整引用解析。
- `urlnorm/normalize.py`：scheme/host 小写、默认端口剥离、pct-encoded 大写、
  fragment 剥离与整体规范化。
- `urlnorm/query.py`：query 的 pct-encoded 大写与按 `(name, value)` 稳定排序。
- `urlnorm/dedupe.py`：按规范化结果分组并确定输出顺序。
- `urlnorm/report.py`：构造并写出 JSON 报告。
- `urlnorm/cli.py` / `urlnorm/__main__.py`：命令行入口。
- `demo/urls.jsonl`：7 条验收夹具。
- `tests/test_urlnorm.py`：覆盖全部 11 条判定口径的 unittest。

## 分段解析口径

`parse_uri_reference` 按 RFC 3986 Appendix B 的正则把输入拆成七段：
`scheme`、`userinfo`、`host`、`port`、`path`、`query`、`fragment`。
authority 内最后一个 `@` 之前为 userinfo；host 以 `[` 开头时按 IPv6/IP-literal
处理，`]` 之后的 `:` 才是端口分隔符，避免与地址内部的冒号混淆。

相对引用由 `resolve_reference` 严格按 RFC 3986 §5.2.2 解析：

1. 引用自带 scheme 时整体以引用为准，并对其 path 执行 §5.2.4；
2. 否则引用带 authority（如 `//other.org/x`）时继承 base 的 scheme；
3. 否则走 path 分支：绝对路径直接做 §5.2.4；相对路径先走 §5.2.3 merge
   （base 无 path 时补 `/`，否则取 base path 最后一个 `/` 之前的前缀），再做
   §5.2.4；空引用继承 base 的 path 与 query；仅 query 不同时沿用 base path；
4. fragment 始终取自引用；规范化阶段再统一剥离。

§5.2.4 按 RFC 的输入/输出缓冲规则逐段消解 `.` 与 `..`，只作用于 path 段，
绝不触碰 query/fragment。连续斜杠与尾斜杠不属于点段，原样保留。

## host 与默认端口

- scheme 与 host 统一转小写。
- `http` 的 `80`、`https` 的 `443` 在与 scheme 匹配时剥离；其他端口（如
  `8080`）原样保留。端口按十进制数字匹配，非数字端口不做默认端口推断。
- IPv6 字面量保留方括号形式（如 `[2001:db8::1]`），只对其中的十六进制字母
  随 host 一起小写，不做地址重排或压缩。

## `%2F` 与百分号编码规则

- 任何 pct-encoded（`%` + 两位十六进制数）都不会被解码，因此 path 中的
  `%2F` 永远是三个字符，不会变成路径分隔符 `/`，也不会参与点段消解。
- pct-encoded 的十六进制字母统一大写：`%2f` → `%2F`、`%3a` → `%3A`。该规则
  同时应用于 path、query；userinfo 同样只做大写、不解码、不删除。
- 明文出现的合法字符保持明文，不会被强行百分号编码。path 中保持明文的字符
  包括 unreserved（含 `~`）、sub-delims（`! $ & ' ( ) * + , ; =`）以及 `:`、
  `@`；分隔路径的 `/` 自然也保留。query 的保留集更宽，明文 `/` 与 `?` 合法且
  保持原样。

## query 排序与空值/裸键

- 以 `&` 切分参数，按复合键 `(name, value)` 做 Python 稳定排序；同名参数再按
  值排序，完全相同的 `(name, value)` 保留输入时的相对次序。
- 带等号的空值（`z=`）与裸键（`z`）都视为空值且必须保留，输出统一写成
  `z=`。因此 `?y=2&z` 与 `?z=&y=2` 规范化后都是 `?y=2&z=`。
- 空但存在的 query（URL 末尾单独一个 `?`）保留为空字符串；没有 `?` 则输出中
  也没有 query 段。

## fragment、分组顺序与序号

- fragment 一律剥离，规范化结果中不会出现 `#` 及其后内容。
- 去重以规范化后的逐字节结果为键。组内记录序号按输入次序升序；组间按组内最小
  输入序号升序，保证输出完全确定。
- 记录序号从 1 开始，等于输入行号。

## 幂等性保证

规范化只做可逆性质的收敛：大小写归一、默认端口删除、点段消解、pct-encoded
大写、query 稳定排序、fragment 剥离。这些操作的输出不再包含可被继续收敛的
形态（无 fragment、无默认端口、pct 已是大写、query 已排序、path 已无点段），
因此对任意 canonical 再次以同一 base 规范化，结果与输入逐字节相等。

## 报告格式

报告 JSON 只含两个顶层字段，摘要数字不会混入报告：

```json
{
  "groups": [
    {
      "canonical": "https://example.com/b?y=2&z=1",
      "records": [1, 2, 3]
    }
  ],
  "total_records": 7
}
```

## 使用方式

```bash
python -m urlnorm.cli \
  --input demo/urls.jsonl \
  --base https://example.com/dir/page.html \
  --out out/report.json
```

命令结束后在 stdout 打印一行摘要，依次为读入条数、去重后组数、规范化后唯一
地址数（与组数相同）、最大组的原始条数；四个数字均由 `groups` 派生。

运行测试：

```bash
python -m unittest test_urlnorm -v
```
