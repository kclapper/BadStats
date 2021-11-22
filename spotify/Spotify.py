import json, requests, base64, os, re, logging
from datetime import datetime, timedelta

from flask import current_app
from spotify.Token import BasicCreds

from badstats.db import get_db

from spotify.WebAPI import WebAPI

# class AbstractSpotify:
#     id = os.environ["CLIENTID"]
#     secret = os.environ["CLIENTSECRET"]

#     def __init__(self, *args, **kwargs):
#         self.token = self._getToken(*args, **kwargs)
        
#     def _getToken(self):
#         raise NotImplementedError("_getToken() is not implemented!")
    
#     @classmethod
#     def _tokenRequest(cls, data):
        
#         ## Get base64 encoded spotify app ID and secret
#         secret = f'{cls.id}:{cls.secret}'
#         encodedSecret = str(base64.b64encode(secret.encode("utf-8")), "utf-8")

#         ## Make post request to ask for bearer token
#         headers = {
#         'Authorization': f'Basic {encodedSecret}'
#         }

#         return requests.post("https://accounts.spotify.com/api/token", data=data, headers=headers)

#     @staticmethod
#     def _expires(response):
#         dateformatstring = '%a, %d %b %Y %H:%M:%S %Z'
#         expires = datetime.strptime(response.headers['date'], dateformatstring) \
#                         + timedelta(seconds=response.json()["expires_in"]) 
#         return expires

#     @staticmethod
#     def _tokenExpired(token):
#         """Return true if the token expired, false if valid"""
#         return datetime.utcnow() >= datetime.fromisoformat(token["expires"])

#     def _apiQuery(self, url, params=None):
#         # Format and send request
#         headers = {
#             'Authorization': f'Bearer {self.token}'
#         }

#         return WebAPI.get(
#             url,
#             headers=headers,
#             params=params
#         )

class Spotify:
    
    def __init__(self):
        self.token = BasicCreds().value()

    def _apiQuery(self, url, params=None):
        # Format and send request
        headers = {
            'Authorization': f'Bearer {self.token}'
        }

        return WebAPI.get(
            url,
            headers=headers,
            params=params
        )

    def search(self, query, kind):
        ## Used to search for artists to inspect

        if kind not in ['artist', 'album', 'song']:
            raise Exception("Invalid search kind")

        if kind == 'song':
            kind = 'track'

        # Format and send request
        url = 'https://api.spotify.com/v1/search'
        params={'q': f'{query}', 'type': f'{kind}', 'limit': '8'}
        response = self._apiQuery(url, params)

        if kind == 'artist':
            return response['artists']['items']

        elif kind =='album':
            return response['albums']['items']

        elif kind == 'track':
            for track in (result := response['tracks']['items']):
                track.update({"images": track['album']['images']})
            return result

        else:
            raise Exception("Invalid search kind after response")

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

        result = {key:value for (key, value) in response}

        url = f'https://api.spotify.com/v1/artists/{id}/top-tracks'
        params = {'market': 'US'}
        response = self._apiQuery(url, params=params)
        
        result.update({
            "top-tracks": response['tracks']
        })

        return result

    def album(self, id):
        # Get specific album information

        url = f'https://api.spotify.com/v1/albums/{id}'
        response = self._apiQuery(url)

        return response

    def song(self, id, region='US'):
        # Get specific song information

        url = f'https://api.spotify.com/v1/tracks/{id}'
        params = {'market': region}
        response = self._apiQuery(url, params=params)
        
        result = {key:value for key, value in response}

        url = f'https://api.spotify.com/v1/audio-features/{id}'
        response = self._apiQuery(url)
        
        result.update({key:value for key, value in response})

        return result
        
    def albumTrackDetails(self, id, region='US'):
        album = self.item('album', id)
        def trackSort(item):
            return item['track_number']
        album['tracks']['items'].sort(key=trackSort)
        tracks = {
            'album': album['name'],
            'tracks': [self.song(x['id'], region) for x in album['tracks']['items']]
            }

        return tracks

class UserSpotify(Spotify):
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