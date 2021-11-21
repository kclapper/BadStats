import base64, os

from datetime import datetime, timedelta

from badstats.db import get_db

from spotify.WebAPI import WebAPI

class Token:
    """Represents a token with an expiration datetime."""

    def __init__(self, value: str, expires: datetime):
        """Prepare common elements of token requests."""
        
        self._value = value
        self._expires = expires

    def isExpired(self) -> bool:
        """Determines if the token is expired."""
        
        return datetime.utcnow() >= self._expires

    def value(self) -> str:
        """Get the value of the token."""

        return self._value

    @classmethod
    def getNewToken(cls, grant_type):
        """Sends the request for a new token from the spotify web api."""

        url = "https://accounts.spotify.com/api/token"
        headers = {'Authorization': f'Basic {cls._getEncodedCredentials()}'}
        data = {"grant_type": grant_type}

        return WebAPI.post(url, headers=headers, data=data).json()

    @staticmethod
    def _getEncodedCredentials():
        """
        Formats the application id and secret in the way spotify wants them
        for token requests.
        """
        
        id = os.environ["CLIENTID"]
        secret = os.environ["CLIENTSECRET"]

        tokenString = f"{id}:{secret}".encode("utf-8")
        b64EncodedToken = base64.b64encode(tokenString, "utf-8")

        return str(b64EncodedToken)

class ClientToken(Token):

    def __init__(self, value: str, expires, id=None):
        super().__init__(value, expires)
        self._id = id

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
        
    def removeFromDatabase(self):
        """Removes the token from the database."""
        
        if not self._id:
            raise Exception("ClientToken must have an id to remove it from the database.")
        db = get_db()
        db.execute('DELETE FROM token WHERE id=(?)', (self._id,))
        db.commit()

    def addToDatabase(self):
        """Adds a token to the database."""

        db = get_db()
        db.execute(
                'INSERT INTO token (token, expires, refresh, token_type, sessionid)'
                ' VALUES (?, ?, ?, ?, ?)',
                (self._value, self._expires.isoformat(), None, "client", None)
            )
        db.commit()

class Creds:

    @classmethod
    def _tokenRequest(cls, grant_type):
        """Sends the request for a new token from the spotify web api."""

        url = "https://accounts.spotify.com/api/token"
        headers = {'Authorization': f'Basic {cls._getEncodedCredentials()}'}
        data = {"grant_type": grant_type}

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

        response = self._tokenRequest("client_credentials")

        token = ClientToken(response["access_token"], self._expires(response))

        token.addToDatabase()

        return token

    def value(self):
        """Returns the value of the ClientToken."""
        
        return self._token.value()