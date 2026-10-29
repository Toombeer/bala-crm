import os
import sys
import tempfile

import pytest

_tmp = tempfile.mkdtemp(prefix='bala-test-')
os.environ['BALA_DB'] = os.path.join(_tmp, 'test.db')
os.environ['BALA_RATES_AUTO'] = '0'
os.environ['BALA_SECRET'] = 'test-secret-not-for-production-0123456789'
os.environ['BALA_LOGIN_ATTEMPTS'] = '1000'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from starlette.testclient import TestClient  # noqa: E402

from bala.app import create_app  # noqa: E402

_n = [0]


@pytest.fixture(scope='session')
def client():
    return TestClient(create_app(run_background=False))


@pytest.fixture
def owner(client):
    """Новый центр и его владелец; возвращает функцию запроса с токеном."""
    _n[0] += 1
    r = client.post('/api/v1/auth/register', json={'center_name': f'Центр {_n[0]}', 'city': 'Астана', 'name': 'Владелец', 'email': f'owner{_n[0]}@test.kz', 'password': 'secret-pass-1'})
    assert r.status_code == 201, r.text
    return Api(client, r.json()['token'])


class Api:
    def __init__(self, client, token):
        self.c, self.h = client, {'Authorization': f'Bearer {token}'}

    def __call__(self, method, path, json=None, status=None, **params):
        r = self.c.request(method, '/api/v1' + path, json=json, headers=self.h, params=params or None)
        if status is not None:
            assert r.status_code == status, f'{method} {path}: {r.status_code} {r.text}'
        return r.json() if r.headers.get('content-type', '').startswith('application/json') else r
