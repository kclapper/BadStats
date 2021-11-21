import requests

class WebAPI:
    """
    Handles requests to and responses from the spotify web api.
    """

    def __init__(self, response):
        """Takes in a requests module Reponse object and extracts necessary information."""

        self._rawResponse = response
        self._statusCode = response.status_code
        self._assertSuccessful()
        self._content = {"headers": self._rawResponse.headers}
        self._content.update(self._rawResponse.json())

    def _assertSuccessful(self):
        """Throws an exception if the request was not successful."""

        if self._statusCode >= 300:
            raise Exception(f"API Query Error, status code: {self._statusCode}, response: {self._rawResponse}")

    @classmethod
    def get(cls, *args, **kwargs):
        """Send get request and instantiate the class with the response."""

        return cls(requests.get(*args, **kwargs))

    @classmethod
    def post(cls, *args, **kwargs):
        """Send post request and instantiate the class with the response."""

        return cls(requests.post(*args, **kwargs))

    def json(self):
        """Return a json representation of the response from the Spotify API."""

        return self._rawResponse.json()

    def __getitem__(self, key):
        """Get the value of a key from the json representation of the response."""

        return self._content[key]