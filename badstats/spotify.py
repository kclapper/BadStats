import json, requests, base64, os, re, logging
from datetime import datetime, timedelta

from flask import current_app

from badstats.db import get_db

class AbstractSpotify:
    id = os.environ["CLIENTID"]
    secret = os.environ["CLIENTSECRET"]

    def __init__(self, *args, **kwargs):
        self.token = self._getToken(*args, **kwargs)
        
    def _getToken(self):
        raise NotImplementedError("_getToken() is not implemented!")
    
    @classmethod
    def _tokenRequest(cls, data):

        ## Get base64 encoded spotify app ID and secret
        secret = f'{cls.id}:{cls.secret}'
        encodedSecret = str(base64.b64encode(secret.encode("utf-8")), "utf-8")

        ## Make post request to ask for bearer token
        headers = {
        'Authorization': f'Basic {encodedSecret}'
        }

        return requests.post("https://accounts.spotify.com/api/token", data=data, headers=headers)

    @staticmethod
    def _expires(response):
        dateformatstring = '%a, %d %b %Y %H:%M:%S %Z'
        expires = datetime.strptime(response.headers['date'], dateformatstring) \
                        + timedelta(seconds=response.json()["expires_in"]) 
        return expires

    @staticmethod
    def _tokenExpired(token):
        """Return true if the token expired, false if valid"""
        return datetime.utcnow() >= datetime.fromisoformat(token["expires"])

    def _apiQuery(self, url, params=None):
        # Format and send request
        headers = {
            'Authorization': f'Bearer {self.token}'
        }
        response = requests.get(
            url, 
            headers=headers,
            params=params,
            )
        
        if response.status_code >= 300:
            raise Exception(f"API Query Error, status code {response.status_code}, message: {response.json()['error']['message']} \n \
                                API query url: {url}")
        
        return response.json()

class PublicSpotify(AbstractSpotify):
    def _checkTokenCache(self):
        db = get_db()

        token = db.execute('SELECT * FROM token WHERE token_type="client"').fetchone()

        if token is None:
            return False
        elif self._tokenExpired(token):
            db.execute('DELETE FROM token WHERE id=(?)', (token['id'],))
            db.commit()
            return False
        else:
            return token['token']

    def _cacheToken(self, response):
        ## Cache token to file in db
        
        expires = self._expires(response)
        
        token = response.json()["access_token"]
        
        db = get_db()
        db.execute(
                'INSERT INTO token (token, expires, refresh, token_type, sessionid)'
                ' VALUES (?, ?, ?, ?, ?)',
                (token, expires, None, "client", None)
            )
        db.commit()

        return 
        
    def _getToken(self):
        """Get authentication token from Spotify"""

        ## First check cache for valid token
        cachedToken = self._checkTokenCache()
        if cachedToken:
            return cachedToken

        ## Make post request to ask for bearer token
        data = {
            'grant_type': 'client_credentials'
        }
        response = self._tokenRequest(data)
        
        if response.status_code >= 300:
            raise Exception("Client token request failed")
        
        # Cache and return token
        self._cacheToken(response)
        return response.json()["access_token"]

    def search(self, query, kind):
        ## Used to search for artists to inspect

        if kind not in ['artist', 'album', 'song']:
            raise Exception("Invalid search kind")

        if kind == 'song':
            kind = 'track'

        # Format and send request
        url = 'https://api.spotify.com/v1/search'
        params={'q': f'{query}', 'type': f'{kind}', 'limit': '5'}
        response = self._apiQuery(url, params)

        if kind == 'artist':
            result = [
                {
                    'name': x['name'],
                    'id': x['id'],
                    'images': x['images']
                } for x in response['artists']['items']]
        elif kind =='album':
            result = [
                {
                    'id': x['id'],
                    'images': x['images'],
                    'name': x['name'],
                    'release_date': x['release_date'],
                    'total_tracks': x['total_tracks']
                } for x in response['albums']['items']]
        elif kind == 'track':
            result = [
                {
                    'id': x['id'],
                    'name': x['name'],
                    'images': x['album']['images'],
                } for x in response['tracks']['items']
            ]
        else:
            result = []


        return result

    def item(self, kind, id, region='US'):
        if kind == 'artist':
            return self.artist(id)
        elif kind == 'album':
            return self.album(id)
        elif kind == 'song':
            return self.song(id, region)
        else:
            raise Exception("Invalid item kind")

    def artist(self, id):
        # Return info about a specific artist
        
        url = f'https://api.spotify.com/v1/artists/{id}'
        response = self._apiQuery(url)
        
        result = {
            'genres': response['genres'],
            'images': response['images'],
            'followers': response['followers']['total'],
            'name': response['name'],
            'popularity': response['popularity'],
        }

        url = f'https://api.spotify.com/v1/artists/{id}/top-tracks'
        params = {'market': 'US'}
        response = self._apiQuery(url, params=params)

        response = response['tracks']
        result.update({
            'top-tracks': [
                {
                    'name': x['name'],
                    'popularity': x['popularity'],
                    'id': x['id'],
                    'explicit': x['explicit'],
                    'duration': x['duration_ms'],
                    'album': x['album']['name'],
                    'albumid': x['album']['id'],
                    'images': x['album']['images'],
                    'artists': [y['name'] for y in x['album']['artists']]
                } for x in response]
        })

    
        return result

    def album(self, id):
        # Get specific album information

        url = f'https://api.spotify.com/v1/albums/{id}'
        response = self._apiQuery(url)
        
        result = {
            'artists': [y['name'] for y in response['artists']],
            'genres': response['genres'],
            'id': response['id'],
            'images': response['images'],
            'name': response['name'],
            'popularity': response['popularity'],
            'release_date': response['release_date'],
            'tracks': [{
                'name': y['name'],
                'id': y['id'],
                'track_number': y['track_number'],
                } for y in response['tracks']['items']]
        } 

        return result

    def song(self, id, region='US'):
        # Get specific song information

        url = f'https://api.spotify.com/v1/tracks/{id}'
        params = {'market': region}
        response = self._apiQuery(url, params=params)
        
        result = {
            'album': {
                'name': response['album']['name'],
                'id': response['album']['id'],
                },
            'id': response['id'],
            'images': response['album']['images'],
            'name': response['name'],
            'popularity': response['popularity'],
            'artists': [{
                'name': y['name'],
                'id': y['id']} for y in response['artists']],
            'explicit': response['explicit'],
            'duration_ms': response['duration_ms'],
        } 

        url = f'https://api.spotify.com/v1/audio-features/{id}'
        response = self._apiQuery(url)
        
        result.update({
            "danceability": response['danceability'],
            "energy": response['energy'],
            "key": response['key'],
            "loudness": response['loudness'],
            "mode": response['mode'],
            "speechiness": response['speechiness'],
            "acousticness": response['acousticness'],
            "instrumentalness": response['instrumentalness'],
            "liveness": response['liveness'],
            "valence": response['valence'],
            "tempo": response['tempo'],
            "time_signature": response['time_signature'],
        })

        return result
        
    def albumTrackDetails(self, id, region='US'):
        album = self.item('album', id)
        def trackSort(item):
            return item['track_number']
        album['tracks'].sort(key=trackSort)
        tracks = {
            'album': album['name'],
            'tracks': [self.song(x['id'], region) for x in album['tracks']]
            }

        return tracks

class UserSpotify(PublicSpotify):
    def _checkTokenCache(self, sessionid):
        ## Check if we still have a valid token
        ## Return token if we do, False if we don't
        
        db = get_db()

        token = db.execute('SELECT * FROM token WHERE sessionid=(?)', (sessionid,)).fetchone()
        
        if token is None:
            return False
        elif self._tokenExpired(token):
            return False
        else:
            return token['token']

    @classmethod
    def _cacheToken(cls, response, sessionid):
        
        expires = cls._expires(response)
        token = response.json()["access_token"]
        refresh_token = response.json()['refresh_token']
        
        db = get_db()
        db.execute(
                'INSERT INTO token (token, expires, refresh, token_type, sessionid)'
                ' VALUES (?, ?, ?, ?, ?)',
                (token, expires, refresh_token, "auth", sessionid)
            )
        db.commit()

        return

    def _getToken(self, sessionid):

        cachedToken = self._checkTokenCache(sessionid)
        if cachedToken:
            return cachedToken
        
        db = get_db()

        token = db.execute('SELECT * FROM token WHERE sessionid=(?)', (sessionid,)).fetchone()

        ## Make post request to ask for new token
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': token['refresh']
        }
        response = self._tokenRequest(data)
        
        if response.status_code >= 300:
            raise Exception("Auth token refresh failed")
        
        expires = self._expires(response)
        response = response.json()
        
        db.execute("UPDATE token SET token=?, expires=?, refresh=?", 
                    (response['access_token'], expires, token['refresh'])
        )
        db.commit()

        return response['access_token']

    @classmethod
    def fromCode(cls, code, url, sessionid):
        ## Get user authenticated token
        ## Stores the token in the database for session based auth

        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': url,
        }
        response = cls._tokenRequest(data)

        if response.status_code >= 300:
            raise Exception("User authentication token request failed")
        
        current_app.logger.debug("User authenticated token acquired")

        cls._cacheToken(response, sessionid)
        
        return cls(sessionid)

    def getUserPlaylists(self):
        # Requires User Authorization. Instance must be instantiated with code and redirecturi.

        url = "https://api.spotify.com/v1/me/playlists"

        response = self._apiQuery(url)

        results = [{
            'description': x['description'],
            'id': x['id'],
            'images': x['images'],
            'name': x['name'],
            'owner': x['owner']['display_name'],
        } for x in response['items']]

        return results

    def getPlaylist(self, id):

        url = f"https://api.spotify.com/v1/playlists/{id}"

        response = self._apiQuery(url)

        results = {
            'description': response['description'],
            'followers': response['followers']['total'],
            'id': response['id'],
            'images': response['images'],
            'name': response['name'],
            'owner': response['owner']['display_name'],
            'public': response['public'],
            'tracks': [
                {
                    'albumid': track['track']['album']['id'],
                    'albumname': track['track']['album']['name'],
                    'albumimages': track['track']['album']['images'],
                    'artists': [
                        {
                            'id': artist['id'],
                            'name': artist['name'],
                        } for artist in track['track']['album']['artists']
                    ],
                    'id': track['track']['id'],
                    'name': track['track']['name'],
                    'popularity': track['track']['popularity'],
                } 
                for track in response['tracks']['items']
            ]
        }

        return results