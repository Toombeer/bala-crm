"""Работа центра: журнал посещений, заявки, задачи, история и заметки."""
from ..core import ApiError, api, today
from ..db import row, rows, tx
from ..schemas import AttendanceIn, LeadIn, NoteIn, StageIn, TaskIn, TaskPatch
from ..services import add_task, get_owned, lead_stage, log_event, run_rules, set_marks

# ---------- журнал ----------
@api('GET', '/attendance', tag='Журнал', summary='Отметки за дату (date=ГГГГ-ММ-ДД, group_id необязателен)')
def attendance_get(ctx):
    d = ctx.query.get('date') or today()
    q, a = 'SELECT date, group_id, kid_id, status FROM attendance WHERE org_id = ? AND date = ?', [ctx.org, d]
    if ctx.query.get('group_id'):
        q += ' AND group_id = ?'
        a.append(int(ctx.query['group_id']))
    return rows(ctx.conn.execute(q, a))


@api('PUT', '/attendance', cap='attendance', body=AttendanceIn, tag='Журнал',
     summary='Отметить группу: {kid_id: статус или null}. «Был» и «опоздал» списывают занятие; запускаются правила пропуска и продления')
def attendance_put(ctx, body: AttendanceIn):
    if body.date > today():
        raise ApiError(422, 'Нельзя отметить будущую дату', 'validation')
    with tx(ctx.conn):
        res = set_marks(ctx.conn, ctx.org, ctx.uid, body.date, body.group_id, body.marks)
    return res


# ---------- заявки ----------
@api('GET', '/leads', cap='leads', tag='Заявки', summary='Заявки (stage=0..4 для фильтра)')
def leads_list(ctx):
    q, a = 'SELECT * FROM leads WHERE org_id = ?', [ctx.org]
    if ctx.query.get('stage') is not None and ctx.query.get('stage') != '':
        q += ' AND stage = ?'
        a.append(int(ctx.query['stage']))
    return rows(ctx.conn.execute(q + ' ORDER BY date DESC, id DESC', a))


@api('POST', '/leads', cap='leads', body=LeadIn, tag='Заявки', summary='Новая заявка (запускает правила этапа)')
def leads_create(ctx, body: LeadIn):
    if body.stage == 4 and not body.reason:
        raise ApiError(422, 'Укажите причину отказа', 'validation')
    with tx(ctx.conn):
        lid = ctx.conn.execute('INSERT INTO leads (org_id, parent, phone, child, age, dir, src, stage, max_stage, reason, note, date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                               (ctx.org, body.parent, body.phone, body.child, body.age, body.dir, body.src, body.stage, min(body.stage, 3), body.reason if body.stage == 4 else '', body.note, today())).lastrowid
        log_event(ctx.conn, ctx.org, 'lead', lid, f'Заявка создана: {body.src}' + (f', {body.dir}' if body.dir else ''), 'create', ctx.uid)
        run_rules(ctx.conn, ctx.org, f'lead{body.stage}', 'lead', lid, body.child or body.parent)
    return {**get_owned(ctx.conn, 'leads', ctx.org, lid), '_created': True}


@api('PUT', '/leads/{id}', cap='leads', body=LeadIn, tag='Заявки', summary='Изменить заявку (смена этапа запускает правила)')
def leads_update(ctx, id: int, body: LeadIn):
    lead = get_owned(ctx.conn, 'leads', ctx.org, id, 'Заявка')
    with tx(ctx.conn):
        ctx.conn.execute('UPDATE leads SET parent = ?, phone = ?, child = ?, age = ?, dir = ?, src = ?, note = ? WHERE id = ?',
                         (body.parent, body.phone, body.child, body.age, body.dir, body.src, body.note, id))
        if body.stage != lead['stage']:
            lead_stage(ctx.conn, ctx.org, {**lead, 'child': body.child, 'parent': body.parent}, body.stage, body.reason, ctx.uid)
        elif body.stage == 4:
            ctx.conn.execute('UPDATE leads SET reason = ? WHERE id = ?', (body.reason, id))
    return get_owned(ctx.conn, 'leads', ctx.org, id)


@api('POST', '/leads/{id}/stage', cap='leads', body=StageIn, tag='Заявки', summary='Перевести заявку на этап (для «Отказа» нужна причина)')
def leads_stage(ctx, id: int, body: StageIn):
    lead = get_owned(ctx.conn, 'leads', ctx.org, id, 'Заявка')
    with tx(ctx.conn):
        if body.note is not None:
            ctx.conn.execute('UPDATE leads SET note = ? WHERE id = ?', (body.note, id))
        lead_stage(ctx.conn, ctx.org, lead, body.stage, body.reason, ctx.uid)
    return get_owned(ctx.conn, 'leads', ctx.org, id)


@api('DELETE', '/leads/{id}', cap='leads', tag='Заявки', summary='Удалить заявку')
def leads_delete(ctx, id: int):
    get_owned(ctx.conn, 'leads', ctx.org, id, 'Заявка')
    ctx.conn.execute('DELETE FROM leads WHERE id = ?', (id,))
    ctx.conn.execute("DELETE FROM tasks WHERE org_id = ? AND ref_type = 'lead' AND ref_id = ? AND done = 0", (ctx.org, id))
    return {'ok': True}


# ---------- задачи ----------
def _check_ref(ctx, ref_type, ref_id):
    if ref_type:
        get_owned(ctx.conn, {'lead': 'leads', 'kid': 'kids', 'fam': 'families'}[ref_type], ctx.org, ref_id or 0, 'Связанная запись')


@api('GET', '/tasks', cap='tasks', tag='Задачи', summary='Задачи (done=0|1, mine=1)')
def tasks_list(ctx):
    q, a = 'SELECT * FROM tasks WHERE org_id = ?', [ctx.org]
    if ctx.query.get('done') in ('0', '1'):
        q += ' AND done = ?'
        a.append(int(ctx.query['done']))
    if ctx.query.get('mine') == '1':
        q += ' AND assignee_id = ?'
        a.append(ctx.uid)
    return rows(ctx.conn.execute(q + ' ORDER BY done, due IS NULL, due, id', a))


@api('POST', '/tasks', cap='tasks', body=TaskIn, tag='Задачи', summary='Новая задача')
def tasks_create(ctx, body: TaskIn):
    _check_ref(ctx, body.ref_type, body.ref_id)
    if body.assignee_id:
        get_owned(ctx.conn, 'users', ctx.org, body.assignee_id, 'Сотрудник')
    tid = ctx.conn.execute('INSERT INTO tasks (org_id, title, due, assignee_id, ref_type, ref_id, tpl_id, auto, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)',
                           (ctx.org, body.title, body.due, body.assignee_id or None, body.ref_type, body.ref_id if body.ref_type else None, body.tpl_id, today())).lastrowid
    if body.ref_type:
        log_event(ctx.conn, ctx.org, body.ref_type, body.ref_id, 'Задача: ' + body.title, 'task', ctx.uid)
    return {**get_owned(ctx.conn, 'tasks', ctx.org, tid), '_created': True}


@api('PATCH', '/tasks/{id}', cap='tasks', body=TaskPatch, tag='Задачи', summary='Изменить задачу или отметить выполненной')
def tasks_patch(ctx, id: int, body: TaskPatch):
    t = get_owned(ctx.conn, 'tasks', ctx.org, id, 'Задача')
    d = body.model_dump(exclude_unset=True)
    if d.get('assignee_id'):
        get_owned(ctx.conn, 'users', ctx.org, d['assignee_id'], 'Сотрудник')
    done = t['done'] if d.get('done') is None else int(d['done'])
    ctx.conn.execute('UPDATE tasks SET title = ?, due = ?, assignee_id = ?, done = ?, done_at = ? WHERE id = ?',
                     (d.get('title') or t['title'], d['due'] if 'due' in d else t['due'], (d['assignee_id'] or None) if 'assignee_id' in d else t['assignee_id'],
                      done, today() if done and not t['done'] else (t['done_at'] if done else None), id))
    if done and not t['done'] and t['ref_type']:
        log_event(ctx.conn, ctx.org, t['ref_type'], t['ref_id'], 'Выполнено: ' + t['title'], 'task', ctx.uid)
    return get_owned(ctx.conn, 'tasks', ctx.org, id)


@api('DELETE', '/tasks/{id}', cap='tasks', tag='Задачи', summary='Удалить задачу')
def tasks_delete(ctx, id: int):
    get_owned(ctx.conn, 'tasks', ctx.org, id, 'Задача')
    ctx.conn.execute('DELETE FROM tasks WHERE id = ?', (id,))
    return {'ok': True}


# ---------- история ----------
@api('GET', '/events', tag='История', summary='История по записи (ref_type=lead|kid|fam&ref_id=…) или всего центра')
def events_list(ctx):
    q, a = 'SELECT * FROM events WHERE org_id = ?', [ctx.org]
    if ctx.query.get('ref_type'):
        q += ' AND ref_type = ? AND ref_id = ?'
        a += [ctx.query['ref_type'], int(ctx.query.get('ref_id') or 0)]
    return rows(ctx.conn.execute(q + ' ORDER BY id DESC LIMIT ?', a + [min(int(ctx.query.get('limit') or 100), 1000)]))


@api('POST', '/events', cap='read', body=NoteIn, tag='История', summary='Добавить заметку или записать отправленное сообщение')
def events_create(ctx, body: NoteIn):
    _check_ref(ctx, body.ref_type, body.ref_id)
    log_event(ctx.conn, ctx.org, body.ref_type, body.ref_id, body.text, body.type, ctx.uid)
    return {'ok': True, '_created': True}
