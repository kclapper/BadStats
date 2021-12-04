import base64, os

from datetime import datetime, timedelta

from flask.globals import session

from badstats.db import get_db

from spotify.WebAPI import WebAPI

class Token:
    """Represents a token with an expiration datetime."""

    def __init__(self, value: str, expires: datetime, id=None):
        """Prepare common elements of token requests."""
        
        self._value = value
        self._expires = expires
        self._id = id

    def removeFromDatabase(self):
        """Removes the token from the database."""
        
        if not self._id:
            raise Exception("Token must have an id to remove it from the database.")
        db = get_db()
        db.execute('DELETE FROM token WHERE id=(?)', (self._id,))
        db.commit()

    def isExpired(self) -> bool:
        """Determines if the token is expired."""
        
        return datetime.utcnow() >= self._expires

    def value(self) -> str:
        """Get the value of the token."""

        return self._value

class ClientToken(Token):

    def __init__(self, value: str, expires, id=None):
        super().__init__(value, expires, id)

    @classmethod
    def fromDatabase(cls):
        """Return a ClientToken cached in the database."""

        db = get_db()

        token = db.execute('SELECT * FROM token WHERE token_type="client"').fetchone()

        if token is None:
            raise Exception("No client token found in the database!")

        return cls(
            token['token'], 
            datetime.fromisoformat(token['expires']), 
            id=token['id']
            )
        
    def addToDatabase(self):
        """Adds a token to the database."""

        db = get_db()
        db.execute(
                'INSERT INTO token (token, expires, refresh, token_type, sessionid)'
                ' VALUES (?, ?, ?, ?, ?)',
                (self._value, self._expires.isoformat(), None, "client", None)
            )
        db.commit()

class UserToken(Token):

    def __init__(self, value, expires, refresh_token, sessionid, id=None):
        super().__init__(value, expires, id)
        self._refreshTokenValue = refresh_token
        self._sessionid = sessionid
    
    @classmethod
    def fromDatabase(cls, sessionid):
        """Return a UserToken tied to a sessionid cached in the database."""

        db = get_db()

        token = db.execute('SELECT * FROM token WHERE sessionid=(?)', (sessionid,)).fetchone()

        if token is None:
            raise Exception("UserToken not found in the database!")

        return cls(
            token['token'], 
            datetime.fromisoformat(token['expires']),
            token['refresh'],
            token['sessionid'], 
            id=token['id']
            )

    def addToDatabase(self):
        """Adds the token to the database."""

        db = get_db()
        db.execute(
                'INSERT INTO token (token, expires, refresh, token_type, sessionid)'
                ' VALUES (?, ?, ?, ?, ?)',
                (self._value, self._expires.isoformat(), self._refreshTokenValue, "auth", self._sessionid)
            )
        db.commit()

    def refreshTokenValue(self):
        return self._refreshTokenValue

    def refresh(self, token, expires, refreshToken):
        """Refresh the token with new credentials."""

        self._value = token
        self._expires = expires
        self._refreshTokenValue = refreshToken

        db = get_db()
        db.execute("UPDATE token SET token=?, expires=? WHERE sessionid=?", 
                    (self._value, self._expires, self._sessionid)
        )
        db.commit()

class Creds:

    @classmethod
    def _tokenRequest(cls, data):
        """Sends the request for a new token from the spotify web api."""

        url = "https://accounts.spotify.com/api/token"
        headers = {'Authorization': f'Basic {cls._getEncodedCredentials()}'}

        return WebAPI.post(url, headers=headers, data=data)

    @staticmethod
    def _getEncodedCredentials():
        """
        Formats the application id and secret in the way spotify wants them
        for token requests.
        """
        
        id = os.environ["CLIENTID"]
        secret = os.environ["CLIENTSECRET"]

        tokenString = f"{id}:{secret}".encode("utf-8")
        b64EncodedToken = base64.b64encode(tokenString)

        return str(b64EncodedToken, "utf-8")

    @staticmethod
    def _expires(response):
        dateformatstring = '%a, %d %b %Y %H:%M:%S %Z'
        expires = datetime.strptime(response['headers']['date'], dateformatstring) \
                        + timedelta(seconds=response["expires_in"]) 
        return expires

    def value(self):
        """Returns the value of the corresponding token."""

        ## The concrete class must define self._token in it's construction.

        return self._token.value()

class BasicCreds(Creds):
    """Represents 'client' credentials from the spotify web api."""

    def __init__(self):

        try:
            self._token = ClientToken.fromDatabase()
        except:
            self._token = self._getNewToken()
        
        if self._token.isExpired():
            self._token.removeFromDatabase()
            self._token = self._getNewToken()

    def _getNewToken(self):
        """Request a new ClientToken"""

        response = self._tokenRequest({"grant_type": "client_credentials"})

        token = ClientToken(response["access_token"], self._expires(response))

        token.addToDatabase()

        return token

class UserCreds(Creds):
    """Represents credentials for a specific Spotify user account"""

    def __init__(self, sessionid):

        self._token = UserToken.fromDatabase(sessionid)

        if self._token.isExpired():
            self._refreshToken()
        
    def _refreshToken(self):
        """Uses the refresh token to get a new auth token."""

        response = self._tokenRequest({
            'grant_type': 'refresh_token',
            'refresh_token': self._token.refreshTokenValue()
        })

        self._token.refresh(
            response['access_token'],
            self._expires(response),
        )

    @classmethod
    def fromCode(cls, code, url, sessionid):
        """Create new user credentials."""

        response = cls._tokenRequest({
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': url,
        })

        tokenValue = response['access_token']
        expires = cls._expires(response)
        refreshTokenValue = response['refresh_token']

        token = UserToken(
            tokenValue,
            expires,
            refreshTokenValue,
            sessionid 
        )

        token.addToDatabase()

        return cls(sessionid)
    

            