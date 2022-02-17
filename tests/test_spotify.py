import pytest, os
from datetime import datetime, timezone, timedelta
from badstats.db import get_db
from spotify.Spotify import UserSpotify, Spotify
from spotify.Token import Token, UserToken, ClientToken, BasicCreds

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

@pytest.mark.parametrize('kind, items', (
    ("artist", ["74XFHRwlV6OrjEM0A2NCMF", "1XpDYCrUJnvCo9Ez6yeMWh", "1gUi2utSbJLNPddYENJAp4"]),
    ("album", ["4sgYpkIASM1jVlNC8Wp9oF", "4UdZHRBCIoe7XCPr8KdVg7", "1AckkxSo39144vOBrJ1GkS"]),
    ("song", ["1j8z4TTjJ1YOdoFEDwJTQa", "0G2wimhVoDYXbQ6csDxtSf", "6crBy2sODw2HS53xquM6us"]),
    ("song", ["1j8z4TTjJ1YOdoFEDwJTQa"]),
))
def test_public_spotify_item(app, kind, items):
    with app.app_context():
        spotify = Spotify()

        result = spotify.multipleItems(kind, items)

@pytest.mark.parametrize('items', (
    (["1j8z4TTjJ1YOdoFEDwJTQa", "0G2wimhVoDYXbQ6csDxtSf", "6crBy2sODw2HS53xquM6us"]),
    (["1j8z4TTjJ1YOdoFEDwJTQa"]),
))
def test_public_spotify_item(app, items):
    with app.app_context():
        spotify = Spotify()

        result = spotify.multipleSongDetails(items)

def test_public_spotify_albumtrackdetails(app):
    with app.app_context():
        spotify = Spotify()

        results = spotify.albumTrackDetails("4sgYpkIASM1jVlNC8Wp9oF")

        assert "Paramore" == results['album']
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

def test_token_removeFromDB(app):
    with app.app_context():
        db = get_db()
        db.execute('DELETE FROM token WHERE token_type="client"')
        db.commit()
        db.execute('INSERT INTO token (token, expires, refresh, token_type, sessionid)'
                ' VALUES (?, ?, ?, ?, ?)',
                ("test", "2000-01-01T00:00:00", None, "client", None)
                )
        db.commit()
        dbEntry = db.execute('SELECT * FROM token WHERE token_type="client"').fetchone()
        
        token = Token(dbEntry['token'], dbEntry['expires'], dbEntry['id'])
        token.removeFromDatabase()

        dbEntry = db.execute('SELECT * FROM token WHERE token_type="client"').fetchone()

        assert dbEntry == None

        db.execute('DELETE FROM token WHERE token_type="client"')
        db.commit()

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

def test_UserToken_fromDB(app):
    with app.app_context():
        db = get_db()
        db.execute('DELETE FROM token WHERE sessionid="test"')
        db.commit()
        db.execute('INSERT INTO token (token, expires, refresh, token_type, sessionid)'
                ' VALUES (?, ?, ?, ?, ?)',
                ("test", "2000-01-01T00:00:00", "test", "auth", "test")
                )
        db.commit()

        token = UserToken.fromDatabase("test")

        assert token.value() == "test"
        assert token.isExpired()

        db.execute('DELETE FROM token WHERE sessionid="test"')
        db.commit()

def test_UserToken_addToDB(app):
    with app.app_context():
        db = get_db()
        db.execute('DELETE FROM token WHERE sessionid="test"')
        db.commit()

        token = UserToken("test", datetime(2000,1,1), "test", "test")
        token.addToDatabase()

        dbEntry = db.execute('SELECT * FROM token WHERE sessionid="test"').fetchone()

        assert dbEntry['token'] == "test"
        assert dbEntry['expires'] == '2000-01-01T00:00:00'
        assert dbEntry['refresh'] == "test"
        assert dbEntry['token_type'] == "auth"
        assert dbEntry['sessionid'] == "test"

        db.execute('DELETE FROM token WHERE sessionid="test"')
        db.commit()