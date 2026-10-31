import bcrypt

# bcrypt only uses the first 72 bytes of a password. bcrypt>=5 raises instead of
# silently truncating, so registration enforces this limit (see schemas.UserCreate)
# and verification truncates defensively for hashes made by older versions.
BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:BCRYPT_MAX_BYTES], bcrypt.gensalt()).decode("ascii")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8")[:BCRYPT_MAX_BYTES],
            hashed_password.encode("ascii"),
        )
    except ValueError:
        # Malformed hash in the database.
        return False
