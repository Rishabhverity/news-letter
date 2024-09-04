from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, ForeignKey
from dotenv import load_dotenv
import os
from datetime import datetime
from sqlalchemy import  Table, Column, String, Integer,Float,Boolean ,MetaData, DateTime, ForeignKey, text
from sqlalchemy.dialects.mysql import VARCHAR
import uuid
from sqlalchemy import text
from sqlalchemy.sql import func
from flask_swagger_ui import get_swaggerui_blueprint


load_dotenv()

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

engine = create_engine(os.getenv('DATABASE_URI'))


metadata = MetaData()
# Models

# Models

class Subscription(db.Model):
    uuid = db.Column(db.String(36), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    unsubscribe = db.Column(db.DateTime, nullable=True)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)  # Soft delete flag

    # Relationship to logs
    logs = db.relationship('Log', backref='subscription', lazy=True)


class Log(db.Model):
    uuid = db.Column(db.String(36), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # "subscribe" or "unsubscribe"
    datetime = db.Column(db.DateTime, default=datetime.now)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)  # Soft delete flag

    # Foreign key to Subscription
    subscription_id = db.Column(db.String(36), db.ForeignKey('subscription.uuid'), nullable=False)

# Create all tables
with app.app_context():
    db.create_all()



subscription = Table('subscription', metadata,
    Column('uuid', VARCHAR(36), primary_key=True),
    Column('name', String(100), nullable=False),
    Column('email', String(100), nullable=False, unique=True),
    Column('unsubscribe', DateTime, nullable=True),
    Column('is_deleted', Boolean, nullable=False, default=False)  # Default value set to False
)

# Log table with soft delete column
log = Table('log', metadata,
    Column('uuid', VARCHAR(36), primary_key=True),
    Column('name', String(100), nullable=False),
    Column('email', String(100), nullable=False),
    Column('action', String(100), nullable=False),
    Column('datetime', DateTime, nullable=False, default=func.now()),
    Column('subscription_id', VARCHAR(36), ForeignKey('subscription.uuid'), nullable=True),
    Column('is_deleted', Boolean, nullable=False, default=False)  # Default value set to False
)

# Create all tables
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

    new_subscription_uuid = str(uuid.uuid4())
    new_log_uuid = str(uuid.uuid4())

    try:
        with engine.begin() as connection:
            # Check if the subscription already exists
            check_subscription_query = text("SELECT uuid FROM subscription WHERE email = :email AND is_deleted = False")
            result = connection.execute(check_subscription_query, {"email": email}).fetchone()

            if result:
                subscription_uuid = result[0]
                # Update existing subscription
                update_subscription_query = text("""
                    UPDATE subscription 
                    SET unsubscribe = NULL 
                    WHERE email = :email
                """)
                connection.execute(update_subscription_query, {"email": email})
            else:
                # Insert a new subscription record
                insert_subscription_sql = text("""
                    INSERT INTO subscription (uuid, name, email, unsubscribe, is_deleted)
                    VALUES (:uuid, :name, :email, NULL, False)
                """)
                connection.execute(insert_subscription_sql, {
                    'uuid': new_subscription_uuid,
                    'name': name,
                    'email': email
                })
                subscription_uuid = new_subscription_uuid

            # Log the subscription action
            insert_log_sql = text("""
                INSERT INTO log (uuid, name, email, action, datetime, subscription_id, is_deleted)
                VALUES (:uuid, :name, :email, 'subscribe', :datetime, :subscription_id, False)
            """)
            connection.execute(insert_log_sql, {
                'uuid': new_log_uuid,
                'name': name,
                'email': email,
                'datetime': datetime.now(),
                'subscription_id': subscription_uuid
            })

            # Return success message within the try block
            return jsonify({'message': 'Subscribed successfully!', 'subscription_id': subscription_uuid}), 200

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({'error': str(e)}), 400



@app.route('/subscriptions', methods=['GET'])
def get_subscriptions():
    subscription_uuid = request.args.get('uuid')

    try:
        with engine.connect() as connection:
            if subscription_uuid:
                # Query to fetch a single subscription by UUID
                fetch_subscription_sql = text("""
                    SELECT uuid, name, email, unsubscribe 
                    FROM subscription
                    WHERE uuid = :uuid AND is_deleted = False
                """)
                result = connection.execute(fetch_subscription_sql, {'uuid': subscription_uuid}).fetchone()

                if result:
                    subscription = {
                        'uuid': result[0],
                        'name': result[1],
                        'email': result[2],
                        'unsubscribe': result[3].isoformat() if result[3] else None
                    }
                    return jsonify({'data': subscription}), 200
                else:
                    return jsonify({'message': 'Subscription not found!'}), 404
            else:
                # Query to fetch all subscription records
                fetch_subscriptions_sql = text("""
                    SELECT uuid, name, email, unsubscribe 
                    FROM subscription
                    WHERE is_deleted = False
                """)
                result = connection.execute(fetch_subscriptions_sql)
                subscriptions = [
                    {
                        'uuid': row[0],
                        'name': row[1],
                        'email': row[2],
                        'unsubscribe': row[3].isoformat() if row[3] else None
                    }
                    for row in result
                ]

                return jsonify({'data': subscriptions}), 200
    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/subscription/<subscription_uuid>', methods=['PUT'])
def update_subscription(subscription_uuid):
    data = request.get_json()
    new_name = data.get('name')
    new_email = data.get('email')
    unsubscribe_date = datetime.now()  # Set unsubscribe date to the current datetime

    try:
        with engine.begin() as connection:
            # Check if the subscription exists
            check_subscription_query = text("""
                SELECT uuid, name, email, unsubscribe 
                FROM subscription 
                WHERE uuid = :uuid AND is_deleted = False
            """)
            result = connection.execute(check_subscription_query, {"uuid": subscription_uuid}).fetchone()

            if result:
                # Retrieve existing values
                current_name = result[1]
                current_email = result[2]

                # Update the subscription with the new details
                update_subscription_query = text("""
                    UPDATE subscription
                    SET name = :name, email = :email, unsubscribe = :unsubscribe
                    WHERE uuid = :uuid
                """)
                connection.execute(update_subscription_query, {
                    'uuid': subscription_uuid,
                    'name': new_name if new_name is not None else current_name,
                    'email': new_email if new_email is not None else current_email,
                    'unsubscribe': unsubscribe_date  # Always update unsubscribe date
                })

                # Insert a new log entry for unsubscribe action
                new_log_uuid = str(uuid.uuid4())  # This now correctly refers to the uuid module
                insert_log_sql = text("""
                    INSERT INTO log (uuid, name, email, action, datetime, subscription_id, is_deleted)
                    VALUES (:uuid, :name, :email, 'unsubscribe', :datetime, :subscription_id, False)
                """)
                connection.execute(insert_log_sql, {
                    'uuid': new_log_uuid,
                    'name': new_name if new_name is not None else current_name,
                    'email': new_email if new_email is not None else current_email,
                    'datetime': unsubscribe_date,
                    'subscription_id': subscription_uuid
                })

                return jsonify({"message": "Subscription unsubscribed and log updated successfully!"}), 200
            else:
                return jsonify({"message": "Subscription not found!"}), 404

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({'error': str(e)}), 500




@app.route('/subscription/<uuid>', methods=['DELETE'])
def delete_subscription(uuid):
    try:
        with engine.begin() as connection:
            # Check if the subscription exists and is not already deleted
            check_subscription_query = text("SELECT uuid FROM subscription WHERE uuid = :uuid AND is_deleted = False")
            result = connection.execute(check_subscription_query, {"uuid": uuid}).fetchone()

            if result:
                # Soft delete the subscription
                soft_delete_subscription_query = text("""
                    UPDATE subscription
                    SET is_deleted = True
                    WHERE uuid = :uuid
                """)
                connection.execute(soft_delete_subscription_query, {"uuid": uuid})

                # Soft delete associated logs
                soft_delete_logs_query = text("""
                    UPDATE log
                    SET is_deleted = True
                    WHERE subscription_id = :subscription_id
                """)
                connection.execute(soft_delete_logs_query, {"subscription_id": uuid})

                return jsonify({"message": "Subscription and associated logs soft-deleted successfully!"}), 200
            else:
                return jsonify({"message": "Subscription not found or already deleted!"}), 404

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/log', methods=['POST'])
def add_log():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    action = data.get('action')  # e.g., "subscribe" or "unsubscribe"

    new_log_uuid = str(uuid.uuid4())

    try:
        with engine.begin() as connection:
            # Get the subscription ID based on the email
            subscription_query = text("SELECT uuid FROM subscription WHERE email = :email AND is_deleted = False")
            subscription_result = connection.execute(subscription_query, {"email": email}).fetchone()

            if not subscription_result:
                return jsonify({'error': 'Subscription not found or already deleted!'}), 404

            subscription_id = subscription_result[0]

            # Insert a new log entry
            insert_log_sql = text("""
                INSERT INTO log (uuid, name, email, action, datetime, subscription_id, is_deleted)
                VALUES (:uuid, :name, :email, :action, :datetime, :subscription_id, False)
            """)
            connection.execute(insert_log_sql, {
                'uuid': new_log_uuid,
                'name': name,
                'email': email,
                'action': action,
                'datetime': datetime.now(),
                'subscription_id': subscription_id
            })

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({'error': str(e)}), 400

    return jsonify({'message': 'Log added successfully!', 'log_id': new_log_uuid}), 200



# @app.route('/logs', methods=['GET'])
# def get_logs():
#     try:
#         with engine.connect() as connection:
#             # Fetch all log records, including subscribe and unsubscribe actions
#             fetch_logs_sql = text("""
#                 SELECT uuid, name, email, action, datetime 
#                 FROM log
#                 WHERE is_deleted = False
#                 ORDER BY datetime DESC
#             """)
#             result = connection.execute(fetch_logs_sql)
#             logs = [
#                 {
#                     'uuid': row[0],
#                     'name': row[1],
#                     'email': row[2],
#                     'action': row[3],
#                     'datetime': row[4].isoformat() if row[4] else None
#                 }
#                 for row in result
#             ]

#             return jsonify({'data': logs}), 200
#     except Exception as e:
#         print(f"Error occurred: {e}")
#         return jsonify({'error': str(e)}), 500


@app.route('/logs', methods=['GET'])
def get_logs():
    try:
        with engine.connect() as connection:
            # Fetch all log records, including subscribe and unsubscribe actions
            fetch_logs_sql = text("""
                SELECT uuid, name, email, action, datetime 
                FROM log
                WHERE is_deleted = False
                ORDER BY datetime DESC
            """)
            result = connection.execute(fetch_logs_sql)
            logs = [
                {
                    'uuid': row[0],
                    'name': row[1],
                    'email': row[2],
                    'action': row[3],
                    'datetime': row[4].isoformat() if row[4] else None
                }
                for row in result
            ]

            return jsonify({'data': logs}), 200
    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({'error': str(e)}), 500


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
    app.run(host='0.0.0.0', port=5000, debug=True)

