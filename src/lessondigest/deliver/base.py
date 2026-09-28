from __future__ import annotations

import sys
from pathlib import Path
from typing import Protocol, runtime_checkable

from lessondigest.domain import Digest


@runtime_checkable
class Deliverer(Protocol):
    name: str

    def deliver(
        self, run_id: str, digest: Digest, md_path: Path, json_path: Path
    ) -> dict[str, str]: ...


def open_path(path: Path) -> None:
    try:
        if sys.platform.startswith("win"):
            import os

            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            import subprocess

            subprocess.run(["open", str(path)], check=False)
        else:
            import subprocess

            subprocess.run(["xdg-open", str(path)], check=False)
    except OSError:
        pass
