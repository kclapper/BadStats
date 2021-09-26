import functools, os
from datetime import datetime, timedelta

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from badstats.db import get_db
from spotify import Spotify

bp = Blueprint('auth', __name__, url_prefix='/auth')


def isValid(csrf):
    # Return True if csrf is valid
    # Return False if not
    
    # Return false if no csrf given
    if not csrf:
        return False

    # Check if a matching csrf token is in the database
    db = get_db()
    token = db.execute(
        'SELECT * FROM csrf WHERE token = ?', csrf
    ).fetchone()

    # If no token was found then the csrf token is invalid
    if not token:
        return False
    # Otherwise a token was found that matches

    # Determine when the csrf token expires
    tokenexpires = datetime.fromisoformat(token["created"]) + timedelta(minutes=2) 

    # If it's past it's expiration date, delete form database and return False
    if datetime.utcnow() >= tokenexpires:
        db.execute('DELETE FROM csrf WHERE token = ?', csrf)
        db.commit()
        return False
    
    return True

@bp.route('/spotify/:kind/authorize', methods=('POST'))
def userAuthorize(kind):
    # Make sure request has a valid csrf token
    csrf = request.form['csrf']
    if not isValid(csrf):
        redirect( url_for('stats.search', kind='artist', results=''))

    # Set necessary authorization scope
    scope = request.form['scope']

    # Determine redirect uri
    if not os.environ['HOSTNAME']:
        host = "localhost"
    else:
        host = os.environ['HOSTNAME']
    redirecturi = f'{host}{url_for("stats.user", kind=kind)}'

    # Get spotify api client id from environment variable
    clientid = os.environ['CLIENTID']

    # Redirect to spotify authorization
    

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