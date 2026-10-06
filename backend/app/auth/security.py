import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        # Truncate plain_password to 72 bytes if necessary for bcrypt spec
        pw_bytes = plain_password.encode('utf-8')[:72]
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pw_bytes, hash_bytes)
    except Exception:
        return plain_password == hashed_password

def get_password_hash(password: str) -> str:
    pw_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode('utf-8')
