from flask import (
    Blueprint, render_template, request, redirect, url_for, g, current_app, session
)
from werkzeug.exceptions import abort
import logging
from datetime import datetime, timedelta
from badstats.db import get_db

from spotify.Spotify import Spotify, UserSpotify
from badstats import getHostname
import badstats.plot as plot
from badstats.auth import withValidSession

bp = Blueprint('stats', __name__)

@bp.route('/')
def index():
    return redirect( url_for('stats.search', kind='artist', results=''))

@bp.route('/termsofservice')
def tos():
    return render_template('stats/tos.html')

@bp.route('/privacypolicy')
def privacypolicy():
    return render_template('stats/privacypolicy.html')

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
@withValidSession
def userPlaylists(kind):

    spotify = UserSpotify(session['id'])

    results = spotify.getUserPlaylists()

    return render_template("stats/user/playlistSelect.html", results=results)

@bp.route('/user/<kind>/<id>')
@withValidSession
def userItem(kind, id):
    spotify = UserSpotify(session['id'])

    if kind == "playlist":
        results = spotify.getPlaylist(id)

    return render_template(f'stats/user/{kind}.html', stats=results)

@bp.route('/user/playlist/<id>/plot/<kind>')
@withValidSession
def userPlaylistPlot(id, kind):
    spotify = UserSpotify(session['id'])

    results = spotify.getPlaylist(id)
    tracks = []
    for track in results['tracks']:
        trackstats = spotify.song(track['id'])
        tracks.append({
            'name': trackstats['name'],
            kind: trackstats[kind]
        })
    
    fig_data = plot.playlist(kind, tracks, results['name'])



    return render_template(f'stats/user/playlistPlot.html', result=fig_data.decode('utf-8'))
    