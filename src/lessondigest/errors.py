from __future__ import annotations


class LessonDigestError(Exception):
    exit_code = 1


class ValidationError(LessonDigestError):
    exit_code = 2


class StageError(LessonDigestError):
    stage = "unknown"
    exit_code = 1

    def __init__(self, message: str, *, stage: str | None = None) -> None:
        super().__init__(message)
        if stage is not None:
            self.stage = stage


class IngestError(StageError):
    stage = "ingest"
    exit_code = 2


class AsrError(StageError):
    stage = "asr"
    exit_code = 3


class LlmError(StageError):
    stage = "summarize"
    exit_code = 4


class ConfigError(LessonDigestError):
    exit_code = 2


class MissingArtifactError(StageError):
    exit_code = 2
