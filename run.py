import os
from app import create_app
from app.extensions import db

app = create_app(os.environ.get("FLASK_ENV", "development"))


@app.cli.command("init-db")
def init_db():
    """Initialize the database (create all tables)."""
    with app.app_context():
        db.create_all()
        print("Database tables created.")


@app.cli.command("seed-data")
def seed_data():
    """Populate database with rich realistic demo data."""
    from seed_demo import seed_database
    seed_database()


if __name__ == "__main__":
    app.run(port=5001)
