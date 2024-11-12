from app import app, db
from models import User
from passlib.context import CryptContext

# Initialize the password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Function to create the admin user
def create_admin():
    email = "muibiyusuf@hotmail.com"  # Admin email
    password = "Tek3Lagos!"  # Admin password
    hashed_password = pwd_context.hash(password)  # Hash the password
    first_name = "Yusuf"  # First name for admin
    last_name = "Muibi"  # Last name for admin

    # Use app context to query the database
    with app.app_context():
        # Check if the admin user already exists by email
        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            print(f"Admin user with email {email} already exists.")
        else:
            # Create a new admin user instance
            admin_user = User(
                email=email,
                password=hashed_password,
                first_name=first_name,
                last_name=last_name
            )

            # Add and commit the new admin user
            db.session.add(admin_user)
            db.session.commit()
            print(f"Admin user created: {email}")

# Call the function to create the admin user when running the script
if __name__ == "__main__":
    create_admin()
