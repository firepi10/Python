"""At-rest encryption for stored app-specific passwords.

A Fernet key is generated on first use and kept in DATA_DIR/secrets/ with
0600 permissions. This protects the SQLite file from casual copying; anyone
with root on the device can of course still recover secrets.
"""

from pathlib import Path

from cryptography.fernet import Fernet

from app.core.config import get_settings

_cached: Fernet | None = None


def _key_path() -> Path:
    return get_settings().data_dir / "secrets" / "fernet.key"


def get_fernet() -> Fernet:
    global _cached
    if _cached is not None:
        return _cached
    path = _key_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        key = path.read_bytes()
    else:
        key = Fernet.generate_key()
        path.touch(mode=0o600)
        path.write_bytes(key)
        path.chmod(0o600)
    _cached = Fernet(key)
    return _cached


def reset_fernet_cache() -> None:
    global _cached
    _cached = None


def encrypt(plaintext: str) -> bytes:
    return get_fernet().encrypt(plaintext.encode())


def decrypt(token: bytes) -> str:
    return get_fernet().decrypt(token).decode()
