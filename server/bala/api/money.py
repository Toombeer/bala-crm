"""Деньги: счета, оплаты, расчёт стоимости абонемента."""
import json

from ..core import ApiError, api, today
from ..db import jload, row, rows, tx
from ..schemas import InvoiceIn, PaymentIn, QuoteIn
from ..services import METHODS, allocate, debt_of, get_owned, log_event, org_settings, quote, run_rules

T = 'Оплаты'


def _inv_out(i):
    i = dict(i)
    i['kids'] = jload(i['kids'], [])
    i['status'] = 'paid' if i['paid'] >= i['amount'] else 'partial' if i['paid'] else 'unpaid'
    return i


def _check_kids(ctx, fid, kids):
    for k in kids:
        kid = get_owned(ctx.conn, 'kids', ctx.org, k, 'Ученик')
        if kid['family_id'] != fid:
            raise ApiError(422, f'Ученик «{kid["name"]}» не из этой семьи', 'validation')


@api('POST', '/quote', cap='billing', body=QuoteIn, tag=T, summary='Посчитать стоимость абонемента с семейной и доп. скидкой')
def quote_calc(ctx, body: QuoteIn):
    return quote(ctx.conn, ctx.org, body.kids, body.lessons, body.extra)


@api('GET', '/invoices', cap='billing', tag=T, summary='Счета (family_id, status=unpaid|partial|paid)')
def invoices_list(ctx):
    q, a = 'SELECT * FROM invoices WHERE org_id = ?', [ctx.org]
    if ctx.query.get('family_id'):
        q += ' AND family_id = ?'
        a.append(int(ctx.query['family_id']))
    out = [_inv_out(i) for i in ctx.conn.execute(q + ' ORDER BY date DESC, id DESC', a)]
    st = ctx.query.get('status')
    return [i for i in out if not st or i['status'] == st]


@api('POST', '/invoices', cap='billing', body=InvoiceIn, tag=T, summary='Выставить счёт. Когда он оплачен полностью, занятия добавятся детям')
def invoices_create(ctx, body: InvoiceIn):
    f = get_owned(ctx.conn, 'families', ctx.org, body.family_id, 'Семья')
    _check_kids(ctx, body.family_id, body.kids)
    with tx(ctx.conn):
        iid = ctx.conn.execute('INSERT INTO invoices (org_id, family_id, kids, lessons, amount, note, date) VALUES (?, ?, ?, ?, ?, ?, ?)',
                               (ctx.org, body.family_id, json.dumps(sorted(set(body.kids))), body.lessons, body.amount, body.note, body.date or today())).lastrowid
        log_event(ctx.conn, ctx.org, 'fam', body.family_id, f'Счёт {body.amount:,} ₸'.replace(',', ' ') + (f' · {body.note}' if body.note else ''), 'inv', ctx.uid)
        run_rules(ctx.conn, ctx.org, 'invoice', 'fam', body.family_id, f['parent'])
        allocate(ctx.conn, ctx.org, body.family_id)
    return {**_inv_out(get_owned(ctx.conn, 'invoices', ctx.org, iid)), 'message': invoice_message(ctx, iid)['text'], '_created': True}


@api('PUT', '/invoices/{id}', cap='billing', body=InvoiceIn, tag=T, summary='Изменить счёт')
def invoices_update(ctx, id: int, body: InvoiceIn):
    old = get_owned(ctx.conn, 'invoices', ctx.org, id, 'Счёт')
    get_owned(ctx.conn, 'families', ctx.org, body.family_id, 'Семья')
    _check_kids(ctx, body.family_id, body.kids)
    with tx(ctx.conn):
        ctx.conn.execute('UPDATE invoices SET family_id = ?, kids = ?, lessons = ?, amount = ?, note = ?, date = ? WHERE id = ?',
                         (body.family_id, json.dumps(sorted(set(body.kids))), body.lessons, body.amount, body.note, body.date or old['date'], id))
        allocate(ctx.conn, ctx.org, old['family_id'])
        allocate(ctx.conn, ctx.org, body.family_id)
    return _inv_out(get_owned(ctx.conn, 'invoices', ctx.org, id))


@api('DELETE', '/invoices/{id}', cap='billing', tag=T, summary='Удалить счёт')
def invoices_delete(ctx, id: int):
    inv = get_owned(ctx.conn, 'invoices', ctx.org, id, 'Счёт')
    with tx(ctx.conn):
        ctx.conn.execute('DELETE FROM invoices WHERE id = ?', (id,))
        allocate(ctx.conn, ctx.org, inv['family_id'])
    return {'ok': True}


@api('GET', '/invoices/{id}/message', cap='billing', tag=T, summary='Текст счёта для WhatsApp и ссылка wa.me')
def invoice_message(ctx, id: int):
    from urllib.parse import quote as q
    i = get_owned(ctx.conn, 'invoices', ctx.org, id, 'Счёт')
    f = get_owned(ctx.conn, 'families', ctx.org, i['family_id'], 'Семья')
    o = row(ctx.conn.execute('SELECT name FROM orgs WHERE id = ?', (ctx.org,)).fetchone())
    st = org_settings(ctx.conn, ctx.org)
    names = [r['name'].split(' ')[0] for k in jload(i['kids'], []) for r in ctx.conn.execute('SELECT name FROM kids WHERE id = ?', (k,))]
    text = (f'Здравствуйте, {f["parent"]}! Счёт от «{o["name"]}»' + (f': {i["lessons"]} занятий' if i['lessons'] else '') + (f' ({", ".join(names)})' if names else '')
            + (f', {i["note"]}' if i['note'] else '') + f'. К оплате: {i["amount"]:,} ₸.'.replace(',', ' ') + (f' Оплатить через Kaspi: {st["kaspi_link"]}' if st['kaspi_link'] else ''))
    digits = ''.join(ch for ch in f['phone'] if ch.isdigit())
    if len(digits) == 11 and digits[0] == '8':
        digits = '7' + digits[1:]
    return {'text': text, 'whatsapp': f'https://wa.me/{digits}?text={q(text)}' if digits else None}


@api('GET', '/payments', cap='billing', tag=T, summary='Оплаты (month=ГГГГ-ММ, method, family_id)')
def payments_list(ctx):
    q, a = 'SELECT * FROM payments WHERE org_id = ?', [ctx.org]
    for key, sql in (('month', ' AND substr(date, 1, 7) = ?'), ('method', ' AND method = ?'), ('family_id', ' AND family_id = ?')):
        if ctx.query.get(key):
            q += sql
            a.append(int(ctx.query[key]) if key == 'family_id' else ctx.query[key])
    return rows(ctx.conn.execute(q + ' ORDER BY date DESC, id DESC', a))


@api('POST', '/payments', cap='billing', body=PaymentIn, tag=T, summary='Принять оплату. Распределяется по счетам семьи, закрытые счета добавляют занятия')
def payments_create(ctx, body: PaymentIn):
    if body.family_id:
        get_owned(ctx.conn, 'families', ctx.org, body.family_id, 'Семья')
    if body.date and body.date > today():
        raise ApiError(422, 'Дата оплаты не может быть в будущем', 'validation')
    with tx(ctx.conn):
        pid = ctx.conn.execute('INSERT INTO payments (org_id, family_id, amount, method, date, note, created_by) VALUES (?, ?, ?, ?, ?, ?, ?)',
                               (ctx.org, body.family_id, body.amount, body.method, body.date or today(), body.note, ctx.uid)).lastrowid
        if body.family_id:
            log_event(ctx.conn, ctx.org, 'fam', body.family_id, f'Оплата {body.amount:,} ₸ · {METHODS[body.method]}'.replace(',', ' '), 'pay', ctx.uid)
            allocate(ctx.conn, ctx.org, body.family_id)
    p = get_owned(ctx.conn, 'payments', ctx.org, pid)
    return {**p, 'debt_left': debt_of(ctx.conn, ctx.org, body.family_id) if body.family_id else 0, '_created': True}


@api('PUT', '/payments/{id}', cap='billing', body=PaymentIn, tag=T, summary='Исправить оплату')
def payments_update(ctx, id: int, body: PaymentIn):
    old = get_owned(ctx.conn, 'payments', ctx.org, id, 'Оплата')
    if body.family_id:
        get_owned(ctx.conn, 'families', ctx.org, body.family_id, 'Семья')
    with tx(ctx.conn):
        ctx.conn.execute('UPDATE payments SET family_id = ?, amount = ?, method = ?, date = ?, note = ? WHERE id = ?',
                         (body.family_id, body.amount, body.method, body.date or old['date'], body.note, id))
        allocate(ctx.conn, ctx.org, old['family_id'])
        allocate(ctx.conn, ctx.org, body.family_id)
    return {**get_owned(ctx.conn, 'payments', ctx.org, id), 'debt_left': debt_of(ctx.conn, ctx.org, body.family_id) if body.family_id else 0}


@api('DELETE', '/payments/{id}', cap='billing', tag=T, summary='Удалить оплату')
def payments_delete(ctx, id: int):
    p = get_owned(ctx.conn, 'payments', ctx.org, id, 'Оплата')
    with tx(ctx.conn):
        ctx.conn.execute('DELETE FROM payments WHERE id = ?', (id,))
        allocate(ctx.conn, ctx.org, p['family_id'])
    return {'ok': True}


@api('GET', '/debts', cap='billing', tag=T, summary='Кто должен и сколько')
def debts(ctx):
    out = []
    for f in ctx.conn.execute('SELECT id, parent, phone FROM families WHERE org_id = ?', (ctx.org,)):
        d = debt_of(ctx.conn, ctx.org, f['id'])
        if d > 0:
            out.append({'family_id': f['id'], 'parent': f['parent'], 'phone': f['phone'], 'debt': d})
    return sorted(out, key=lambda x: -x['debt'])
