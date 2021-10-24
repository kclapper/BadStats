import os, base64, requests
import tempfile
from datetime import datetime, timezone

import pytest
from badstats import create_app
from badstats.db import get_db, init_db
from badstats.spotify import AbstractSpotify

with open(os.path.join(os.path.dirname(__file__), 'data.sql'), 'rb') as f:
    _data_sql = f.read().decode('utf8')


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()

    app = create_app({
        'TESTING': True,
        'DATABASE': db_path,
    })

    with app.app_context():
        init_db()
        get_db().executescript(_data_sql)

    yield app

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()

class AuthActions(object):
    def __init__(self, client):
        self._client = client

    def login(self, username='test', password='test'):
        return self._client.post(
            '/auth/login',
            data={'username': username, 'password': password}
        )

    def logout(self):
        return self._client.get('/auth/logout')


@pytest.fixture
def auth(client):
    return AuthActions(client)

@pytest.fixture
def spotify_creds(monkeypatch):
    monkeypatch.setattr(AbstractSpotify, "id", "test", raising=True)
    monkeypatch.setattr(AbstractSpotify, "secret", "test", raising=True)

class FakeResponse:
    def __init__(self, json={}, status_code=200, date=datetime(2021, 1, 1, 0, 0, 0, 0, timezone.utc)):
        self.jsondata = json
        self.status_code = status_code

        self.headers = {
            'date': date.strftime('%a, %d %b %Y %H:%M:%S %Z')
        }

    def json(self):
        self.jsondata.update({
            'expires_in': 5 # 5 seconds
        })
        return self.jsondata

@pytest.fixture
def fake_response():
    yield FakeResponse

@pytest.fixture
def mock_spotify_auth(monkeypatch, spotify_creds):

    def mock_post(url, data, headers):
        if url == "https://accounts.spotify.com/api/token":
            ## For getting either a client or auth token
            
            ## Check authorization header is present and valid
            assert "Authorization" in headers and headers['Authorization'] == f'Basic {str(base64.b64encode("test:test".encode("utf-8")), "utf-8")}'

            ## Check grant type specified
            assert 'grant_type' in data

            if (grant := data['grant_type']) == 'client_credentials':
                return FakeResponse(json={"access_token" : "fake_client_token"})
            elif grant == 'authorization_code':   
                assert 'code' in data and 'redirect_uri' in data

                return FakeResponse(json = {
                    'refresh_token': 'fake_refresh_token',
                    'access_token': 'fake_auth_token',
                })
            elif grant == 'refresh_token':
                return FakeResponse(json = {
                    'refresh_token': 'fake_refresh_token',
                    'access_token': 'fake_auth_token',
                })
            else:
                raise Exception(f"Improper grant type specified: {grant}")

        else:
            raise Exception("Wrong url sent to Spotify api")

    monkeypatch.setattr(requests, "post", mock_post)