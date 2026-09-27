"""
Shared helper utilities: permission decorators, notification factory, image upload.
"""
import os
from functools import wraps
from typing import Optional

from flask import abort, current_app, flash, redirect, url_for
from flask_login import current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import (
    MemberStatusEnum,
    Notification,
    NotificationTypeEnum,
    RoleEnum,
)


# ---------------------------------------------------------------------------
# Permission decorators
# ---------------------------------------------------------------------------

def role_required(*roles):
    """Restrict a view to users with one of the given roles."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator


def admin_required(f):
    return role_required(RoleEnum.ADMIN)(f)


def student_required(f):
    return role_required(RoleEnum.STUDENT, RoleEnum.ADMIN)(f)


def mentor_required(f):
    return role_required(RoleEnum.MENTOR, RoleEnum.ADMIN)(f)


# ---------------------------------------------------------------------------
# Notification factory
# ---------------------------------------------------------------------------

def create_notification(user_id: int, notif_type: str, payload: dict) -> Notification:
    """Create and persist a Notification row."""
    import json
    n = Notification(
        user_id=user_id,
        type=notif_type,
        payload=json.dumps(payload),
        read=False,
    )
    db.session.add(n)
    return n


def notify_group_invite(invitee_id: int, group_name: str, leader_name: str, invite_id: int):
    create_notification(
        invitee_id,
        NotificationTypeEnum.GROUP_INVITE,
        {"group_name": group_name, "leader_name": leader_name, "invite_id": invite_id},
    )


def notify_invite_response(leader_id: int, invitee_name: str, group_name: str, accepted: bool):
    create_notification(
        leader_id,
        NotificationTypeEnum.INVITE_RESPONSE,
        {"invitee_name": invitee_name, "group_name": group_name, "accepted": accepted},
    )


def notify_member_left(recipient_id: int, member_name: str, group_name: str):
    create_notification(
        recipient_id,
        NotificationTypeEnum.MEMBER_LEFT,
        {"member_name": member_name, "group_name": group_name},
    )


def notify_mentor_request(mentor_id: int, group_name: str, leader_name: str,
                           members: list, domain: str, tech_tags: str, request_id: int):
    create_notification(
        mentor_id,
        NotificationTypeEnum.MENTOR_REQUEST,
        {
            "group_name": group_name,
            "leader_name": leader_name,
            "members": members,
            "domain": domain,
            "tech_tags": tech_tags,
            "request_id": request_id,
        },
    )


def notify_mentor_decision(recipient_id: int, group_name: str, mentor_name: str, accepted: bool):
    create_notification(
        recipient_id,
        NotificationTypeEnum.MENTOR_DECISION,
        {"group_name": group_name, "mentor_name": mentor_name, "accepted": accepted},
    )


def notify_group_disbanded(recipient_id: int, group_name: str, disbanded_by: str):
    create_notification(
        recipient_id,
        NotificationTypeEnum.GROUP_DISBANDED,
        {"group_name": group_name, "disbanded_by": disbanded_by},
    )


# ---------------------------------------------------------------------------
# Image upload helper
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_image(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def save_group_image(file_storage) -> Optional[str]:
    """
    Validate and save a group image.
    Returns the relative URL path or None on failure.
    Raises ValueError with a user-facing message on validation failure.
    """
    if not file_storage or file_storage.filename == "":
        return None

    if not allowed_image(file_storage.filename):
        raise ValueError("Only image files (png, jpg, jpeg, gif, webp) are allowed.")

    # Werkzeug already checks MAX_CONTENT_LENGTH at the WSGI level,
    # but we double-check here for a cleaner error message.
    file_storage.seek(0, 2)
    size = file_storage.tell()
    file_storage.seek(0)
    max_size = current_app.config.get("MAX_CONTENT_LENGTH", 2 * 1024 * 1024)
    if size > max_size:
        raise ValueError(f"Image must be under {max_size // (1024*1024)} MB.")

    filename = secure_filename(file_storage.filename)
    # prepend timestamp to avoid filename collision
    import time
    unique_filename = f"{int(time.time())}_{filename}"
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    save_path = os.path.join(upload_folder, unique_filename)
    file_storage.save(save_path)

    # Return a URL relative to /static/
    return f"/static/img/groups/{unique_filename}"


# ---------------------------------------------------------------------------
# Attachment upload helper
# ---------------------------------------------------------------------------

def allowed_attachment(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    allowed = current_app.config.get("ALLOWED_ATTACHMENT_EXTENSIONS", set())
    return ext in allowed


def save_attachment(file_storage, uploader_id: int, task_id: Optional[int] = None, project_id: Optional[int] = None):
    """Save an uploaded file attachment and create an Attachment record."""
    import time
    from app.models import Attachment

    if not file_storage or not file_storage.filename:
        return None

    orig_name = file_storage.filename
    if not allowed_attachment(orig_name):
        raise ValueError("File type is not permitted. Supported types: PDF, Word, Excel, ZIP, images, code, text.")

    file_storage.seek(0, 2)
    size = file_storage.tell()
    file_storage.seek(0)

    max_size = current_app.config.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)
    if size > max_size:
        raise ValueError(f"File size exceeds maximum allowed ({max_size // (1024 * 1024)} MB).")

    safe_name = secure_filename(orig_name)
    stored_name = f"{int(time.time())}_{uploader_id}_{safe_name}"
    folder = current_app.config.get("ATTACHMENTS_FOLDER", os.path.join(current_app.root_path, "static", "uploads", "attachments"))
    os.makedirs(folder, exist_ok=True)

    file_path = os.path.join(folder, stored_name)
    file_storage.save(file_path)

    attachment = Attachment(
        filename=stored_name,
        original_name=orig_name,
        file_size=size,
        mime_type=file_storage.content_type,
        uploader_id=uploader_id,
        task_id=task_id,
        project_id=project_id,
    )
    db.session.add(attachment)
    db.session.commit()
    return attachment


def save_avatar(file_storage) -> Optional[str]:
    """Save user avatar image and return relative URL."""
    import time
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_image(file_storage.filename):
        raise ValueError("Avatar must be a valid image file (PNG, JPG, JPEG, WEBP).")

    safe_name = secure_filename(file_storage.filename)
    filename = f"avatar_{int(time.time())}_{safe_name}"
    folder = os.path.join(current_app.root_path, "static", "uploads", "avatars")
    os.makedirs(folder, exist_ok=True)
    file_storage.save(os.path.join(folder, filename))
    return f"/static/uploads/avatars/{filename}"
