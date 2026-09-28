from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class RunStatus(str, Enum):
    CREATED = "created"
    INGESTING = "ingesting"
    ASR_RUNNING = "asr_running"
    ASR_DONE = "asr_done"
    SUMMARIZING = "summarizing"
    DIGEST_READY = "digest_ready"
    DELIVERED = "delivered"
    FAILED = "failed"


class HomeworkConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ABSENT = "absent"


class MediaInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    duration_sec: float | None = None
    sample_rate: int | None = None
    channels: int | None = None
    codec: str | None = None
    format_name: str | None = None


class TranscriptSegment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    start: float
    end: float
    text: str


class TranscriptResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str
    segments: list[TranscriptSegment] | None = None
    language: str = "ru"
    provider: str = ""
    model: str = ""
    elapsed_sec: float = 0.0

    def char_count(self) -> int:
        return len(self.text)


class Chunk(BaseModel):
    model_config = ConfigDict(extra="ignore")

    index: int
    text: str
    start_sec: float | None = None
    end_sec: float | None = None


class ChunkingResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    chunks: list[Chunk]
    strategy: str


class Digest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    topic: str = ""
    concepts: list[str] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)
    formulas: list[str] = Field(default_factory=list)
    homework: str | None = None
    homework_confidence: HomeworkConfidence = HomeworkConfidence.ABSENT
    questions: list[str] = Field(default_factory=list)
    prompt_version: str = ""
    model: str = ""


class HumanEvaluation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    run_id: str
    usefulness_1_to_5: int | None = None
    homework_correct: bool | None = None
    notes: str = ""
    evaluator: str = ""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class RunMeta(BaseModel):
    model_config = ConfigDict(extra="ignore")

    run_id: str
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    subject: str = "lesson"
    status: RunStatus = RunStatus.CREATED
    progress: float | None = None
    progress_stage: str | None = None

    source_original_name: str = ""
    checksum_sha256: str = ""
    duration_sec: float | None = None
    media: MediaInfo = Field(default_factory=MediaInfo)

    audio_raw: str | None = None
    audio_normalized: str | None = None
    transcript_txt: str | None = None
    transcript_segments: str | None = None
    chunks_json: str | None = None
    digest_md: str | None = None
    digest_json: str | None = None

    asr_provider: str = ""
    asr_model: str = ""
    llm_provider: str = ""
    llm_model: str = ""
    prompt_version: str = ""

    timings: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
