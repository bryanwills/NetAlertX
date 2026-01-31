# test/api_endpoints/test_docs.py - Tests for root redirect and API docs endpoints


from api_server import api_server_start


def test_index_redirect_logic():
    """Test the redirect function logic directly."""
    with api_server_start.app.test_request_context():
        response = api_server_start.index_redirect()
        # In Flask, a redirect return object is a Response
        assert response.status_code == 302
        assert response.headers['Location'] == '/docs'


def test_api_docs_logic():
    """Test that api_docs attempts to serve the correct file."""
    with api_server_start.app.test_request_context():
        response = api_server_start.api_docs()
        assert response.status_code == 200
        assert response.mimetype == 'text/html'
        # Manually join the chunks from the generator
        data = b"".join(response.response)
        assert b'<!DOCTYPE html>' in data or b'<html>' in data
