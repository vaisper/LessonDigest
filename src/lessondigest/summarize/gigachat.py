from __future__ import annotations

import base64
import time
import uuid

import httpx

from lessondigest.config import LlmConfig, Secrets
from lessondigest.errors import LlmError
from lessondigest.logging_setup import get_logger
from lessondigest.summarize.base import LlmOptions, LlmResult

log = get_logger("summarize.gigachat")


def _is_authorization_key(value: str) -> bool:
    try:
        decoded = base64.b64decode(value, validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return False
    return ":" in decoded


class GigaChatLlm:
    name = "gigachat"

    def __init__(self, config: LlmConfig, secrets: Secrets) -> None:
        self.config = config
        self.secrets = secrets
        self._token: str | None = None
        self._expires_at: float = 0.0

    def _verify(self) -> bool | str:
        if self.config.ca_bundle:
            return self.config.ca_bundle
        return self.config.verify_ssl

    def _basic_header_value(self) -> str:
        if self.secrets.gigachat_auth_key:
            return self.secrets.gigachat_auth_key
        client_id, client_secret = self.secrets.gigachat_credentials()
        if _is_authorization_key(client_secret):
            return client_secret
        return base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    def _get_token(self, force: bool = False) -> str:
        if not force and self._token and time.time() < self._expires_at - 30:
            return self._token

        basic = self._basic_header_value()
        headers = {
            "Authorization": f"Basic {basic}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        data = {"scope": self.secrets.gigachat_scope}
        try:
            response = httpx.post(
                self.config.oauth_url,
                headers=headers,
                data=data,
                timeout=self.config.timeout_sec,
                verify=self._verify(),
            )
        except httpx.HTTPError as exc:
            raise LlmError(f"GigaChat OAuth недоступен: {exc}") from exc
        if response.status_code >= 400:
            raise LlmError(f"GigaChat OAuth {response.status_code}: {response.text[:300]}")
        payload = response.json()

        token = payload.get("access_token")
        if not token:
            raise LlmError("GigaChat OAuth не вернул access_token")
        self._token = token
        self._expires_at = float(payload.get("expires_at", 0)) / 1000.0 or (time.time() + 1500)
        log.debug("GigaChat access_token получен, истекает в %.0f", self._expires_at)
        return token

    def complete(self, prompt: str, options: LlmOptions) -> LlmResult:
        started = time.perf_counter()
        payload = {
            "model": options.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": options.temperature,
            "max_tokens": options.max_tokens,
        }
        response = self._post_chat(payload, options)
        if response.status_code in {401, 403}:
            log.info("GigaChat token истёк — обновляю")
            self._get_token(force=True)
            response = self._post_chat(payload, options)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = response.text[:500]
            raise LlmError(f"GigaChat вернул {response.status_code}: {body}") from exc

        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise LlmError("GigaChat вернул пустой choices")
        text = ((choices[0].get("message") or {}).get("content") or "").strip()
        if not text:
            raise LlmError("GigaChat вернул пустой ответ")

        usage = data.get("usage") or {}
        return LlmResult(
            text=text,
            model=data.get("model") or options.model,
            tokens_in=usage.get("prompt_tokens"),
            tokens_out=usage.get("completion_tokens"),
            elapsed_sec=time.perf_counter() - started,
        )

    def _post_chat(self, payload: dict, options: LlmOptions) -> httpx.Response:
        token = self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            return httpx.post(
                self.config.api_url,
                headers=headers,
                json=payload,
                timeout=options.timeout_sec,
                verify=self._verify(),
            )
        except httpx.HTTPError as exc:
            raise LlmError(f"GigaChat API недоступен: {exc}") from exc
