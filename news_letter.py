from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, ForeignKey
from dotenv import load_dotenv
import os
from datetime import datetime
from sqlalchemy import Table, Column, String, Integer, Float, Boolean, MetaData, DateTime, ForeignKey, text
from sqlalchemy.dialects.mysql import VARCHAR
import uuid
from sqlalchemy.sql import func
from flask_swagger_ui import get_swaggerui_blueprint
from flask_migrate import Migrate
import re 
load_dotenv()

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

engine = create_engine(os.getenv('DATABASE_URI'))
migrate = Migrate(app, db)

metadata = MetaData()

# Models
class Subscription(db.Model):
    id = db.Column(db.String(36), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    unsubscribe = db.Column(db.DateTime, nullable=True)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)  # Soft delete flag

    logs = db.relationship('Log', backref='subscription', lazy=True)


class Log(db.Model):
    id = db.Column(db.String(36), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # "subscribe" or "unsubscribe"
    datetime = db.Column(db.DateTime, default=datetime.now)
    
    subscription_id = db.Column(db.String(36), db.ForeignKey('subscription.id'), nullable=False)

# Create all tables
with app.app_context():
    db.create_all()

# Define tables explicitly with new 'id' naming convention
subscription = Table('subscription', metadata,
    Column('id', VARCHAR(36), primary_key=True),
    Column('name', String(100), nullable=False),
    Column('email', String(120), nullable=False, unique=True),
    Column('unsubscribe', DateTime, nullable=True),
    Column('is_deleted', Boolean, nullable=False, default=False)
)

log = Table('log', metadata,
    Column('id', VARCHAR(36), primary_key=True),
    Column('name', String(100), nullable=False),
    Column('email', String(120), nullable=False),
    Column('action', String(50), nullable=False),
    Column('datetime', DateTime, nullable=False, default=func.now()),
    Column('subscription_id', VARCHAR(36), ForeignKey('subscription.id'), nullable=True)
)

metadata.create_all(engine)

def generate_uuid():
    return str(uuid.uuid4())


@app.route('/')
def home():
    return jsonify({"message": "Welcome to the Newsletter Subscription API!"})




@app.route('/subscription', methods=['POST'])
def subscribe():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')

    if not name or not email:
        return jsonify({'error': 'Name and email are required!'}), 400

    # Basic email validation using regex
    email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(email_pattern, email):
        return jsonify({'error': 'Invalid email format! Email must contain @ and a valid domain like .com'}), 400

    new_subscription_id = str(uuid.uuid4())
    new_log_id = str(uuid.uuid4())

    try:
        with engine.begin() as connection:
            # Check if the subscription already exists
            check_subscription_query = text("""
                SELECT id, unsubscribe 
                FROM subscription 
                WHERE email = :email AND is_deleted = False
            """)
            result = connection.execute(check_subscription_query, {"email": email}).fetchone()

            if result:
                subscription_id = result[0]
                unsubscribe = result[1]
                
                if unsubscribe is None:
                    return jsonify({'error': 'Email is already subscribed!'}), 409
                
                # Reset unsubscribe if resubscribing
                update_subscription_query = text("""
                    UPDATE subscription 
                    SET unsubscribe = NULL 
                    WHERE email = :email
                """)
                connection.execute(update_subscription_query, {"email": email})
            else:
                # Insert a new subscription
                insert_subscription_sql = text("""
                    INSERT INTO subscription (id, name, email, unsubscribe, is_deleted)
                    VALUES (:id, :name, :email, NULL, False)
                """)
                connection.execute(insert_subscription_sql, {
                    'id': new_subscription_id,
                    'name': name,
                    'email': email
                })
                subscription_id = new_subscription_id

            # Insert a log entry for the subscription
            insert_log_sql = text("""
                INSERT INTO log (id, name, email, action, datetime, subscription_id)
                VALUES (:id, :name, :email, 'subscribe', :datetime, :subscription_id)
            """)
            connection.execute(insert_log_sql, {
                'id': new_log_id,
                'name': name,
                'email': email,
                'datetime': datetime.now(),
                'subscription_id': subscription_id
            })

            return jsonify({'message': 'Subscribed successfully!', 'subscription_id': subscription_id}), 200

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({'error': 'An error occurred while subscribing. Please try again later.'}), 500



@app.route('/subscriptions', methods=['GET'])
def get_subscriptions():
    subscription_id = request.args.get('id')

    try:
        with engine.connect() as connection:
            if subscription_id:
                fetch_subscription_sql = text("""
                    SELECT id, name, email, unsubscribe 
                    FROM subscription
                    WHERE id = :id AND is_deleted = False
                """)
                result = connection.execute(fetch_subscription_sql, {'id': subscription_id}).fetchone()

                if result:
                    subscription = {
                        'id': result[0],
                        'name': result[1],
                        'email': result[2],
                        'unsubscribe': result[3].isoformat() if result[3] else None
                    }
                    return jsonify({'data': subscription}), 200
                else:
                    return jsonify({'message': 'Subscription not found!'}), 404
            else:
                
                fetch_subscriptions_sql = text("""
                    SELECT id, name, email, unsubscribe 
                    FROM subscription
                    WHERE is_deleted = False
                    ORDER BY unsubscribe DESC  -- Order by the latest unsubscribe time only
                """)
                result = connection.execute(fetch_subscriptions_sql)
                subscriptions = [
                    {
                        'id': row[0],
                        'name': row[1],
                        'email': row[2],
                        'unsubscribe': row[3].isoformat() if row[3] else None
                    }
                    for row in result
                ]

                return jsonify({'data': subscriptions}), 200
    except Exception as e:
        print(f"Error occurred: {e}")  # Print the actual error for debugging
        return jsonify({'error': f"An error occurred while fetching subscriptions. Please try again later. Error: {str(e)}"}), 500

@app.route('/subscription/<id>', methods=['PUT'])
def update_subscription(id):
    data = request.get_json()
    new_name = data.get('name')
    new_email = data.get('email')
    action = data.get('action')  

   
    if not new_name and not new_email and not action:
        return jsonify({'error': 'At least one of name, email, or action must be provided!'}), 400

    try:
        with engine.begin() as connection:
            check_subscription_query = text("""
                SELECT id, name, email, unsubscribe 
                FROM subscription 
                WHERE id = :id AND is_deleted = False
            """)
            result = connection.execute(check_subscription_query, {"id": id}).fetchone()

            if result:
                current_name = result[1]
                current_email = result[2]
                unsubscribe_date = result[3]  # Current value of unsubscribe field

                # Determine action based updates
                if action == 'unsubscribe':
                    unsubscribe_date = datetime.now()
                elif action == 'subscribe':
                    unsubscribe_date = None  # Reset unsubscribe if re-subscribing

                # Update subscription details
                update_subscription_query = text("""
                    UPDATE subscription
                    SET name = :name, email = :email, unsubscribe = :unsubscribe
                    WHERE id = :id
                """)
                connection.execute(update_subscription_query, {
                    'id': id,
                    'name': new_name if new_name is not None else current_name,
                    'email': new_email if new_email is not None else current_email,
                    'unsubscribe': unsubscribe_date
                })

                # Insert a log entry for the action
                new_log_id = str(uuid.uuid4())
                insert_log_sql = text("""
                    INSERT INTO log (id, name, email, action, datetime, subscription_id)
                    VALUES (:id, :name, :email, :action, :datetime, :subscription_id)
                """)
                connection.execute(insert_log_sql, {
                    'id': new_log_id,
                    'name': new_name if new_name is not None else current_name,
                    'email': new_email if new_email is not None else current_email,
                    'action': action if action is not None else 'update',
                    'datetime': datetime.now(),
                    'subscription_id': id
                })

                return jsonify({"message": f"Subscription {action if action else 'updated'} successfully!"}), 200
            else:
                return jsonify({"message": "Subscription not found!"}), 404

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({'error': 'An error occurred while updating the subscription. Please try again later.'}), 500



@app.route('/subscription/<id>', methods=['DELETE'])
def delete_subscription(id):
    try:
        with engine.begin() as connection:
            # Check if the subscription exists and is not already deleted
            check_subscription_query = text("""
                SELECT id, name, email FROM subscription WHERE id = :id AND is_deleted = False
            """)
            result = connection.execute(check_subscription_query, {"id": id}).fetchone()

            if result:
                subscription_id = result[0]
                subscription_name = result[1]
                subscription_email = result[2]

                # Soft delete the subscription (only update the is_deleted flag)
                soft_delete_subscription_query = text("""
                    UPDATE subscription
                    SET is_deleted = True
                    WHERE id = :id
                """)
                connection.execute(soft_delete_subscription_query, {"id": subscription_id})

                # Insert a log entry for the deletion action
                new_log_id = str(uuid.uuid4())
                insert_log_sql = text("""
                    INSERT INTO log (id, name, email, action, datetime, subscription_id)
                    VALUES (:id, :name, :email, 'delete', :datetime, :subscription_id)
                """)
                connection.execute(insert_log_sql, {
                    'id': new_log_id,
                    'name': subscription_name,
                    'email': subscription_email,
                    'datetime': datetime.now(),
                    'subscription_id': subscription_id
                })

                return jsonify({'message': 'Subscription soft-deleted and log created successfully!'}), 200
            else:
                return jsonify({'message': 'Subscription not found!'}), 404

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/logs', methods=['GET'])
def get_logs():
    subscription_id = request.args.get('subscription_id')  # Optional filter by subscription ID

    try:
        with engine.connect() as connection:
            if subscription_id:
                # Validate the subscription_id format
                if not subscription_id.isalnum() or len(subscription_id) != 36:
                    return jsonify({'error': 'Invalid subscription ID format!'}), 400

                # Fetch logs even if the subscription is soft-deleted
                fetch_logs_query = text("""
                    SELECT log.id, log.name, log.email, log.action, log.datetime, log.subscription_id
                    FROM log
                    JOIN subscription ON log.subscription_id = subscription.id
                    WHERE log.subscription_id = :subscription_id
                    ORDER BY log.datetime DESC
                """)
                result = connection.execute(fetch_logs_query, {'subscription_id': subscription_id})
            else:
                # Fetch all logs, ignoring subscription's is_deleted status
                fetch_logs_query = text("""
                    SELECT log.id, log.name, log.email, log.action, log.datetime, log.subscription_id
                    FROM log
                    ORDER BY log.datetime DESC
                """)
                result = connection.execute(fetch_logs_query)

            logs = [
                {
                    'id': row[0],
                    'name': row[1],
                    'email': row[2],
                    'action': row[3],
                    'datetime': row[4].isoformat(),
                    'subscription_id': row[5]
                }
                for row in result
            ]

            if not logs:
                # Return `{"data": []}` when no logs are found
                return jsonify({'data': []}), 200

            return jsonify({'data': logs}), 200

    except Exception as e:
        print(f"Error occurred while fetching logs: {e}")
        return jsonify({'error': 'An error occurred while fetching logs. Please try again later.'}), 500




# POST Logs API
@app.route('/log', methods=['POST'])
def add_log():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    action = data.get('action')  # e.g., "subscribe" or "unsubscribe"

    new_log_id = str(uuid.uuid4())  # Renaming uuid to id

    try:
        with engine.begin() as connection:
            # Get the subscription ID based on the email
            subscription_query = text("SELECT id FROM subscription WHERE email = :email AND is_deleted = False")
            subscription_result = connection.execute(subscription_query, {"email": email}).fetchone()

            if not subscription_result:
                return jsonify({'error': 'Subscription not found or already deleted!'}), 404

            subscription_id = subscription_result[0]

            # Insert a new log entry
            insert_log_sql = text("""
                INSERT INTO log (id, name, email, action, datetime, subscription_id)
                VALUES (:id, :name, :email, :action, :datetime, :subscription_id)
            """)
            connection.execute(insert_log_sql, {
                'id': new_log_id,
                'name': name,
                'email': email,
                'action': action,
                'datetime': datetime.now(),
                'subscription_id': subscription_id
            })

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({'error': str(e)}), 400

    return jsonify({'message': 'Log added successfully!', 'log_id': new_log_id}), 200



# Swagger specific configurations
SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.json'  # Correct API URL

# Serve the Swagger JSON file
@app.route(API_URL)
def serve_swagger_json():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'swagger.json')

# Create Swagger blueprint
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "Newsletter Subscription API"
    }
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)