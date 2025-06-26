from fastapi.testclient import TestClient
from GPT_RP import app

client = TestClient(app)


def test_respond_default_character():
    resp = client.post('/respond', json={'message': 'Hello'})
    assert resp.status_code == 200
    data = resp.json()
    assert data['replies'][0]['name'] == 'lazul'
    assert data['replies'][0]['reply'] == 'Hello'


def test_respond_multiple_characters():
    resp = client.post('/respond', json={'message': 'Hi', 'characters': ['lazul', 'chacha']})
    assert resp.status_code == 200
    data = resp.json()
    names = {r['name'] for r in data['replies']}
    assert names == {'lazul', 'chacha'}
    for r in data['replies']:
        assert r['reply'] == 'Hi'


def test_missing_character_returns_404():
    resp = client.post('/respond', json={'message': 'Hi', 'characters': ['nonexist']})
    assert resp.status_code == 404


def test_list_roles():
    resp = client.get('/list_roles')
    assert resp.status_code == 200
    data = resp.json()
    assert 'lazul' in data['roles']
    assert 'chacha' in data['roles']
