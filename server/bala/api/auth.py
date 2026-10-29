"""Регистрация центра, вход, профиль, смена пароля."""
import time
from collections import defaultdict, deque

from ..config import settings
from ..core import ApiError, api
from ..db import row, tx
from ..schemas import LoginIn, PasswordIn, RegisterIn
from ..security import ROLE_NAMES, caps, check_password, hash_password, make_token
from ..services import create_org, log_event

_attempts: dict[str, deque] = defaultdict(deque)
WINDOW = 15 * 60


def _throttle(ip: str):
    q, now = _attempts[ip], time.time()
    while q and now - q[0] > WINDOW:
        q.popleft()
    if len(q) >= settings.login_attempts:
        raise ApiError(429, 'Слишком много попыток входа. Подождите 15 минут.', 'rate_limited')
    q.append(now)


def _session(u: dict) -> dict:
    return {'token': make_token(u), 'user': {'id': u['id'], 'name': u['name'], 'email': u['email'], 'role': u['role'], 'role_name': ROLE_NAMES[u['role']], 'caps': sorted(caps(u['role']))}}


@api('POST', '/auth/register', body=RegisterIn, public=True, tag='Вход', summary='Зарегистрировать центр и владельца')
def register(ctx, body: RegisterIn):
    _throttle(ctx.request.client.host if ctx.request.client else '?')
    if ctx.conn.execute('SELECT 1 FROM users WHERE email = ?', (body.email,)).fetchone():
        raise ApiError(409, 'Этот email уже зарегистрирован. Войдите или используйте другой.', 'email_taken')
    with tx(ctx.conn):
        org = create_org(ctx.conn, body.center_name, body.city)
        uid = ctx.conn.execute('INSERT INTO users (org_id, name, email, role, pass_hash) VALUES (?, ?, ?, ?, ?)',
                               (org, body.name, body.email.lower(), 'owner', hash_password(body.password))).lastrowid
        log_event(ctx.conn, org, None, None, f'Центр «{body.center_name}» создан', 'event', uid)
    u = row(ctx.conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone())
    return {**_session(u), '_created': True}


@api('POST', '/auth/login', body=LoginIn, public=True, tag='Вход', summary='Войти по email и паролю')
def login(ctx, body: LoginIn):
    _throttle(ctx.request.client.host if ctx.request.client else '?')
    u = row(ctx.conn.execute('SELECT * FROM users WHERE email = ?', (body.email.lower(),)).fetchone())
    if not u or not check_password(body.password, u['pass_hash']):
        raise ApiError(401, 'Неверный email или пароль', 'bad_credentials')
    if not u['active']:
        raise ApiError(403, 'Доступ отключён владельцем центра', 'inactive')
    return _session(u)


@api('GET', '/auth/me', cap=None, tag='Вход', summary='Текущий пользователь')
def me(ctx):
    u = ctx.user
    return {'id': u['id'], 'name': u['name'], 'email': u['email'], 'role': u['role'], 'role_name': ROLE_NAMES[u['role']], 'caps': sorted(caps(u['role'])), 'org_id': u['org_id']}


@api('POST', '/auth/password', cap=None, body=PasswordIn, tag='Вход', summary='Сменить свой пароль (все сессии завершаются)')
def change_password(ctx, body: PasswordIn):
    u = row(ctx.conn.execute('SELECT * FROM users WHERE id = ?', (ctx.uid,)).fetchone())
    if not check_password(body.old_password, u['pass_hash']):
        raise ApiError(400, 'Текущий пароль неверный', 'bad_credentials')
    ctx.conn.execute('UPDATE users SET pass_hash = ?, token_version = token_version + 1 WHERE id = ?', (hash_password(body.new_password), ctx.uid))
    u = row(ctx.conn.execute('SELECT * FROM users WHERE id = ?', (ctx.uid,)).fetchone())
    return _session(u)


@api('POST', '/auth/logout-all', cap=None, tag='Вход', summary='Завершить все сессии на всех устройствах')
def logout_all(ctx):
    ctx.conn.execute('UPDATE users SET token_version = token_version + 1 WHERE id = ?', (ctx.uid,))
    return {'ok': True}
