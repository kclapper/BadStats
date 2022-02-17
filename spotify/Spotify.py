from flask import current_app
from spotify.Token import BasicCreds, UserCreds

from badstats.db import get_db

from spotify.WebAPI import WebAPI

class Spotify:
    
    def __init__(self):
        self._token = BasicCreds()

    def _apiQuery(self, url, params=None):
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

    def item(self, kind, id):
        
        resourceMap = {
            "artist": ("artists", f'https://api.spotify.com/v1/artists/{id}/top-tracks', {'market': 'US'}),
            "album": ("albums", False, None),
            "song": ("tracks", f'https://api.spotify.com/v1/audio-features/{id}', None),
        }
        resource = resourceMap[kind]

        url = f'https://api.spotify.com/v1/{resource[0]}/{id}'
        response = self._apiQuery(url)

        if resource[1]:
            response.update(self._apiQuery(resource[1], params=resource[2]))

        return response

    def multipleItems(self, kind, ids):

        resourceMap = {
            "artist": ("artists", 50),
            "album": ("albums", 20),
            "song": ("tracks", 50),
        }
        resource = resourceMap[kind]

        url = f'https://api.spotify.com/v1/{resource[0]}'
        params = {
            'ids': ",".join(ids),
            'market': 'US',
        }
        response = self._apiQuery(url, params=params)[resource[0]]

        return response
        
    def multipleSongDetails(self, ids):

        url = f'https://api.spotify.com/v1/audio-features'
        params = {
            'ids': ",".join(ids),
            'market': 'US',
        }
        audioFeatures = self._apiQuery(url, params=params)["audio_features"]

        tracks = self.multipleItems("song", ids)

        for track in tracks:
            for feature in audioFeatures:
                if track['id'] == feature['id']:
                    track.update(feature)

        return tracks

    def albumTrackDetails(self, id):
        album = self.item('album', id)

        def trackSort(item):
            return item['track_number']

        album['tracks']['items'].sort(key=trackSort)
        tracks = {
            'album': album['name'],
            'tracks': self.multipleSongDetails([song['id'] for song in album['tracks']['items']])
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
        
        url = "https://api.spotify.com/v1/me/playlists"

        response = self._apiQuery(url)

        return response

    def getPlaylist(self, id):

        url = f"https://api.spotify.com/v1/playlists/{id}"

        response = self._apiQuery(url)

        return response