"""Официальные курсы Национального банка РК: загрузка RSS и хранение в таблице rates."""
import datetime as dt
import logging
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET

from . import db as dbm
from .config import settings

log = logging.getLogger('bala.rates')
RSS = 'https://nationalbank.kz/rss/get_rates.cfm?fdate={}'


def parse_rss(xml_bytes: bytes) -> list[dict]:
    out = []
    for it in ET.fromstring(xml_bytes).iter('item'):
        code = (it.findtext('title') or '').strip()
        rate = (it.findtext('description') or '').strip().replace(',', '.')
        if len(code) == 3 and rate:
            out.append({'code': code, 'name': (it.findtext('fullname') or code).strip(), 'nom': int(float(it.findtext('quant') or 1)), 'rate': float(rate)})
    return out


def fetch_day(day: dt.date) -> list[dict]:
    req = urllib.request.Request(RSS.format(day.strftime('%d.%m.%Y')), headers={'User-Agent': 'BALA-CRM rates'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return parse_rss(r.read())


def store(conn, day: str, items: list[dict]) -> int:
    for x in items:
        conn.execute('INSERT INTO rates (date, code, name, nom, rate) VALUES (?, ?, ?, ?, ?) ON CONFLICT (date, code) DO UPDATE SET rate = excluded.rate, nom = excluded.nom, name = excluded.name',
                     (day, x['code'], x['name'], x['nom'], x['rate']))
    return len(items)


def refresh(conn, days: int = 3) -> dict:
    """Загружает курсы за последние `days` дней, которых ещё нет в базе (сегодня — всегда)."""
    today = (dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) + dt.timedelta(hours=settings.tz_offset_hours)).date()
    have = {r['date'] for r in conn.execute('SELECT DISTINCT date FROM rates')}
    got, errors = 0, []
    for i in range(days):
        day = today - dt.timedelta(days=i)
        if day.isoformat() in have and i:
            continue
        try:
            items = fetch_day(day)
        except Exception as e:  # сеть/формат — пропускаем день
            errors.append(f'{day}: {e}')
            continue
        if items:
            store(conn, day.isoformat(), items)
            got += 1
    return {'days_loaded': got, 'errors': errors}


def latest(conn, history_days: int = 60) -> dict:
    d = conn.execute('SELECT MAX(date) d FROM rates').fetchone()['d']
    if not d:
        return {'date': None, 'rates': {}, 'history': {}}
    since = (dt.date.fromisoformat(d) - dt.timedelta(days=history_days)).isoformat()
    rates = {r['code']: {'name': r['name'], 'nom': r['nom'], 'rate': r['rate']} for r in conn.execute('SELECT * FROM rates WHERE date = ?', (d,))}
    hist: dict = {}
    for r in conn.execute('SELECT date, code, rate FROM rates WHERE date >= ? ORDER BY date', (since,)):
        hist.setdefault(r['code'], []).append([r['date'], r['rate']])
    return {'date': d, 'rates': rates, 'history': hist}


def start_scheduler():
    """Фоновое обновление: при старте (30 дней истории, если база пустая) и каждые 6 часов."""
    def loop():
        first = True
        while True:
            try:
                conn = dbm.connect()
                try:
                    empty = conn.execute('SELECT COUNT(*) c FROM rates').fetchone()['c'] == 0
                    res = refresh(conn, 30 if (first and empty) else 3)
                    log.info('Курсы НБ РК: %s', res)
                finally:
                    conn.close()
            except Exception:
                log.exception('Не удалось обновить курсы')
            first = False
            time.sleep(6 * 3600)
    threading.Thread(target=loop, name='rates', daemon=True).start()
