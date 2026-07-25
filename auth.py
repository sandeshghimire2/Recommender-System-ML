"""
Minimal username/password auth backed by the `users` table.
Passwords are hashed with bcrypt before being stored — never stored in plaintext.
"""

import bcrypt

from database import get_session, User


def register_user(username: str, password: str):
    """Returns (success: bool, message: str)."""
    username = username.strip()
    session = get_session()
    try:
        if not username or not password:
            return False, "Username and password are required."
        if len(password) < 6:
            return False, "Password must be at least 6 characters."
        if session.query(User).filter_by(username=username).first():
            return False, "Username already taken."

        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        session.add(User(username=username, password_hash=hashed))
        session.commit()
        return True, "Account created — you can log in now."
    finally:
        session.close()


def authenticate_user(username: str, password: str):
    """Returns the user's id on success, or None on failure."""
    session = get_session()
    try:
        user = session.query(User).filter_by(username=username.strip()).first()
        if not user:
            return None
        if bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            return user.id
        return None
    finally:
        session.close()
