import pytest, os
from datetime import datetime, timezone, timedelta
from badstats.db import get_db
from spotify.Spotify import UserSpotify, AbstractSpotify, Spotify

def test_abs_init(app, spotify_creds):
    with app.app_context():
        with pytest.raises(NotImplementedError):
            spotify = AbstractSpotify()

def test_abs_expires(fake_response):
    response = fake_response(date=datetime(2021, 1, 1, 0, 0, 0, 0, timezone.utc))
    assert AbstractSpotify._expires(response) == datetime(2021, 1, 1, 0, 0, 5, 0)

def test_abs_tokenExpires():
    token = {
        "expires": datetime.now().isoformat()
    }
    assert AbstractSpotify._tokenExpired(token) == True

    token = {
        "expires": (datetime.now() + timedelta(1)).isoformat()
    }
    assert AbstractSpotify._tokenExpired(token) == False

def test_public_spotify_init_fail(app, spotify_creds, dbReturnsNone):
    with app.app_context():
        with pytest.raises(Exception):
            print(os.environ['CLIENTID'])
            spotify = Spotify()

def test_public_spotify_init(app):
    with app.app_context():
        spotify = Spotify()

@pytest.mark.parametrize('kind, search, expected', (
    ("artist", "paramore", "74XFHRwlV6OrjEM0A2NCMF"),
    ("album", "paramore", "4sgYpkIASM1jVlNC8Wp9oF"),
    ("song", "aint it fun", "1j8z4TTjJ1YOdoFEDwJTQa"),
))
def test_public_spotify_search(app, kind, search, expected):
    with app.app_context():
        spotify = Spotify()

        results = spotify.search(search, kind)

        assert expected in [result['id'] for result in results]

@pytest.mark.parametrize('kind, item, expected', (
    ("artist", "74XFHRwlV6OrjEM0A2NCMF", "Paramore"),
    ("album", "4sgYpkIASM1jVlNC8Wp9oF", "Paramore"),
    ("song", "1j8z4TTjJ1YOdoFEDwJTQa", "Ain't It Fun"),
))
def test_public_spotify_item(app, kind, item, expected):
    with app.app_context():
        spotify = Spotify()

        result = spotify.item(kind, item)

        assert result['name'] == expected

def test_public_spotify_albumtrackdetails(app):
    with app.app_context():
        spotify = Spotify()

        results = spotify.albumTrackDetails("4sgYpkIASM1jVlNC8Wp9oF")

        assert "Ain't It Fun" in [result['name'] for result in results['tracks']]

@pytest.mark.parametrize('statusCode', (
    300,
    500,
))
def test_api_query_exception(app, failedQuery, statusCode):

    failedQuery(statusCode)

    with app.app_context():
        spotify = Spotify()

        with pytest.raises(Exception):
            results = spotify.item('song', "1j8z4TTjJ1YOdoFEDwJTQa")
