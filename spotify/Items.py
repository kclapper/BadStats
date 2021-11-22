

class Item:
    """Represents an item from the spotify api."""

    def __init__(self, data):
        
        self._id = data["id"]
        self._name = data['name']
        self._url = data['url']

        self._data = {
            "id": data['id'],
            "name": data['name'],
            "url": data['url']
        }

    def data(self):
        return self._data
    

class Track(Item):

    def __init__(self, data):
        
        super().__init__(self, data)

        self._data.update(
            {
                "album": {
                    "images": data['album']['images'],
                    "name": data['album']['name'],
                    "id": data['album']['id']
                    },
                "artists": [
                    {
                        "name": artist['name'],
                        "id": artist['id']
                    }
                    for artist in data['artists']
                ],
                "explicit": data['explicit'],
                "duration_ms": data['duration_ms'],
                "popularity": data['popularity'],
                "preview_url": data['preview_url'],
                "track_number": data['track_number'],
                


            }
        )

    

    