import pytest
from badstats.db import get_db
from flask import url_for

@pytest.mark.parametrize('path', (
    '/',
    '/termsofservice',
    '/privacypolicy',
))
def test_get_basic_pages(client, path):
    response = client.get(path)
    assert response.status_code == 200 or 302

@pytest.mark.parametrize('path, search', (
    ("/search/artist", "paramore"),
    ("/search/album", "paramore"),
    ("/search/song", "aint it fun"),
))
def test_search(client, path, search):
    
    response = client.get(path)
    assert response.status_code == 200

    response = client.post(path, data={
        "search": search,
    }, follow_redirects=True)
    assert response.status_code == 200 

@pytest.mark.parametrize('path', (
    "/item/artist/74XFHRwlV6OrjEM0A2NCMF",
    "/item/album/4sgYpkIASM1jVlNC8Wp9oF",
    "/item/song/1j8z4TTjJ1YOdoFEDwJTQa",
))
def test_item(client, path):
    response = client.get(path)
    assert response.status_code == 200

@pytest.mark.parametrize('path', (
    "/plot/album/popularity/4sgYpkIASM1jVlNC8Wp9oF",
    "/plot/album/danceability/4sgYpkIASM1jVlNC8Wp9oF",
    "/plot/album/duration_ms/4sgYpkIASM1jVlNC8Wp9oF",
    "/plot/album/energy/4sgYpkIASM1jVlNC8Wp9oF",
    "/plot/album/loudness/4sgYpkIASM1jVlNC8Wp9oF",
    "/plot/album/speechiness/4sgYpkIASM1jVlNC8Wp9oF",
    "/plot/album/acousticness/4sgYpkIASM1jVlNC8Wp9oF",
    "/plot/album/instrumentalness/4sgYpkIASM1jVlNC8Wp9oF",
    "/plot/album/liveness/4sgYpkIASM1jVlNC8Wp9oF",
    "/plot/album/valence/4sgYpkIASM1jVlNC8Wp9oF",
    "/plot/album/tempo/4sgYpkIASM1jVlNC8Wp9oF",
))
def test_plot(client, path):
    response = client.get(path)
    assert response.status_code == 200

# @pytest.mark.parametrize('path', (
#     '/create',
#     '/1/update',
#     '/1/delete',
# ))
# def test_login_required(client, path):
#     response = client.post(path)
#     assert response.headers['Location'] == 'http://localhost/auth/login'


# def test_author_required(app, client, auth):
#     # change the post author to another user
#     with app.app_context():
#         db = get_db()
#         db.execute('UPDATE post SET author_id = 2 WHERE id = 1')
#         db.commit()

#     auth.login()
#     # current user can't modify other user's post
#     assert client.post('/1/update').status_code == 403
#     assert client.post('/1/delete').status_code == 403
#     # current user doesn't see edit link
#     assert b'href="/1/update"' not in client.get('/').data


# @pytest.mark.parametrize('path', (
#     '/2/update',
#     '/2/delete',
# ))
# def test_exists_required(client, auth, path):
#     auth.login()
#     assert client.post(path).status_code == 404

# def test_create(client, auth, app):
#     auth.login()
#     assert client.get('/create').status_code == 200
#     client.post('/create', data={'title': 'created', 'body': ''})

#     with app.app_context():
#         db = get_db()
#         count = db.execute('SELECT COUNT(id) FROM post').fetchone()[0]
#         assert count == 2


# def test_update(client, auth, app):
#     auth.login()
#     assert client.get('/1/update').status_code == 200
#     client.post('/1/update', data={'title': 'updated', 'body': ''})

#     with app.app_context():
#         db = get_db()
#         post = db.execute('SELECT * FROM post WHERE id = 1').fetchone()
#         assert post['title'] == 'updated'


# @pytest.mark.parametrize('path', (
#     '/create',
#     '/1/update',
# ))
# def test_create_update_validate(client, auth, path):
#     auth.login()
#     response = client.post(path, data={'title': '', 'body': ''})
#     assert b'Title is required.' in response.data

# def test_delete(client, auth, app):
#     auth.login()
#     response = client.post('/1/delete')
#     assert response.headers['Location'] == 'http://localhost/'

#     with app.app_context():
#         db = get_db()
#         post = db.execute('SELECT * FROM post WHERE id = 1').fetchone()
#         assert post is None