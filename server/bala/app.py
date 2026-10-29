"""Сборка приложения: маршруты API, документация, веб-клиент, безопасность, фоновые задачи."""
import contextlib
import logging
import os

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse, HTMLResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import api  # noqa: F401 — регистрирует эндпоинты
from . import db as dbm
from . import rates as ratesm
from .config import settings
from .core import ENDPOINTS, PREFIX, make_route, openapi

logging.basicConfig(level=os.getenv('BALA_LOG', 'INFO'), format='%(asctime)s %(levelname)s %(name)s: %(message)s')

DOCS = '''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>BALA CRM API</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui.css"></head><body><div id="ui"></div>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
<script>SwaggerUIBundle({url: '/api/openapi.json', dom_id: '#ui', persistAuthorization: true});</script></body></html>'''


class SecurityHeaders:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)

        async def wrapped(msg):
            if msg['type'] == 'http.response.start':
                h = msg.setdefault('headers', [])
                h += [(b'x-content-type-options', b'nosniff'), (b'referrer-policy', b'strict-origin-when-cross-origin'),
                      (b'x-frame-options', b'DENY'), (b'permissions-policy', b'camera=(), microphone=(), geolocation=()')]
                if scope['path'].startswith('/api/'):
                    h.append((b'cache-control', b'no-store'))
            await send(msg)
        await self.app(scope, receive, wrapped)


def create_app(run_background: bool = True) -> Starlette:
    conn = dbm.connect()
    try:
        applied = dbm.migrate(conn)
        if applied:
            logging.getLogger('bala').info('Миграции применены: %s', applied)
    finally:
        conn.close()

    async def openapi_json(request):
        return JSONResponse(openapi())

    async def docs(request):
        return HTMLResponse(DOCS)

    async def not_found_api(request):
        return JSONResponse({'error': 'Такого адреса API нет. Список — /api/docs', 'code': 'not_found'}, status_code=404)

    routes = [make_route(ep) for ep in ENDPOINTS]
    routes += [Route('/api/openapi.json', openapi_json), Route('/api/docs', docs), Route(PREFIX + '/{rest:path}', not_found_api, methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])]
    if os.path.isdir(settings.web_dir):
        index = os.path.join(settings.web_dir, 'index.html')

        async def spa(request):
            return FileResponse(index, headers={'cache-control': 'no-cache'})
        routes += [Route('/', spa), Route('/p/{token}', spa), Mount('/', StaticFiles(directory=settings.web_dir, html=True), name='web')]

    middleware = [Middleware(SecurityHeaders)]
    if settings.cors_origins:
        middleware.append(Middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=['*'], allow_headers=['authorization', 'content-type']))

    @contextlib.asynccontextmanager
    async def lifespan(app):
        if run_background and settings.rates_auto:
            ratesm.start_scheduler()
        yield

    return Starlette(routes=routes, middleware=middleware, lifespan=lifespan)


app = create_app()
