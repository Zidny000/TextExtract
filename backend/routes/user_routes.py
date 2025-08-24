import logging
from flask import Blueprint, request, jsonify, g
from database.models import User, Subscription
from auth import login_required
from database.db import supabase
import datetime

logger = logging.getLogger(__name__)
user_routes = Blueprint('users', __name__, url_prefix='/users')

@user_routes.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """Get user profile with usage statistics"""
    try:
        # Get user data from global context
        user = g.user.copy()
        # Remove sensitive data
        user.pop('password_hash', None)
        
        # Get today's request count
        today_count = User.get_subscription_period_request_count(user['id'])

        subscription = Subscription.get_active_subscription(user['id'])

        if not subscription:
            return jsonify({"error": "Subscription not found"}), 404

        # Return user profile
        return jsonify({
            "user": user,
            "usage": {
                "subscription_status": subscription.get("status"),
                "subscription_starts": subscription.get("start_date"),
                "monthly_requests": today_count,
                "remaining_requests": user.get("max_requests_per_month", 20) - today_count,
                "plan_limit": user.get("max_requests_per_month", 20),
                "credit_requests": user.get("credit_requests", 0)
            },
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_profile route: {str(e)}")
        return jsonify({"error": "An error occurred fetching profile data"}), 500

@user_routes.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    """Update user profile"""
    try:
        data = request.json
        
        # Validate data
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Prepare update data
        update_data = {}
        
        # Fields that are allowed to be updated
        allowed_fields = ['full_name']
        
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
        
        if not update_data:
            return jsonify({"error": "No valid fields to update"}), 400
        
        # Update the user
        try:
            update_data["updated_at"] = datetime.datetime.now().isoformat()
            response = supabase.table("users").update(update_data).eq("id", g.user_id).execute()

            if len(response.data) > 0:
                updated_user = response.data[0]
                updated_user.pop('password_hash', None)
                return jsonify(updated_user), 200
            
            return jsonify({"error": "Failed to update profile"}), 500
            
        except Exception as e:
            logger.error(f"Database error updating profile: {str(e)}")
            return jsonify({"error": "Failed to update profile"}), 500
        
    except Exception as e:
        logger.error(f"Error in update_profile route: {str(e)}")
        return jsonify({"error": "An error occurred updating profile"}), 500


@user_routes.route('/usage', methods=['GET'])
@login_required
def get_usage():
    """Get user's API usage statistics"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Validate dates
        try:
            if start_date:
                start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            if end_date:
                end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        
        # Query usage stats
        query = supabase.table("usage_stats").select("*").eq("user_id", g.user_id)
        
        # Apply date filters if provided
        if start_date:
            query = query.gte("date", start_date.isoformat())
        if end_date:
            query = query.lte("date", end_date.isoformat())
        
        # Execute query
        response = query.order("date").execute()
        
        return jsonify(response.data), 200
        
    except Exception as e:
        logger.error(f"Error in get_usage route: {str(e)}")
        return jsonify({"error": "An error occurred fetching usage data"}), 500

@user_routes.route('/requests', methods=['GET'])
@login_required
def get_requests():
    """Get user's API request history"""
    try:
        # Get query parameters
        limit = request.args.get('limit', 10)
        offset = request.args.get('offset', 0)
        
        try:
            limit = int(limit)
            offset = int(offset)
            
            if limit < 1 or limit > 100:
                limit = 10
        except ValueError:
            return jsonify({"error": "Invalid limit or offset value"}), 400
        
        # Query requests
        response = supabase.table("api_requests").select("*").eq("user_id", g.user_id).order("created_at", desc=True).limit(limit).offset(offset).execute()
        
        return jsonify(response.data), 200
        
    except Exception as e:
        logger.error(f"Error in get_requests route: {str(e)}")
        return jsonify({"error": "An error occurred fetching request history"}), 500
        
@user_routes.route('/reviews', methods=['GET'])
@login_required
def get_reviews():
    """Get user's reviews"""
    try:
        from database.models import UserReview
        reviews = UserReview.get_by_user_id(g.user_id)
        return jsonify(reviews), 200
    except Exception as e:
        logger.error(f"Error in get_reviews route: {str(e)}")
        return jsonify({"error": "An error occurred fetching reviews"}), 500
        
@user_routes.route('/reviews', methods=['POST'])
@login_required
def create_review():
    """Create a new user review"""
    try:
        data = request.json
        
        # Validate data
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        rating = data.get('rating')
        review_text = data.get('review_text')
        
        # Validate fields
        if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({"error": "Rating must be between 1 and 5"}), 400
            
        if not review_text or not isinstance(review_text, str) or len(review_text) < 5:
            return jsonify({"error": "Review text must be at least 5 characters"}), 400
            
        # Create the review
        from database.models import UserReview
        review = UserReview.create(g.user_id, rating, review_text)
        
        if review:
            return jsonify(review), 201
        
        return jsonify({"error": "Failed to create review"}), 500
        
    except Exception as e:
        logger.error(f"Error in create_review route: {str(e)}")
        return jsonify({"error": "An error occurred creating review"}), 500 