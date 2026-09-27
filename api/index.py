import os
import sys

# Ensure root directory is on the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import User

# Create Flask application instance
app = create_app(os.environ.get("FLASK_ENV", "production"))

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
