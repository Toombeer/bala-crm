-- BALA CRM: начальная схема. Все бизнес-таблицы содержат org_id (мультиарендность).
CREATE TABLE orgs (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  city TEXT NOT NULL DEFAULT '',
  settings TEXT NOT NULL DEFAULT '{}',
  demo INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  org_id INTEGER NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE COLLATE NOCASE,
  phone TEXT NOT NULL DEFAULT '',
  role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'teacher', 'manager', 'accountant')),
  pass_hash TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  token_version INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX users_org ON users(org_id);
CREATE TABLE groups (
  id INTEGER PRIMARY KEY,
  org_id INTEGER NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  name TEXT NOT NULL, dir TEXT NOT NULL DEFAULT '', teacher TEXT NOT NULL DEFAULT '', room TEXT NOT NULL DEFAULT '',
  age_from INTEGER, age_to INTEGER, cap INTEGER, days TEXT NOT NULL DEFAULT '[]', time TEXT NOT NULL DEFAULT '16:00', price INTEGER
);
CREATE INDEX groups_org ON groups(org_id);
CREATE TABLE families (
  id INTEGER PRIMARY KEY,
  org_id INTEGER NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  parent TEXT NOT NULL, phone TEXT NOT NULL DEFAULT '', token TEXT NOT NULL UNIQUE
);
CREATE INDEX families_org ON families(org_id);
CREATE TABLE kids (
  id INTEGER PRIMARY KEY,
  org_id INTEGER NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  family_id INTEGER REFERENCES families(id) ON DELETE SET NULL,
  group_id INTEGER REFERENCES groups(id) ON DELETE SET NULL,
  name TEXT NOT NULL, age INTEGER, lessons_left INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('trial', 'active', 'pause', 'left')), note TEXT NOT NULL DEFAULT ''
);
CREATE INDEX kids_org ON kids(org_id);
CREATE TABLE attendance (
  org_id INTEGER NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  date TEXT NOT NULL, group_id INTEGER NOT NULL, kid_id INTEGER NOT NULL REFERENCES kids(id) ON DELETE CASCADE,
  status TEXT NOT NULL CHECK (status IN ('was', 'late', 'absent', 'excused')), marked_by INTEGER,
  PRIMARY KEY (org_id, date, group_id, kid_id)
);
CREATE TABLE leads (
  id INTEGER PRIMARY KEY,
  org_id INTEGER NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  parent TEXT NOT NULL, phone TEXT NOT NULL DEFAULT '', child TEXT NOT NULL DEFAULT '', age INTEGER, dir TEXT NOT NULL DEFAULT '',
  src TEXT NOT NULL DEFAULT 'Другое', stage INTEGER NOT NULL DEFAULT 0 CHECK (stage BETWEEN 0 AND 4), max_stage INTEGER NOT NULL DEFAULT 0,
  reason TEXT NOT NULL DEFAULT '', note TEXT NOT NULL DEFAULT '', date TEXT NOT NULL
);
CREATE INDEX leads_org ON leads(org_id);
CREATE TABLE tasks (
  id INTEGER PRIMARY KEY,
  org_id INTEGER NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  title TEXT NOT NULL, due TEXT, assignee_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  ref_type TEXT CHECK (ref_type IN ('lead', 'kid', 'fam')), ref_id INTEGER, tpl_id INTEGER,
  done INTEGER NOT NULL DEFAULT 0, done_at TEXT, auto INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
);
CREATE INDEX tasks_org ON tasks(org_id, done);
CREATE TABLE invoices (
  id INTEGER PRIMARY KEY,
  org_id INTEGER NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  family_id INTEGER NOT NULL REFERENCES families(id) ON DELETE CASCADE,
  kids TEXT NOT NULL DEFAULT '[]', lessons INTEGER NOT NULL DEFAULT 0, amount INTEGER NOT NULL CHECK (amount > 0),
  paid INTEGER NOT NULL DEFAULT 0, applied INTEGER NOT NULL DEFAULT 0, note TEXT NOT NULL DEFAULT '', date TEXT NOT NULL
);
CREATE INDEX invoices_org ON invoices(org_id, family_id);
CREATE TABLE payments (
  id INTEGER PRIMARY KEY,
  org_id INTEGER NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  family_id INTEGER REFERENCES families(id) ON DELETE SET NULL,
  amount INTEGER NOT NULL CHECK (amount > 0), method TEXT NOT NULL CHECK (method IN ('cash', 'kaspi', 'transfer')),
  date TEXT NOT NULL, note TEXT NOT NULL DEFAULT '', created_by INTEGER
);
CREATE INDEX payments_org ON payments(org_id, date);
CREATE TABLE expenses (
  id INTEGER PRIMARY KEY,
  org_id INTEGER NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  cat TEXT NOT NULL, amount INTEGER NOT NULL CHECK (amount > 0), date TEXT NOT NULL, note TEXT NOT NULL DEFAULT ''
);
CREATE INDEX expenses_org ON expenses(org_id, date);
CREATE TABLE items (
  id INTEGER PRIMARY KEY,
  org_id INTEGER NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  name TEXT NOT NULL, unit TEXT NOT NULL DEFAULT 'шт.', target INTEGER NOT NULL DEFAULT 0, link TEXT NOT NULL DEFAULT ''
);
CREATE TABLE item_prices (
  item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE, date TEXT NOT NULL, price INTEGER NOT NULL CHECK (price > 0),
  PRIMARY KEY (item_id, date)
);
CREATE TABLE templates (
  id INTEGER PRIMARY KEY,
  org_id INTEGER NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  name TEXT NOT NULL, text TEXT NOT NULL
);
CREATE TABLE rules (
  id INTEGER PRIMARY KEY,
  org_id INTEGER NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  trigger TEXT NOT NULL, task TEXT NOT NULL, days INTEGER NOT NULL DEFAULT 0, tpl_id INTEGER
);
CREATE TABLE events (
  id INTEGER PRIMARY KEY,
  org_id INTEGER NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  at TEXT NOT NULL, ref_type TEXT, ref_id INTEGER, type TEXT NOT NULL DEFAULT 'event', text TEXT NOT NULL, user_id INTEGER
);
CREATE INDEX events_ref ON events(org_id, ref_type, ref_id);
CREATE TABLE rates (
  date TEXT NOT NULL, code TEXT NOT NULL, name TEXT NOT NULL, nom INTEGER NOT NULL, rate REAL NOT NULL,
  PRIMARY KEY (date, code)
);
