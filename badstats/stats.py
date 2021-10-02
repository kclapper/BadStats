from flask import (
    Blueprint, render_template, request, redirect, url_for, g, current_app
)
from werkzeug.exceptions import abort
import logging

from badstats.spotify import Spotify
from badstats import getHostname
import badstats.plot as plot

bp = Blueprint('stats', __name__)

# log = logging.getLogger('badstats')

@bp.route('/')
def index():
    return redirect( url_for('stats.search', kind='artist', results=''))

@bp.route('/search/<kind>', methods=['GET', 'POST'])
def search(kind):
    if kind not in ['artist', 'album', 'song']:
        return render_template('stats/index.html')
    if request.method == 'POST' and request.form['search']:
        spotify = Spotify()
        results = spotify.search(request.form['search'], kind)

        if not results:
            abort(500)

        return render_template(f'stats/search.html', kind=kind, results=results)
    return render_template(f'stats/search.html', kind=kind, results='')

@bp.route('/item/<kind>/<id>')
def item(kind, id):
    if kind not in ['artist', 'album', 'song']:
        return render_template('stats/index.html')
    if not id:
        return render_template('stats/index.html')
    
    spotify = Spotify()
    result = spotify.item(kind, id)

    if not result:
        abort(500)
        
    return render_template(f'stats/{kind}.html', stats=result)

@bp.route('/plot/album/<kind>/<id>')
def plotPNG(kind, id):
    spotify = Spotify()
    tracks = spotify.albumTrackDetails(id)
    fig_data = plot.album(kind, tracks, regions=['US'])
        
    return render_template('stats/plot.html', result=fig_data.decode('utf-8'))

@bp.route('/user/<kind>')
def userItem(kind):

    # Check the code query string is there
    if "code" not in request.args:
        return redirect(url_for('stats.index'))
    code = request.args.get("code")

    # The redirecturl is predictable based on kind
    host = getHostname()
    redirecturl = f"{host}{url_for('auth.receiveAuth', kind=kind)}"
    current_app.logger.debug(f'userItem redirecturl: {redirecturl}')

    spotify = Spotify(code=code, url=redirecturl)

    results = spotify.getUserPlaylists()

    return render_template("stats/user/playlistSelect.html", results=results)
    