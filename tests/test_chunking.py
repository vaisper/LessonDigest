from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lessondigest.chunking import chunk_transcript, estimate_tokens  # noqa: E402
from lessondigest.config import ChunkingConfig  # noqa: E402
from lessondigest.domain import TranscriptSegment  # noqa: E402


class ChunkingTest(unittest.TestCase):
    def test_single_chunk(self) -> None:
        config = ChunkingConfig(soft_char_limit=1000)
        result = chunk_transcript("Короткий текст урока.", None, config)
        self.assertEqual(len(result.chunks), 1)
        self.assertTrue(result.strategy.startswith("single"))

    def test_sentences_split(self) -> None:
        text = ". ".join(f"Предложение номер {i}" for i in range(200)) + "."
        config = ChunkingConfig(soft_char_limit=200, overlap_chars=20)
        result = chunk_transcript(text, None, config)
        self.assertGreater(len(result.chunks), 1)
        self.assertEqual(result.strategy, "sentences")
        for i, chunk in enumerate(result.chunks):
            self.assertEqual(chunk.index, i)

    def test_segments_preferred(self) -> None:
        segments = [
            TranscriptSegment(start=0, end=1, text="A" * 120),
            TranscriptSegment(start=1, end=2, text="B" * 120),
        ]
        config = ChunkingConfig(soft_char_limit=150, overlap_chars=0)
        result = chunk_transcript(" ".join(s.text for s in segments), segments, config)
        self.assertEqual(result.strategy, "segments")
        self.assertGreater(len(result.chunks), 1)
        self.assertEqual(result.chunks[0].start_sec, 0)

    def test_estimate_tokens(self) -> None:
        self.assertAlmostEqual(estimate_tokens("abcd", 2.0), 2.0)


if __name__ == "__main__":
    unittest.main()
