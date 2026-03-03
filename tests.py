"""Tests for URL Shortener service."""
import pytest
import os
from app import app


@pytest.fixture
def client():
    """Create a test client."""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        yield client


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert data['status'] == 'ok'


def test_health_endpoint_accessible(client):
    """Test that health endpoint works."""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert data['status'] == 'ok'


def test_app_config(client):
    """Test that app config is set correctly."""
    assert app.config['TESTING'] == True
    assert app.config['WTF_CSRF_ENABLED'] == False


def test_health_check_json_format(client):
    """Test health check returns proper JSON."""
    response = client.get('/health')
    assert response.content_type.startswith('application/json')
    data = response.get_json()
    assert isinstance(data, dict)
    assert 'status' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
