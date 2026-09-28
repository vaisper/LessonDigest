from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lessondigest.config import AppConfig  # noqa: E402


class ConfigTest(unittest.TestCase):
    def test_load_repo_config(self) -> None:
        config = AppConfig.load(REPO_ROOT / "config.yaml")
        self.assertEqual(config.paths.root, REPO_ROOT)
        self.assertTrue(config.paths.transcripts.name == "transcripts")
        self.assertTrue(config.prompt_path().exists())
        self.assertIn("{{TRANSCRIPT}}", config.load_prompt_template())


if __name__ == "__main__":
    unittest.main()
