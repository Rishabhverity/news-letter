import pytest
import os
from flask import Flask
from sqlalchemy import text
from news_letter import app, db, engine

# Sample data for testing
sample_subscription = {
    "name": "Test User",
    "email": "testuser@example.com"
}

sample_log = {
    "name": "Test User",
    "email": "testuser@example.com",
    "action": "subscribe"
}

@pytest.fixture(scope='module')
def test_client():
    # Configure the Flask test client
    app.config['TESTING'] = True

    # Set up the SQLAlchemy database URI from environment variables
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'mysql+pymysql://test_user:test_password@localhost/test_db')

    # Create a test client
    with app.test_client() as testing_client:
        with app.app_context():
            # Create the database tables for testing
            db.create_all()

            yield testing_client  # Test runs here

            # Clean up / reset the database after tests
            db.drop_all()

@pytest.fixture(scope='module')
def init_database():
    # Initialize the database with sample data
    with engine.connect() as connection:
        # Insert sample subscription data
        connection.execute(text("""
            INSERT INTO subscription (uuid, name, email, unsubscribe)
            VALUES (:uuid, :name, :email, NULL)
        """), {'uuid': '123e4567-e89b-12d3-a456-426614174000', **sample_subscription})
        
        # Insert sample log data
        connection.execute(text("""
            INSERT INTO log (uuid, name, email, action, datetime, subscription_id)
            VALUES (:uuid, :name, :email, :action, NOW(), :subscription_id)
        """), {
            'uuid': '223e4567-e89b-12d3-a456-426614174000',
            **sample_log,
            'subscription_id': '123e4567-e89b-12d3-a456-426614174000'
        })

@pytest.mark.usefixtures("init_database")
def test_home_route(test_client):
    response = test_client.get('/')
    assert response.status_code == 200
    assert response.json == {"message": "Welcome to the Newsletter Subscription API!"}

def test_subscribe_route(test_client):
    response = test_client.post('/subscription', json=sample_subscription)
    assert response.status_code == 200
    assert 'Subscribed successfully!' in response.json['message']

def test_get_all_subscriptions_route(test_client):
    response = test_client.get('/subscriptions')
    assert response.status_code == 200
    assert len(response.json['subscriptions']) > 0

def test_update_subscription_route(test_client):
    update_data = {
        "name": "Updated User",
        "email": "updateduser@example.com"
    }
    response = test_client.put('/subscription/123e4567-e89b-12d3-a456-426614174000', json=update_data)
    assert response.status_code == 200
    assert 'Subscription updated successfully' in response.json['message']

def test_delete_subscription_route(test_client):
    response = test_client.delete('/subscription/testuser@example.com')
    assert response.status_code == 200
    assert 'Subscription and related logs deleted successfully!' in response.json['message']

def test_get_logs_route(test_client):
    response = test_client.get('/logs')
    assert response.status_code == 200
    assert len(response.json) > 0

def test_create_log_route(test_client):
    response = test_client.post('/log', json=sample_log)
    assert response.status_code == 201
    assert 'Log created successfully!' in response.json['message']
