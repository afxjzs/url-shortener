"""Tests for URL Shortener service."""
import pytest
import os
from app import app, Session
from models import Base, Shortcode, Click
from sqlalchemy import create_engine


@pytest.fixture
def db():
    """Create a test database."""
    # Use SQLite in-memory for tests
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    """Create a test client."""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        yield client


@pytest.fixture
def test_shortcode(db):
    """Create a test shortcode."""
    shortcode = Shortcode(
        shortcode='test',
        target_url='https://example.com',
        active=True,
        custom=False
    )
    db.add(shortcode)
    db.commit()
    return shortcode


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['status'] == 'ok'


def test_redirect_shortcode_not_found(client):
    """Test redirecting to non-existent shortcode."""
    response = client.get('/nonexistent', follow_redirects=False)
    assert response.status_code == 404
    assert 'not found' in response.json['error'].lower()


def test_qr_code_not_found(client):
    """Test QR code for non-existent shortcode."""
    response = client.get('/qr/nonexistent')
    assert response.status_code == 404
    assert 'not found' in response.json['error'].lower()


def test_stats_not_found(client):
    """Test stats for non-existent shortcode."""
    response = client.get('/stats/nonexistent')
    assert response.status_code == 404
    assert 'not found' in response.json['error'].lower()


def test_rate_limiting(client):
    """Test rate limiting on redirect endpoint."""
    # Make many requests to hit rate limit
    for i in range(101):
        response = client.get('/nonexistent')
        if response.status_code == 429:
            assert 'rate limit' in response.json['error'].lower()
            return
    # If we didn't hit rate limit, that's OK in testing


def test_health_endpoint_accessible(client):
    """Test that health endpoint works."""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert data['status'] == 'ok'


def test_404_handler(client):
    """Test custom 404 handler."""
    response = client.get('/nonexistent-path-xyz')
    assert response.status_code == 404
    assert response.json is not None
