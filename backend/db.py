import os
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

db = SQLAlchemy()

def init_app(app):
    # Check for critical environment variables
    database_url = os.getenv("DATABASE_URL")
    jwt_secret_key = os.getenv("JWT_SECRET_KEY")

    if not database_url:
        raise RuntimeError("Critical configuration missing: DATABASE_URL is not set in the .env file.")
    if not jwt_secret_key:
        raise RuntimeError("Critical configuration missing: JWT_SECRET_KEY is not set in the .env file.")

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = jwt_secret_key

    db.init_app(app)
