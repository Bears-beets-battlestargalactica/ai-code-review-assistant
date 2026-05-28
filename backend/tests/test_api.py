from fastapi.testclient import TestClient
from app.main import app
from app.storage import init_db

init_db()
client = TestClient(app)


def test_health():
    res = client.get('/health')
    assert res.status_code == 200
    assert res.json()['status'] == 'ok'


def test_review_rule_based():
    res = client.post('/api/review', json={
        'files': [{'path': 'src/example.ts', 'language': 'typescript', 'content': 'type X = any;\nvar total = 0;\nconsole.log(total);'}],
        'use_ai': False,
        'include_tests': True
    })
    assert res.status_code == 200
    data = res.json()
    assert 'Reviewed 1 file' in data['summary']
    assert len(data['comments']) >= 2


def test_register_login_history():
    email = 'test@example.com'
    password = 'password123'
    client.post('/api/auth/register', json={'email': email, 'password': password})
    login = client.post('/api/auth/login', json={'email': email, 'password': password})
    assert login.status_code == 200
    token = login.json()['token']
    history = client.get('/api/history', headers={'Authorization': f'Bearer {token}'})
    assert history.status_code == 200
