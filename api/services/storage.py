import os
from pathlib import Path
from typing import Protocol, runtime_checkable

from api.config import get_settings


@runtime_checkable
class StorageBackend(Protocol):
    async def save(self, key: str, data: bytes, content_type: str) -> None: ...
    async def load(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...
    async def exists(self, key: str) -> bool: ...


class LocalStorageBackend:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)

    def _path(self, key: str) -> Path:
        # Prevent path traversal
        safe = Path(key).name if "/" not in key else key
        if "/" in key:
            parts = key.split("/")
            safe = os.path.join(*[Path(p).name for p in parts])
        return self.base_dir / safe

    async def save(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    async def load(self, key: str) -> bytes:
        path = self._path(key)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {key}")
        return path.read_bytes()

    async def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    async def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def ensure_dir(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)


_storage: StorageBackend | None = None


def get_storage() -> StorageBackend:
    global _storage
    if _storage is None:
        settings = get_settings()
        backend = LocalStorageBackend(settings.upload_dir)
        backend.ensure_dir()
        _storage = backend
    return _storage
