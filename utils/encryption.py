import os
from cryptography.fernet import Fernet

KEY_FILE = "config/secret.key"

def get_or_create_key():
    if not os.path.exists("config"):
        os.makedirs("config")
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as key_file:
            key_file.write(key)
    with open(KEY_FILE, "rb") as key_file:
        return key_file.read()

cipher_suite = Fernet(get_or_create_key())

def encrypt_password(password: str) -> bytes:
    return cipher_suite.encrypt(password.encode())

def decrypt_password(encrypted_password: bytes) -> str:
    return cipher_suite.decrypt(encrypted_password).decode()