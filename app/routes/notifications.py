"""Notification routes: list, mark read."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Notification

notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@notifications_bp.route("/")
@login_required
def list_notifications():
    notifications = (
        Notification.query
        .filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    unread_count = sum(1 for n in notifications if not n.read)
    return render_template(
        "notifications/list.html",
        notifications=notifications,
        unread_count=unread_count,
    )


@notifications_bp.route("/<int:notif_id>/read", methods=["POST"])
@login_required
def mark_read(notif_id):
    notif = db.session.get(Notification, notif_id) or abort(404)
    if notif.user_id != current_user.id:
        abort(403)
    notif.read = True
    db.session.commit()

    # Redirect back to where the user came from
    next_url = request.form.get("next") or url_for("notifications.list_notifications")
    return redirect(next_url)


@notifications_bp.route("/mark-all-read", methods=["POST"])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, read=False).update({"read": True})
    db.session.commit()
    flash("All notifications marked as read.", "success")
    return redirect(url_for("notifications.list_notifications"))
