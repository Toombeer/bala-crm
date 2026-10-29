"""Маршрутизация API: описание эндпоинта в одном месте (метод, путь, права, схема тела),
из него строятся маршруты Starlette и документация OpenAPI."""
import datetime as dt
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import jwt
from pydantic import BaseModel, ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from . import db as dbm
from .config import settings
from .security import caps, read_token

log = logging.getLogger('bala')
PREFIX = '/api/v1'


class ApiError(Exception):
    def __init__(self, status: int, message: str, code: str = 'error'):
        super().__init__(message)
        self.status, self.message, self.code = status, message, code


def not_found(what='Запись'):
    return ApiError(404, f'{what} не найдена', 'not_found')


@dataclass
class Ctx:
    conn: Any
    request: Request
    user: dict | None = None
    query: dict = field(default_factory=dict)

    @property
    def org(self) -> int:
        return self.user['org_id']

    @property
    def uid(self) -> int:
        return self.user['id']

    def can(self, cap: str) -> bool:
        return bool(self.user) and cap in caps(self.user['role'])

    def need(self, cap: str):
        if not self.can(cap):
            raise ApiError(403, 'Недостаточно прав для этого действия', 'forbidden')


@dataclass
class Endpoint:
    method: str
    path: str
    fn: Callable
    cap: str | None
    body: type[BaseModel] | None
    summary: str
    tag: str
    public: bool
    raw: bool


ENDPOINTS: list[Endpoint] = []


def api(method: str, path: str, *, cap: str | None = 'read', body: type[BaseModel] | None = None,
        summary: str = '', tag: str = '', public: bool = False, raw: bool = False):
    def deco(fn):
        ENDPOINTS.append(Endpoint(method, path, fn, cap, body, summary, tag, public, raw))
        return fn
    return deco


def today() -> str:
    return (dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) + dt.timedelta(hours=settings.tz_offset_hours)).date().isoformat()


def now_stamp() -> str:
    return (dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) + dt.timedelta(hours=settings.tz_offset_hours)).strftime('%Y-%m-%dT%H:%M')


def _auth(conn, request: Request) -> dict:
    h = request.headers.get('authorization', '')
    if not h.lower().startswith('bearer '):
        raise ApiError(401, 'Нужно войти в систему', 'unauthorized')
    try:
        p = read_token(h[7:].strip())
    except jwt.ExpiredSignatureError:
        raise ApiError(401, 'Сессия истекла, войдите снова', 'token_expired')
    except jwt.PyJWTError:
        raise ApiError(401, 'Неверный токен', 'unauthorized')
    u = dbm.row(conn.execute('SELECT id, org_id, name, email, phone, role, active, token_version FROM users WHERE id = ?', (int(p['sub']),)).fetchone())
    if not u or not u['active'] or u['token_version'] != p.get('tv', 0) or u['org_id'] != p.get('org'):
        raise ApiError(401, 'Доступ отозван, войдите снова', 'unauthorized')
    return u


def _fmt_validation(e: ValidationError) -> str:
    parts = []
    for err in e.errors():
        loc = '.'.join(str(x) for x in err.get('loc', []) if x != 'body')
        parts.append(f'{loc}: {err.get("msg")}' if loc else err.get('msg', ''))
    return 'Проверьте данные — ' + '; '.join(parts)


def make_route(ep: Endpoint) -> Route:
    async def handler(request: Request):
        started = time.perf_counter()
        body_obj = None
        if ep.body is not None:
            try:
                raw = await request.body()
                data = json.loads(raw or b'{}')
            except ValueError:
                return JSONResponse({'error': 'Тело запроса должно быть JSON', 'code': 'bad_json'}, status_code=400)
            try:
                body_obj = ep.body.model_validate(data)
            except ValidationError as e:
                return JSONResponse({'error': _fmt_validation(e), 'code': 'validation'}, status_code=422)

        def run():
            conn = dbm.connect()
            try:
                ctx = Ctx(conn=conn, request=request, query=dict(request.query_params))
                if not ep.public:
                    ctx.user = _auth(conn, request)
                    if ep.cap:
                        ctx.need(ep.cap)
                kwargs = {k: (int(v) if k.endswith('id') else v) for k, v in request.path_params.items()}
                if body_obj is not None:
                    kwargs['body'] = body_obj
                return ep.fn(ctx, **kwargs)
            finally:
                conn.close()

        try:
            result = await run_in_threadpool(run)
        except ApiError as e:
            return JSONResponse({'error': e.message, 'code': e.code}, status_code=e.status)
        except ValueError as e:
            return JSONResponse({'error': str(e), 'code': 'bad_request'}, status_code=400)
        except Exception:  # pragma: no cover — неожиданная ошибка
            log.exception('Ошибка в %s %s', ep.method, ep.path)
            return JSONResponse({'error': 'Внутренняя ошибка сервера', 'code': 'internal'}, status_code=500)
        finally:
            log.info('%s %s %.1fms', ep.method, request.url.path, (time.perf_counter() - started) * 1000)
        if isinstance(result, Response):
            return result
        status = 201 if ep.method == 'POST' and isinstance(result, dict) and result.get('_created') else 200
        if isinstance(result, dict):
            result.pop('_created', None)
        return JSONResponse(result if result is not None else {'ok': True}, status_code=status)

    return Route(PREFIX + ep.path, handler, methods=[ep.method])


def openapi() -> dict:
    paths: dict = {}
    schemas: dict = {}
    for ep in ENDPOINTS:
        op: dict = {'summary': ep.summary or ep.fn.__name__, 'tags': [ep.tag or 'Общее'], 'responses': {'200': {'description': 'Успешно'}}}
        if not ep.public:
            op['security'] = [{'bearer': []}]
            op['description'] = f'Нужное право: `{ep.cap}`' if ep.cap else 'Любой вошедший пользователь'
            op['responses'].update({'401': {'description': 'Не выполнен вход'}, '403': {'description': 'Нет прав'}})
        params = [{'name': p, 'in': 'path', 'required': True, 'schema': {'type': 'integer' if p.endswith('id') else 'string'}}
                  for p in [s[1:-1] for s in ep.path.split('/') if s.startswith('{')]]
        if params:
            op['parameters'] = params
        if ep.body is not None:
            sch = ep.body.model_json_schema(ref_template='#/components/schemas/{model}')
            for k, v in sch.pop('$defs', {}).items():
                schemas[k] = v
            schemas[ep.body.__name__] = sch
            op['requestBody'] = {'required': True, 'content': {'application/json': {'schema': {'$ref': f'#/components/schemas/{ep.body.__name__}'}}}}
            op['responses']['422'] = {'description': 'Ошибка проверки данных'}
        paths.setdefault(PREFIX + ep.path, {})[ep.method.lower()] = op
    return {
        'openapi': '3.1.0',
        'info': {'title': 'BALA CRM API', 'version': '1.0.0', 'description': 'API CRM для детских центров. Авторизация: `Authorization: Bearer <токен>` из /auth/login или /auth/register.'},
        'paths': paths,
        'components': {'schemas': schemas, 'securitySchemes': {'bearer': {'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT'}}},
    }
