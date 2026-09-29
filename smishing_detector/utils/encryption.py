"""
utils/encryption.py — AES-256-CBC encrypt/decrypt for secure API communication.

Shared key is stored in .env as SMS_ENCRYPTION_KEY (64-char hex = 32 bytes).
Mobile encrypts SMS body with the same key before sending to /predict_secure.
"""

import os
import base64
import secrets
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from dotenv import load_dotenv

load_dotenv()

# 32-byte (256-bit) key from env — generate once with:
#   python -c "import os; print(os.urandom(32).hex())"
def _load_key_hex() -> str:
    key_hex = os.getenv("SMS_ENCRYPTION_KEY")
    if not key_hex:
        # Fallback to known default so mobile and server stay in sync
        # when .env is not yet configured. Set SMS_ENCRYPTION_KEY in .env
        # before deploying to production.
        key_hex = "5fc5555dfd4b23ecfbfbfda273cb82eb5fdfb8b25c5b1357a2568d6afa1f472e"
        print("Warning: SMS_ENCRYPTION_KEY not set in .env; using built-in dev key.")
    if len(key_hex) != 64:
        raise ValueError("SMS_ENCRYPTION_KEY must be a 64-character hex string.")
    bytes.fromhex(key_hex)  # validate it's valid hex
    return key_hex


_KEY_HEX = _load_key_hex()


def get_key() -> bytes:
    return bytes.fromhex(_KEY_HEX)


def decrypt_message(encrypted_b64: str) -> str:
    """
    Decrypt a base64-encoded AES-256-CBC ciphertext.
    Format: base64(IV[16] + ciphertext)
    Matching encrypt_message() in mobile src/utils/encryption.js
    """
    data = base64.b64decode(encrypted_b64)
    iv         = data[:16]
    ciphertext = data[16:]
    key        = get_key()

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()

    # Remove PKCS7 padding
    pad_len = padded[-1]
    return padded[:-pad_len].decode("utf-8")


def encrypt_message(plaintext: str) -> str:
    """
    Encrypt a string with AES-256-CBC (for testing / server-to-client responses).
    Returns base64(IV[16] + ciphertext).
    """
    key = get_key()
    iv  = secrets.token_bytes(16)

    # PKCS7 padding
    raw = plaintext.encode("utf-8")
    pad = 16 - (len(raw) % 16)
    raw += bytes([pad] * pad)

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(raw) + encryptor.finalize()

    return base64.b64encode(iv + ciphertext).decode("utf-8")


def get_key_hex() -> str:
    """Return current key as hex — sent to client on /api/encryption-key."""
    return _KEY_HEX
