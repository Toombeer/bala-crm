"""Бизнес-логика: история, автоматизация, распределение оплат, журнал, состояние центра."""
import datetime as dt
import json

from .core import ApiError, not_found, now_stamp, today
from .db import jload, row, rows, tx
from .security import ROLE_NAMES, new_public_token

DEFAULT_SETTINGS = {'price': 3000, 'pack': 8, 'sib2': 10, 'sib3': 15, 'tax': 4, 'kaspi_point': '', 'kaspi_link': '', 'instagram': '', 'sel_cur': ['USD', 'RUB']}
DEFAULT_TEMPLATES = [
    ('Ответ на заявку', 'Здравствуйте, {родитель}! Это {центр}. Спасибо за интерес к занятиям. Подскажите, сколько лет ребёнку и какое направление интересует? Пригласим на бесплатное пробное занятие.'),
    ('Напоминание о пробном', 'Здравствуйте, {родитель}! Напоминаем о пробном занятии в {центр}. Ждём вас!'),
    ('Как прошло пробное', 'Здравствуйте, {родитель}! Как прошло пробное занятие? Если понравилось, подберём удобную группу и оформим абонемент.'),
    ('Напоминание об оплате', 'Здравствуйте, {родитель}! Напоминаем об оплате занятий в {центр}: {долг}. {kaspi}'),
    ('Скоро закончится абонемент', 'Здравствуйте, {родитель}! Абонемент: {ребёнок}, осталось занятий: {остаток}. Продлеваем?'),
    ('Пропуск занятия', 'Здравствуйте, {родитель}! Сегодня {ребёнок} не пришёл(ла) на занятие. Всё хорошо? Можем подобрать отработку.'),
]
# (триггер, задача, через дней, номер шаблона в DEFAULT_TEMPLATES)
DEFAULT_RULES = [('lead0', 'Ответить на заявку', 0, 0), ('lead2', 'Напомнить о пробном занятии', 0, 1), ('lead2', 'Узнать впечатления после пробного', 2, 2),
                 ('kidlow', 'Предложить продление абонемента', 0, 4), ('absent', 'Узнать причину пропуска', 0, 5), ('invoice', 'Проверить оплату счёта', 3, 3)]
STAGES = ['Новая', 'Связались', 'Пробное', 'Купил', 'Отказ']
METHODS = {'cash': 'Наличные', 'kaspi': 'Kaspi', 'transfer': 'Перевод'}


def add_days(d: str, n: int) -> str:
    return (dt.date.fromisoformat(d) + dt.timedelta(days=n)).isoformat()


# ---------- центр ----------
def org_settings(conn, org: int) -> dict:
    o = conn.execute('SELECT settings FROM orgs WHERE id = ?', (org,)).fetchone()
    return {**DEFAULT_SETTINGS, **jload(o['settings'] if o else '{}', {})}


def create_org(conn, name: str, city: str) -> int:
    cur = conn.execute('INSERT INTO orgs (name, city, settings) VALUES (?, ?, ?)', (name, city, json.dumps(DEFAULT_SETTINGS, ensure_ascii=False)))
    org = cur.lastrowid
    tpl_ids = [conn.execute('INSERT INTO templates (org_id, name, text) VALUES (?, ?, ?)', (org, n, t)).lastrowid for n, t in DEFAULT_TEMPLATES]
    for trig, task, days, ti in DEFAULT_RULES:
        conn.execute('INSERT INTO rules (org_id, trigger, task, days, tpl_id) VALUES (?, ?, ?, ?, ?)', (org, trig, task, days, tpl_ids[ti]))
    return org


def get_owned(conn, table: str, org: int, id_: int, what: str = 'Запись') -> dict:
    r = row(conn.execute(f'SELECT * FROM {table} WHERE id = ? AND org_id = ?', (id_, org)).fetchone())
    if not r:
        raise not_found(what)
    return r


# ---------- история и задачи ----------
def log_event(conn, org: int, ref_type, ref_id, text: str, type_: str = 'event', user_id=None):
    conn.execute('INSERT INTO events (org_id, at, ref_type, ref_id, type, text, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
                 (org, now_stamp(), ref_type, ref_id, type_, text[:2000], user_id))


def add_task(conn, org: int, title: str, days: int, ref_type=None, ref_id=None, tpl_id=None, auto=True):
    if ref_type and conn.execute('SELECT 1 FROM tasks WHERE org_id = ? AND done = 0 AND title = ? AND ref_type = ? AND ref_id = ?',
                                 (org, title, ref_type, ref_id)).fetchone():
        return None
    return conn.execute('INSERT INTO tasks (org_id, title, due, ref_type, ref_id, tpl_id, auto, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                        (org, title, add_days(today(), days or 0), ref_type, ref_id, tpl_id, 1 if auto else 0, today())).lastrowid


def run_rules(conn, org: int, trigger: str, ref_type, ref_id, label: str = ''):
    for r in conn.execute('SELECT * FROM rules WHERE org_id = ? AND trigger = ?', (org, trigger)).fetchall():
        add_task(conn, org, r['task'] + (': ' + label if label else ''), r['days'], ref_type, ref_id, r['tpl_id'])


# ---------- деньги ----------
def debt_of(conn, org: int, fid: int) -> int:
    inv = conn.execute('SELECT COALESCE(SUM(amount), 0) s FROM invoices WHERE org_id = ? AND family_id = ?', (org, fid)).fetchone()['s']
    paid = conn.execute('SELECT COALESCE(SUM(amount), 0) s FROM payments WHERE org_id = ? AND family_id = ?', (org, fid)).fetchone()['s']
    return max(0, inv - paid)


def allocate(conn, org: int, fid: int | None):
    """Распределяет все оплаты семьи по счетам от старых к новым. Полностью оплаченный счёт
    один раз добавляет занятия детям из счёта и переводит пробных в активные."""
    if not fid:
        return
    left = conn.execute('SELECT COALESCE(SUM(amount), 0) s FROM payments WHERE org_id = ? AND family_id = ?', (org, fid)).fetchone()['s']
    for inv in conn.execute('SELECT * FROM invoices WHERE org_id = ? AND family_id = ? ORDER BY date, id', (org, fid)).fetchall():
        cov = min(max(left, 0), inv['amount'])
        left -= cov
        conn.execute('UPDATE invoices SET paid = ? WHERE id = ?', (cov, inv['id']))
        if cov >= inv['amount'] and not inv['applied']:
            conn.execute('UPDATE invoices SET applied = 1 WHERE id = ?', (inv['id'],))
            for kid in jload(inv['kids'], []):
                conn.execute("UPDATE kids SET lessons_left = lessons_left + ?, status = CASE WHEN status = 'trial' THEN 'active' ELSE status END WHERE id = ? AND org_id = ?",
                             (inv['lessons'], kid, org))


def price_of(conn, org: int, gid, st: dict) -> int:
    if gid:
        g = conn.execute('SELECT price FROM groups WHERE id = ? AND org_id = ?', (gid, org)).fetchone()
        if g and g['price']:
            return g['price']
    return st['price']


def quote(conn, org: int, kid_ids: list[int], lessons: int, extra: float = 0) -> dict:
    st = org_settings(conn, org)
    ks = [row(conn.execute('SELECT id, group_id FROM kids WHERE id = ? AND org_id = ?', (k, org)).fetchone()) for k in sorted(set(kid_ids))]
    base = fam = 0
    for i, k in enumerate([k for k in ks if k]):
        b = lessons * price_of(conn, org, k['group_id'], st)
        base += b
        fam += b * (1 if i == 0 else 1 - st['sib2'] / 100 if i == 1 else 1 - st['sib3'] / 100)
    ex = fam * extra / 100
    return {'base': round(base), 'sibling_discount': round(base - fam), 'extra_discount': round(ex), 'total': round(fam - ex)}


# ---------- журнал ----------
USED = ('was', 'late')


def set_marks(conn, org: int, user_id: int, date: str, gid: int, marks: dict) -> dict:
    get_owned(conn, 'groups', org, gid, 'Группа')
    changed = 0
    for kid, st in marks.items():
        k = row(conn.execute('SELECT * FROM kids WHERE id = ? AND org_id = ?', (kid, org)).fetchone())
        if not k:
            raise not_found('Ученик')
        prev = conn.execute('SELECT status FROM attendance WHERE org_id = ? AND date = ? AND group_id = ? AND kid_id = ?', (org, date, gid, kid)).fetchone()
        prev = prev['status'] if prev else None
        if prev == st:
            continue
        delta = (1 if prev in USED else 0) - (1 if st in USED else 0)
        if st is None:
            conn.execute('DELETE FROM attendance WHERE org_id = ? AND date = ? AND group_id = ? AND kid_id = ?', (org, date, gid, kid))
        else:
            conn.execute('INSERT INTO attendance (org_id, date, group_id, kid_id, status, marked_by) VALUES (?, ?, ?, ?, ?, ?) '
                         'ON CONFLICT (org_id, date, group_id, kid_id) DO UPDATE SET status = excluded.status, marked_by = excluded.marked_by',
                         (org, date, gid, kid, st, user_id))
        if delta:
            conn.execute('UPDATE kids SET lessons_left = lessons_left + ? WHERE id = ?', (delta, kid))
        changed += 1
        left = k['lessons_left'] + delta
        if st == 'absent':
            run_rules(conn, org, 'absent', 'kid', kid, k['name'])
        if left <= 2 and k['status'] in ('active', 'trial'):
            run_rules(conn, org, 'kidlow', 'kid', kid, k['name'])
    return {'changed': changed}


# ---------- воронка ----------
def lead_stage(conn, org: int, lead: dict, to: int, reason: str = '', user_id=None):
    frm = lead['stage']
    if frm == to:
        return
    if to == 4 and not reason:
        raise ApiError(422, 'Укажите причину отказа: по ней строится аналитика', 'validation')
    max_stage = max(lead['max_stage'], to) if to < 4 else lead['max_stage']
    conn.execute('UPDATE leads SET stage = ?, max_stage = ?, reason = ? WHERE id = ?', (to, max_stage, reason if to == 4 else '', lead['id']))
    log_event(conn, org, 'lead', lead['id'], f'Этап: {STAGES[frm]} → {STAGES[to]}' + (f' ({reason})' if to == 4 else ''), 'stage', user_id)
    run_rules(conn, org, f'lead{to}', 'lead', lead['id'], lead['child'] or lead['parent'])


# ---------- состояние центра для веб-клиента ----------
def build_state(conn, user: dict, caps: set) -> dict:
    org = user['org_id']
    o = row(conn.execute('SELECT * FROM orgs WHERE id = ?', (org,)).fetchone())
    st = org_settings(conn, org)
    fin = 'billing' in caps or 'finance' in caps
    att: dict = {}
    for a in conn.execute('SELECT date, group_id, kid_id, status FROM attendance WHERE org_id = ? AND date >= ?', (org, add_days(today(), -400))):
        att.setdefault(a['date'], {}).setdefault(str(a['group_id']), {})[str(a['kid_id'])] = a['status']
    items = rows(conn.execute('SELECT * FROM items WHERE org_id = ? ORDER BY id DESC', (org,)))
    for it in items:
        it['h'] = [[p['date'], p['price']] for p in conn.execute('SELECT date, price FROM item_prices WHERE item_id = ? ORDER BY date', (it['id'],))]
    groups = rows(conn.execute('SELECT * FROM groups WHERE org_id = ? ORDER BY time, id', (org,)))
    for g in groups:
        g['days'] = jload(g['days'], [])
        g['ages'] = [g.pop('age_from'), g.pop('age_to')]
    invoices = rows(conn.execute('SELECT * FROM invoices WHERE org_id = ? ORDER BY date, id', (org,))) if fin else []
    for i in invoices:
        i['kids'] = jload(i['kids'], [])
        i['fid'] = i.pop('family_id')
    payments = rows(conn.execute('SELECT id, family_id AS fid, amount, method, date, note FROM payments WHERE org_id = ? ORDER BY date, id', (org,))) if fin else []
    debts = {r['id']: debt_of(conn, org, r['id']) for r in conn.execute('SELECT id FROM families WHERE org_id = ?', (org,))}
    families = [{**f, 'debt': debts.get(f['id'], 0) if fin else 0, 'token': f['token'] if 'students' in caps or fin else None} for f in rows(conn.execute('SELECT id, parent, phone, token FROM families WHERE org_id = ? ORDER BY id', (org,)))]
    return {
        'v': 3, 'server': True, 'demo': bool(o['demo']),
        'me': {'id': user['id'], 'name': user['name'], 'email': user['email'], 'role': user['role'], 'role_name': ROLE_NAMES[user['role']], 'caps': sorted(caps)},
        'center': {'name': o['name'], 'city': o['city'], 'price': st['price'], 'pack': st['pack'], 'sib2': st['sib2'], 'sib3': st['sib3'], 'tax': st['tax'],
                   'kaspiPoint': st['kaspi_point'], 'kaspiLink': st['kaspi_link'], 'instagram': st['instagram']},
        'selCur': st['sel_cur'],
        'groups': groups,
        'families': families,
        'kids': [{'id': k['id'], 'name': k['name'], 'age': k['age'], 'gid': k['group_id'] or 0, 'fid': k['family_id'] or 0, 'left': k['lessons_left'], 'status': k['status'], 'note': k['note']}
                 for k in conn.execute('SELECT * FROM kids WHERE org_id = ? ORDER BY name', (org,))],
        'leads': [{**l, 'maxStage': l.pop('max_stage')} for l in rows(conn.execute('SELECT * FROM leads WHERE org_id = ? ORDER BY date DESC, id DESC', (org,)))] if 'leads' in caps or 'students' in caps else [],
        'invoices': invoices,
        'payments': payments,
        'expenses': rows(conn.execute('SELECT id, cat, amount, date, note FROM expenses WHERE org_id = ? ORDER BY date, id', (org,))) if 'finance' in caps else [],
        'items': items if fin else [],
        'att': att,
        'tasks': [{'id': t['id'], 'title': t['title'], 'due': t['due'], 'who': t['assignee_id'] or 0, 'ref': {'t': t['ref_type'], 'id': t['ref_id']} if t['ref_type'] else None,
                   'tpl': t['tpl_id'] or 0, 'done': bool(t['done']), 'doneAt': t['done_at'], 'auto': bool(t['auto']), 'created': t['created_at']}
                  for t in conn.execute('SELECT * FROM tasks WHERE org_id = ? AND (done = 0 OR done_at >= ?) ORDER BY id', (org, add_days(today(), -60)))],
        'staff': [{'id': u['id'], 'name': u['name'], 'role': ROLE_NAMES[u['role']], 'roleKey': u['role'], 'email': u['email'], 'phone': u['phone'], 'active': bool(u['active'])}
                  for u in conn.execute('SELECT * FROM users WHERE org_id = ? ORDER BY id', (org,))],
        'templates': rows(conn.execute('SELECT id, name, text FROM templates WHERE org_id = ? ORDER BY id', (org,))),
        'rules': [{'id': r['id'], 'on': r['trigger'], 'task': r['task'], 'days': r['days'], 'tpl': r['tpl_id'] or 0} for r in conn.execute('SELECT * FROM rules WHERE org_id = ? ORDER BY id', (org,))],
        'log': [{'id': e['id'], 'at': e['at'], 'ref': {'t': e['ref_type'], 'id': e['ref_id']} if e['ref_type'] else None, 'text': e['text'], 'type': e['type']}
                for e in conn.execute('SELECT * FROM events WHERE org_id = ? ORDER BY id DESC LIMIT 3000', (org,))],
    }


# ---------- импорт резервной копии локального приложения ----------
def import_backup(conn, org: int, data: dict) -> dict:
    """Переносит данные из файла резервной копии (Умный Зайка v2 / BALA локальная v3) в центр."""
    if data.get('v') not in (2, 3) or not isinstance(data.get('kids'), list):
        raise ApiError(422, 'Это не файл резервной копии BALA CRM или Умного Зайки', 'validation')
    m: dict = {'g': {}, 'f': {}, 'k': {}, 'l': {}}
    c = data.get('center') or {}
    st = org_settings(conn, org)
    for a, b in (('price', 'price'), ('pack', 'pack'), ('sib2', 'sib2'), ('sib3', 'sib3'), ('tax', 'tax'), ('kaspiPoint', 'kaspi_point'), ('kaspiLink', 'kaspi_link'), ('instagram', 'instagram')):
        if c.get(a) not in (None, ''):
            st[b] = c[a]
    conn.execute('UPDATE orgs SET settings = ? WHERE id = ?', (json.dumps(st, ensure_ascii=False), org))
    for g in data.get('groups', []):
        ages = g.get('ages') or [None, None]
        m['g'][g['id']] = conn.execute('INSERT INTO groups (org_id, name, dir, teacher, room, age_from, age_to, cap, days, time, price) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                                       (org, g.get('name') or 'Группа', g.get('dir') or '', g.get('teacher') or '', g.get('room') or '', ages[0], ages[1], g.get('cap'),
                                        json.dumps(g.get('days') or []), g.get('time') or '16:00', g.get('price'))).lastrowid
    for f in data.get('families', []):
        m['f'][f['id']] = conn.execute('INSERT INTO families (org_id, parent, phone, token) VALUES (?, ?, ?, ?)', (org, f.get('parent') or 'Родитель', f.get('phone') or '', new_public_token())).lastrowid
    for k in data.get('kids', []):
        m['k'][k['id']] = conn.execute('INSERT INTO kids (org_id, family_id, group_id, name, age, lessons_left, status, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                                       (org, m['f'].get(k.get('fid')), m['g'].get(k.get('gid')), k.get('name') or 'Ученик', k.get('age'), int(k.get('left') or 0),
                                        k.get('status') if k.get('status') in ('trial', 'active', 'pause', 'left') else 'active', k.get('note') or '')).lastrowid
    for l in data.get('leads', []):
        m['l'][l['id']] = conn.execute('INSERT INTO leads (org_id, parent, phone, child, age, dir, src, stage, max_stage, reason, note, date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                                       (org, l.get('parent') or '—', l.get('phone') or '', l.get('child') or '', l.get('age'), l.get('dir') or '', l.get('src') or 'Другое',
                                        int(l.get('stage') or 0), int(l.get('maxStage') or 0), l.get('reason') or '', l.get('note') or '', l.get('date') or today())).lastrowid
    for i in data.get('invoices', []):
        fid = m['f'].get(i.get('fid'))
        if fid and i.get('amount', 0) > 0:
            conn.execute('INSERT INTO invoices (org_id, family_id, kids, lessons, amount, paid, applied, note, date) VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)',
                         (org, fid, json.dumps([m['k'][x] for x in i.get('kids', []) if x in m['k']]), int(i.get('lessons') or 0), int(i['amount']), 1 if i.get('applied') else 0, i.get('note') or '', i.get('date') or today()))
    for p in data.get('payments', []):
        if p.get('amount', 0) > 0:
            conn.execute('INSERT INTO payments (org_id, family_id, amount, method, date, note) VALUES (?, ?, ?, ?, ?, ?)',
                         (org, m['f'].get(p.get('fid')), int(p['amount']), p.get('method') if p.get('method') in METHODS else 'cash', p.get('date') or today(), p.get('note') or ''))
    for e in data.get('expenses', []):
        if e.get('amount', 0) > 0:
            conn.execute('INSERT INTO expenses (org_id, cat, amount, date, note) VALUES (?, ?, ?, ?, ?)', (org, e.get('cat') or 'Прочее', int(e['amount']), e.get('date') or today(), e.get('note') or ''))
    for it in data.get('items', []):
        iid = conn.execute('INSERT INTO items (org_id, name, unit, target, link) VALUES (?, ?, ?, ?, ?)', (org, it.get('name') or 'Товар', it.get('unit') or 'шт.', int(it.get('target') or 0), it.get('link') or '')).lastrowid
        for d, p in it.get('h', []):
            conn.execute('INSERT OR REPLACE INTO item_prices (item_id, date, price) VALUES (?, ?, ?)', (iid, d, int(p)))
    for d, gs in (data.get('att') or {}).items():
        for gid, ks in gs.items():
            for kid, s in ks.items():
                if int(gid) in m['g'] and int(kid) in m['k'] and s in ('was', 'late', 'absent', 'excused'):
                    conn.execute('INSERT OR REPLACE INTO attendance (org_id, date, group_id, kid_id, status) VALUES (?, ?, ?, ?, ?)', (org, d, m['g'][int(gid)], m['k'][int(kid)], s))
    for f in m['f'].values():
        allocate(conn, org, f)
    log_event(conn, org, None, None, f'Импорт резервной копии: {len(m["k"])} учеников, {len(m["g"])} групп', 'event')
    return {'groups': len(m['g']), 'families': len(m['f']), 'kids': len(m['k']), 'leads': len(m['l'])}


def wipe_org_data(conn, org: int):
    for t in ('attendance', 'tasks', 'events', 'payments', 'invoices', 'expenses', 'kids', 'families', 'groups', 'leads'):
        conn.execute(f'DELETE FROM {t} WHERE org_id = ?', (org,))
    conn.execute('DELETE FROM items WHERE org_id = ?', (org,))
