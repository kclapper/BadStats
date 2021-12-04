import json, requests, base64, os, re, logging
from datetime import datetime, timedelta

from flask import current_app
from spotify.Token import BasicCreds, UserCreds, UserToken

from badstats.db import get_db

from spotify.WebAPI import WebAPI

class Spotify:
    
    def __init__(self):
        self._token = BasicCreds()

    def _apiQuery(self, url, params=None):
        # Format and send request
        headers = {
            'Authorization': f'Bearer {self._token.value()}'
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

    def __init__(self, sessionid):
        self._token = UserCreds(sessionid)
    
    @classmethod
    def fromCode(cls, code, url, sessionid):

        UserCreds.fromCode(code, url, sessionid)

        return cls(sessionid)

    def getUserPlaylists(self):
        # Requires User Authorization. Instance must be instantiated with code and redirecturi.

        url = "https://api.spotify.com/v1/me/playlists"

        response = self._apiQuery(url)

        return response

    def getPlaylist(self, id):

        url = f"https://api.spotify.com/v1/playlists/{id}"

        response = self._apiQuery(url)

        return response