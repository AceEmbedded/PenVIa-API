from flask import Blueprint, request, jsonify, current_app
from models import Category, Budget, User, Spending
from db import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_mail import Message
from extensions import mail  # Import Flask-Mail instance
from sqlalchemy import func

budget_bp = Blueprint('budget', __name__)

# User's Monthly Income Setup and Initial Budget
@budget_bp.route('/income', methods=['POST'])
@jwt_required()
def set_income():
    current_user_email = get_jwt_identity()
    current_user = User.query.filter_by(email=current_user_email).first()

    if not current_user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    income = data.get('income')

    if not income or not isinstance(income, (int, float)) or income <= 0:
        return jsonify({"error": "Valid income is required"}), 400

    # Calculate 20% savings (for needs)
    current_month_savings = income * 0.2
    current_user.savings_balance += current_month_savings  # Add to cumulative savings

    # Calculate the remaining 80% for Essentials and Wants
    remaining_budget = income * 0.8
    essentials = remaining_budget * 0.5  # 50% of remaining 80% for Essentials
    wants = remaining_budget * 0.3  # 30% of remaining 80% for Wants

    # Update the previous month's 80% balance to be carried over to the next month
    current_user.previous_80_balance = remaining_budget - essentials - wants

    # Commit the changes to the database
    db.session.commit()

    return jsonify({
        "message": "Income set successfully",
        "current_savings": current_user.savings_balance,
        "remaining_essentials": essentials,
        "remaining_wants": wants,
        "previous_balance": current_user.previous_80_balance
    }), 200

# Track Monthly Budget Spending
@budget_bp.route('/spending', methods=['POST'])
@jwt_required()
def track_spending():
    current_user_email = get_jwt_identity()
    current_user = User.query.filter_by(email=current_user_email).first()

    if not current_user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    category = data.get('category')  # 'essentials' or 'wants'
    spending = data.get('spending')

    if not category or spending is None:
        return jsonify({"error": "Category and spending amount are required"}), 400

    # Get the current budget limits for the user
    if category == 'essentials':
        budget_limit = current_user.savings_balance * 0.8 * 0.5  # 50% of 80%
    elif category == 'wants':
        budget_limit = current_user.savings_balance * 0.8 * 0.3  # 30% of 80%
    else:
        return jsonify({"error": "Invalid category"}), 400

    # Track spending and check if it exceeds the budget
    if spending > budget_limit:
        return jsonify({
            "message": "Warning: You have exceeded your budget limit. Do you want to proceed?",
            "budget_limit": budget_limit
        }), 400

    # Save the spending for the category
    spending_entry = Spending(category=category, amount=spending, user_id=current_user.id)
    db.session.add(spending_entry)
    db.session.commit()

    return jsonify({"message": f"Spending tracked for {category}."}), 200

# Budget Limit Monitoring and Notifications
@budget_bp.route('/budget_limit', methods=['GET'])
@jwt_required()
def budget_limit_monitoring():
    current_user_email = get_jwt_identity()
    current_user = User.query.filter_by(email=current_user_email).first()

    if not current_user:
        return jsonify({"error": "User not found"}), 404

    # Get the current monthly limits
    essentials_limit = current_user.savings_balance * 0.8 * 0.5
    wants_limit = current_user.savings_balance * 0.8 * 0.3

    # Retrieve user's current spending from database
    total_essentials_spending = db.session.query(func.sum(Spending.amount)).filter_by(user_id=current_user.id, category='essentials').scalar()
    total_wants_spending = db.session.query(func.sum(Spending.amount)).filter_by(user_id=current_user.id, category='wants').scalar()

    # Check if spending exceeds budget limits
    if total_essentials_spending > essentials_limit:
        send_notification(current_user, "Essentials budget exceeded", essentials_limit)
    
    if total_wants_spending > wants_limit:
        send_notification(current_user, "Wants budget exceeded", wants_limit)

    return jsonify({
        "essentials_limit": essentials_limit,
        "wants_limit": wants_limit,
        "total_essentials_spending": total_essentials_spending,
        "total_wants_spending": total_wants_spending
    }), 200

# Send Email Notification for Budget Exceeded
def send_notification(user, message, limit):
    """Sends an email notification to the user if budget is exceeded."""
    try:
        msg = Message(
            subject="Budget Limit Exceeded",
            recipients=[user.email],
            body=f"Dear {user.first_name},\n\n{message}.\nYour limit for this category was {limit}."
        )
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f"Error sending email: {e}")
        return jsonify({"error": "Failed to send email notification."}), 500


