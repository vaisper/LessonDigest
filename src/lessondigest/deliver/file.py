from __future__ import annotations

from pathlib import Path

from lessondigest.deliver.base import open_path
from lessondigest.domain import Digest
from lessondigest.logging_setup import get_logger

log = get_logger("deliver.file")


class FileDeliverer:
    name = "file"

    def __init__(self, *, open_result: bool = False) -> None:
        self.open_result = open_result

    def deliver(
        self, run_id: str, digest: Digest, md_path: Path, json_path: Path
    ) -> dict[str, str]:
        log.info("Дайджест сохранён: %s", md_path)
        if json_path.exists():
            log.debug("JSON дайджеста: %s", json_path)
        if self.open_result:
            open_path(md_path)
        return {"digest_md": str(md_path), "digest_json": str(json_path)}
