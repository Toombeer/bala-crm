"""Данные центра целиком, отчёты, курсы, экспорт и импорт, демо, кабинет родителя."""
import csv
import datetime as dt
import io
import json

from starlette.responses import Response

from .. import rates as ratesm
from ..core import ApiError, api, today
from ..db import jload, row, rows, tx
from ..schemas import ImportIn
from ..security import caps
from ..services import (STAGES, add_days, allocate, build_state, debt_of, import_backup, log_event, org_settings, wipe_org_data)


@api('GET', '/state', tag='Данные', summary='Все данные центра для веб-клиента (с учётом прав роли)')
def state(ctx):
    return build_state(ctx.conn, ctx.user, caps(ctx.user['role']))


# ---------- отчёты ----------
def _month(ctx) -> str:
    m = ctx.query.get('month') or today()[:7]
    if len(m) != 7 or m[4] != '-':
        raise ApiError(422, 'Параметр month в формате ГГГГ-ММ', 'validation')
    return m


@api('GET', '/reports/dashboard', tag='Отчёты', summary='Главный экран: занятия сегодня, долги, заявки, задачи')
def dashboard(ctx):
    t = today()
    dow = (dt.date.fromisoformat(t).isoweekday()) % 7
    groups = [g for g in rows(ctx.conn.execute('SELECT id, name, time, dir FROM groups WHERE org_id = ?', (ctx.org,))) if dow in jload(ctx.conn.execute('SELECT days FROM groups WHERE id = ?', (g['id'],)).fetchone()['days'], [])]
    out = {'date': t, 'lessons_today': sorted(groups, key=lambda g: g['time']),
           'kids_active': ctx.conn.execute("SELECT COUNT(*) c FROM kids WHERE org_id = ? AND status IN ('active', 'trial')", (ctx.org,)).fetchone()['c'],
           'leads_open': ctx.conn.execute('SELECT COUNT(*) c FROM leads WHERE org_id = ? AND stage < 3', (ctx.org,)).fetchone()['c'],
           'tasks_today': ctx.conn.execute('SELECT COUNT(*) c FROM tasks WHERE org_id = ? AND done = 0 AND (due IS NULL OR due <= ?)', (ctx.org, t)).fetchone()['c'],
           'tasks_overdue': ctx.conn.execute('SELECT COUNT(*) c FROM tasks WHERE org_id = ? AND done = 0 AND due < ?', (ctx.org, t)).fetchone()['c']}
    if ctx.can('billing'):
        debts = [debt_of(ctx.conn, ctx.org, f['id']) for f in ctx.conn.execute('SELECT id FROM families WHERE org_id = ?', (ctx.org,))]
        out.update({'debt_total': sum(debts), 'debt_families': sum(1 for d in debts if d > 0),
                    'revenue_month': ctx.conn.execute('SELECT COALESCE(SUM(amount), 0) s FROM payments WHERE org_id = ? AND substr(date, 1, 7) = ?', (ctx.org, t[:7])).fetchone()['s']})
    return out


@api('GET', '/reports/finance', cap='finance', tag='Отчёты', summary='Финансы за месяц: выручка, расходы, прибыль, налог, способы оплаты')
def finance(ctx):
    m = _month(ctx)
    rev = ctx.conn.execute('SELECT COALESCE(SUM(amount), 0) s FROM payments WHERE org_id = ? AND substr(date, 1, 7) = ?', (ctx.org, m)).fetchone()['s']
    exp = ctx.conn.execute('SELECT COALESCE(SUM(amount), 0) s FROM expenses WHERE org_id = ? AND substr(date, 1, 7) = ?', (ctx.org, m)).fetchone()['s']
    tax_rate = org_settings(ctx.conn, ctx.org)['tax']
    by_method = {r['method']: r['s'] for r in ctx.conn.execute('SELECT method, SUM(amount) s FROM payments WHERE org_id = ? AND substr(date, 1, 7) = ? GROUP BY method', (ctx.org, m))}
    by_cat = {r['cat']: r['s'] for r in ctx.conn.execute('SELECT cat, SUM(amount) s FROM expenses WHERE org_id = ? AND substr(date, 1, 7) = ? GROUP BY cat ORDER BY s DESC', (ctx.org, m))}
    return {'month': m, 'revenue': rev, 'expenses': exp, 'profit': rev - exp, 'tax_rate': tax_rate, 'tax': round(rev * tax_rate / 100), 'by_method': by_method, 'by_category': by_cat}


@api('GET', '/reports/analytics', tag='Отчёты', summary='Аналитика: источники, воронка, отказы, посещаемость, заполненность')
def analytics(ctx):
    since = add_days(today(), -30)
    leads = rows(ctx.conn.execute('SELECT * FROM leads WHERE org_id = ?', (ctx.org,)))
    cnt = lambda key, arr: dict(sorted(((k, sum(1 for l in arr if (l[key] or 'Не указано') == k)) for k in {l[key] or 'Не указано' for l in arr}), key=lambda x: -x[1]))
    reached = lambda i: sum(1 for l in leads if (l['stage'] if l['stage'] != 4 else l['max_stage']) >= i)
    att = ctx.conn.execute("SELECT COUNT(*) a, SUM(status IN ('was', 'late')) w FROM attendance WHERE org_id = ? AND date >= ?", (ctx.org, since)).fetchone()
    groups = [{'id': g['id'], 'name': g['name'], 'cap': g['cap'], 'kids': ctx.conn.execute("SELECT COUNT(*) c FROM kids WHERE group_id = ? AND status != 'left'", (g['id'],)).fetchone()['c']}
              for g in ctx.conn.execute('SELECT id, name, cap FROM groups WHERE org_id = ?', (ctx.org,))]
    bought = sum(1 for l in leads if l['stage'] == 3)
    return {'leads_total': len(leads), 'leads_30d': sum(1 for l in leads if l['date'] >= since), 'conversion': round(bought / len(leads) * 100) if leads else 0,
            'sources': cnt('src', leads), 'interests': cnt('dir', leads), 'refusals': cnt('reason', [l for l in leads if l['stage'] == 4]),
            'funnel': {STAGES[0]: len(leads), STAGES[1]: reached(1), STAGES[2]: reached(2), STAGES[3]: bought},
            'attendance_rate': round((att['w'] or 0) / att['a'] * 100) if att['a'] else None, 'groups': groups}


# ---------- курсы ----------
@api('GET', '/rates', tag='Курсы валют', summary='Последние курсы НБ РК и история за 60 дней')
def rates_get(ctx):
    return ratesm.latest(ctx.conn)


@api('POST', '/rates/refresh', cap='data', tag='Курсы валют', summary='Загрузить свежие курсы с сайта Нацбанка сейчас')
def rates_refresh(ctx):
    return ratesm.refresh(ctx.conn, 30)


# ---------- экспорт и импорт ----------
def _csv(name: str, header: list, data: list) -> Response:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=';')
    w.writerow(header)
    w.writerows(data)
    return Response('﻿' + buf.getvalue(), media_type='text/csv; charset=utf-8', headers={'Content-Disposition': f'attachment; filename="{name}"'})


@api('GET', '/export/payments.csv', cap='finance', tag='Экспорт', summary='Оплаты за месяц в CSV для Excel (month=ГГГГ-ММ)')
def export_payments(ctx):
    m = _month(ctx)
    data = [[p['date'], p['parent'] or 'Без семьи', p['amount'], {'cash': 'Наличные', 'kaspi': 'Kaspi', 'transfer': 'Перевод'}[p['method']], p['note']]
            for p in ctx.conn.execute('SELECT p.*, f.parent FROM payments p LEFT JOIN families f ON f.id = p.family_id WHERE p.org_id = ? AND substr(p.date, 1, 7) = ? ORDER BY p.date', (ctx.org, m))]
    return _csv(f'oplaty-{m}.csv', ['Дата', 'Семья', 'Сумма', 'Способ', 'Комментарий'], data)


@api('GET', '/export/expenses.csv', cap='finance', tag='Экспорт', summary='Расходы за месяц в CSV')
def export_expenses(ctx):
    m = _month(ctx)
    data = [[e['date'], e['cat'], e['amount'], e['note']] for e in ctx.conn.execute('SELECT * FROM expenses WHERE org_id = ? AND substr(date, 1, 7) = ? ORDER BY date', (ctx.org, m))]
    return _csv(f'rashody-{m}.csv', ['Дата', 'Категория', 'Сумма', 'Комментарий'], data)


@api('GET', '/export/backup.json', cap='data', tag='Экспорт', summary='Полная резервная копия центра (формат совместим с импортом)')
def export_backup(ctx):
    s = build_state(ctx.conn, ctx.user, caps('owner'))
    for k in ('me', 'server', 'log', 'tasks', 'staff', 'templates', 'rules'):
        s.pop(k, None)
    body = json.dumps(s, ensure_ascii=False)
    return Response(body, media_type='application/json', headers={'Content-Disposition': f'attachment; filename="bala-crm-{today()}.json"'})


@api('POST', '/import', cap='data', body=ImportIn, tag='Экспорт', summary='Импорт резервной копии из локального приложения (Умный Зайка или BALA CRM)')
def import_data(ctx, body: ImportIn):
    with tx(ctx.conn):
        res = import_backup(ctx.conn, ctx.org, body.model_dump())
    return {**res, '_created': True}


@api('POST', '/org/reset', cap='data', tag='Данные', summary='Удалить все данные центра (настройки, сотрудники, шаблоны сохраняются)')
def org_reset(ctx):
    with tx(ctx.conn):
        wipe_org_data(ctx.conn, ctx.org)
        ctx.conn.execute('UPDATE orgs SET demo = 0 WHERE id = ?', (ctx.org,))
        log_event(ctx.conn, ctx.org, None, None, 'Данные центра очищены', 'event', ctx.uid)
    return {'ok': True}


@api('POST', '/org/demo', cap='data', tag='Данные', summary='Заполнить пустой центр демо-данными')
def org_demo(ctx):
    if ctx.conn.execute('SELECT COUNT(*) c FROM kids WHERE org_id = ?', (ctx.org,)).fetchone()['c']:
        raise ApiError(409, 'В центре уже есть ученики. Демо-данные можно загрузить только в пустой центр.', 'not_empty')
    from ..demo import demo_backup
    with tx(ctx.conn):
        res = import_backup(ctx.conn, ctx.org, demo_backup(today()))
        ctx.conn.execute('UPDATE orgs SET demo = 1 WHERE id = ?', (ctx.org,))
        for l in ctx.conn.execute('SELECT * FROM leads WHERE org_id = ? AND stage IN (0, 2)', (ctx.org,)).fetchall():
            from ..services import run_rules
            run_rules(ctx.conn, ctx.org, f'lead{l["stage"]}', 'lead', l['id'], l['child'] or l['parent'])
    return {**res, '_created': True}


# ---------- кабинет родителя (без входа, по секретной ссылке) ----------
@api('GET', '/public/family/{token}', public=True, tag='Кабинет родителя', summary='Данные семьи по секретной ссылке: дети, расписание, остаток занятий, долг, оплаты')
def parent_cabinet(ctx, token: str):
    f = row(ctx.conn.execute('SELECT * FROM families WHERE token = ?', (token,)).fetchone())
    if not f or len(token) < 16:
        raise ApiError(404, 'Ссылка недействительна. Попросите у центра новую.', 'not_found')
    org = f['org_id']
    o = row(ctx.conn.execute('SELECT name, city FROM orgs WHERE id = ?', (org,)).fetchone())
    st = org_settings(ctx.conn, org)
    kids = []
    for k in ctx.conn.execute("SELECT * FROM kids WHERE family_id = ? AND status != 'left'", (f['id'],)):
        g = row(ctx.conn.execute('SELECT name, dir, teacher, room, days, time FROM groups WHERE id = ?', (k['group_id'],)).fetchone()) if k['group_id'] else None
        if g:
            g['days'] = jload(g['days'], [])
        visits = rows(ctx.conn.execute('SELECT date, status FROM attendance WHERE kid_id = ? ORDER BY date DESC LIMIT 10', (k['id'],)))
        kids.append({'name': k['name'], 'lessons_left': k['lessons_left'], 'status': k['status'], 'group': g, 'visits': visits})
    pays = rows(ctx.conn.execute('SELECT date, amount, method FROM payments WHERE family_id = ? ORDER BY date DESC LIMIT 10', (f['id'],)))
    return {'center': o, 'parent': f['parent'], 'kids': kids, 'debt': debt_of(ctx.conn, org, f['id']), 'payments': pays, 'kaspi_link': st['kaspi_link'] or None}


@api('GET', '/health', public=True, tag='Служебное', summary='Проверка работы сервера')
def health(ctx):
    ctx.conn.execute('SELECT 1').fetchone()
    return {'ok': True, 'time': today()}
