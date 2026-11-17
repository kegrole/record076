"""Shim entry point so ``python -m unittest test_urlnorm -v`` works from the repo root."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tests.test_urlnorm import *  # noqa: F401,F403


if __name__ == "__main__":
    unittest.main()
