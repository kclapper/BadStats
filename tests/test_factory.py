import os

from badstats import create_app, getHostname


def test_config():
    assert not create_app().testing
    assert create_app({'TESTING': True}).testing

def test_hostname(monkeypatch):
    monkeypatch.delenv("REDIRECT_HOSTNAME", raising=False)
    assert "REDIRECT_HOSTNAME" not in os.environ
    
    assert getHostname() == "http://127.0.0.1:5000"

    monkeypatch.setenv("REDIRECT_HOSTNAME", "Testing")
    assert getHostname() == "Testing"