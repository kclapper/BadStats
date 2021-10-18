import pytest
from badstats.db import get_db
from badstats.spotify import Spotify

def test_client_init(app):
    with app.app_context():
        spotify = Spotify()
        assert spotify != None

        # Twice so it hits the cache
        spotify = Spotify() 
        assert spotify != None

def test_auth_init(app, mock_spotify_auth):
    with app.app_context():
        # Always hits the cache
        spotify = Spotify(code='test', url='testurl.test/test', sessionid='testsession')
    assert spotify != None

# def test_search(app, mock_spotify_search):
