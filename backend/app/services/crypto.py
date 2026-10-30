"""
encryption for the qpi keys
"""
from cryptography.fernet import Fernet
from flask import current_app


def _fernet() -> Fernet:
    key = current_app.config.get("FERNET_KEY")
    if not key:
        raise RuntimeError(
            "FERNET_KEY is not set. Generate one with:\n"
            '  python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"\n'
            "and put it in your .env as FERNET_KEY=..."
        )
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    """Encrypt a secret for storage. Returns a str (Fernet token)."""
    if plaintext is None:
        raise ValueError("Cannot encrypt None")
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a stored secret back to plaintext. Call-time only."""
    if token is None:
        raise ValueError("Cannot decrypt None")
    if isinstance(token, str):
        token = token.encode()
    return _fernet().decrypt(token).decode()
