import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def get_database_uri():
    uri = os.environ.get("POSTGRES_URL") or os.environ.get("DATABASE_URL")
    if uri:
        # SQLAlchemy 2.0 requires 'postgresql://' instead of legacy 'postgres://'
        if uri.startswith("postgres://"):
            uri = uri.replace("postgres://", "postgresql://", 1)
        return uri
    # In Vercel serverless environment, filesystem is read-only except /tmp
    if os.environ.get("VERCEL"):
        return "sqlite:////tmp/student_portal.db"
    return f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'student_portal.db')}"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 2 * 1024 * 1024))  # 2 MB

    # Folder paths: use /tmp on Vercel to prevent read-only filesystem crash
    if os.environ.get("VERCEL"):
        UPLOAD_FOLDER = "/tmp/uploads/groups"
        ATTACHMENTS_FOLDER = "/tmp/uploads/attachments"
    else:
        UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "img", "groups")
        ATTACHMENTS_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads", "attachments")

    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    ALLOWED_ATTACHMENT_EXTENSIONS = {
        "pdf", "docx", "doc", "txt", "zip", "tar", "gz", "png", "jpg", "jpeg", "csv", "xlsx", "pptx", "py", "json", "md"
    }
    WTF_CSRF_ENABLED = True


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = get_database_uri()


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
