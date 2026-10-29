"""Пароли (scrypt), токены (JWT) и права ролей."""
import base64
import datetime as dt
import hashlib
import hmac
import os
import secrets

import jwt

from .config import settings

SCRYPT = dict(n=2 ** 14, r=8, p=1, dklen=32)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, **SCRYPT)
    return 'scrypt$' + base64.b64encode(salt).decode() + '$' + base64.b64encode(dk).decode()


def check_password(password: str, stored: str) -> bool:
    try:
        _, s, h = stored.split('$')
        dk = hashlib.scrypt(password.encode(), salt=base64.b64decode(s), **SCRYPT)
        return hmac.compare_digest(dk, base64.b64decode(h))
    except (ValueError, TypeError):
        return False


def make_token(user: dict) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {'sub': str(user['id']), 'org': user['org_id'], 'role': user['role'], 'tv': user.get('token_version', 0),
               'iat': now, 'exp': now + dt.timedelta(hours=settings.token_hours)}
    return jwt.encode(payload, settings.secret, algorithm='HS256')


def read_token(token: str) -> dict:
    return jwt.decode(token, settings.secret, algorithms=['HS256'])


def new_public_token() -> str:
    return secrets.token_urlsafe(18)


# Права. Владелец может всё; остальные роли — набор возможностей.
CAPS = {
    'owner': {'read', 'attendance', 'students', 'groups', 'leads', 'tasks', 'billing', 'finance', 'settings', 'staff', 'data'},
    'admin': {'read', 'attendance', 'students', 'groups', 'leads', 'tasks', 'billing', 'finance', 'settings'},
    'manager': {'read', 'students', 'leads', 'tasks'},
    'teacher': {'read', 'attendance', 'tasks'},
    'accountant': {'read', 'billing', 'finance'},
}
ROLE_NAMES = {'owner': 'Владелец', 'admin': 'Администратор', 'manager': 'Менеджер', 'teacher': 'Педагог', 'accountant': 'Бухгалтер'}


def caps(role: str) -> set[str]:
    return CAPS.get(role, set())
