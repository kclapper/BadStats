

class Item:
    """Represents an item from the spotify api."""

    def __init__(self, kind, id):

        url = f'https://api.spotify.com/v1/{kind}/{id}'
        response = self._apiQuery(url)
        
        
    

    