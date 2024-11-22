from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from passlib.context import CryptContext
from dotenv import load_dotenv
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import os
import re
from db import db, init_app
from models import User
from budget_routes import budget_bp
from extensions import Mail

app = Flask(__name__)
load_dotenv()

init_app(app)

jwt = JWTManager(app)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
migrate = Migrate(app,db)

app.register_blueprint(budget_bp, url_prefix='/api/v1')

app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Use your mail provider's SMTP
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = 'penviaapp@gmail.com'

mail = Mail(app)

def is_password_valid(password, first_name, last_name, email):
    # Check length
    if len(password) < 8:
        return "Password must be at least 8 characters long."

    # Check for at least one uppercase letter
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter."

    # Check for at least one lowercase letter
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter."

    # Check for at least one digit
    if not re.search(r"[0-9]", password):
        return "Password must contain at least one number."

    # Check for commonly used passwords (you can extend this list)
    common_passwords = ["password", "123456", "12345678", "qwerty", "abc123", "password1"]
    if password.lower() in common_passwords:
        return "Password is too common. Please choose a stronger password."

    # Check if password includes the user's first name, last name, or email
    if first_name and first_name.lower() in password.lower():
        return "Password must not contain your first name."
    if last_name and last_name.lower() in password.lower():
        return "Password must not contain your last name."
    if email and email.split("@")[0].lower() in password.lower():
        return "Password must not contain part of your email."

    return None  # No errors, password is valid

# Function to validate email format
def is_valid_email(email):
    email_regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    return re.match(email_regex, email) is not None

# User Registration
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    print(data)

    # Check if all fields are provided
    required_fields = ['email', 'password', 'confirm_password', 'first_name', 'last_name']
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    first_name = data.get('first_name')
    last_name = data.get('last_name')

    # Check if email is valid
    if not email or not is_valid_email(email):
        return jsonify({"error": "Invalid email format."}), 400
    
    # Check if password and confirm_password match
    if password != confirm_password:
        return jsonify({"error": "Passwords do not match"}), 400

    # Validate password strength
    password_error = is_password_valid(password, first_name, last_name, email)
    if password_error:
        return jsonify({"error": password_error}), 400
    
    # Hash the password
    hashed_password = pwd_context.hash(password)
    
    # Check if the email already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"error": "The provided email is already registered."}), 400

    # Register the user
    try:
        user = User(email=email, password=hashed_password, first_name=first_name, last_name=last_name)
        db.session.add(user)
        db.session.commit()
        return jsonify({"message": "User registered successfully"}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Registration failed due to: {str(e)}")
        return jsonify({"error": "Registration failed. Please try again later."}), 400

# User Login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    # Extract email and password from the incoming request
    email = data.get('email')
    password = data.get('password')

    # Check if both email and password are provided
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    # Find user by email
    user = User.query.filter_by(email=email).first()

    # If the user does not exist or the password doesn't match, return error
    if not user or not pwd_context.verify(password, user.password):
        return jsonify({"error": "Invalid credentials"}), 401

    # Create access token
    access_token = create_access_token(identity=user.email)

    # Return the access token and success message
    return jsonify({"message": "Login successful", "access_token": access_token}), 200

# Update Profile
@app.route('/update-profile', methods=['PUT'])
@jwt_required()
def update_profile():
    current_user = get_jwt_identity()
    data = request.get_json()

    # Check if the fields are provided before updating
    required_fields = ['email', 'first_name', 'last_name']  # Update the list based on your requirements
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    new_email = data.get('email')
    new_password = data.get('password')
    new_first_name = data.get('first_name')
    new_last_name = data.get('last_name')

    user = User.query.filter_by(email=current_user).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        if new_email:
            user.email = new_email
        if new_password:
            user.password = pwd_context.hash(new_password)
        if new_first_name:
            user.first_name = new_first_name
        if new_last_name:
            user.last_name = new_last_name

        db.session.commit()
        return jsonify({"message": "Profile updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(e)  # For debugging
        return jsonify({"error": "Update failed"}), 400

# Fetch Registered Users
@app.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    try:
        # Query all users from the database
        users = User.query.all()

        if not users:
            return jsonify({"message": "No users found"}), 404

        # Format the user data (excluding username as it's not in the model anymore)
        users_data = [{"id": user.id, "email": user.email, "first_name": user.first_name, 
                       "last_name": user.last_name, "created_at": user.created_at}
                      for user in users]

        return jsonify({"users": users_data}), 200

    except Exception as e:
        # Log the error for debugging
        app.logger.error(f"Error occurred while fetching users: {str(e)}")
        return jsonify({"error": "An error occurred while fetching users"}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    print(f"Unhandled exception: {str(e)}")  # Log for debugging
    return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500

if __name__ == "__main__":
    app.run(debug=True)