"""Сквозные проверки API: вход, права, изоляция центров, журнал, деньги, воронка, импорт."""
from conftest import Api


def setup_center(api):
    g = api('POST', '/groups', {'name': 'Совята', 'dir': 'Английский', 'days': [0, 1, 2, 3, 4, 5, 6], 'time': '16:00', 'cap': 8}, status=201)
    k1 = api('POST', '/kids', {'name': 'Маша Иванова', 'age': 5, 'group_id': g['id'], 'parent': 'Анна Иванова', 'phone': '87011234567'}, status=201)
    k2 = api('POST', '/kids', {'name': 'Петя Иванов', 'age': 7, 'group_id': g['id'], 'family_id': k1['family_id']}, status=201)
    return g, k1, k2


# ---------- вход и безопасность ----------
def test_register_login_me(client):
    r = client.post('/api/v1/auth/register', json={'center_name': 'Звезда', 'name': 'Аня', 'email': 'a@b.kz', 'password': 'longpassword'})
    assert r.status_code == 201
    assert client.post('/api/v1/auth/register', json={'center_name': 'Звезда', 'name': 'Аня', 'email': 'A@b.kz', 'password': 'longpassword'}).status_code == 409
    assert client.post('/api/v1/auth/login', json={'email': 'a@b.kz', 'password': 'wrong'}).status_code == 401
    tok = client.post('/api/v1/auth/login', json={'email': 'A@B.kz', 'password': 'longpassword'}).json()['token']
    me = client.get('/api/v1/auth/me', headers={'Authorization': 'Bearer ' + tok}).json()
    assert me['role'] == 'owner' and 'staff' in me['caps']


def test_requires_auth_and_validates(client, owner):
    assert client.get('/api/v1/kids').status_code == 401
    assert client.get('/api/v1/kids', headers={'Authorization': 'Bearer garbage'}).status_code == 401
    r = owner('POST', '/groups', {'name': '', 'days': []})
    assert 'error' in r and 'Проверьте данные' in r['error']
    assert client.get('/api/v1/nope', headers=owner.h).status_code == 404


def test_short_password_rejected(client):
    r = client.post('/api/v1/auth/register', json={'center_name': 'X', 'name': 'Y', 'email': 'short@x.kz', 'password': '123'})
    assert r.status_code == 422


def test_orgs_are_isolated(client, owner):
    g, k1, _ = setup_center(owner)
    other = client.post('/api/v1/auth/register', json={'center_name': 'Чужой', 'name': 'Б', 'email': 'other@x.kz', 'password': 'longpassword'}).json()['token']
    o = Api(client, other)
    assert o('GET', '/kids') == []
    assert o('GET', f'/kids/{k1["id"]}', status=404)
    o('PATCH', f'/kids/{k1["id"]}', {'name': 'Взлом'}, status=404)
    o('DELETE', f'/groups/{g["id"]}', status=404)
    o('POST', '/payments', {'family_id': k1['family_id'], 'amount': 100}, status=404)
    assert owner('GET', f'/kids/{k1["id"]}')['name'] == 'Маша Иванова'


def test_roles_and_revocation(client, owner):
    setup_center(owner)
    t = owner('POST', '/users', {'name': 'Педагог', 'email': 'teacher@x.kz', 'password': 'teacherpass', 'role': 'teacher'}, status=201)
    tok = client.post('/api/v1/auth/login', json={'email': 'teacher@x.kz', 'password': 'teacherpass'}).json()['token']
    teacher = Api(client, tok)
    teacher('GET', '/kids', status=200)
    teacher('GET', '/payments', status=403)
    teacher('POST', '/groups', {'name': 'X', 'days': [1]}, status=403)
    st = teacher('GET', '/state', status=200)
    assert st['payments'] == [] and st['invoices'] == [] and st['me']['role'] == 'teacher'
    owner('PATCH', f'/users/{t["id"]}', {'active': False}, status=200)
    teacher('GET', '/kids', status=401)
    owner('POST', '/users', {'name': 'Ещё владелец', 'email': 'o2@x.kz', 'password': 'longpassword', 'role': 'owner'}, status=422)


# ---------- журнал ----------
def test_attendance_decrements_and_triggers(owner):
    g, k1, k2 = setup_center(owner)
    owner('PATCH', f'/kids/{k1["id"]}', {'lessons_left': 4}, status=200)
    from bala.core import today
    d = today()
    owner('PUT', '/attendance', {'date': d, 'group_id': g['id'], 'marks': {str(k1['id']): 'was', str(k2['id']): 'absent'}}, status=200)
    assert owner('GET', f'/kids/{k1["id"]}')['lessons_left'] == 3
    owner('PUT', '/attendance', {'date': d, 'group_id': g['id'], 'marks': {str(k1['id']): 'late'}}, status=200)
    assert owner('GET', f'/kids/{k1["id"]}')['lessons_left'] == 3, 'смена «был» на «опоздал» не списывает повторно'
    owner('PUT', '/attendance', {'date': d, 'group_id': g['id'], 'marks': {str(k1['id']): None}}, status=200)
    assert owner('GET', f'/kids/{k1["id"]}')['lessons_left'] == 4, 'снятие отметки возвращает занятие'
    titles = [t['title'] for t in owner('GET', '/tasks')]
    assert any('Узнать причину пропуска: Петя Иванов' == t for t in titles)
    assert any(t.startswith('Предложить продление абонемента: Петя') for t in titles), 'у Пети 0 занятий → задача на продление'
    owner('PUT', '/attendance', {'date': '2999-01-01', 'group_id': g['id'], 'marks': {}}, status=422)


# ---------- деньги ----------
def test_invoice_payment_allocation(owner):
    g, k1, k2 = setup_center(owner)
    fid = k1['family_id']
    q = owner('POST', '/quote', {'kids': [k1['id'], k2['id']], 'lessons': 8}, status=200)
    assert q == {'base': 48000, 'sibling_discount': 2400, 'extra_discount': 0, 'total': 45600}
    inv = owner('POST', '/invoices', {'family_id': fid, 'kids': [k1['id'], k2['id']], 'lessons': 8, 'amount': q['total'], 'note': 'ноябрь'}, status=201)
    assert inv['status'] == 'unpaid' and '45 600 ₸' in inv['message']
    msg = owner('GET', f'/invoices/{inv["id"]}/message')
    assert msg['whatsapp'].startswith('https://wa.me/77011234567?text=')
    p1 = owner('POST', '/payments', {'family_id': fid, 'amount': 20000, 'method': 'cash'}, status=201)
    assert p1['debt_left'] == 25600
    assert owner('GET', f'/kids/{k1["id"]}')['lessons_left'] == 0, 'частичная оплата не добавляет занятия'
    owner('POST', '/payments', {'family_id': fid, 'amount': 25600, 'method': 'kaspi'}, status=201)
    assert owner('GET', f'/kids/{k1["id"]}')['lessons_left'] == 8
    assert owner('GET', f'/kids/{k2["id"]}')['lessons_left'] == 8
    assert owner('GET', '/debts') == []
    owner('DELETE', f'/payments/{p1["id"]}', status=200)
    assert owner('GET', '/debts')[0]['debt'] == 20000
    assert owner('GET', f'/kids/{k1["id"]}')['lessons_left'] == 8, 'занятия начисляются один раз'
    other = owner('POST', '/kids', {'name': 'Чужой', 'parent': 'Другой'}, status=201)
    owner('POST', '/invoices', {'family_id': fid, 'kids': [other['id']], 'amount': 100}, status=422)


def test_finance_report_and_csv(owner):
    owner('POST', '/expenses', {'cat': 'Аренда', 'amount': 100000}, status=201)
    owner('POST', '/payments', {'amount': 300000, 'method': 'kaspi', 'note': 'итог'}, status=201)
    owner('PATCH', '/org', {'tax': 4}, status=200)
    f = owner('GET', '/reports/finance')
    assert f['revenue'] == 300000 and f['expenses'] == 100000 and f['profit'] == 200000 and f['tax'] == 12000
    r = owner('GET', '/export/payments.csv')
    assert r.status_code == 200 and 'Дата;Семья;Сумма' in r.text


# ---------- воронка ----------
def test_lead_pipeline_and_convert(owner):
    g, *_ = setup_center(owner)
    lead = owner('POST', '/leads', {'parent': 'Ольга', 'child': 'Ника', 'phone': '+77017778899', 'src': 'Instagram', 'dir': 'Английский', 'age': 5}, status=201)
    assert any(t['title'] == 'Ответить на заявку: Ника' for t in owner('GET', '/tasks'))
    owner('POST', f'/leads/{lead["id"]}/stage', {'stage': 2}, status=200)
    titles = [t['title'] for t in owner('GET', '/tasks')]
    assert 'Напомнить о пробном занятии: Ника' in titles and 'Узнать впечатления после пробного: Ника' in titles
    owner('POST', f'/leads/{lead["id"]}/stage', {'stage': 4}, status=422)
    kid = owner('POST', '/kids', {'name': 'Ника', 'group_id': g['id'], 'parent': 'Ольга', 'phone': '+77017778899', 'status': 'trial', 'lead_id': lead['id']}, status=201)
    assert owner('GET', '/leads', stage='3')[0]['id'] == lead['id']
    ev = owner('GET', '/events', ref_type='lead', ref_id=str(lead['id']))
    assert any('Пробное → Купил' in e['text'] for e in ev)
    a = owner('GET', '/reports/analytics')
    assert a['sources']['Instagram'] == 1 and a['funnel']['Купил'] == 1
    assert kid['status'] == 'trial'


def test_tasks_and_notes(owner):
    _, k1, _ = setup_center(owner)
    t = owner('POST', '/tasks', {'title': 'Перезвонить', 'ref_type': 'kid', 'ref_id': k1['id']}, status=201)
    owner('PATCH', f'/tasks/{t["id"]}', {'done': True}, status=200)
    owner('POST', '/events', {'ref_type': 'kid', 'ref_id': k1['id'], 'text': 'Аллергия на орехи'}, status=201)
    texts = [e['text'] for e in owner('GET', '/events', ref_type='kid', ref_id=str(k1['id']))]
    assert 'Выполнено: Перезвонить' in texts and 'Аллергия на орехи' in texts
    owner('POST', '/tasks', {'title': 'X', 'ref_type': 'kid', 'ref_id': 999999}, status=404)


# ---------- данные ----------
def test_state_demo_import_reset(client, owner):
    demo = owner('POST', '/org/demo', status=201)
    assert demo['kids'] == 12
    owner('POST', '/org/demo', status=409)
    st = owner('GET', '/state')
    assert len(st['kids']) == 12 and len(st['groups']) == 6 and st['demo'] is True
    assert any(t['title'].startswith('Ответить на заявку') for t in st['tasks'])
    debts = {d['parent']: d['debt'] for d in owner('GET', '/debts')}
    assert debts == {'Азамат Беков': 45600, 'Ирина Волкова': 25600}
    backup = owner('GET', '/export/backup.json')
    owner('POST', '/org/reset', status=200)
    assert owner('GET', '/kids') == []
    res = owner('POST', '/import', backup, status=201)
    assert res['kids'] == 12
    assert {d['parent']: d['debt'] for d in owner('GET', '/debts')} == debts


def test_import_local_app_v2(owner):
    v2 = {'v': 2, 'center': {'name': 'Умный Зайка', 'price': 3000}, 'groups': [{'id': 1, 'name': 'Совята', 'days': [1, 3], 'time': '16:00', 'ages': [5, 6]}],
          'families': [{'id': 2, 'parent': 'Анна', 'phone': '87011234567'}], 'kids': [{'id': 3, 'name': 'Маша', 'gid': 1, 'fid': 2, 'left': 3, 'status': 'active'}],
          'leads': [], 'invoices': [{'fid': 2, 'kids': [3], 'lessons': 8, 'amount': 24000, 'date': '2026-10-01', 'applied': True}],
          'payments': [{'fid': 2, 'amount': 4000, 'method': 'cash', 'date': '2026-10-02'}], 'expenses': [], 'items': [], 'att': {'2026-10-05': {'1': {'3': 'was'}}}}
    owner('POST', '/import', v2, status=201)
    kid = owner('GET', '/kids')[0]
    assert kid['lessons_left'] == 3 and owner('GET', '/debts')[0]['debt'] == 20000
    assert owner('GET', '/attendance', date='2026-10-05')[0]['status'] == 'was'
    owner('POST', '/import', {'v': 9}, status=422)


def test_parent_cabinet(client, owner):
    _, k1, _ = setup_center(owner)
    token = owner('GET', '/families')[0]['token']
    r = client.get(f'/api/v1/public/family/{token}')
    assert r.status_code == 200 and r.json()['parent'] == 'Анна Иванова' and len(r.json()['kids']) == 2
    assert client.get('/api/v1/public/family/wrongtoken-wrongtoken').status_code == 404
    owner('POST', f'/families/{k1["family_id"]}/token', status=200)
    assert client.get(f'/api/v1/public/family/{token}').status_code == 404


def test_rates_parse_and_store(owner):
    from bala import rates
    xml = b'<rss><channel><item><title>USD</title><fullname>\xd0\x94\xd0\x9e\xd0\x9b\xd0\x9b\xd0\x90\xd0\xa0</fullname><description>457.09</description><quant>1</quant></item>' \
          b'<item><title>KRW</title><fullname>W</fullname><description>34.15</description><quant>100</quant></item></channel></rss>'
    items = rates.parse_rss(xml)
    assert items[0]['code'] == 'USD' and items[1]['nom'] == 100
    from bala import db
    conn = db.connect()
    try:
        rates.store(conn, '2026-10-28', [{**items[0], 'rate': 455.63}])
        rates.store(conn, '2026-10-29', items)
    finally:
        conn.close()
    r = owner('GET', '/rates')
    assert r['date'] >= '2026-10-29' and r['history']['USD'][-1][1] == 457.09


def test_openapi_and_health(client):
    o = client.get('/api/openapi.json').json()
    assert o['info']['title'] == 'BALA CRM API' and '/api/v1/payments' in o['paths']
    assert client.get('/api/v1/health').json()['ok'] is True
    assert client.get('/api/docs').status_code == 200
