from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lessondigest.asr.fake import FakeAsr  # noqa: E402
from lessondigest.config import AppConfig  # noqa: E402
from lessondigest.domain import RunStatus  # noqa: E402
from lessondigest.pipeline import Pipeline  # noqa: E402
from lessondigest.storage import FilesystemStorage  # noqa: E402
from lessondigest.summarize.fake import FakeLlm  # noqa: E402

TRANSCRIPT = (
    "Сегодня мы изучили квадратные уравнения. "
    "Дискриминант D равен b в квадрате минус четыре a c. "
    "Домашнее задание: параграф двенадцать, номера триста сорок пять."
)

FAKE_CONFIG = """
paths:
  root: "."
asr:
  provider: fake
  model: fake
llm:
  provider: fake
  model: fake
  prompt_version: v1
chunking:
  enabled: true
  soft_char_limit: 24000
"""


class PipelineTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "config.yaml").write_text(FAKE_CONFIG, encoding="utf-8")
        prompts = self.root / "prompts"
        prompts.mkdir()
        (prompts / "v1_digest.txt").write_text(
            "Сделай конспект и верни JSON.\n\nТранскрипт:\n\"\"\"\n{{TRANSCRIPT}}\n\"\"\"\n",
            encoding="utf-8",
        )
        self.audio = self.root / "lesson.m4a"
        self.audio.write_bytes(b"\x00\x01fakeaudio")
        self.config = AppConfig.load(self.root / "config.yaml")
        self.storage = FilesystemStorage(self.config.paths)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _pipeline(self) -> Pipeline:
        return Pipeline(self.config, asr=FakeAsr(text=TRANSCRIPT), llm=FakeLlm())

    def test_end_to_end(self) -> None:
        result = self._pipeline().run(audio=self.audio, subject="algebra")
        self.assertEqual(result.status, RunStatus.DELIVERED)
        self.assertIsNotNone(result.digest_md)
        assert result.digest_md is not None
        self.assertTrue(result.digest_md.exists())
        self.assertIn("## Домашнее задание", result.digest_md.read_text(encoding="utf-8"))

        meta = self.storage.load_run_meta(result.run_id)
        self.assertEqual(meta.status, RunStatus.DELIVERED)
        self.assertEqual(meta.asr_provider, "fake")
        self.assertEqual(meta.progress, 1.0)
        self.assertTrue(meta.audio_raw is not None)
        self.assertTrue((self.config.paths.audio_raw / Path(meta.audio_raw).name).exists())
        self.assertTrue(self.storage.metrics_path(result.run_id).exists())
        self.assertTrue(self.storage.digest_json_path(result.run_id).exists())
        self.assertTrue(self.storage.analytic_json_path(result.run_id).exists())

    def test_rerun_skips_stages(self) -> None:
        first = self._pipeline().run(audio=self.audio, subject="algebra")
        second = self._pipeline().run(audio=self.audio, subject="algebra")
        self.assertEqual(first.run_id, second.run_id)
        self.assertIn("ingest", second.skipped_stages)
        self.assertIn("asr", second.skipped_stages)
        self.assertIn("summarize", second.skipped_stages)

    def test_resume_from_summarize_force(self) -> None:
        first = self._pipeline().run(audio=self.audio, subject="algebra")
        result = self._pipeline().run(run_id=first.run_id, subject="algebra", from_stage="summarize", force=True)
        self.assertEqual(result.status, RunStatus.DELIVERED)
        self.assertIn("asr", result.skipped_stages)
        self.assertNotIn("summarize", result.skipped_stages)

    def test_homework_detected_without_marker_warning(self) -> None:
        result = self._pipeline().run(audio=self.audio, subject="algebra")
        self.assertFalse(any("маркеры домашки" in w for w in result.warnings))
        digest = self.storage.load_digest(result.run_id)
        self.assertIsNotNone(digest.homework)


if __name__ == "__main__":
    unittest.main()
