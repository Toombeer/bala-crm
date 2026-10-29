#!/usr/bin/env python3
"""Горячая резервная копия базы SQLite без остановки сервера.

Пример (cron, каждую ночь): 0 3 * * * docker compose exec -T app python scripts/backup.py /data/backups
Хранит последние 30 копий.
"""
import datetime as dt
import os
import sqlite3
import sys

src = os.getenv('BALA_DB', '/data/bala.db')
dst_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(src), 'backups')
os.makedirs(dst_dir, exist_ok=True)
dst = os.path.join(dst_dir, 'bala-' + dt.datetime.now().strftime('%Y%m%d-%H%M%S') + '.db')
with sqlite3.connect(src) as s, sqlite3.connect(dst) as d:
    s.backup(d)
old = sorted(f for f in os.listdir(dst_dir) if f.startswith('bala-') and f.endswith('.db'))[:-30]
for f in old:
    os.remove(os.path.join(dst_dir, f))
print('Копия:', dst)
