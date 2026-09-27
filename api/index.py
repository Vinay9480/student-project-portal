import os
import sys

# Ensure root directory is on the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import User

# Create Flask application instance
app = create_app(os.environ.get("FLASK_ENV", "production"))

# Vercel WSGI Middleware to preserve the original URL path when internal rewrites occur
class VercelPathFixMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # When Vercel internally rewrites requests to /api/index or /api/index.py,
        # it passes the original requested path in HTTP_X_MATCHED_PATH or REQUEST_URI.
        path_info = environ.get("PATH_INFO", "")
        if path_info in ("/api/index", "/api/index.py", "/api"):
            original_path = environ.get("HTTP_X_MATCHED_PATH") or environ.get("RAW_URI") or environ.get("REQUEST_URI")
            if original_path:
                clean_path = original_path.split("?")[0]
                if clean_path and clean_path != path_info:
                    environ["PATH_INFO"] = clean_path
        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathFixMiddleware(app.wsgi_app)

# Auto-initialize database tables and seed demo data on cold start if table is empty
with app.app_context():
    try:
        db.create_all()
        # Seed initial demo data on fresh deployment if no users exist
        if User.query.count() == 0:
            from seed_demo import seed_database
            seed_database(app=app)
    except Exception as e:
        print(f"Notice during database initialization: {e}")

# Expose app for Vercel Python WSGI
