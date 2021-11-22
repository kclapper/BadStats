import pytest, os
from datetime import datetime, timezone, timedelta
from badstats.db import get_db
from spotify.Spotify import UserSpotify, Spotify
from spotify.Token import Token, ClientToken, BasicCreds

# def test_abs_init(app, spotify_creds):
#     with app.app_context():
#         with pytest.raises(NotImplementedError):
#             spotify = AbstractSpotify()

# def test_abs_expires(fake_response):
#     response = fake_response(date=datetime(2021, 1, 1, 0, 0, 0, 0, timezone.utc))
#     assert AbstractSpotify._expires(response) == datetime(2021, 1, 1, 0, 0, 5, 0)

# def test_abs_tokenExpires():
#     token = {
#         "expires": datetime.now().isoformat()
#     }
#     assert AbstractSpotify._tokenExpired(token) == True

#     token = {
#         "expires": (datetime.now() + timedelta(1)).isoformat()
#     }
#     assert AbstractSpotify._tokenExpired(token) == False

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

def test_token_isExpired():
    expires = datetime(2000,1,1,1)

    token = Token("test", expires)

    assert token.isExpired()

def test_token_value():

    expires = datetime(2000,1,1,1)

    token = Token("test", expires)

    assert token.value() == "test"

def test_clientToken_fromDB(app):
    with app.app_context():
        db = get_db()
        db.execute('DELETE FROM token WHERE token_type="client"')
        db.commit()
        db.execute('INSERT INTO token (token, expires, refresh, token_type, sessionid)'
                ' VALUES (?, ?, ?, ?, ?)',
                ("test", "2000-01-01T00:00:00", None, "client", None)
                )
        db.commit()

        token = ClientToken.fromDatabase()

        assert token.value() == "test"
        assert token.isExpired()

        db.execute('DELETE FROM token WHERE token_type="client"')
        db.commit()

def test_clientToken_addToDB(app):
    with app.app_context():
        db = get_db()
        db.execute('DELETE FROM token WHERE token_type="client"')
        db.commit()
        
        token = ClientToken("test", datetime(2000,1,1))
        token.addToDatabase()

        dbEntry = db.execute('SELECT * FROM token WHERE token_type="client"').fetchone()

        assert dbEntry['token'] == "test"
        assert dbEntry['expires'] == '2000-01-01T00:00:00'

        db.execute('DELETE FROM token WHERE token_type="client"')
        db.commit()

def test_clientToken_removeFromDB(app):
    with app.app_context():
        db = get_db()
        db.execute('DELETE FROM token WHERE token_type="client"')
        db.commit()
        db.execute('INSERT INTO token (token, expires, refresh, token_type, sessionid)'
                ' VALUES (?, ?, ?, ?, ?)',
                ("test", "2000-01-01T00:00:00", None, "client", None)
                )
        db.commit()
        
        token = ClientToken.fromDatabase()
        token.removeFromDatabase()

        dbEntry = db.execute('SELECT * FROM token WHERE token_type="client"').fetchone()

        assert dbEntry == None

        db.execute('DELETE FROM token WHERE token_type="client"')
        db.commit()

def test_BasicCreds_init(app):
    with app.app_context():
        db = get_db()
        db.execute('DELETE FROM token WHERE token_type="client"')
        db.commit()

        creds = BasicCreds()

        assert creds != None
        assert creds.value() != None
        assert creds.value() != "test"

def test_BasicCreds_expired_init(app):
    with app.app_context():
        db = get_db()
        db.execute('DELETE FROM token WHERE token_type="client"')
        db.commit()
        db.execute('INSERT INTO token (token, expires, refresh, token_type, sessionid)'
                ' VALUES (?, ?, ?, ?, ?)',
                ("test", "2000-01-01T00:00:00", None, "client", None)
                )
        db.commit()

        creds = BasicCreds()

        assert creds != None
        assert creds.value() != None
        assert creds.value() != "test"

        dbRows = db.execute('SELECT * FROM token WHERE token_type="client"').fetchall()

        assert len(dbRows) == 1