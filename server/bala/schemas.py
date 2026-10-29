"""Схемы входных данных (Pydantic). Описывают и проверяют тело каждого запроса."""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

DATE = r'^\d{4}-\d{2}-\d{2}$'


class In(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='ignore')


# ---------- вход ----------
class RegisterIn(In):
    center_name: str = Field(min_length=1, max_length=120)
    city: str = Field('', max_length=80)
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=200, pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
    password: str = Field(min_length=8, max_length=200)


class LoginIn(In):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=200)


class PasswordIn(In):
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=200)


# ---------- центр ----------
class OrgIn(In):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    city: Optional[str] = Field(None, max_length=80)
    price: Optional[int] = Field(None, ge=0, le=10_000_000)
    pack: Optional[int] = Field(None, ge=1, le=500)
    sib2: Optional[float] = Field(None, ge=0, le=100)
    sib3: Optional[float] = Field(None, ge=0, le=100)
    tax: Optional[float] = Field(None, ge=0, le=50)
    kaspi_point: Optional[str] = Field(None, max_length=120)
    kaspi_link: Optional[str] = Field(None, max_length=500)
    instagram: Optional[str] = Field(None, max_length=120)
    sel_cur: Optional[list[str]] = None

    @field_validator('kaspi_link')
    @classmethod
    def https_only(cls, v):
        if v and not v.startswith('https://'):
            raise ValueError('ссылка должна начинаться с https://')
        return v


# ---------- сотрудники ----------
Role = Literal['owner', 'admin', 'teacher', 'manager', 'accountant']


class UserIn(In):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=200, pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
    phone: str = Field('', max_length=40)
    role: Role = 'teacher'
    password: str = Field(min_length=8, max_length=200)


class UserPatch(In):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    phone: Optional[str] = Field(None, max_length=40)
    role: Optional[Role] = None
    active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8, max_length=200)


# ---------- группы, семьи, ученики ----------
class GroupIn(In):
    name: str = Field(min_length=1, max_length=120)
    dir: str = Field('', max_length=80)
    teacher: str = Field('', max_length=120)
    room: str = Field('', max_length=80)
    age_from: Optional[int] = Field(None, ge=0, le=25)
    age_to: Optional[int] = Field(None, ge=0, le=25)
    cap: Optional[int] = Field(None, ge=1, le=500)
    days: list[int] = Field(min_length=1)
    time: str = Field('16:00', pattern=r'^\d{2}:\d{2}$')
    price: Optional[int] = Field(None, ge=0, le=10_000_000)

    @field_validator('days')
    @classmethod
    def days_ok(cls, v):
        if any(d not in range(7) for d in v):
            raise ValueError('дни недели — числа от 0 (вс) до 6 (сб)')
        return sorted(set(v))


class FamilyIn(In):
    parent: str = Field(min_length=1, max_length=120)
    phone: str = Field('', max_length=40)


KidStatus = Literal['trial', 'active', 'pause', 'left']


class KidIn(In):
    name: str = Field(min_length=1, max_length=120)
    age: Optional[int] = Field(None, ge=0, le=25)
    group_id: Optional[int] = None
    status: KidStatus = 'active'
    lessons_left: int = Field(0, ge=-1000, le=10_000)
    note: str = Field('', max_length=4000)
    family_id: Optional[int] = None
    parent: str = Field('', max_length=120)
    phone: str = Field('', max_length=40)
    lead_id: Optional[int] = None


class KidPatch(In):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    age: Optional[int] = Field(None, ge=0, le=25)
    group_id: Optional[int] = None
    status: Optional[KidStatus] = None
    lessons_left: Optional[int] = Field(None, ge=-1000, le=10_000)
    note: Optional[str] = Field(None, max_length=4000)
    family_id: Optional[int] = None
    parent: Optional[str] = Field(None, max_length=120)
    phone: Optional[str] = Field(None, max_length=40)


# ---------- журнал ----------
Mark = Literal['was', 'late', 'absent', 'excused']


class AttendanceIn(In):
    date: str = Field(pattern=DATE)
    group_id: int
    marks: dict[int, Optional[Mark]]


# ---------- заявки и задачи ----------
class LeadIn(In):
    parent: str = Field(min_length=1, max_length=120)
    phone: str = Field('', max_length=40)
    child: str = Field('', max_length=120)
    age: Optional[int] = Field(None, ge=0, le=25)
    dir: str = Field('', max_length=80)
    src: str = Field('Другое', max_length=40)
    stage: int = Field(0, ge=0, le=4)
    reason: str = Field('', max_length=80)
    note: str = Field('', max_length=4000)


class StageIn(In):
    stage: int = Field(ge=0, le=4)
    reason: str = Field('', max_length=80)
    note: Optional[str] = Field(None, max_length=4000)


RefType = Literal['lead', 'kid', 'fam']


class TaskIn(In):
    title: str = Field(min_length=1, max_length=300)
    due: Optional[str] = Field(None, pattern=DATE)
    assignee_id: Optional[int] = None
    ref_type: Optional[RefType] = None
    ref_id: Optional[int] = None
    tpl_id: Optional[int] = None


class TaskPatch(In):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    due: Optional[str] = Field(None, pattern=DATE)
    assignee_id: Optional[int] = None
    done: Optional[bool] = None


class NoteIn(In):
    ref_type: RefType
    ref_id: int
    text: str = Field(min_length=1, max_length=4000)
    type: Literal['note', 'msg'] = 'note'


# ---------- деньги ----------
class InvoiceIn(In):
    family_id: int
    kids: list[int] = []
    lessons: int = Field(0, ge=0, le=1000)
    amount: int = Field(gt=0, le=100_000_000)
    note: str = Field('', max_length=300)
    date: Optional[str] = Field(None, pattern=DATE)


class QuoteIn(In):
    kids: list[int]
    lessons: int = Field(ge=0, le=1000)
    extra: float = Field(0, ge=0, le=100)


Method = Literal['cash', 'kaspi', 'transfer']


class PaymentIn(In):
    family_id: Optional[int] = None
    amount: int = Field(gt=0, le=100_000_000)
    method: Method = 'cash'
    date: Optional[str] = Field(None, pattern=DATE)
    note: str = Field('', max_length=300)


class ExpenseIn(In):
    cat: str = Field(min_length=1, max_length=60)
    amount: int = Field(gt=0, le=100_000_000)
    date: Optional[str] = Field(None, pattern=DATE)
    note: str = Field('', max_length=300)


class ItemIn(In):
    name: str = Field(min_length=1, max_length=200)
    unit: str = Field('шт.', max_length=30)
    target: int = Field(0, ge=0)
    link: str = Field('', max_length=500)
    price: Optional[int] = Field(None, gt=0)

    @field_validator('link')
    @classmethod
    def https_only(cls, v):
        if v and not v.startswith('https://'):
            raise ValueError('ссылка должна начинаться с https://')
        return v


class PriceIn(In):
    price: int = Field(gt=0, le=100_000_000)
    date: Optional[str] = Field(None, pattern=DATE)


class TemplateIn(In):
    name: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=2000)


Trigger = Literal['lead0', 'lead1', 'lead2', 'lead3', 'lead4', 'kidlow', 'absent', 'invoice']


class RuleIn(In):
    trigger: Trigger
    task: str = Field(min_length=1, max_length=300)
    days: int = Field(0, ge=0, le=60)
    tpl_id: Optional[int] = None


class ImportIn(In):
    model_config = ConfigDict(extra='allow')
    v: int
