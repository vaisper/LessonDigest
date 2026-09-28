from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

from lessondigest.errors import ConfigError

DEFAULT_CONFIG_NAME = "config.yaml"


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    audio_raw: Path
    audio_incoming: Path
    audio_normalized: Path
    transcripts: Path
    digests: Path
    digests_eval: Path
    runs: Path
    prompts: Path
    samples: Path

    @classmethod
    def from_root(cls, root: Path) -> "ProjectPaths":
        root = root.resolve()
        return cls(
            root=root,
            audio_raw=root / "audio" / "raw",
            audio_incoming=root / "audio" / "incoming",
            audio_normalized=root / "audio" / "normalized",
            transcripts=root / "transcripts",
            digests=root / "digests",
            digests_eval=root / "digests" / "_eval",
            runs=root / "runs",
            prompts=root / "prompts",
            samples=root / "samples",
        )

    def ensure(self) -> None:
        for path in (
            self.audio_raw,
            self.audio_incoming,
            self.audio_normalized,
            self.transcripts,
            self.digests,
            self.digests_eval,
            self.runs,
        ):
            path.mkdir(parents=True, exist_ok=True)


class AsrConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    provider: str = "faster_whisper"
    model: str = "small"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str = "ru"
    beam_size: int = 5
    vad: bool = True


class LlmConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    provider: str = "gigachat"
    model: str = "GigaChat-2-Pro"
    prompt_version: str = "v1"
    temperature: float = 0.2
    max_tokens: int = 2048
    timeout_sec: float = 120.0
    verify_ssl: bool = True
    ca_bundle: str | None = None
    oauth_url: str = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    api_url: str = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"


class ChunkingConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    soft_char_limit: int = 24000
    overlap_chars: int = 200
    chars_per_token: float = 2.5


class Secrets(BaseModel):
    model_config = ConfigDict(extra="ignore")

    gigachat_client_id: str | None = None
    gigachat_client_secret: str | None = None
    gigachat_auth_key: str | None = None
    gigachat_scope: str = "GIGACHAT_API_PERS"
    yandex_api_key: str | None = None
    yandex_folder_id: str | None = None
    telegram_bot_token: str | None = None

    def gigachat_credentials(self) -> tuple[str, str]:
        if not self.gigachat_client_id or not self.gigachat_client_secret:
            raise ConfigError(
                "GIGACHAT_CLIENT_ID / GIGACHAT_CLIENT_SECRET не заданы. "
                "Скопируйте .env.example в .env и заполните."
            )
        return self.gigachat_client_id, self.gigachat_client_secret

    def has_gigachat_credentials(self) -> bool:
        return bool(self.gigachat_auth_key) or bool(
            self.gigachat_client_id and self.gigachat_client_secret
        )


SECRET_KEYS = {
    "gigachat_client_id": "GIGACHAT_CLIENT_ID",
    "gigachat_client_secret": "GIGACHAT_CLIENT_SECRET",
    "gigachat_auth_key": "GIGACHAT_AUTH_KEY",
    "gigachat_scope": "GIGACHAT_SCOPE",
    "yandex_api_key": "YANDEX_API_KEY",
    "yandex_folder_id": "YANDEX_FOLDER_ID",
    "telegram_bot_token": "TELEGRAM_BOT_TOKEN",
}


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True)

    paths: ProjectPaths
    asr: AsrConfig = Field(default_factory=AsrConfig)
    llm: LlmConfig = Field(default_factory=LlmConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    secrets: Secrets = Field(default_factory=Secrets)

    @classmethod
    def load(cls, config_path: Path | str | None = None) -> "AppConfig":
        config_path = Path(config_path) if config_path else _discover_config()
        file_dir = config_path.parent.resolve() if config_path.exists() else Path.cwd()

        raw: dict = {}
        if config_path.exists():
            loaded = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            if not isinstance(loaded, dict):
                raise ConfigError(f"{config_path}: ожидался YAML-словарь")
            raw = loaded

        env_file = file_dir / ".env"
        load_dotenv(env_file if env_file.exists() else None, override=False)

        paths_raw = dict(raw.get("paths") or {})
        root_value = os.environ.get("LESSONDIGEST_ROOT") or paths_raw.get("root") or "."
        root = Path(root_value)
        if not root.is_absolute():
            root = (file_dir / root).resolve()
        paths = ProjectPaths.from_root(root)

        llm = LlmConfig.model_validate(raw.get("llm") or {})
        if llm.ca_bundle:
            ca_path = Path(llm.ca_bundle)
            if not ca_path.is_absolute():
                llm.ca_bundle = str((paths.root / ca_path).resolve())

        secrets = Secrets(
            **{field: os.environ.get(env) for field, env in SECRET_KEYS.items() if os.environ.get(env)}
        )

        return cls(
            paths=paths,
            asr=AsrConfig.model_validate(raw.get("asr") or {}),
            llm=llm,
            chunking=ChunkingConfig.model_validate(raw.get("chunking") or {}),
            secrets=secrets,
        )

    def prompt_path(self, version: str | None = None) -> Path:
        return self.paths.prompts / f"{version or self.llm.prompt_version}_digest.txt"

    def load_prompt_template(self, version: str | None = None) -> str:
        path = self.prompt_path(version)
        if not path.exists():
            raise ConfigError(f"Промпт не найден: {path}")
        return path.read_text(encoding="utf-8")


def _discover_config() -> Path:
    env_path = os.environ.get("LESSONDIGEST_CONFIG")
    if env_path:
        return Path(env_path)
    candidate = Path.cwd() / DEFAULT_CONFIG_NAME
    if candidate.exists():
        return candidate
    return Path(__file__).resolve().parents[2] / DEFAULT_CONFIG_NAME
