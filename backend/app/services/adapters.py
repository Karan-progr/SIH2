from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, AsyncIterator


class BaseSocialAdapter(ABC):
    platform = "unknown"

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def health_check(self) -> dict[str, Any]: ...

    @abstractmethod
    async def fetch_recent(self, limit: int = 100) -> list[dict[str, Any]]: ...

    async def stream_events(self) -> AsyncIterator[dict[str, Any]]:
        if False:
            yield {}

    def normalize_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload


class ConfiguredAdapter(BaseSocialAdapter):
    def __init__(self, platform: str, required_env: tuple[str, ...]):
        self.platform = platform
        self.required_env = required_env

    @property
    def configured(self) -> bool:
        return all(os.getenv(key) for key in self.required_env)

    async def connect(self) -> None:
        return None

    async def health_check(self) -> dict[str, Any]:
        return {"platform": self.platform, "status": "connected" if self.configured else "not_configured", "synthetic": False}

    async def fetch_recent(self, limit: int = 100) -> list[dict[str, Any]]:
        return []


class XAdapter(ConfiguredAdapter):
    def __init__(self):
        super().__init__("x", ("X_BEARER_TOKEN",))


class TelegramAdapter(ConfiguredAdapter):
    def __init__(self):
        super().__init__("telegram", ("TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TELEGRAM_BOT_TOKEN"))


class DemoDataAdapter(BaseSocialAdapter):
    platform = "demo"

    async def connect(self) -> None:
        return None

    async def health_check(self) -> dict[str, Any]:
        return {"platform": "demo", "status": "active", "synthetic": True}

    async def fetch_recent(self, limit: int = 100) -> list[dict[str, Any]]:
        return []

