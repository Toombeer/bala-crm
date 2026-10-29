# BALA CRM API

Базовый адрес: `/api/v1`. Формат: JSON. Авторизация: заголовок `Authorization: Bearer <токен>` из `/auth/login` или `/auth/register`.
Интерактивная документация на работающем сервере: `/api/docs` (Swagger UI), схема: `/api/openapi.json`.

Ошибки возвращаются как `{"error": "текст для человека", "code": "машинный_код"}` с HTTP-статусом 4xx/5xx.

## Роли и права

| Роль | Права |
| --- | --- |
| Владелец (`owner`) | attendance, billing, data, finance, groups, leads, read, settings, staff, students, tasks |
| Администратор (`admin`) | attendance, billing, finance, groups, leads, read, settings, students, tasks |
| Менеджер (`manager`) | leads, read, students, tasks |
| Педагог (`teacher`) | attendance, read, tasks |
| Бухгалтер (`accountant`) | billing, finance, read |

## Вход

| Метод | Путь | Право | Описание |
| --- | --- | --- | --- |
| `POST` | `/api/v1/auth/register` | публично | Зарегистрировать центр и владельца |
| `POST` | `/api/v1/auth/login` | публично | Войти по email и паролю |
| `GET` | `/api/v1/auth/me` | любой вход | Текущий пользователь |
| `POST` | `/api/v1/auth/password` | любой вход | Сменить свой пароль (все сессии завершаются) |
| `POST` | `/api/v1/auth/logout-all` | любой вход | Завершить все сессии на всех устройствах |

## Данные

| Метод | Путь | Право | Описание |
| --- | --- | --- | --- |
| `GET` | `/api/v1/state` | read | Все данные центра для веб-клиента (с учётом прав роли) |
| `POST` | `/api/v1/org/reset` | data | Удалить все данные центра (настройки, сотрудники, шаблоны сохраняются) |
| `POST` | `/api/v1/org/demo` | data | Заполнить пустой центр демо-данными |

## Отчёты

| Метод | Путь | Право | Описание |
| --- | --- | --- | --- |
| `GET` | `/api/v1/reports/dashboard` | read | Главный экран: занятия сегодня, долги, заявки, задачи |
| `GET` | `/api/v1/reports/finance` | finance | Финансы за месяц: выручка, расходы, прибыль, налог, способы оплаты |
| `GET` | `/api/v1/reports/analytics` | read | Аналитика: источники, воронка, отказы, посещаемость, заполненность |

## Курсы валют

| Метод | Путь | Право | Описание |
| --- | --- | --- | --- |
| `GET` | `/api/v1/rates` | read | Последние курсы НБ РК и история за 60 дней |
| `POST` | `/api/v1/rates/refresh` | data | Загрузить свежие курсы с сайта Нацбанка сейчас |

## Экспорт

| Метод | Путь | Право | Описание |
| --- | --- | --- | --- |
| `GET` | `/api/v1/export/payments.csv` | finance | Оплаты за месяц в CSV для Excel (month=ГГГГ-ММ) |
| `GET` | `/api/v1/export/expenses.csv` | finance | Расходы за месяц в CSV |
| `GET` | `/api/v1/export/backup.json` | data | Полная резервная копия центра (формат совместим с импортом) |
| `POST` | `/api/v1/import` | data | Импорт резервной копии из локального приложения (Умный Зайка или BALA CRM) |

## Кабинет родителя

| Метод | Путь | Право | Описание |
| --- | --- | --- | --- |
| `GET` | `/api/v1/public/family/{token}` | публично | Данные семьи по секретной ссылке: дети, расписание, остаток занятий, долг, оплаты |

## Служебное

| Метод | Путь | Право | Описание |
| --- | --- | --- | --- |
| `GET` | `/api/v1/health` | публично | Проверка работы сервера |

## Оплаты

| Метод | Путь | Право | Описание |
| --- | --- | --- | --- |
| `POST` | `/api/v1/quote` | billing | Посчитать стоимость абонемента с семейной и доп. скидкой |
| `GET` | `/api/v1/invoices` | billing | Счета (family_id, status=unpaid|partial|paid) |
| `POST` | `/api/v1/invoices` | billing | Выставить счёт. Когда он оплачен полностью, занятия добавятся детям |
| `PUT` | `/api/v1/invoices/{id}` | billing | Изменить счёт |
| `DELETE` | `/api/v1/invoices/{id}` | billing | Удалить счёт |
| `GET` | `/api/v1/invoices/{id}/message` | billing | Текст счёта для WhatsApp и ссылка wa.me |
| `GET` | `/api/v1/payments` | billing | Оплаты (month=ГГГГ-ММ, method, family_id) |
| `POST` | `/api/v1/payments` | billing | Принять оплату. Распределяется по счетам семьи, закрытые счета добавляют занятия |
| `PUT` | `/api/v1/payments/{id}` | billing | Исправить оплату |
| `DELETE` | `/api/v1/payments/{id}` | billing | Удалить оплату |
| `GET` | `/api/v1/debts` | billing | Кто должен и сколько |

## Центр

| Метод | Путь | Право | Описание |
| --- | --- | --- | --- |
| `GET` | `/api/v1/org` | read | Настройки центра |
| `PATCH` | `/api/v1/org` | settings | Изменить название, цены, скидки, налог, Kaspi |
| `PATCH` | `/api/v1/org/currencies` | read | Выбрать валюты на главном экране |

## Сотрудники

| Метод | Путь | Право | Описание |
| --- | --- | --- | --- |
| `GET` | `/api/v1/users` | read | Список сотрудников |
| `POST` | `/api/v1/users` | staff | Добавить сотрудника с логином и паролем |
| `PATCH` | `/api/v1/users/{id}` | staff | Изменить сотрудника, роль, пароль, отключить доступ |
| `DELETE` | `/api/v1/users/{id}` | staff | Удалить сотрудника |

## Справочники

| Метод | Путь | Право | Описание |
| --- | --- | --- | --- |
| `GET` | `/api/v1/groups` | read | Группы |
| `POST` | `/api/v1/groups` | groups | Создать группу |
| `PUT` | `/api/v1/groups/{id}` | groups | Изменить группу |
| `DELETE` | `/api/v1/groups/{id}` | groups | Удалить группу (ученики останутся без группы) |
| `GET` | `/api/v1/families` | read | Семьи |
| `POST` | `/api/v1/families` | students | Создать семью |
| `PUT` | `/api/v1/families/{id}` | students | Изменить семью |
| `POST` | `/api/v1/families/{id}/token` | students | Выпустить новую ссылку на кабинет родителя (старая перестанет работать) |
| `DELETE` | `/api/v1/families/{id}` | students | Удалить семью вместе со счетами |
| `GET` | `/api/v1/kids` | read | Ученики |
| `GET` | `/api/v1/kids/{id}` | read | Карточка ученика |
| `POST` | `/api/v1/kids` | students | Добавить ученика (с существующей или новой семьёй, можно из заявки) |
| `PATCH` | `/api/v1/kids/{id}` | students | Изменить ученика |
| `DELETE` | `/api/v1/kids/{id}` | students | Удалить ученика |

## Финансы

| Метод | Путь | Право | Описание |
| --- | --- | --- | --- |
| `GET` | `/api/v1/expenses` | finance | Расходы (параметр month=ГГГГ-ММ) |
| `POST` | `/api/v1/expenses` | finance | Добавить расход |
| `PUT` | `/api/v1/expenses/{id}` | finance | Изменить расход |
| `DELETE` | `/api/v1/expenses/{id}` | finance | Удалить расход |

## Закупки

| Метод | Путь | Право | Описание |
| --- | --- | --- | --- |
| `GET` | `/api/v1/items` | billing | Список закупок с историей цен |
| `POST` | `/api/v1/items` | billing | Добавить товар (с первой ценой) |
| `PUT` | `/api/v1/items/{id}` | billing | Изменить товар |
| `POST` | `/api/v1/items/{id}/prices` | billing | Записать цену товара на дату |
| `DELETE` | `/api/v1/items/{id}` | billing | Удалить товар |

## Автоматизация

| Метод | Путь | Право | Описание |
| --- | --- | --- | --- |
| `GET` | `/api/v1/templates` | read | Шаблоны сообщений |
| `POST` | `/api/v1/templates` | settings | Добавить шаблон |
| `PUT` | `/api/v1/templates/{id}` | settings | Изменить шаблон |
| `DELETE` | `/api/v1/templates/{id}` | settings | Удалить шаблон |
| `GET` | `/api/v1/rules` | read | Правила автоматизации |
| `POST` | `/api/v1/rules` | settings | Добавить правило: событие → задача |
| `PUT` | `/api/v1/rules/{id}` | settings | Изменить правило |
| `DELETE` | `/api/v1/rules/{id}` | settings | Удалить правило |

## Журнал

| Метод | Путь | Право | Описание |
| --- | --- | --- | --- |
| `GET` | `/api/v1/attendance` | read | Отметки за дату (date=ГГГГ-ММ-ДД, group_id необязателен) |
| `PUT` | `/api/v1/attendance` | attendance | Отметить группу: {kid_id: статус или null}. «Был» и «опоздал» списывают занятие; запускаются правила пропуска и продления |

## Заявки

| Метод | Путь | Право | Описание |
| --- | --- | --- | --- |
| `GET` | `/api/v1/leads` | leads | Заявки (stage=0..4 для фильтра) |
| `POST` | `/api/v1/leads` | leads | Новая заявка (запускает правила этапа) |
| `PUT` | `/api/v1/leads/{id}` | leads | Изменить заявку (смена этапа запускает правила) |
| `POST` | `/api/v1/leads/{id}/stage` | leads | Перевести заявку на этап (для «Отказа» нужна причина) |
| `DELETE` | `/api/v1/leads/{id}` | leads | Удалить заявку |

## Задачи

| Метод | Путь | Право | Описание |
| --- | --- | --- | --- |
| `GET` | `/api/v1/tasks` | tasks | Задачи (done=0|1, mine=1) |
| `POST` | `/api/v1/tasks` | tasks | Новая задача |
| `PATCH` | `/api/v1/tasks/{id}` | tasks | Изменить задачу или отметить выполненной |
| `DELETE` | `/api/v1/tasks/{id}` | tasks | Удалить задачу |

## История

| Метод | Путь | Право | Описание |
| --- | --- | --- | --- |
| `GET` | `/api/v1/events` | read | История по записи (ref_type=lead|kid|fam&ref_id=…) или всего центра |
| `POST` | `/api/v1/events` | read | Добавить заметку или записать отправленное сообщение |
