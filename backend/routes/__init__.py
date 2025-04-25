from .auth_routes import auth_routes
from .user_routes import user_routes
from .api_routes import api_routes

def register_routes(app):
    """Register all application routes"""
    app.register_blueprint(auth_routes)
    app.register_blueprint(user_routes)
    app.register_blueprint(api_routes) 