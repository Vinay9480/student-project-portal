"""
Flask application factory.
"""
import os

from flask import Flask

from config import config
from app.extensions import csrf, db, login_manager, migrate


def create_app(config_name: str = "default") -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])

    # Ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)

    # Ensure group image upload and attachments folder exist
    os.makedirs(app.config.get("UPLOAD_FOLDER", ""), exist_ok=True)
    os.makedirs(app.config.get("ATTACHMENTS_FOLDER", ""), exist_ok=True)

    # Initialise extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    # User loader
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.projects import projects_bp
    from app.routes.tasks import tasks_bp
    from app.routes.groups import groups_bp
    from app.routes.mentors import mentors_bp
    from app.routes.comments import comments_bp
    from app.routes.notifications import notifications_bp
    from app.routes.users import users_bp
    from app.routes.main import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(mentors_bp)
    app.register_blueprint(comments_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(users_bp)

    # Error handlers
    from app.errors import register_error_handlers
    register_error_handlers(app)

    # Create tables on first run and auto-upgrade sqlite columns
    with app.app_context():
        db.create_all()
        _upgrade_sqlite_schema(app, db)

    return app


def _upgrade_sqlite_schema(app, db):
    """Automatically adds newly defined columns to existing SQLite tables safely."""
    try:
        if db.engine.name != "sqlite":
            return
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        if "user" in tables:
            user_cols = {c["name"] for c in inspector.get_columns("user")}
            if "avatar_url" not in user_cols:
                db.session.execute(text("ALTER TABLE user ADD COLUMN avatar_url VARCHAR(300)"))
            if "bio" not in user_cols:
                db.session.execute(text("ALTER TABLE user ADD COLUMN bio TEXT"))
            if "github_url" not in user_cols:
                db.session.execute(text("ALTER TABLE user ADD COLUMN github_url VARCHAR(200)"))
            if "linkedin_url" not in user_cols:
                db.session.execute(text("ALTER TABLE user ADD COLUMN linkedin_url VARCHAR(200)"))

        if "project" in tables:
            project_cols = {c["name"] for c in inspector.get_columns("project")}
            if "status" not in project_cols:
                db.session.execute(text("ALTER TABLE project ADD COLUMN status VARCHAR(20) DEFAULT 'in_progress'"))
            if "github_repo" not in project_cols:
                db.session.execute(text("ALTER TABLE project ADD COLUMN github_repo VARCHAR(255)"))
            if "live_demo_url" not in project_cols:
                db.session.execute(text("ALTER TABLE project ADD COLUMN live_demo_url VARCHAR(255)"))

        if "task" in tables:
            task_cols = {c["name"] for c in inspector.get_columns("task")}
            if "priority" not in task_cols:
                db.session.execute(text("ALTER TABLE task ADD COLUMN priority VARCHAR(10) DEFAULT 'medium'"))
            if "tags" not in task_cols:
                db.session.execute(text("ALTER TABLE task ADD COLUMN tags VARCHAR(300)"))
            if "order" not in task_cols:
                db.session.execute(text("ALTER TABLE task ADD COLUMN `order` INTEGER DEFAULT 0"))

        db.session.commit()
    except Exception:
        db.session.rollback()
