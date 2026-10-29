#!/usr/bin/env python3
"""Генерирует docs/API.md и docs/openapi.json из описания эндпоинтов."""
import json
import os
import sys

os.environ.setdefault('BALA_DB', ':memory:')
os.environ.setdefault('BALA_RATES_AUTO', '0')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from bala import api  # noqa: E402,F401
from bala.core import ENDPOINTS, PREFIX, openapi  # noqa: E402
from bala.security import CAPS, ROLE_NAMES  # noqa: E402

out = ['# BALA CRM API', '', 'Базовый адрес: `/api/v1`. Формат: JSON. Авторизация: заголовок `Authorization: Bearer <токен>` из `/auth/login` или `/auth/register`.',
       'Интерактивная документация на работающем сервере: `/api/docs` (Swagger UI), схема: `/api/openapi.json`.', '',
       'Ошибки возвращаются как `{"error": "текст для человека", "code": "машинный_код"}` с HTTP-статусом 4xx/5xx.', '', '## Роли и права', '',
       '| Роль | Права |', '| --- | --- |']
out += [f'| {ROLE_NAMES[r]} (`{r}`) | {", ".join(sorted(c))} |' for r, c in CAPS.items()]
tags: dict = {}
for ep in ENDPOINTS:
    tags.setdefault(ep.tag or 'Общее', []).append(ep)
for tag, eps in tags.items():
    out += ['', f'## {tag}', '', '| Метод | Путь | Право | Описание |', '| --- | --- | --- | --- |']
    for ep in eps:
        out.append(f'| `{ep.method}` | `{PREFIX}{ep.path}` | {"публично" if ep.public else (ep.cap or "любой вход")} | {ep.summary} |')
os.makedirs(os.path.join(ROOT, 'docs'), exist_ok=True)
open(os.path.join(ROOT, 'docs', 'API.md'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
json.dump(openapi(), open(os.path.join(ROOT, 'docs', 'openapi.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('docs/API.md:', len(ENDPOINTS), 'эндпоинтов')
