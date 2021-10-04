import json, requests, base64, os, re, logging
from datetime import datetime, timedelta

from flask import current_app

from badstats.db import get_db

class Spotify:
    def __init__(self, code=None, url=None, sessionid=None):
        ## Get Spotify credentials from environment variables and get access token
        self.id = os.environ["CLIENTID"]
        self.secret = os.environ["CLIENTSECRET"]
        if code and url and sessionid:
            self.token = self.generateAuthToken(code, url, sessionid)
        elif sessionid:
            self.token = self.getAuthToken(sessionid)
        elif code or url or sessionid:
            current_app.logger.warning("Incomplete arguments given to Spotify(), running as client")
        else:
            self.token = self.getClientToken()
        
    def tokenRequest(self, data):
        ## Make token request for either client or auth token

        ## Get base64 encoded spotify app ID and secret
        secret = f'{self.id}:{self.secret}'
        encodedSecret = str(base64.b64encode(secret.encode("utf-8")), "utf-8")

        ## Make post request to ask for bearer token
        headers = {
        'Authorization': f'Basic {encodedSecret}'
        }

        return requests.post("https://accounts.spotify.com/api/token", data=data, headers=headers)

    def getClientToken(self):
            ## Get authentication token from Spotify 
            ## Return token if authenticated, None if not.

            ## First check cache for valid token
            cachedToken = self.checkTokenCache()
            if cachedToken:
                return cachedToken

            ## Make initial post request to ask for bearer token
            data = {
                'grant_type': 'client_credentials'
            }
            response = self.tokenRequest(data)
            
            if response.status_code >= 300:
                return None

            # Cache and return token
            self.cacheToken(response)
            return response.json()["access_token"]
    
    def generateAuthToken(self, code, url, sessionid):
        ## Get user authenticated token
        ## Stores the token in the database for session based auth

        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': url,
        }
        response = self.tokenRequest(data)

        if response.status_code >= 300:
            current_app.logger.warning("getAuthToken failed to get user auth token")
            return None
        
        current_app.logger.debug("User authenticated token acquired")

        self.cacheToken(response, sessionid)
        
        return self.getAuthToken(sessionid)
        # return response.json()['access_token']

    def getAuthToken(self, sessionid):

        cachedToken = self.checkTokenCache(sessionid)
        if cachedToken:
            return cachedToken
        
        db = get_db()

        token = db.execute('SELECT * FROM token WHERE sessionid=(?)', (sessionid,)).fetchone()

        ## Make post request to ask for new token
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': token['refresh']
        }
        response = self.tokenRequest(data)
        
        if response.status_code >= 300:
            current_app.logger.warning("Token refresh failed!")
            return None
        
        expires = self.expires(response)
        response = response.json()
        
        db.execute("UPDATE token SET token=?, expires=?, refresh=?", 
                    (response['access_token'], expires, token['refresh'])
        )
        db.commit()

        return response['access_token']
    
    @staticmethod
    def expires(response):
        dateformatstring = '%a, %d %b %Y %H:%M:%S %Z'
        expires = datetime.strptime(response.headers['date'], dateformatstring) \
                        + timedelta(seconds=response.json()["expires_in"]) 
        return expires

    def checkTokenCache(self, sessionid=None):
        ## Check if we still have a valid token
        ## Return token if we do, False if we don't
        
        ## Get token file from db
        db = get_db()

        if sessionid:
            token = db.execute('SELECT * FROM token WHERE sessionid=(?)', (sessionid,)).fetchone()
        else:
            token = db.execute('SELECT * FROM token WHERE token_type="client"').fetchone()
        
        if token is None:
            return False
        elif datetime.utcnow() >= datetime.fromisoformat(token["expires"]):
            if token['token_type'] == 'auth': # Don't delete the token if it's an auth token, we need to refresh it instead
                return False
            db.execute('DELETE FROM token WHERE id=(?)', (token['id'],))
            db.commit()
            return False
        else:
            return token['token']

    def cacheToken(self, response, sessionid=None):
        ## Cache token to file in db
        
        expires = self.expires(response)
        
        token = response.json()["access_token"]
        
        if 'refresh_token' in response.json():
            refresh_token = response.json()['refresh_token']
            token_type = "auth"
        else:
            refresh_token = None
            token_type = "client"
        
        db = get_db()
        db.execute(
                'INSERT INTO token (token, expires, refresh, token_type, sessionid)'
                ' VALUES (?, ?, ?, ?, ?)',
                (token, expires, refresh_token, token_type, sessionid)
            )
        db.commit()

        return

    def apiQuery(self, url, params=None):
        # Format and send request
        headers = {
            'Authorization': f'Bearer {self.token}'
        }
        response = requests.get(
            url, 
            headers=headers,
            params=params,
            )
        
        if response.status_code >= 400:
            current_app.logger.warning(f"API Query Error, status code {response.status_code}, message: {response.json()['error']['message']}")
            current_app.logger.warning(f"API query url: {url}")
            return []
        
        return response.json()


    def search(self, query, kind):
        ## Used to search for artists to inspect

        if kind not in ['artist', 'album', 'song']:
            return []

        if kind == 'song':
            kind = 'track'

        # Format and send request
        url = 'https://api.spotify.com/v1/search'
        params={'q': f'{query}', 'type': f'{kind}', 'limit': '5'}
        response = self.apiQuery(url, params)

        if not response:
            return []

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
            return []

    def artist(self, id):
        # Return info about a specific artist
        
        url = f'https://api.spotify.com/v1/artists/{id}'
        response = self.apiQuery(url)
        
        if not response:
            result = {}
        else:
            result = {
                'genres': response['genres'],
                'images': response['images'],
                'followers': response['followers']['total'],
                'name': response['name'],
                'popularity': response['popularity'],
            }

        url = f'https://api.spotify.com/v1/artists/{id}/top-tracks'
        params = {'market': 'US'}
        response = self.apiQuery(url, params=params)

        if response:
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
        response = self.apiQuery(url)

        if not response:
            return {}
        
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
        response = self.apiQuery(url, params=params)

        if not response:
            return {}
        
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
        response = self.apiQuery(url)

        if not response:
            return {}
        
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

    def getUserPlaylists(self):
        # Requires User Authorization. Instance must be instantiated with code and redirecturi.

        url = "https://api.spotify.com/v1/me/playlists"

        response = self.apiQuery(url)

        if not response:
            return {}

        results = [{
            'description': x['description'],
            'id': x['id'],
            'images': x['images'],
            'name': x['name'],
            'owner': x['owner']['display_name'],
        } for x in response['items']]

        current_app.logger.debug(results)

        return results

    def getPlaylist(self, id):

        url = f"https://api.spotify.com/v1/playlists/{id}"

        response = self.apiQuery(url)

        if not response:
            return {}

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