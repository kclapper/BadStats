import functools, os, requests, logging
from secrets import token_urlsafe
from datetime import datetime, timedelta

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)
from werkzeug.security import check_password_hash, generate_password_hash

from badstats.db import get_db
from badstats import getHostname
from badstats.spotify import UserSpotify

bp = Blueprint('auth', __name__, url_prefix='/auth')

# log = logging.getLogger('badstats')

def issueCsrf():
    csrf = token_urlsafe()
    db = get_db()
    db.execute(
        'INSERT INTO csrf (token, created) VALUES (?, ?);',
        (csrf, datetime.utcnow().isoformat())
    )
    db.commit()
    return csrf

def isValid(csrf):
    # Return True if csrf is valid
    # Return False if not
    
    # Return false if no csrf given
    if not csrf:
        return False

    # Check if a matching csrf token is in the database
    db = get_db()
    token = db.execute("SELECT * FROM csrf WHERE token = ?", (csrf,)).fetchone()

    # If no token was found then the csrf token is invalid
    if not token:
        return False
    # Otherwise a token was found that matches

    # Determine when the csrf token expires
    tokenexpires = datetime.fromisoformat(token["created"]) + timedelta(minutes=2) 

    # If it's past it's expiration date, delete form database and return False
    if datetime.utcnow() >= tokenexpires:
        db.execute('DELETE FROM csrf WHERE token = ?', (csrf,))
        db.commit()
        print("CSRF token expired, deleted token")
        return False
    
    return True

@bp.route('/spotify/authorize/<kind>', methods=['POST', 'GET'])
def userAuth(kind):

    # Make sure it's a valid kind and set necessary authorization scope
    if kind == "playlist":
        scope = "playlist-read-private"
    else:
        # Only handling playlists right now
        return redirect( url_for('stats.search', kind='artist', results=''))

    if request.method == "GET":
        return render_template("auth/user.html", kind=kind, csrf=issueCsrf())
        

    # Make sure request has a valid csrf token
    csrf = request.form['csrf']
    if not isValid(csrf):
        print("CSRF not valid, redirecting to index")
        return redirect( url_for('stats.search', kind='artist', results=''))

    # Determine redirect uri
    redirecturi = f'{getHostname()}{url_for("auth.receiveAuth", kind=kind)}'

    # Get spotify api client id from environment variable
    client_id = os.environ['CLIENTID']

    # Always ask for authentication
    show_dialog = 'true'

    params = {
        'client_id': client_id,
        'scope': scope,
        'redirect_uri': redirecturi,
        'response_type': 'code',
        'state': csrf,
        'show_dialog': show_dialog,
    }
    url = "https://accounts.spotify.com/authorize"
    
    # See if there's any errors by sending the request once first
    response = requests.get(url, params=params)

    if response.status_code >= 300:
        current_app.logger.warning(f"Spotify user auth redirect error, status code: {response.status_code}")
        current_app.logger.warning(response.json()['error'])
        return redirect(url_for('stats.index'))
    
    # If no errors, redirect to that same url
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




# @bp.before_app_request
# def load_logged_in_user():
#     user_id = session.get('user_id')

#     if user_id is None:
#         g.user = None
#     else:
#         g.user = get_db().execute(
#             'SELECT * FROM user WHERE id = ?', (user_id,)
#         ).fetchone()

# @bp.route('/register', methods=('GET', 'POST'))
# def register():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         db = get_db()
#         error = None

#         if not username:
#             error = 'Username is required.'
#         elif not password:
#             error = 'Password is required.'

#         if error is None:
#             try:
#                 db.execute(
#                     "INSERT INTO user (username, password) VALUES (?, ?)",
#                     (username, generate_password_hash(password)),
#                 )
#                 db.commit()
#             except db.IntegrityError:
#                 error = f"User {username} is already registered."
#             else:
#                 return redirect(url_for("auth.login"))

#         flash(error)

#     return render_template('auth/register.html')

# @bp.route('/login', methods=('GET', 'POST'))
# def login():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         db = get_db()
#         error = None
#         user = db.execute(
#             'SELECT * FROM user WHERE username = ?', (username,)
#         ).fetchone()

#         if user is None:
#             error = 'Incorrect username.'
#         elif not check_password_hash(user['password'], password):
#             error = 'Incorrect password.'

#         if error is None:
#             session.clear()
#             session['user_id'] = user['id']
#             return redirect(url_for('index'))

#         flash(error)

#     return render_template('auth/login.html')

# @bp.route('/logout')
# def logout():
#     session.clear()
#     return redirect(url_for('index'))

# def login_required(view):
#     @functools.wraps(view)
#     def wrapped_view(**kwargs):
#         if g.user is None:
#             return redirect(url_for('auth.login'))

#         return view(**kwargs)

#     return wrapped_view