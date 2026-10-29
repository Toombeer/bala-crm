"""Справочники: центр, сотрудники, группы, семьи, ученики, расходы, закупки, шаблоны, правила."""
import json

from ..core import ApiError, api, not_found, today
from ..db import row, rows, tx
from ..schemas import (ExpenseIn, FamilyIn, GroupIn, ItemIn, KidIn, KidPatch, OrgIn, PriceIn, RuleIn, TemplateIn, UserIn, UserPatch)
from ..security import ROLE_NAMES, hash_password, new_public_token
from ..services import get_owned, lead_stage, log_event, org_settings

T = 'Справочники'


# ---------- центр ----------
@api('GET', '/org', tag='Центр', summary='Настройки центра')
def org_get(ctx):
    o = row(ctx.conn.execute('SELECT id, name, city, demo, created_at FROM orgs WHERE id = ?', (ctx.org,)).fetchone())
    return {**o, 'settings': org_settings(ctx.conn, ctx.org)}


@api('PATCH', '/org', cap='settings', body=OrgIn, tag='Центр', summary='Изменить название, цены, скидки, налог, Kaspi')
def org_patch(ctx, body: OrgIn):
    d = body.model_dump(exclude_none=True)
    st = org_settings(ctx.conn, ctx.org)
    for k in ('price', 'pack', 'sib2', 'sib3', 'tax', 'kaspi_point', 'kaspi_link', 'instagram', 'sel_cur'):
        if k in d:
            st[k] = d[k]
    ctx.conn.execute('UPDATE orgs SET name = COALESCE(?, name), city = COALESCE(?, city), settings = ? WHERE id = ?',
                     (d.get('name'), d.get('city'), json.dumps(st, ensure_ascii=False), ctx.org))
    return org_get(ctx)


@api('PATCH', '/org/currencies', cap='read', body=OrgIn, tag='Центр', summary='Выбрать валюты на главном экране')
def org_currencies(ctx, body: OrgIn):
    st = org_settings(ctx.conn, ctx.org)
    st['sel_cur'] = [c for c in (body.sel_cur or ['USD', 'RUB']) if len(c) == 3][:12] or ['USD', 'RUB']
    ctx.conn.execute('UPDATE orgs SET settings = ? WHERE id = ?', (json.dumps(st, ensure_ascii=False), ctx.org))
    return {'sel_cur': st['sel_cur']}


# ---------- сотрудники ----------
def _user_out(u):
    return {'id': u['id'], 'name': u['name'], 'email': u['email'], 'phone': u['phone'], 'role': u['role'], 'role_name': ROLE_NAMES[u['role']], 'active': bool(u['active'])}


@api('GET', '/users', tag='Сотрудники', summary='Список сотрудников')
def users_list(ctx):
    return [_user_out(u) for u in ctx.conn.execute('SELECT * FROM users WHERE org_id = ? ORDER BY id', (ctx.org,))]


@api('POST', '/users', cap='staff', body=UserIn, tag='Сотрудники', summary='Добавить сотрудника с логином и паролем')
def users_create(ctx, body: UserIn):
    if body.role == 'owner':
        raise ApiError(422, 'Владелец в центре один. Выберите другую роль.', 'validation')
    if ctx.conn.execute('SELECT 1 FROM users WHERE email = ?', (body.email,)).fetchone():
        raise ApiError(409, 'Этот email уже используется', 'email_taken')
    uid = ctx.conn.execute('INSERT INTO users (org_id, name, email, phone, role, pass_hash) VALUES (?, ?, ?, ?, ?, ?)',
                           (ctx.org, body.name, body.email.lower(), body.phone, body.role, hash_password(body.password))).lastrowid
    return {**_user_out(row(ctx.conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone())), '_created': True}


@api('PATCH', '/users/{id}', cap='staff', body=UserPatch, tag='Сотрудники', summary='Изменить сотрудника, роль, пароль, отключить доступ')
def users_patch(ctx, id: int, body: UserPatch):
    u = get_owned(ctx.conn, 'users', ctx.org, id, 'Сотрудник')
    d = body.model_dump(exclude_none=True)
    if u['role'] == 'owner' and (d.get('role', 'owner') != 'owner' or d.get('active') is False):
        raise ApiError(422, 'Нельзя понизить или отключить владельца', 'validation')
    if d.get('role') == 'owner' and u['role'] != 'owner':
        raise ApiError(422, 'Владелец в центре один', 'validation')
    bump = 1 if ('password' in d or d.get('active') is False or 'role' in d) else 0
    ctx.conn.execute('UPDATE users SET name = COALESCE(?, name), phone = COALESCE(?, phone), role = COALESCE(?, role), active = COALESCE(?, active), '
                     'pass_hash = COALESCE(?, pass_hash), token_version = token_version + ? WHERE id = ?',
                     (d.get('name'), d.get('phone'), d.get('role'), (1 if d['active'] else 0) if 'active' in d else None,
                      hash_password(d['password']) if 'password' in d else None, bump, id))
    return _user_out(row(ctx.conn.execute('SELECT * FROM users WHERE id = ?', (id,)).fetchone()))


@api('DELETE', '/users/{id}', cap='staff', tag='Сотрудники', summary='Удалить сотрудника')
def users_delete(ctx, id: int):
    u = get_owned(ctx.conn, 'users', ctx.org, id, 'Сотрудник')
    if u['role'] == 'owner':
        raise ApiError(422, 'Нельзя удалить владельца', 'validation')
    ctx.conn.execute('DELETE FROM users WHERE id = ?', (id,))
    return {'ok': True}


# ---------- группы ----------
def _group_out(g):
    g = dict(g)
    g['days'] = json.loads(g['days'])
    return g


@api('GET', '/groups', tag=T, summary='Группы')
def groups_list(ctx):
    return [_group_out(g) for g in ctx.conn.execute('SELECT * FROM groups WHERE org_id = ? ORDER BY time, id', (ctx.org,))]


@api('POST', '/groups', cap='groups', body=GroupIn, tag=T, summary='Создать группу')
def groups_create(ctx, body: GroupIn):
    d = body.model_dump()
    gid = ctx.conn.execute('INSERT INTO groups (org_id, name, dir, teacher, room, age_from, age_to, cap, days, time, price) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                           (ctx.org, d['name'], d['dir'], d['teacher'], d['room'], d['age_from'], d['age_to'], d['cap'], json.dumps(d['days']), d['time'], d['price'])).lastrowid
    return {**_group_out(get_owned(ctx.conn, 'groups', ctx.org, gid)), '_created': True}


@api('PUT', '/groups/{id}', cap='groups', body=GroupIn, tag=T, summary='Изменить группу')
def groups_update(ctx, id: int, body: GroupIn):
    get_owned(ctx.conn, 'groups', ctx.org, id, 'Группа')
    d = body.model_dump()
    ctx.conn.execute('UPDATE groups SET name = ?, dir = ?, teacher = ?, room = ?, age_from = ?, age_to = ?, cap = ?, days = ?, time = ?, price = ? WHERE id = ?',
                     (d['name'], d['dir'], d['teacher'], d['room'], d['age_from'], d['age_to'], d['cap'], json.dumps(d['days']), d['time'], d['price'], id))
    return _group_out(get_owned(ctx.conn, 'groups', ctx.org, id))


@api('DELETE', '/groups/{id}', cap='groups', tag=T, summary='Удалить группу (ученики останутся без группы)')
def groups_delete(ctx, id: int):
    get_owned(ctx.conn, 'groups', ctx.org, id, 'Группа')
    ctx.conn.execute('DELETE FROM groups WHERE id = ?', (id,))
    return {'ok': True}


# ---------- семьи ----------
@api('GET', '/families', tag=T, summary='Семьи')
def families_list(ctx):
    return rows(ctx.conn.execute('SELECT id, parent, phone, token FROM families WHERE org_id = ? ORDER BY id', (ctx.org,)))


@api('POST', '/families', cap='students', body=FamilyIn, tag=T, summary='Создать семью')
def families_create(ctx, body: FamilyIn):
    fid = ctx.conn.execute('INSERT INTO families (org_id, parent, phone, token) VALUES (?, ?, ?, ?)', (ctx.org, body.parent, body.phone, new_public_token())).lastrowid
    return {**get_owned(ctx.conn, 'families', ctx.org, fid), '_created': True}


@api('PUT', '/families/{id}', cap='students', body=FamilyIn, tag=T, summary='Изменить семью')
def families_update(ctx, id: int, body: FamilyIn):
    get_owned(ctx.conn, 'families', ctx.org, id, 'Семья')
    ctx.conn.execute('UPDATE families SET parent = ?, phone = ? WHERE id = ?', (body.parent, body.phone, id))
    return get_owned(ctx.conn, 'families', ctx.org, id)


@api('POST', '/families/{id}/token', cap='students', tag=T, summary='Выпустить новую ссылку на кабинет родителя (старая перестанет работать)')
def families_token(ctx, id: int):
    get_owned(ctx.conn, 'families', ctx.org, id, 'Семья')
    ctx.conn.execute('UPDATE families SET token = ? WHERE id = ?', (new_public_token(), id))
    return get_owned(ctx.conn, 'families', ctx.org, id)


@api('DELETE', '/families/{id}', cap='students', tag=T, summary='Удалить семью вместе со счетами')
def families_delete(ctx, id: int):
    get_owned(ctx.conn, 'families', ctx.org, id, 'Семья')
    ctx.conn.execute('DELETE FROM families WHERE id = ?', (id,))
    return {'ok': True}


# ---------- ученики ----------
def _kid_family(ctx, d: dict, current: int | None) -> int | None:
    """Семья ученика: существующая (обновляем имя и телефон родителя) или новая."""
    fid = d.get('family_id')
    if fid is None and current:
        fid = current
    if fid:
        get_owned(ctx.conn, 'families', ctx.org, fid, 'Семья')
        if d.get('parent'):
            ctx.conn.execute('UPDATE families SET parent = ? WHERE id = ?', (d['parent'], fid))
        if d.get('phone'):
            ctx.conn.execute('UPDATE families SET phone = ? WHERE id = ?', (d['phone'], fid))
        return fid
    if not d.get('parent'):
        raise ApiError(422, 'Укажите семью или имя родителя для новой семьи', 'validation')
    return ctx.conn.execute('INSERT INTO families (org_id, parent, phone, token) VALUES (?, ?, ?, ?)', (ctx.org, d['parent'], d.get('phone') or '', new_public_token())).lastrowid


def _kid_out(k):
    return {'id': k['id'], 'name': k['name'], 'age': k['age'], 'group_id': k['group_id'], 'family_id': k['family_id'], 'lessons_left': k['lessons_left'], 'status': k['status'], 'note': k['note']}


@api('GET', '/kids', tag=T, summary='Ученики')
def kids_list(ctx):
    return [_kid_out(k) for k in ctx.conn.execute('SELECT * FROM kids WHERE org_id = ? ORDER BY name', (ctx.org,))]


@api('GET', '/kids/{id}', tag=T, summary='Карточка ученика')
def kids_get(ctx, id: int):
    return _kid_out(get_owned(ctx.conn, 'kids', ctx.org, id, 'Ученик'))


@api('POST', '/kids', cap='students', body=KidIn, tag=T, summary='Добавить ученика (с существующей или новой семьёй, можно из заявки)')
def kids_create(ctx, body: KidIn):
    d = body.model_dump()
    with tx(ctx.conn):
        gid = d['group_id'] or None
        if gid:
            g = get_owned(ctx.conn, 'groups', ctx.org, gid, 'Группа')
        fid = _kid_family(ctx, d, None)
        kid = ctx.conn.execute('INSERT INTO kids (org_id, family_id, group_id, name, age, lessons_left, status, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                               (ctx.org, fid, gid, d['name'], d['age'], d['lessons_left'], d['status'], d['note'])).lastrowid
        log_event(ctx.conn, ctx.org, 'kid', kid, 'Ученик добавлен' + (f' в группу «{g["name"]}»' if gid else ''), 'create', ctx.uid)
        if d.get('lead_id'):
            lead = get_owned(ctx.conn, 'leads', ctx.org, d['lead_id'], 'Заявка')
            lead_stage(ctx.conn, ctx.org, lead, 3, user_id=ctx.uid)
            log_event(ctx.conn, ctx.org, 'kid', kid, f'Пришёл из заявки ({lead["src"]})', 'create', ctx.uid)
    return {**_kid_out(get_owned(ctx.conn, 'kids', ctx.org, kid)), '_created': True}


@api('PATCH', '/kids/{id}', cap='students', body=KidPatch, tag=T, summary='Изменить ученика')
def kids_patch(ctx, id: int, body: KidPatch):
    k = get_owned(ctx.conn, 'kids', ctx.org, id, 'Ученик')
    d = body.model_dump(exclude_unset=True)
    with tx(ctx.conn):
        if 'group_id' in d and d['group_id']:
            get_owned(ctx.conn, 'groups', ctx.org, d['group_id'], 'Группа')
        fid = _kid_family(ctx, d, k['family_id']) if ('family_id' in d or 'parent' in d or 'phone' in d) else k['family_id']
        new = {**k, **{x: d[x] for x in ('name', 'age', 'status', 'lessons_left', 'note') if x in d and d[x] is not None}}
        new['group_id'] = (d['group_id'] or None) if 'group_id' in d else k['group_id']
        ctx.conn.execute('UPDATE kids SET name = ?, age = ?, group_id = ?, family_id = ?, status = ?, lessons_left = ?, note = ? WHERE id = ?',
                         (new['name'], new['age'], new['group_id'], fid, new['status'], new['lessons_left'], new['note'], id))
        if new['status'] != k['status']:
            log_event(ctx.conn, ctx.org, 'kid', id, f'Статус: {k["status"]} → {new["status"]}', 'event', ctx.uid)
    return _kid_out(get_owned(ctx.conn, 'kids', ctx.org, id))


@api('DELETE', '/kids/{id}', cap='students', tag=T, summary='Удалить ученика')
def kids_delete(ctx, id: int):
    get_owned(ctx.conn, 'kids', ctx.org, id, 'Ученик')
    ctx.conn.execute('DELETE FROM kids WHERE id = ?', (id,))
    return {'ok': True}


# ---------- расходы ----------
@api('GET', '/expenses', cap='finance', tag='Финансы', summary='Расходы (параметр month=ГГГГ-ММ)')
def expenses_list(ctx):
    m = ctx.query.get('month')
    q, a = 'SELECT * FROM expenses WHERE org_id = ?', [ctx.org]
    if m:
        q += ' AND substr(date, 1, 7) = ?'
        a.append(m)
    return rows(ctx.conn.execute(q + ' ORDER BY date DESC, id DESC', a))


@api('POST', '/expenses', cap='finance', body=ExpenseIn, tag='Финансы', summary='Добавить расход')
def expenses_create(ctx, body: ExpenseIn):
    eid = ctx.conn.execute('INSERT INTO expenses (org_id, cat, amount, date, note) VALUES (?, ?, ?, ?, ?)', (ctx.org, body.cat, body.amount, body.date or today(), body.note)).lastrowid
    return {**get_owned(ctx.conn, 'expenses', ctx.org, eid), '_created': True}


@api('PUT', '/expenses/{id}', cap='finance', body=ExpenseIn, tag='Финансы', summary='Изменить расход')
def expenses_update(ctx, id: int, body: ExpenseIn):
    get_owned(ctx.conn, 'expenses', ctx.org, id, 'Расход')
    ctx.conn.execute('UPDATE expenses SET cat = ?, amount = ?, date = ?, note = ? WHERE id = ?', (body.cat, body.amount, body.date or today(), body.note, id))
    return get_owned(ctx.conn, 'expenses', ctx.org, id)


@api('DELETE', '/expenses/{id}', cap='finance', tag='Финансы', summary='Удалить расход')
def expenses_delete(ctx, id: int):
    get_owned(ctx.conn, 'expenses', ctx.org, id, 'Расход')
    ctx.conn.execute('DELETE FROM expenses WHERE id = ?', (id,))
    return {'ok': True}


# ---------- закупки ----------
def _item_out(conn, it):
    return {**it, 'h': [[p['date'], p['price']] for p in conn.execute('SELECT date, price FROM item_prices WHERE item_id = ? ORDER BY date', (it['id'],))]}


@api('GET', '/items', cap='billing', tag='Закупки', summary='Список закупок с историей цен')
def items_list(ctx):
    return [_item_out(ctx.conn, it) for it in rows(ctx.conn.execute('SELECT * FROM items WHERE org_id = ? ORDER BY id DESC', (ctx.org,)))]


@api('POST', '/items', cap='billing', body=ItemIn, tag='Закупки', summary='Добавить товар (с первой ценой)')
def items_create(ctx, body: ItemIn):
    if not body.price:
        raise ApiError(422, 'Укажите цену товара', 'validation')
    iid = ctx.conn.execute('INSERT INTO items (org_id, name, unit, target, link) VALUES (?, ?, ?, ?, ?)', (ctx.org, body.name, body.unit, body.target, body.link)).lastrowid
    ctx.conn.execute('INSERT INTO item_prices (item_id, date, price) VALUES (?, ?, ?)', (iid, today(), body.price))
    return {**_item_out(ctx.conn, get_owned(ctx.conn, 'items', ctx.org, iid)), '_created': True}


@api('PUT', '/items/{id}', cap='billing', body=ItemIn, tag='Закупки', summary='Изменить товар')
def items_update(ctx, id: int, body: ItemIn):
    get_owned(ctx.conn, 'items', ctx.org, id, 'Товар')
    ctx.conn.execute('UPDATE items SET name = ?, unit = ?, target = ?, link = ? WHERE id = ?', (body.name, body.unit, body.target, body.link, id))
    return _item_out(ctx.conn, get_owned(ctx.conn, 'items', ctx.org, id))


@api('POST', '/items/{id}/prices', cap='billing', body=PriceIn, tag='Закупки', summary='Записать цену товара на дату')
def items_price(ctx, id: int, body: PriceIn):
    get_owned(ctx.conn, 'items', ctx.org, id, 'Товар')
    ctx.conn.execute('INSERT INTO item_prices (item_id, date, price) VALUES (?, ?, ?) ON CONFLICT (item_id, date) DO UPDATE SET price = excluded.price', (id, body.date or today(), body.price))
    return _item_out(ctx.conn, get_owned(ctx.conn, 'items', ctx.org, id))


@api('DELETE', '/items/{id}', cap='billing', tag='Закупки', summary='Удалить товар')
def items_delete(ctx, id: int):
    get_owned(ctx.conn, 'items', ctx.org, id, 'Товар')
    ctx.conn.execute('DELETE FROM items WHERE id = ?', (id,))
    return {'ok': True}


# ---------- шаблоны и правила ----------
@api('GET', '/templates', tag='Автоматизация', summary='Шаблоны сообщений')
def templates_list(ctx):
    return rows(ctx.conn.execute('SELECT id, name, text FROM templates WHERE org_id = ? ORDER BY id', (ctx.org,)))


@api('POST', '/templates', cap='settings', body=TemplateIn, tag='Автоматизация', summary='Добавить шаблон')
def templates_create(ctx, body: TemplateIn):
    tid = ctx.conn.execute('INSERT INTO templates (org_id, name, text) VALUES (?, ?, ?)', (ctx.org, body.name, body.text)).lastrowid
    return {'id': tid, 'name': body.name, 'text': body.text, '_created': True}


@api('PUT', '/templates/{id}', cap='settings', body=TemplateIn, tag='Автоматизация', summary='Изменить шаблон')
def templates_update(ctx, id: int, body: TemplateIn):
    get_owned(ctx.conn, 'templates', ctx.org, id, 'Шаблон')
    ctx.conn.execute('UPDATE templates SET name = ?, text = ? WHERE id = ?', (body.name, body.text, id))
    return {'id': id, 'name': body.name, 'text': body.text}


@api('DELETE', '/templates/{id}', cap='settings', tag='Автоматизация', summary='Удалить шаблон')
def templates_delete(ctx, id: int):
    get_owned(ctx.conn, 'templates', ctx.org, id, 'Шаблон')
    ctx.conn.execute('UPDATE rules SET tpl_id = NULL WHERE tpl_id = ? AND org_id = ?', (id, ctx.org))
    ctx.conn.execute('DELETE FROM templates WHERE id = ?', (id,))
    return {'ok': True}


@api('GET', '/rules', tag='Автоматизация', summary='Правила автоматизации')
def rules_list(ctx):
    return rows(ctx.conn.execute('SELECT id, trigger, task, days, tpl_id FROM rules WHERE org_id = ? ORDER BY id', (ctx.org,)))


@api('POST', '/rules', cap='settings', body=RuleIn, tag='Автоматизация', summary='Добавить правило: событие → задача')
def rules_create(ctx, body: RuleIn):
    if body.tpl_id:
        get_owned(ctx.conn, 'templates', ctx.org, body.tpl_id, 'Шаблон')
    rid = ctx.conn.execute('INSERT INTO rules (org_id, trigger, task, days, tpl_id) VALUES (?, ?, ?, ?, ?)', (ctx.org, body.trigger, body.task, body.days, body.tpl_id or None)).lastrowid
    return {'id': rid, **body.model_dump(), '_created': True}


@api('PUT', '/rules/{id}', cap='settings', body=RuleIn, tag='Автоматизация', summary='Изменить правило')
def rules_update(ctx, id: int, body: RuleIn):
    get_owned(ctx.conn, 'rules', ctx.org, id, 'Правило')
    if body.tpl_id:
        get_owned(ctx.conn, 'templates', ctx.org, body.tpl_id, 'Шаблон')
    ctx.conn.execute('UPDATE rules SET trigger = ?, task = ?, days = ?, tpl_id = ? WHERE id = ?', (body.trigger, body.task, body.days, body.tpl_id or None, id))
    return {'id': id, **body.model_dump()}


@api('DELETE', '/rules/{id}', cap='settings', tag='Автоматизация', summary='Удалить правило')
def rules_delete(ctx, id: int):
    get_owned(ctx.conn, 'rules', ctx.org, id, 'Правило')
    ctx.conn.execute('DELETE FROM rules WHERE id = ?', (id,))
    return {'ok': True}
