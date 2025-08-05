from flask import Blueprint

# Import route blueprints
from .auth_routes import auth_routes
from .user_routes import user_routes
from .api_routes import api_routes
from .subscription_routes import subscription_routes
from .stripe_routes import stripe_routes
from .update_routes import update_routes

def init_routes(app):
    """Initialize routes for the Flask app"""
    app.register_blueprint(auth_routes)
    app.register_blueprint(user_routes)
    app.register_blueprint(api_routes)
    app.register_blueprint(subscription_routes)
    app.register_blueprint(update_routes)
    app.register_blueprint(stripe_routes)