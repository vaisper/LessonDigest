from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fastapi.testclient import TestClient  # noqa: E402

from lessondigest.config import AppConfig  # noqa: E402
from lessondigest.web.app import create_app  # noqa: E402

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

PROMPT = "Сделай конспект и верни JSON.\n\nТранскрипт:\n\"\"\"\n{{TRANSCRIPT}}\n\"\"\"\n"


class WebTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "config.yaml").write_text(FAKE_CONFIG, encoding="utf-8")
        prompts = self.root / "prompts"
        prompts.mkdir()
        (prompts / "v1_digest.txt").write_text(PROMPT, encoding="utf-8")
        self.config = AppConfig.load(self.root / "config.yaml")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _wait(self, client: TestClient, run_id: str) -> dict:
        status: dict = {}
        for _ in range(100):
            status = client.get(f"/api/runs/{run_id}").json()
            if status["status"] in ("done", "failed"):
                return status
            time.sleep(0.1)
        return status

    def test_index_and_empty_list(self) -> None:
        with TestClient(create_app(self.config)) as client:
            self.assertEqual(client.get("/").status_code, 200)
            self.assertIn("LessonDigest", client.get("/").text)
            self.assertEqual(client.get("/api/runs").json(), [])

    def test_upload_end_to_end(self) -> None:
        app = create_app(self.config)
        with TestClient(app) as client:
            response = client.post(
                "/api/runs",
                files={"file": ("lesson.wav", b"\x00\x01fake-audio", "audio/wav")},
                data={"subject": "web_test"},
            )
            self.assertEqual(response.status_code, 202)
            run_id = response.json()["run_id"]

            status = self._wait(client, run_id)
            self.assertEqual(status["status"], "done", status)
            self.assertEqual(status["percent"], 100)
            self.assertEqual(status["progress"], 1.0)

            digest = client.get(f"/api/runs/{run_id}/digest").json()
            self.assertIn("Домашнее задание", digest["html"])
            self.assertTrue(digest["homework"])

            md = client.get(f"/api/runs/{run_id}/digest.md")
            self.assertEqual(md.status_code, 200)
            self.assertIn("#", md.text)

            runs = client.get("/api/runs").json()
            self.assertEqual(runs[0]["run_id"], run_id)

    def test_rejects_unknown_extension(self) -> None:
        with TestClient(create_app(self.config)) as client:
            response = client.post(
                "/api/runs",
                files={"file": ("notes.txt", b"hello", "text/plain")},
            )
            self.assertEqual(response.status_code, 400)

    def test_unknown_run_404(self) -> None:
        with TestClient(create_app(self.config)) as client:
            self.assertEqual(client.get("/api/runs/nope").status_code, 404)


if __name__ == "__main__":
    unittest.main()
