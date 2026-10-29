#!/usr/bin/env python3
"""Загружает официальные курсы Национального банка РК и обновляет rates.json.

Источник: RSS Нацбанка (тот же курс, что на странице
https://nationalbank.kz/ru/exchangerates/ezhednevnye-oficialnye-rynochnye-kursy-valyut).
При первом запуске добирает историю за последние 30 дней.
"""
import json, os, sys, time, datetime as dt
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, 'app', 'rates.json')
RSS = 'https://nationalbank.kz/rss/get_rates.cfm?fdate={}'
KEEP_DAYS = 400


def fetch(day):
    url = RSS.format(day.strftime('%d.%m.%Y'))
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (umny-zayka rates bot)'})
    with urllib.request.urlopen(req, timeout=30) as r:
        root = ET.fromstring(r.read())
    out = {}
    for it in root.iter('item'):
        code = (it.findtext('title') or '').strip()
        rate = (it.findtext('description') or '').strip().replace(',', '.')
        if len(code) != 3 or not rate:
            continue
        out[code] = {'name': (it.findtext('fullname') or code).strip(), 'nom': int(float(it.findtext('quant') or 1)), 'rate': float(rate)}
    return out


def main():
    data = {'date': None, 'rates': {}, 'history': {}}
    if os.path.exists(PATH):
        with open(PATH, encoding='utf-8') as f:
            data = json.load(f)
    hist = data.setdefault('history', {})
    known = {d for h in hist.values() for d, _ in h}
    today = (dt.datetime.utcnow() + dt.timedelta(hours=5)).date()
    days = [today - dt.timedelta(days=i) for i in range(30 if len(known) < 20 else 3)]
    got = 0
    for day in sorted(days):
        iso = day.isoformat()
        if iso in known and iso != today.isoformat():
            continue
        try:
            rates = fetch(day)
        except Exception as e:  # сеть или формат
            print('не удалось получить', iso, e)
            continue
        if not rates:
            print('пусто за', iso)
            continue
        got += 1
        for code, v in rates.items():
            h = [x for x in hist.get(code, []) if x[0] != iso]
            h.append([iso, v['rate']])
            h.sort()
            hist[code] = h[-KEEP_DAYS:]
        if iso >= (data.get('date') or ''):
            data['date'] = iso
            data['rates'] = rates
        time.sleep(0.5)
    if not got:
        print('новых данных нет')
        return 0
    with open(PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    print('обновлено дней:', got, 'последняя дата:', data['date'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
