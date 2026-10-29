"""Демо-центр «Умный Зайка» в формате резервной копии (используется /org/demo и тестами)."""
import datetime as dt


def _d(base: str, n: int) -> str:
    return (dt.date.fromisoformat(base) + dt.timedelta(days=n)).isoformat()


def _shift_month(ym: str, n: int) -> str:
    y, m = map(int, ym.split('-'))
    m += n
    while m < 1:
        m += 12
        y -= 1
    while m > 12:
        m -= 12
        y += 1
    return f'{y:04d}-{m:02d}'


def demo_backup(today: str) -> dict:
    ym = today[:7]
    ms = ym + '-01'
    groups = [
        (1, 'Совята', 'Английский', [5, 6], 'Айгуль Нурлановна', 'Кабинет 1', [1, 3, 5], '16:00', 8),
        (2, 'Механики', 'Робототехника', [8, 10], 'Данияр Серикович', 'Лаборатория', [2, 4], '17:00', 8),
        (3, 'Акварельки', 'Рисование', [4, 5], 'Мадина Ерболатовна', 'Кабинет 2', [1, 3], '15:00', 8),
        (4, 'Ладья', 'Шахматы', [7, 9], 'Руслан Асхатович', 'Кабинет 3', [2, 4, 6], '16:30', 8),
        (5, 'Эксперты', 'Английский', [8, 10], 'Айгуль Нурлановна', 'Кабинет 1', [3, 5], '18:00', 8),
        (6, 'Ритм', 'Танцы', [6, 8], 'Алия Маратовна', 'Зал', [6, 0], '11:00', 10),
    ]
    families = ['Динара Ким', 'Азамат Беков', 'Салтанат Серикова', 'Ирина Волкова', 'Ерлан Омаров', 'Гульнара Тлеуова']
    kids = [('Мария Ким', 5, 1, 11, 6), ('Артём Ким', 9, 2, 11, 5), ('Тимур Беков', 6, 1, 12, 1), ('Амина Серикова', 5, 1, 13, 7), ('Алихан Омаров', 9, 4, 15, 4),
            ('Дана Омарова', 4, 3, 15, 3), ('Егор Волков', 8, 2, 14, 2), ('Елизавета Волкова', 5, 3, 14, 0), ('Аружан Тлеуова', 7, 6, 16, 5), ('Мирас Тлеуов', 9, 5, 16, 6),
            ('Софья Нурланова', 6, 1, 13, 8), ('Кирилл Захаров', 8, 4, 12, 3)]
    data = {
        'v': 3,
        'center': {'price': 3000, 'pack': 8, 'sib2': 10, 'sib3': 15, 'tax': 4},
        'groups': [{'id': i, 'name': n, 'dir': d, 'ages': a, 'teacher': t, 'room': r, 'days': ds, 'time': tm, 'cap': c} for i, n, d, a, t, r, ds, tm, c in groups],
        'families': [{'id': 11 + i, 'parent': p, 'phone': f'+7 70{i + 1} 555 0{i + 1} 1{i}'} for i, p in enumerate(families)],
        'kids': [{'id': 21 + i, 'name': n, 'age': a, 'gid': g, 'fid': f, 'left': l, 'status': 'trial' if i == 10 else 'active'} for i, (n, a, g, f, l) in enumerate(kids)],
        'invoices': [], 'payments': [], 'expenses': [], 'items': [], 'leads': [], 'att': {},
    }
    for f in range(11, 17):
        ids = [k['id'] for k in data['kids'] if k['fid'] == f]
        amount = sum(24000 * (1 if i == 0 else 0.9 if i == 1 else 0.85) for i in range(len(ids)))
        data['invoices'].append({'fid': f, 'kids': ids, 'lessons': 8, 'amount': round(amount), 'note': 'Абонемент на месяц', 'date': ms, 'applied': True})
    clamp = lambda d: min(d, today)
    for fid, amount, method, date in [(11, 45600, 'kaspi', clamp(_d(ms, 2))), (15, 45600, 'transfer', clamp(_d(ms, 4))), (13, 45600, 'cash', today), (16, 45600, 'kaspi', today), (14, 20000, 'cash', today)]:
        data['payments'].append({'fid': fid, 'amount': amount, 'method': method, 'date': date, 'note': ''})
    data['payments'].append({'fid': None, 'amount': 1_450_000, 'method': 'kaspi', 'date': ms, 'note': 'Оплаты ранее в этом месяце (пример)'})
    for i, v in enumerate([1.42, 1.31, 1.55, 1.72]):
        m = _shift_month(ym, i - 4) + '-15'
        data['payments'].append({'fid': None, 'amount': round(v * 1e6), 'method': 'kaspi', 'date': m, 'note': 'Итог за месяц (пример)'})
        data['expenses'].append({'cat': 'Прочее', 'amount': round(v * 1e6 * 0.78), 'date': m, 'note': 'Итог за месяц (пример)'})
    for cat, amount in [('Зарплаты', 780000), ('Аренда', 420000), ('Реклама', 150000), ('Материалы', 90000)]:
        data['expenses'].append({'cat': cat, 'amount': amount, 'date': ms, 'note': ''})
    for kid, gid, offs in [(23, 1, [-2, -5]), (27, 2, [-3, -8, -12]), (25, 4, [-6]), (28, 3, [-9])]:
        for o in offs:
            data['att'].setdefault(_d(today, o), {}).setdefault(str(gid), {})[str(kid)] = 'absent'
    leads = [('Жанна К.', 'Ясмин', 5, 'Английский', 'Instagram', 0, ''), ('Бауыржан Т.', 'Нурсултан', 9, 'Робототехника', 'WhatsApp', 0, ''), ('Ольга М.', 'Полина', 6, 'Танцы', 'Сайт', 1, ''),
             ('Руслана А.', 'Тамерлан', 8, 'Шахматы', 'Рекомендация', 2, ''), ('Айнур С.', 'Лейла', 4, 'Рисование', 'Instagram', 2, ''), ('Марат Д.', 'Алан', 7, 'Робототехника', 'Instagram', 3, ''),
             ('Светлана П.', 'Ника', 6, 'Английский', 'Instagram', 4, 'Дорого'), ('Ержан К.', 'Айлин', 5, 'Танцы', '2ГИС', 4, 'Далеко от дома'), ('Алия Б.', 'Тимур', 8, 'Английский', 'Рекомендация', 4, 'Нет времени')]
    for i, (p, c, a, d, s, st, r) in enumerate(leads):
        data['leads'].append({'id': 100 + i, 'parent': p, 'child': c, 'age': a, 'dir': d, 'src': s, 'stage': st, 'maxStage': 2 if st == 4 else st, 'reason': r, 'date': _d(today, -3 * i)})
    for name, unit, target, ps in [('Бумага А4, 500 листов', 'пачка', 2300, [2190, 2290, 2450, 2590]), ('Акварель, 12 цветов', 'набор', 1300, [1490, 1450, 1390, 1320]),
                                   ('Конструктор для робототехники', 'набор', 14500, [14900, 15400, 15900, 15900]), ('Маркеры для доски, 4 шт.', 'набор', 1100, [1290, 1190, 1190, 1090])]:
        data['items'].append({'name': name, 'unit': unit, 'target': target, 'h': [[_shift_month(ym, i - 3) + '-05', p] for i, p in enumerate(ps)]})
    return data
