#!/usr/bin/env python3
"""Собирает статические страницы сайта BALA CRM из общих шапки и подвала."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MARK = '<svg viewBox="0 0 32 32" width="{s}" height="{s}" aria-hidden="true"><path d="M16 10c0-3.2 2.2-5.6 5.6-5.6-.5 3.3-2.7 5.6-5.6 5.6z" fill="#B6F2C9"/><path d="M16 10c0-2.6-1.8-4.4-4.4-4.4.4 2.6 2.2 4.4 4.4 4.4z" fill="#8FE3AE"/><circle cx="16" cy="19.5" r="9" fill="#fff"/><circle cx="12.6" cy="18.5" r="1.5" fill="#3B1D9A"/><circle cx="19.4" cy="18.5" r="1.5" fill="#3B1D9A"/><path d="M12.6 22.4c1.8 1.9 5 1.9 6.8 0" stroke="#3B1D9A" stroke-width="1.8" fill="none" stroke-linecap="round"/><circle cx="10.4" cy="21.6" r="1.3" fill="#FFB8D5"/><circle cx="21.6" cy="21.6" r="1.3" fill="#FFB8D5"/></svg>'


def block(x, y, r, bg, fg, ch):
    return (f'<g transform="translate({x} {y}) rotate({r} 28 28)"><rect width="56" height="56" rx="13" fill="{bg}"/>'
            f'<rect x="5" y="5" width="46" height="46" rx="9" fill="none" stroke="rgba(255,255,255,.5)" stroke-width="2"/>'
            f'<text x="28" y="39" text-anchor="middle" font-family="Unbounded, Onest, system-ui, sans-serif" font-weight="700" font-size="28" fill="{fg}">{ch}</text></g>')


BLOCKS = ('<svg viewBox="0 0 200 150" aria-hidden="true" class="blocks float">' + block(16, 86, -6, '#FFD25E', '#5B2BC0', 'B') + block(74, 90, 4, '#FF8FBF', '#ffffff', 'A')
          + block(132, 86, -3, '#7BE0C3', '#164E40', 'L') + block(76, 28, -9, '#ffffff', '#6C3CE9', 'A') + '</svg>')
BLOCKS_PLAIN = BLOCKS.replace(' class="blocks float"', '')


def ico(path, size=24):
    return f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{path}</svg>'


I = {
    'cal': '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M16 3v4M8 3v4M3 10h18M8 14h3M8 17h6"/>',
    'check': '<rect x="3" y="4" width="18" height="17" rx="3"/><path d="m7.5 10.5 2 2 4-4M7.5 16h9"/>',
    'ticket': '<path d="M4 7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-2a2 2 0 0 0 0-4z"/><path d="M14 5v12" stroke-dasharray="2 2"/>',
    'wallet': '<path d="M3 7a2 2 0 0 1 2-2h13v3"/><path d="M3 7v11a2 2 0 0 0 2 2h14a1 1 0 0 0 1-1v-9a1 1 0 0 0-1-1H5a2 2 0 0 1-2-2z"/><circle cx="16.5" cy="14.5" r="1.2"/>',
    'funnel': '<path d="M3 5h18l-7 8v6l-4-2v-4z"/>',
    'bolt': '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
    'msg': '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/><path d="M8.5 11h7M8.5 14h4"/>',
    'chart': '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    'cart': '<circle cx="9" cy="20" r="1.5"/><circle cx="18" cy="20" r="1.5"/><path d="M2 3h3l2.6 12.4a2 2 0 0 0 2 1.6h8.8a2 2 0 0 0 2-1.6L22 7H6"/>',
    'coin': '<circle cx="12" cy="12" r="9"/><path d="M15 9.5c-.6-1-1.7-1.5-3-1.5-1.7 0-3 .9-3 2.2 0 3 6 1.6 6 4.6 0 1.3-1.3 2.2-3 2.2-1.4 0-2.6-.6-3.1-1.6M12 6v2M12 16v2"/>',
    'users': '<circle cx="9" cy="8" r="3.2"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><path d="M16 5.2a3 3 0 0 1 0 5.6M21 20c0-2.6-1.5-4.7-3.8-5.6"/>',
    'phone': '<rect x="6" y="2.5" width="12" height="19" rx="3"/><path d="M11 18.5h2"/>',
    'shield': '<path d="M12 3 4 6v6c0 4.4 3.4 8.2 8 9 4.6-.8 8-4.6 8-9V6z"/><path d="m9 12 2 2 4-4"/>',
    'clock': '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    'history': '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/>',
    'repeat': '<path d="M17 2l4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14M7 22l-4-4 4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/>',
    'download': '<path d="M12 3v12M7 10l5 5 5-5M4 21h16"/>',
    'menu': '<path d="M4 7h16M4 12h16M4 17h16"/>',
    'toy': '<rect x="3.5" y="11" width="8" height="8" rx="2"/><rect x="12.5" y="11" width="8" height="8" rx="2"/><rect x="8" y="3" width="8" height="8" rx="2"/>',
    'lang': '<path d="M4 5h9M8.5 3v2M6 5c0 4 3 7 6 8M11 5c0 4-3 8-7 9"/><path d="m13 21 4-9 4 9M14.5 18h5"/>',
    'ball': '<circle cx="12" cy="12" r="9"/><path d="m12 7.5 3.5 2.5-1.3 4H9.8L8.5 10zM12 3v4.5M21 10h-5.5M3 10h5.5M7 20l2.8-6M17 20l-2.8-6"/>',
    'palette': '<path d="M12 3a9 9 0 1 0 0 18c1.1 0 2-.9 2-2 0-.5-.2-1-.5-1.3-.3-.4-.5-.8-.5-1.3 0-1.1.9-2 2-2h2.3A4.7 4.7 0 0 0 21 9.8C21 6 17 3 12 3z"/><circle cx="7.5" cy="11.5" r="1.2"/><circle cx="10" cy="7.5" r="1.2"/><circle cx="14.5" cy="7.5" r="1.2"/>',
    'robot': '<rect x="5" y="8" width="14" height="11" rx="3"/><path d="M12 4v4M9 13h.01M15 13h.01M9.5 16.5h5M2 13h3M19 13h3"/>',
    'book': '<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 19V5M8 7h7"/>',
}

PAGES = [('index.html', 'Главная'), ('features.html', 'Возможности'), ('solutions.html', 'Для кого'), ('pricing.html', 'Тарифы'), ('integrations.html', 'Интеграции'), ('start.html', 'Как начать')]
NAV = [p for p in PAGES if p[0] != 'index.html']


def shot(name, alt, cls='phone'):
    return f'<div class="{cls}"><img src="assets/shots/{name}.webp" alt="{alt}" loading="lazy" decoding="async"></div>'


def browser(name, alt):
    return f'<div class="browser"><div class="bar"><i></i><i></i><i></i></div><img src="assets/shots/{name}.webp" alt="{alt}" loading="lazy" decoding="async"></div>'


def layout(file, title, desc, body):
    nav = ''.join(f'<a href="{f}"{" aria-current=\"page\"" if f == file else ""}>{t}</a>' for f, t in NAV)
    return f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="theme-color" content="#6C3CE9">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="assets/shots/desk-today.webp">
<link rel="icon" type="image/png" href="assets/favicon.png">
<link rel="apple-touch-icon" href="assets/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Onest:wght@400;500;600;700&family=Unbounded:wght@500;600;700&display=swap">
<link rel="stylesheet" href="assets/site.css?v=1">
<script src="assets/site.js?v=1"></script>
</head>
<body>
<header class="top"><div class="wrap">
  <a class="brand" href="index.html"><span class="mk">{MARK.format(s=26)}</span>BALA <small>CRM</small></a>
  <nav class="nav" id="nav" aria-label="Разделы сайта">{nav}</nav>
  <div class="actions">
    <button class="icon-btn" id="theme" aria-label="Тема"></button>
    <button class="icon-btn burger" id="burger" aria-label="Меню" aria-expanded="false" aria-controls="nav">{ico(I['menu'], 22)}</button>
    <a class="btn pri sm" href="app/">Открыть приложение</a>
  </div>
</div></header>
<main>
{body}
</main>
<footer><div class="wrap">
  <div><a class="brand" href="index.html"><span class="mk">{MARK.format(s=26)}</span>BALA <small>CRM</small></a>
    <p class="muted" style="margin-top:14px;max-width:36ch;font-size:15px">CRM для детских центров, кружков и секций. Расписание, абонементы, оплаты, заявки и аналитика в одном приложении.</p></div>
  <div><h4>Продукт</h4><ul><li><a href="features.html">Возможности</a></li><li><a href="integrations.html">Интеграции</a></li><li><a href="pricing.html">Тарифы</a></li><li><a href="app/">Открыть приложение</a></li></ul></div>
  <div><h4>Для кого</h4><ul><li><a href="solutions.html#centers">Развивающие центры</a></li><li><a href="solutions.html#lang">Языковые школы</a></li><li><a href="solutions.html#sport">Спортивные секции</a></li><li><a href="solutions.html#art">Творческие студии</a></li></ul></div>
  <div><h4>Помощь</h4><ul><li><a href="start.html">Как начать</a></li><li><a href="start.html#install">Установка на телефон</a></li><li><a href="start.html#backup">Резервная копия</a></li><li><a href="pricing.html#faq">Вопросы и ответы</a></li></ul></div>
  <div class="copy"><span>© <span id="year">2026</span> BALA CRM</span><span>Сделано для детских центров Казахстана</span></div>
</div></footer>
</body>
</html>
'''


def cta(title='Попробуйте BALA CRM на своём центре', text='Бесплатно, без регистрации и карты. Откройте приложение, введите название центра и добавьте первую группу.'):
    return f'''<section><div class="wrap"><div class="cta">
  <div><h2>{title}</h2><p>{text}</p><div class="btns" style="margin-top:26px"><a class="btn" href="app/">Открыть BALA CRM</a><a class="btn ghost" href="start.html">Как начать</a></div></div>
  {BLOCKS_PLAIN}
</div></div></section>'''


# ====================================================================== ГЛАВНАЯ
FEATS = [
    ('cal', 't-vio', 'Расписание и журнал', 'Группы по дням недели, отметки одним нажатием или текстом: «все были, кроме Маши». Занятия сами списываются с абонемента.'),
    ('ticket', 't-sun', 'Абонементы', 'Остаток занятий у каждого ребёнка, семейные скидки на второго и третьего, напоминание, когда пора продлевать.'),
    ('wallet', 't-mint', 'Оплаты и долги', 'Kaspi, наличные со сдачей и переводы. Частичные оплаты, список должников и напоминание в WhatsApp одной кнопкой.'),
    ('funnel', 't-pink', 'Заявки и воронка', 'Каждое обращение из Instagram, WhatsApp и звонков: от «Новая» до «Купил». Причины отказов попадают в аналитику.'),
    ('bolt', 't-sky', 'Автоматизация', 'Правила «когда → что сделать». Новая заявка, пропуск, кончается абонемент — и задача с готовым сообщением уже стоит.'),
    ('msg', 't-vio', 'Сообщения по шаблонам', 'Имя родителя, ребёнка, долг и ссылка Kaspi подставляются сами. Отправка в WhatsApp, всё сохраняется в истории.'),
    ('check', 't-mint', 'Задачи', 'Перезвонить, напомнить, проверить оплату. Сроки, ответственные, просроченные — на главном экране.'),
    ('chart', 't-pink', 'Аналитика', 'Откуда приходят клиенты, конверсия в покупку, почему отказываются, посещаемость, заполненность групп.'),
    ('coin', 't-sun', 'Финансы и налог', 'Выручка, расходы по категориям, прибыль, налог по вашей ставке, график за полгода, выгрузка в Excel для бухгалтера.'),
]

index_body = f'''
<section class="hero"><div class="wrap">
  <div>
    <span class="eyebrow">CRM для детских центров</span>
    <h1>Детский центр <em>под контролем</em>. С телефона.</h1>
    <p class="lead">BALA CRM ведёт расписание, посещения, абонементы, оплаты Kaspi и наличными, заявки и задачи. Администратор тратит на учёт минуты, а владелец видит деньги и загрузку групп каждый день.</p>
    <div class="btns"><a class="btn pri" href="app/">Открыть бесплатно</a><a class="btn" href="features.html">Все возможности</a></div>
    <div class="note"><span>Без регистрации</span><span>Работает на телефоне и компьютере</span><span>Тенге и Kaspi</span></div>
  </div>
  <div class="stage">
    {browser('desk-today', 'Главный экран BALA CRM на компьютере')}
    <div class="phone float"><img src="assets/shots/m-today.webp" alt="Главный экран BALA CRM на телефоне" decoding="async"></div>
    {BLOCKS}
  </div>
</div></section>

<div class="facts"><div class="wrap">
  <div class="fact"><b>1 минута</b><span>чтобы отметить группу: «все были, кроме Маши»</span></div>
  <div class="fact"><b>3 способа оплаты</b><span>Kaspi, наличные со сдачей, перевод</span></div>
  <div class="fact"><b>48 валют</b><span>курсы Нацбанка РК обновляются каждый день</span></div>
  <div class="fact"><b>0 ₸</b><span>чтобы начать: откройте и работайте</span></div>
</div></div>

<section><div class="wrap">
  <div class="sec-head"><span class="eyebrow">Было и стало</span><h2>Тетрадка, WhatsApp и Excel заменяются одним приложением</h2></div>
  <div class="card lift">
    <div class="pain"><span class="was">Посещения в тетради, остаток занятий считают по памяти</span><span class="arr">→</span><span class="now">Отметка в журнале сама списывает занятие и показывает остаток</span></div>
    <div class="pain"><span class="was">Кто не заплатил, видно только в конце месяца</span><span class="arr">→</span><span class="now">Список должников и напоминание родителю в WhatsApp в одно нажатие</span></div>
    <div class="pain"><span class="was">Заявки из Instagram теряются в переписке</span><span class="arr">→</span><span class="now">Каждая заявка в воронке, с задачей «ответить» и историей</span></div>
    <div class="pain"><span class="was">Ребёнок перестал ходить, а заметили через месяц</span><span class="arr">→</span><span class="now">Риск ухода: пропуски, долг и конец абонемента видны сразу</span></div>
    <div class="pain"><span class="was">Непонятно, сколько центр заработал после аренды и зарплат</span><span class="arr">→</span><span class="now">Выручка, расходы, прибыль и налог на одном экране</span></div>
  </div>
</div></section>

<section class="band"><div class="wrap">
  <div class="sec-head center"><span class="eyebrow">Возможности</span><h2>Всё, что нужно детскому центру, и ничего лишнего</h2><p class="lead">Мы взяли подход больших CRM: воронку, автоматические задачи, шаблоны сообщений, историю клиента. И переложили его на язык детского центра: группы, абонементы, родители, пропуски.</p></div>
  <div class="grid g3">{''.join(f'<div class="card"><div class="ic {t}">{ico(I[i])}</div><h3>{h}</h3><p>{p}</p></div>' for i, t, h, p in FEATS)}</div>
  <div class="btns" style="justify-content:center;margin-top:36px"><a class="btn" href="features.html">Подробно о каждой функции</a></div>
</div></section>

<section><div class="wrap">
  <div class="feature">
    <div><span class="eyebrow">День администратора</span><h2>Как выглядит обычный день в BALA CRM</h2>
      <ol class="day" style="padding:0;margin:28px 0 0">
        <li><time>09:00</time><div><b>Открыть «Сегодня»</b><span>Занятия дня, задачи, просроченные дела и кто скоро продлевает.</span></div></li>
        <li><time>10:30</time><div><b>Ответить на заявки</b><span>Приложение уже поставило задачу и подставило шаблон ответа.</span></div></li>
        <li><time>16:00</time><div><b>Отметить группу</b><span>«Все были, кроме Тимура». Занятия списаны, пропуск попал в задачи.</span></div></li>
        <li><time>18:30</time><div><b>Принять оплату</b><span>Наличные со сдачей или Kaspi. Долг закрыт, абонемент продлён.</span></div></li>
        <li><time>20:00</time><div><b>Сверить кассу</b><span>Сколько принято сегодня наличными и через Kaspi.</span></div></li>
      </ol></div>
    <div class="media">{shot('m-journal', 'Журнал занятия в BALA CRM')}{shot('m-cash', 'Приём наличных со сдачей')}</div>
  </div>
</div></section>

<section class="band"><div class="wrap">
  <div class="feature rev">
    <div><span class="eyebrow">Автоматизация</span><h2>Приложение само напоминает, что сделать</h2>
      <p class="lead" style="margin:18px 0 26px">Правила работают как цифровая воронка: событие → задача с готовым сообщением. Правила можно менять и добавлять свои.</p>
      <div class="rule"><div class="when"><small>Когда</small>Новая заявка</div><span class="go">→</span><div class="then"><small>Задача</small>Ответить в тот же день, шаблон «Ответ на заявку»</div></div>
      <div class="rule"><div class="when"><small>Когда</small>Заявка перешла в «Пробное»</div><span class="go">→</span><div class="then"><small>Задача</small>Напомнить о пробном и через 2 дня узнать впечатления</div></div>
      <div class="rule"><div class="when"><small>Когда</small>Осталось 2 занятия</div><span class="go">→</span><div class="then"><small>Задача</small>Предложить продление, шаблон с остатком занятий</div></div>
      <div class="rule"><div class="when"><small>Когда</small>Ребёнок пропустил занятие</div><span class="go">→</span><div class="then"><small>Задача</small>Узнать причину и предложить отработку</div></div>
    </div>
    <div class="media">{shot('m-tasks', 'Задачи в BALA CRM')}{shot('m-message', 'Сообщение родителю по шаблону')}</div>
  </div>
</div></section>

<section><div class="wrap">
  <div class="sec-head"><span class="eyebrow">Экраны</span><h2>Посмотрите приложение изнутри</h2><p class="lead">Это настоящие экраны BALA CRM на демо-данных центра «Умный Зайка».</p></div>
  <div class="gallery">
    {''.join(f'<figure>{shot(n, c)}<figcaption>{c}</figcaption></figure>' for n, c in [('m-today', 'Сегодня'), ('m-payments', 'Оплаты и долги'), ('m-lead', 'Карточка заявки'), ('m-analytics', 'Аналитика'), ('m-purchases', 'Цены на материалы'), ('m-rates', 'Курсы валют'), ('m-today-dark', 'Тёмная тема')])}
  </div>
</div></section>

<section class="band"><div class="wrap">
  <div class="sec-head center"><span class="eyebrow">Для кого</span><h2>Подходит центрам любого направления</h2></div>
  <div class="grid g3">
    {''.join(f'<a class="card" style="text-decoration:none;color:inherit" href="solutions.html#{a}"><div class="ic {t}">{ico(I[e])}</div><h3>{h}</h3><p>{p}</p></a>' for a, t, e, h, p in [
        ('centers', 't-sun', 'toy', 'Развивающие центры', 'Много групп по возрасту, пробные занятия, семьи с несколькими детьми.'),
        ('lang', 't-sky', 'lang', 'Языковые школы', 'Уровни, индивидуальные занятия, продления абонементов каждый месяц.'),
        ('sport', 't-mint', 'ball', 'Спортивные секции', 'Посещаемость, пропуски, сезонные абонементы и форма.'),
        ('art', 't-pink', 'palette', 'Творческие студии', 'Рисование, музыка, танцы: материалы, закупки и выступления.'),
        ('tech', 't-vio', 'robot', 'Робототехника и IT', 'Дорогие наборы, курсы валют для закупок, малые группы.'),
        ('school', 't-sun', 'book', 'Подготовка к школе и логопеды', 'Индивидуальные занятия, заметки по ребёнку, связь с родителями.')])}
  </div>
</div></section>

<section><div class="wrap">
  <div class="sec-head"><span class="eyebrow">Вопросы</span><h2>Коротко о главном</h2></div>
  <div class="faq">
    <details><summary>Сколько стоит?</summary><p>Версия для одного устройства бесплатна и включает все функции. Облачная версия для команды и нескольких устройств готовится, предварительные цены на странице <a href="pricing.html">Тарифы</a>.</p></details>
    <details><summary>Где хранятся данные?</summary><p>Сейчас только на вашем устройстве, в браузере. На сервер они не отправляются. Раз в неделю сохраняйте резервную копию в настройках. Подробнее на странице <a href="start.html#backup">Как начать</a>.</p></details>
    <details><summary>Как работает Kaspi?</summary><p>Вы вставляете ссылку для оплаты из приложения Kaspi Pay. Она добавляется в счета и напоминания, которые уходят родителям в WhatsApp. Оплату администратор отмечает сам, когда приходит уведомление Kaspi.</p></details>
    <details><summary>Нужно ли что-то устанавливать?</summary><p>Нет. BALA CRM открывается в браузере. На телефоне его можно добавить на экран «Домой», и он будет работать как приложение, в том числе без интернета.</p></details>
    <details><summary>Можно перенести данные из «Умного Зайки»?</summary><p>Да. Если вы пользовались приложением «Умный Зайка» в этом же браузере, BALA CRM при первом запуске предложит перенести данные. Или восстановите их из файла резервной копии.</p></details>
  </div>
</div></section>
{cta()}
'''

# ====================================================================== ВОЗМОЖНОСТИ
def feature(eyebrow, title, text, points, media, rev=False, band=False):
    return f'''<section{' class="band"' if band else ''}><div class="wrap"><div class="feature{' rev' if rev else ''}">
  <div><span class="eyebrow">{eyebrow}</span><h2>{title}</h2><p class="lead" style="margin-top:16px">{text}</p><ul class="tick">{''.join(f'<li>{p}</li>' for p in points)}</ul></div>
  <div class="media">{media}</div></div></div></section>'''


features_body = f'''
<section class="page-hero"><div class="wrap"><span class="eyebrow">Возможности</span><h1>Каждая функция придумана для детского центра</h1>
<p class="lead">Ниже всё, что умеет BALA CRM сегодня. Каждый пункт можно попробовать прямо сейчас в приложении, на своих данных или на демо-центре.</p>
<div class="btns" style="margin-top:28px"><a class="btn pri" href="app/">Открыть приложение</a><a class="btn" href="#roadmap">Что будет дальше</a></div></div></section>
{feature('Расписание и журнал', 'Отметить группу за минуту', 'Журнал открывается из расписания или с главного экрана. Отмечайте кнопками или текстом, приложение само поймёт имена, в том числе уменьшительные.', ['Статусы: был, опоздал, не был, уважительная причина', 'Быстрая отметка: «все были, кроме Маши, Тимур опоздал»', '«Был» и «опоздал» списывают занятие, повторное нажатие снимает отметку', 'Можно отметить прошедшую дату, например перенос', 'Группы с педагогом, кабинетом, возрастом, местами и своей ценой'], shot('m-journal', 'Журнал занятия') + shot('m-today', 'Сегодня'), band=False)}
{feature('Ученики и семьи', 'Вся информация о ребёнке в одной карточке', 'Карточка ученика собирает остаток занятий, пропуски, семью и долг, задачи и историю всех событий.', ['Семья с несколькими детьми и общим счётом', 'Статусы: пробный, активный, пауза, ушёл', 'Заметки: аллергии, кто забирает, пожелания родителей', 'История: оплаты, счета, сообщения, заметки, этапы', 'Риск ухода: пропуски, долг и конец абонемента'], shot('m-lead', 'Карточка') + shot('m-today-dark', 'Тёмная тема'), rev=True, band=True)}
{feature('Оплаты', 'Kaspi, наличные и переводы без путаницы', 'Счёт считается сам, с семейной скидкой. Оплата может быть частичной, переплата уходит в следующий счёт. Когда счёт оплачен полностью, занятия добавляются детям автоматически.', ['Счёт в WhatsApp с вашей ссылкой Kaspi', 'Наличные: приложение считает сдачу', 'Кто должен и сколько, напоминание одной кнопкой', 'Касса за день: наличные и Kaspi отдельно', 'Калькулятор абонемента со скидками'], shot('m-payments', 'Оплаты и долги') + shot('m-cash', 'Приём наличных'))}
{feature('Заявки', 'Воронка от первого сообщения до покупки', 'Заявки идут по этапам: новая, связались, пробное, купил или отказ. По ним строится аналитика, а «Купил» в одно нажатие превращает заявку в ученика.', ['Источник: Instagram, WhatsApp, сайт, рекомендация, 2ГИС', 'Причина отказа обязательна, чтобы видеть слабые места', 'Карточка заявки с задачами, заметками и историей', 'Автоматические задачи при смене этапа'], browser('desk-leads', 'Воронка заявок'), rev=True, band=True)}
{feature('Задачи и автоматизация', 'Ничего не забыть, даже в загруженный день', 'Задачи ставятся вручную или по правилам. Каждая автоматическая задача знает, какой шаблон сообщения подходит, и открывает его одним нажатием.', ['Сроки, ответственные, просроченные задачи', 'Правила: новая заявка, этапы, пропуск, конец абонемента, счёт', 'Задачи на главном экране и счётчик просроченных', 'Свои правила и свои шаблоны'], shot('m-tasks', 'Задачи') + shot('m-message', 'Шаблон сообщения'))}
{feature('Финансы', 'Сколько центр заработал на самом деле', 'Выручка считается по принятым оплатам, расходы вы вносите по категориям. Налог считается по вашей ставке, например 4% для упрощённой декларации ИП.', ['Выручка, расходы, прибыль и налог за месяц', 'График выручки и расходов за 6 месяцев', 'Выгрузка оплат и расходов в Excel для бухгалтера', 'Закупки: список товаров и динамика цен', 'Курсы 48 валют Нацбанка РК каждый день, конвертер'], browser('desk-finance', 'Финансы'), rev=True, band=True)}
{feature('Аналитика', 'Решения на основе цифр, а не ощущений', 'Аналитика строится из ваших заявок, посещений и групп. Сразу видно, какой канал приводит клиентов и где они отваливаются.', ['Откуда приходят заявки', 'Воронка и конверсия в покупку', 'Почему отказываются', 'Посещаемость за 30 дней', 'Заполненность каждой группы'], browser('desk-analytics', 'Аналитика'))}

<section class="band" id="roadmap"><div class="wrap">
  <div class="sec-head"><span class="eyebrow">Дальше</span><h2>Что появится в облачной версии</h2><p class="lead">Эти функции требуют сервера и договоров с сервисами, поэтому они в разработке. Мы не показываем их как готовые.</p></div>
  <div class="grid g3">
    {''.join(f'<div class="card"><div class="status-row"><h3>{h}</h3><span class="chip soon">в разработке</span></div><p>{p}</p></div>' for h, p in [
        ('Работа командой', 'Несколько сотрудников и устройств с общими данными, роли и права доступа.'),
        ('Кабинет родителя', 'Расписание, остаток занятий, оплата и новости центра по ссылке, без установки.'),
        ('Автоподтверждение Kaspi', 'Оплата отмечается сама. Зависит от доступа к API Kaspi, который ещё нужно получить.'),
        ('WhatsApp Business API', 'Входящие сообщения прямо в карточке клиента. Нужна верификация бизнеса в Meta.'),
        ('Instagram и реклама', 'Охваты, подписчики, стоимость заявки. Нужно одобрение приложения в Meta.'),
        ('Филиалы', 'Несколько центров в одном аккаунте и отчёты по всей сети.')])}
  </div>
</div></section>
{cta()}
'''

# ====================================================================== ДЛЯ КОГО
SEGS = [
    ('centers', 't-sun', 'toy', 'Развивающие центры', 'Много групп по возрастам, пробные занятия, семьи с двумя-тремя детьми и вечный вопрос «кто сегодня забирает».',
     ['Группы по возрасту с подсказкой при записи', 'Семейная скидка на второго и третьего ребёнка', 'Заметки: аллергии и доверенные взрослые', 'Воронка пробных занятий']),
    ('lang', 't-sky', 'lang', 'Языковые школы', 'Уровни, мини-группы и индивидуальные занятия, абонементы продлеваются каждый месяц.',
     ['Своя цена занятия у каждой группы', 'Задача «предложить продление» за 2 занятия до конца', 'Шаблоны сообщений родителям', 'Аналитика: какие направления интересуют']),
    ('sport', 't-mint', 'ball', 'Спортивные секции', 'Посещаемость решает всё, а пропуски часто означают, что ребёнок скоро уйдёт.',
     ['Быстрая отметка всей группы', 'Риск ухода по пропускам', 'Задача «узнать причину пропуска»', 'Касса: наличные и Kaspi за день']),
    ('art', 't-pink', 'palette', 'Творческие студии', 'Рисование, музыка, танцы, керамика: важно следить за материалами и их ценой.',
     ['Список закупок с динамикой цен', 'Цена-цель: когда выгодно покупать', 'Расходы по категориям', 'Тёмная тема для вечерних занятий']),
    ('tech', 't-vio', 'robot', 'Робототехника и программирование', 'Наборы и комплектующие часто покупаются за валюту, малые группы, дорогие абонементы.',
     ['Курсы доллара, рубля, юаня и других валют каждый день', 'Конвертер для расчёта закупок', 'Частичная оплата абонемента', 'Налог и прибыль по месяцам']),
    ('school', 't-sun', 'book', 'Подготовка к школе и логопеды', 'Индивидуальные занятия, много личного общения с родителями и заметок по каждому ребёнку.',
     ['История и заметки в карточке', 'Сообщения по шаблонам в WhatsApp', 'Задачи с ответственным', 'Отметка прошедших занятий']),
]
solutions_body = f'''
<section class="page-hero"><div class="wrap"><span class="eyebrow">Для кого</span><h1>BALA CRM для вашего направления</h1>
<p class="lead">Детские центры похожи, но у каждого направления свои заботы. Вот что пригодится именно вам.</p></div></section>
<section style="padding-top:0"><div class="wrap"><div class="grid g2">
{''.join(f'<div class="card lift seg-card" id="{a}"><div class="ic {t}">{ico(I[e], 30)}</div><div><h3>{h}</h3><p>{p}</p><ul class="tick">{"".join(f"<li>{x}</li>" for x in pts)}</ul></div></div>' for a, t, e, h, p, pts in SEGS)}
</div></div></section>
<section class="band"><div class="wrap"><div class="split">
  <div><span class="eyebrow">Владельцу</span><h2>Видно, как работает центр, даже когда вас нет на месте</h2><p class="lead" style="margin-top:16px">Выручка, долги, риск ухода, заполненность групп и задачи администратора на одном экране телефона.</p></div>
  <div><span class="eyebrow">Администратору</span><h2>Меньше рутины, больше времени на родителей</h2><p class="lead" style="margin-top:16px">Отметки за минуту, счета и напоминания в WhatsApp одной кнопкой, задачи ставятся сами.</p></div>
</div></div></section>
{cta()}
'''

# ====================================================================== ТАРИФЫ
pricing_body = f'''
<section class="page-hero"><div class="wrap"><span class="eyebrow">Тарифы</span><h1>Начните бесплатно, растите вместе с центром</h1>
<p class="lead">Версия для одного устройства бесплатна уже сейчас. Облачные тарифы для команды и сети центров готовятся, цены на них предварительные.</p></div></section>
<section style="padding-top:0"><div class="wrap">
  <div class="plans">
    <div class="card plan hot"><div class="status-row"><h3>Старт</h3><span class="chip now">доступно сейчас</span></div><div class="price">0 ₸ <small>навсегда</small></div><p>Для небольшого центра, где учёт ведёт один человек.</p>
      <ul class="tick"><li>Все функции приложения</li><li>Без ограничений по детям и группам</li><li>Данные на вашем устройстве</li><li>Резервная копия в файл</li><li>Работает без интернета</li></ul>
      <a class="btn pri" href="app/">Открыть приложение</a></div>
    <div class="card plan"><div class="status-row"><h3>Облако</h3><span class="chip soon">ранний доступ</span></div><div class="price">9 900 ₸ <small>в месяц, предварительно</small></div><p>Для центра, где работают администратор, педагоги и владелец.</p>
      <ul class="tick"><li>Всё из «Старта»</li><li>До 5 сотрудников и любые устройства</li><li>Общие данные в реальном времени</li><li>Кабинет родителя по ссылке</li><li>Серверы в Казахстане</li></ul>
      <a class="btn" data-wa="Здравствуйте! Хочу ранний доступ к BALA CRM Облако." href="#">Хочу ранний доступ</a><span class="chip" data-wa-off>Запуск скоро</span></div>
    <div class="card plan"><div class="status-row"><h3>Сеть</h3><span class="chip soon">ранний доступ</span></div><div class="price">24 900 ₸ <small>в месяц, предварительно</small></div><p>Для сетей и франшиз с несколькими филиалами.</p>
      <ul class="tick"><li>Всё из «Облака»</li><li>Филиалы в одном аккаунте</li><li>Роли и права доступа</li><li>Отчёты по всей сети</li><li>API для интеграций</li></ul>
      <a class="btn" data-wa="Здравствуйте! Интересует BALA CRM для сети центров." href="#">Обсудить</a><span class="chip" data-wa-off>Запуск скоро</span></div>
  </div>
</div></section>
<section class="band"><div class="wrap">
  <div class="sec-head"><span class="eyebrow">Сравнение</span><h2>Что входит в тарифы</h2></div>
  <div class="tblw"><table><thead><tr><th>Функция</th><th class="c">Старт</th><th class="c">Облако</th><th class="c">Сеть</th></tr></thead><tbody>
  {''.join(f'<tr><td>{n}</td>' + ''.join(f'<td class="c {"yes" if v == "✓" else "no"}">{v}</td>' for v in vals) + '</tr>' for n, vals in [
      ('Расписание, журнал, абонементы', ['✓', '✓', '✓']), ('Счета, оплаты Kaspi и наличными, долги', ['✓', '✓', '✓']), ('Заявки, задачи, автоматизация, шаблоны', ['✓', '✓', '✓']),
      ('Финансы, налог, выгрузка в Excel', ['✓', '✓', '✓']), ('Аналитика, закупки, курсы валют', ['✓', '✓', '✓']), ('Несколько устройств и сотрудников', ['—', '✓', '✓']),
      ('Кабинет родителя', ['—', '✓', '✓']), ('Хранение на серверах в Казахстане', ['—', '✓', '✓']), ('Филиалы и отчёты по сети', ['—', '—', '✓']), ('API', ['—', '—', '✓'])])}
  </tbody></table></div>
</div></section>
<section id="faq"><div class="wrap">
  <div class="sec-head"><span class="eyebrow">Вопросы</span><h2>Об оплате и тарифах</h2></div>
  <div class="faq">
    <details><summary>Бесплатная версия правда без ограничений?</summary><p>Да, все функции и без лимитов по детям. Ограничение одно: данные живут на одном устройстве, общей базы для команды нет.</p></details>
    <details><summary>Почему цены облачных тарифов предварительные?</summary><p>Облачная версия ещё в разработке. Окончательные цены объявим при запуске.</p></details>
    <details><summary>Перенесутся ли мои данные в облако?</summary><p>Да. Облачная версия будет принимать файл резервной копии из бесплатной.</p></details>
    <details><summary>Нужна ли карта или регистрация, чтобы начать?</summary><p>Нет. Откройте приложение и введите название центра.</p></details>
  </div>
</div></section>
{cta()}
'''

# ====================================================================== ИНТЕГРАЦИИ
INTEG = [
    ('wallet', 't-pink', 'Kaspi Pay', 'now', 'Ссылка для оплаты из приложения Kaspi Pay добавляется в счета и напоминания родителям.', 'Автоматическая отметка оплаты в разработке: нужен доступ к API Kaspi.'),
    ('msg', 't-mint', 'WhatsApp', 'now', 'Счета, напоминания и сообщения по шаблонам открываются в WhatsApp с готовым текстом. Отправка сохраняется в истории клиента.', 'Входящие сообщения внутри CRM появятся с WhatsApp Business API после верификации бизнеса в Meta.'),
    ('coin', 't-sun', 'Нацбанк РК', 'now', 'Официальные курсы 48 валют загружаются каждый день, с ростом и падением к прошлой дате и конвертером.', ''),
    ('download', 't-sky', 'Excel', 'now', 'Оплаты и расходы за месяц выгружаются в файл, который открывается в Excel и Google Таблицах.', ''),
    ('shield', 't-vio', 'Резервная копия', 'now', 'Все данные центра в одном файле. Восстановление на любом устройстве за минуту.', ''),
    ('phone', 't-mint', 'Телефон', 'now', 'Устанавливается на экран «Домой» на iPhone и Android, работает без интернета.', ''),
    ('chart', 't-pink', 'Instagram', 'soon', 'Охваты, подписчики и заявки из Instagram в аналитике.', 'Нужен профессиональный аккаунт и одобрение приложения в Meta.'),
    ('funnel', 't-sky', 'Реклама Meta', 'soon', 'Расход на рекламу и стоимость заявки по каждой кампании.', 'Нужны права на рекламный кабинет в Meta.'),
    ('cal', 't-sun', 'Онлайн-запись', 'soon', 'Форма записи на пробное занятие для сайта и Instagram, заявки сразу в воронку.', 'Появится в облачной версии.'),
]
integrations_body = f'''
<section class="page-hero"><div class="wrap"><span class="eyebrow">Интеграции</span><h1>Работает с тем, чем вы уже пользуетесь</h1>
<p class="lead">Отмечаем честно: что работает сейчас, а что в разработке и от чего зависит.</p></div></section>
<section style="padding-top:0"><div class="wrap"><div class="grid g3">
{''.join(f'<div class="card"><div class="status-row"><div class="ic {t}" style="margin:0">{ico(I[i])}</div><span class="chip {s}">{"работает" if s == "now" else "в разработке"}</span></div><h3 style="margin-top:14px">{h}</h3><p>{p}</p>{f"<p style=\"margin-top:10px;font-size:14px\">{n}</p>" if n else ""}</div>' for i, t, h, s, p, n in INTEG)}
</div></div></section>
<section class="band"><div class="wrap"><div class="split">
  <div><span class="eyebrow">Безопасность</span><h2>Где хранятся данные детей</h2></div>
  <div><p class="lead">В бесплатной версии все данные хранятся только на вашем устройстве и никуда не отправляются. Облачная версия будет хранить данные на серверах в Казахстане. Закон требует хранить персональные данные граждан на территории страны.</p>
  <p class="callout" style="margin-top:18px">Совет: раз в неделю сохраняйте резервную копию (Настройки → «Сохранить резервную копию») и держите файл в надёжном месте.</p></div>
</div></div></section>
{cta()}
'''

# ====================================================================== КАК НАЧАТЬ
start_body = f'''
<section class="page-hero"><div class="wrap"><span class="eyebrow">Как начать</span><h1>Первый рабочий день в BALA CRM за 15 минут</h1>
<p class="lead">Пять шагов, после которых центр полностью ведётся в приложении.</p></div></section>
<section style="padding-top:0"><div class="wrap"><div class="feature">
  <div class="steps">
    <div class="step"><div><h3>Откройте приложение</h3><p>Перейдите по ссылке <a href="app/">BALA CRM</a>, введите название центра и город, нажмите «Начать с нуля». Хотите сначала посмотреть — нажмите «Посмотреть с примерами».</p></div></div>
    <div class="step"><div><h3>Создайте группы</h3><p>Расписание → «+ Группа»: название, направление, педагог, дни, время, места и цена занятия.</p></div></div>
    <div class="step"><div><h3>Добавьте учеников</h3><p>Ученики → «+ Ученик»: имя, группа, родитель и телефон для WhatsApp. Детей из одной семьи объединяйте в одну семью, тогда скидка посчитается сама.</p></div></div>
    <div class="step"><div><h3>Привяжите Kaspi</h3><p>В Kaspi Pay откройте «Удалённая оплата» → «Ссылка для оплаты». Скопируйте ссылку и вставьте в Настройки → Kaspi Pay.</p></div></div>
    <div class="step"><div><h3>Выставите счета</h3><p>Финансы → «Оплаты и долги» → «+ Выставить счёт». Сумма посчитается со скидками, а сообщение уйдёт родителю в WhatsApp со ссылкой Kaspi.</p></div></div>
  </div>
  <div class="media">{shot('m-today', 'Главный экран')}{shot('m-payments', 'Счета и оплаты')}</div>
</div></div></section>
<section class="band" id="install"><div class="wrap">
  <div class="sec-head"><span class="eyebrow">Установка</span><h2>Как поставить BALA CRM на телефон</h2></div>
  <div class="grid g2">
    <div class="card lift"><h3>iPhone</h3><ol style="margin:12px 0 0;padding-left:20px;color:var(--muted)"><li>Откройте <a href="app/">приложение</a> в Safari.</li><li>Нажмите «Поделиться» (квадрат со стрелкой).</li><li>Выберите «На экран Домой» → «Добавить».</li></ol><p class="callout" style="margin-top:16px">На iPhone данные приложения с экрана «Домой» и данные в Safari хранятся отдельно. Пользуйтесь всегда иконкой.</p></div>
    <div class="card lift"><h3>Android</h3><ol style="margin:12px 0 0;padding-left:20px;color:var(--muted)"><li>Откройте <a href="app/">приложение</a> в Chrome.</li><li>Нажмите меню ⋮.</li><li>Выберите «Установить приложение» или «Добавить на главный экран».</li></ol></div>
  </div>
</div></section>
<section id="backup"><div class="wrap"><div class="split">
  <div><span class="eyebrow">Резервная копия</span><h2>Сохраняйте данные раз в неделю</h2></div>
  <div><p class="lead">В бесплатной версии данные хранятся только на устройстве. Если очистить браузер или потерять телефон, они пропадут.</p>
  <ul class="tick"><li>Настройки → «Сохранить резервную копию»: файл сохранится в загрузки</li><li>Храните файл в облаке или отправьте себе в мессенджер</li><li>Восстановление: Настройки → «Восстановить из копии» на любом устройстве</li><li>Переходите со старого «Умного Зайки»: BALA CRM сама предложит перенести данные</li></ul></div>
</div></div></section>
{cta('Всё готово, чтобы начать', 'Откройте BALA CRM и создайте первую группу. Если понадобится, вернитесь к этой инструкции.')}
'''

SITE = {
    'index.html': ('BALA CRM — CRM для детских центров', 'Расписание, посещения, абонементы, оплаты Kaspi и наличными, заявки, задачи и аналитика для детских центров, кружков и секций.', index_body),
    'features.html': ('Возможности · BALA CRM', 'Журнал и расписание, абонементы, оплаты, заявки, задачи и автоматизация, финансы и аналитика для детских центров.', features_body),
    'solutions.html': ('Для кого · BALA CRM', 'BALA CRM для развивающих центров, языковых школ, спортивных секций, творческих студий, робототехники и логопедов.', solutions_body),
    'pricing.html': ('Тарифы · BALA CRM', 'Бесплатная версия BALA CRM уже доступна. Облачные тарифы для команды и сети центров в раннем доступе.', pricing_body),
    'integrations.html': ('Интеграции · BALA CRM', 'Kaspi Pay, WhatsApp, курсы Нацбанка РК, Excel и резервные копии в BALA CRM.', integrations_body),
    'start.html': ('Как начать · BALA CRM', 'Пять шагов, чтобы начать вести детский центр в BALA CRM, установка на телефон и резервные копии.', start_body),
}
for f, (t, d, b) in SITE.items():
    with open(os.path.join(ROOT, f), 'w', encoding='utf-8') as fh:
        fh.write(layout(f, t, d, b))
print('pages:', ', '.join(SITE))
