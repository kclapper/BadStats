import functools, os, requests, logging
from secrets import token_urlsafe
from datetime import datetime, timedelta

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, 
    current_app
)
from werkzeug.security import check_password_hash, generate_password_hash

from badstats.db import get_db
from badstats import getHostname
from spotify.Spotify import UserSpotify

bp = Blueprint('auth', __name__, url_prefix='/auth')

def issueCsrf():
    csrfToken = token_urlsafe()

    db = get_db()
    db.execute(
        'INSERT INTO csrf (token, created) VALUES (?, ?);',
        (csrfToken, datetime.utcnow().isoformat())
    )
    db.commit()

    return csrfToken

def isValid(csrf):
    if not csrf:
        return False

    db = get_db()
    token = db.execute("SELECT * FROM csrf WHERE token = ?", (csrf,)).fetchone()

    if not token:
        return False

    tokenexpires = datetime.fromisoformat(token["created"]) \
        + timedelta(minutes=2) 

    if datetime.utcnow() >= tokenexpires:
        db.execute('DELETE FROM csrf WHERE token = ?', (csrf,))
        db.commit()
        print("CSRF token expired, deleted token")
        return False
    
    return True

@bp.route('/spotify/authorize/<kind>', methods=['POST', 'GET'])
def userAuth(kind):
    if kind != "playlist":
        return redirect( url_for('stats.search', kind='artist', results=''))

    if request.method == "GET":
        return render_template("auth/user.html", kind=kind, csrf=issueCsrf())

    csrf = request.form['csrf']
    if not isValid(csrf):
        print("CSRF not valid, redirecting to index")
        return redirect( url_for('stats.search', kind='artist', results=''))

    redirecturi = f'{getHostname()}{url_for("auth.receiveAuth", kind=kind)}'
    client_id = os.environ['CLIENTID']
    show_dialog = 'true'
    scope = "playlist-read-private"
    params = {
        'client_id': client_id,
        'scope': scope,
        'redirect_uri': redirecturi,
        'response_type': 'code',
        'state': csrf,
        'show_dialog': show_dialog,
    }
    url = "https://accounts.spotify.com/authorize"
    
    response = requests.get(url, params=params)

    if response.status_code >= 300:
        current_app.logger.warning(f"Spotify user auth redirect error, \
            status code: {response.status_code}")
        current_app.logger.warning(response.json()['error'])
        return redirect(url_for('stats.index'))
    
    req = requests.Request("GET", url, params=params).prepare()
    return redirect(f'https://accounts.spotify.com{req.path_url}')
    
@bp.route('/spotify/receive/<kind>', methods=['GET'])
def receiveAuth(kind):
    # Redirect url from authorization request, receives code and state from spotify
    # Validates the state then redirects to a view along with the code

    # Send them back home if there was an error
    if "error" in request.args:
        current_app.logger.warning(f"Error on Spotify auth reception: {request.args['error']}")
        return redirect(url_for('stats.index'))

    # Redirect with the spotify api code to the route to actually
    # Use the authenticated instance of spotify
    state = request.args['state']
    if isValid(state):
        session['id'] = token_urlsafe()
        session['created'] = datetime.utcnow().isoformat()

        host = getHostname()
        redirecturl = f"{host}{url_for('auth.receiveAuth', kind=kind)}"

        UserSpotify.fromCode(request.args.get('code'), redirecturl, session['id'])

        return redirect(url_for('stats.userPlaylists', kind=kind))

    # Anything else means the csrf state was invalid
    current_app.logger.warning(f"Invalid state: {state}")
    return redirect(url_for('stats.index'))

def withValidSession(func):
    @functools.wraps(func)
    def withValidSession(*args, **kwargs):
        
        def handlePop(reason=None):
            session.pop('id', None)
            session.pop('created', None)
            current_app.logger.debug("Popped session")
            current_app.logger.debug(f"Popped for {reason}")
        
        session_created = session.get('created')
        
        if session_created is None:
            return redirect(url_for('auth.userAuth', kind='playlist'))
        
        expires = datetime.fromisoformat(session_created) + timedelta(minutes=30)
        
        if datetime.utcnow() >= expires:
            handlePop()
            return redirect(url_for('auth.userAuth', kind='playlist'))

        if datetime.fromisoformat(session_created) > datetime.utcnow():
            handlePop()
            return redirect(url_for('auth.userAuth', kind='playlist'))

        db = get_db()

        sessionid = db.execute("SELECT sessionid FROM token WHERE sessionid=?", (session.get('id'),)).fetchone()
        if sessionid is None:
            handlePop()
            return redirect(url_for('auth.userAuth', kind='playlist'))

        return func(*args, **kwargs)
    return withValidSession

@bp.route('/disconnect')
@withValidSession
def disconnect():

    db = get_db()
    db.execute("DELETE FROM token WHERE sessionid=?", (session['id'],))
    db.commit()

    session.pop('id', None)
    session.pop('created', None)

    return redirect( url_for('stats.index') )