from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, ForeignKey
from dotenv import load_dotenv
import os
from datetime import datetime
from sqlalchemy import  Table, Column, String, Integer, Float, MetaData, DateTime, ForeignKey, text
from sqlalchemy.dialects.mysql import VARCHAR
import uuid
from sqlalchemy import text

load_dotenv()

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

engine = create_engine(os.getenv('DATABASE_URI'))


metadata = MetaData()
# Models

class Subscription(db.Model):
    uuid = db.Column(db.String(36), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    unsubscribe = db.Column(db.DateTime, nullable=True)

    # Relationship to logs
    logs = db.relationship('Log', backref='subscription', lazy=True)


class Log(db.Model):
    uuid = db.Column(db.String(36), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # "subscribe" or "unsubscribe"
    datetime = db.Column(db.DateTime, default=datetime.now)

    # Foreign key to Subscription
    subscription_id = db.Column(db.String(36), db.ForeignKey('subscription.uuid'), nullable=False)

# Create all tables
with app.app_context():
    db.create_all()



subscription = Table('subscription', metadata,
    Column('uuid', VARCHAR(36), primary_key=True),
    Column('name', String(100), nullable=False),
    Column('email', String(100), nullable=False, unique=True),
    Column('unsubscribe', DateTime, nullable=True)
)

log = Table('log', metadata,
    Column('uuid', VARCHAR(36), primary_key=True),
    Column('name', String(100), nullable=False),
    Column('email', String(100), nullable=False),
    Column('action', String(100), nullable=False),
    Column('datetime', DateTime, nullable=False),
    Column('subscription_id', VARCHAR(36), ForeignKey('subscription.uuid'), nullable=True)
)

# Create all tables
metadata.create_all(engine)

def generate_uuid():
    return str(uuid.uuid4())

with app.app_context():
    db.create_all()

# Routes

@app.route('/')
def home():
    return jsonify({"message": "Welcome to the Newsletter Subscription API!"})


@app.route('/subscription', methods=['POST'])
def subscribe():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')

    new_subscription_uuid = generate_uuid()
    new_log_uuid = generate_uuid()

    insert_subscription_sql = text("""
        INSERT INTO subscription (uuid, name, email, unsubscribe)
        VALUES (:uuid, :name, :email, NULL)
    """)

    insert_log_sql = text("""
        INSERT INTO log (uuid, name, email, action, datetime, subscription_id)
        VALUES (:uuid, :name, :email, 'subscribe', :datetime, :subscription_id)
    """)

    try:
        with engine.begin() as connection:
            # Check if the subscription already exists
            check_subscription_query = text("SELECT uuid FROM subscription WHERE email = :email")
            result = connection.execute(check_subscription_query, {"email": email}).fetchone()

            if result:
                subscription_uuid = result[0]  # Access the UUID from the tuple
                # Update existing subscription
                update_subscription_query = text("""
                    UPDATE subscription 
                    SET unsubscribe = NULL 
                    WHERE email = :email
                """)
                connection.execute(update_subscription_query, {"email": email})
            else:
                # Insert a new subscription record
                connection.execute(insert_subscription_sql, {
                    'uuid': new_subscription_uuid,
                    'name': name,
                    'email': email
                })
                # Fetch the new subscription UUID
                result = connection.execute(check_subscription_query, {"email": email}).fetchone()
                subscription_uuid = result[0]  # Access the UUID from the tuple

            # Log the subscription action
            connection.execute(insert_log_sql, {
                'uuid': new_log_uuid,
                'name': name,
                'email': email,
                'datetime': datetime.now(),  # Use local datetime here
                'subscription_id': subscription_uuid
            })

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({'error': str(e)}), 400

    return jsonify({'message': 'Subscribed successfully!', 'subscription_id': subscription_uuid}), 200

def generate_uuid():
    return str(uuid.uuid4())




@app.route('/subscriptions', methods=['GET'])
def get_all_subscriptions():
    try:
        with engine.connect() as connection:
            # Query to fetch all subscription records
            fetch_subscriptions_sql = text("""
                SELECT uuid, name, email, unsubscribe 
                FROM subscription
            """)
            result = connection.execute(fetch_subscriptions_sql)
            subscriptions = [
                {
                    'uuid': row[0],  # uuid is the first column
                    'name': row[1],  # name is the second column
                    'email': row[2],  # email is the third column
                    'unsubscribe': row[3].isoformat() if row[3] else None  # unsubscribe is the fourth column
                }
                for row in result
            ]

        return jsonify({'subscriptions': subscriptions}), 200
    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/subscription/<uuid>', methods=['PUT'])
def update_subscription(uuid):
    data = request.get_json()

    # SQL statement to update the subscription
    update_subscription_sql = text("""
        UPDATE subscription
        SET name = :name,
            email = :email
        WHERE uuid = :uuid
    """)

    # SQL statement to insert a log for the update action
    insert_log_sql = text("""
        INSERT INTO log (uuid, name, email, action, datetime, subscription_id)
        VALUES (:log_uuid, :name, :email, 'update', :datetime, :subscription_id)
    """)

    try:
        with engine.begin() as connection:
            # Check if the subscription exists
            check_subscription_query = text("SELECT uuid FROM subscription WHERE uuid = :uuid")
            result = connection.execute(check_subscription_query, {"uuid": uuid}).fetchone()

            if not result:
                return jsonify({"message": "Subscription not found!"}), 404

            # Execute the update query
            connection.execute(update_subscription_sql, {
                'uuid': uuid,
                'name': data['name'],
                'email': data['email']
            })

            # Log the update action
            connection.execute(insert_log_sql, {
                'log_uuid': str(uuid.uuid4()),
                'name': data['name'],
                'email': data['email'],
                'datetime': datetime.now(),
                'subscription_id': uuid
            })

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({'error': str(e)}), 400

    return jsonify({'message': 'Subscription updated successfully'}), 200



@app.route('/subscription/<email>', methods=['DELETE'])
def delete_subscription(email):
    try:
        with engine.connect() as connection:
            # Check if the email exists in the subscription table
            check_subscription_query = text("SELECT uuid, name FROM subscription WHERE email = :email")
            result = connection.execute(check_subscription_query, {"email": email}).fetchone()

            if result:
                subscription_uuid = result[0]  # uuid from the result tuple

                # Delete the related logs first
                delete_logs_query = text("DELETE FROM log WHERE subscription_id = :subscription_id")
                connection.execute(delete_logs_query, {"subscription_id": subscription_uuid})

                # Delete the subscription record
                delete_subscription_query = text("DELETE FROM subscription WHERE uuid = :uuid")
                connection.execute(delete_subscription_query, {"uuid": subscription_uuid})

                return jsonify({"message": "Subscription and related logs deleted successfully!"}), 200
            else:
                return jsonify({"message": "Subscription not found!"}), 404

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({'error': str(e)}), 500

def generate_uuid():
    return str(uuid.uuid4())


@app.route('/logs', methods=['GET'])
def get_logs():
    log_id = request.args.get('id')

    try:
        with engine.connect() as connection:
            if log_id:
                # Fetch a single log by ID
                log_query = text("SELECT uuid, name, email, action, datetime, subscription_id FROM log WHERE uuid = :uuid")
                result = connection.execute(log_query, {"uuid": log_id}).fetchone()

                if result:
                    log = {
                        "uuid": result[0],
                        "name": result[1],
                        "email": result[2],
                        "action": result[3],
                        "datetime": result[4],
                        "subscription_id": result[5]
                    }
                    return jsonify(log), 200
                else:
                    return jsonify({"message": "Log not found!"}), 404
            else:
                # Fetch all logs
                logs_query = text("SELECT uuid, name, email, action, datetime, subscription_id FROM log")
                result = connection.execute(logs_query).fetchall()
                logs = [
                    {
                        "uuid": row[0],
                        "name": row[1],
                        "email": row[2],
                        "action": row[3],
                        "datetime": row[4],
                        "subscription_id": row[5]
                    }
                    for row in result
                ]
                return jsonify(logs), 200

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/log', methods=['POST'])
def create_log():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    action = data.get('action')

    try:
        with engine.connect() as connection:
            # Get the subscription UUID
            check_subscription_query = text("SELECT uuid FROM subscription WHERE email = :email")
            subscription = connection.execute(check_subscription_query, {"email": email}).fetchone()

            if subscription:
                insert_log_query = text("""
                    INSERT INTO log (uuid, name, email, action, datetime, subscription_id)
                    VALUES (:uuid, :name, :email, :action, :datetime, :subscription_id)
                """)
                connection.execute(insert_log_query, {
                    "uuid": str(uuid.uuid4()),
                    "name": name,
                    "email": email,
                    "action": action,
                    "datetime": datetime.now(),
                    "subscription_id": subscription[0]  # UUID from the subscription result tuple
                })
                return jsonify({"message": "Log created successfully!"}), 201
            else:
                return jsonify({"message": "Subscription not found!"}), 404

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)


