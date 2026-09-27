"""User profile routes (view profile, admin role change)."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.helpers import admin_required
from app.models import MemberStatusEnum, RoleEnum, User

users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.route("/<int:user_id>")
@login_required
def profile(user_id):
    user = db.session.get(User, user_id) or abort(404)
    accepted_groups = user.accepted_groups()
    group_count = len(accepted_groups)
    return render_template(
        "users/profile.html",
        profile_user=user,
        accepted_groups=accepted_groups,
        group_count=group_count,
    )


@users_bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    user = db.session.get(User, user_id) or abort(404)
    # User can edit their own profile; admins can edit anyone
    if user.id != current_user.id and not current_user.is_admin:
        abort(403)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        bio = request.form.get("bio", "").strip()
        github_url = request.form.get("github_url", "").strip()
        linkedin_url = request.form.get("linkedin_url", "").strip()

        if not name:
            flash("Name cannot be empty.", "danger")
            return render_template("users/edit.html", user=user, roles=RoleEnum.ALL)

        if current_user.is_admin:
            role = request.form.get("role", user.role)
            if role in RoleEnum.ALL:
                user.role = role

        user.name = name
        user.bio = bio or None
        user.github_url = github_url or None
        user.linkedin_url = linkedin_url or None

        # Avatar upload
        if "avatar" in request.files:
            avatar_file = request.files["avatar"]
            if avatar_file and avatar_file.filename:
                from app.helpers import save_avatar
                try:
                    user.avatar_url = save_avatar(avatar_file)
                except ValueError as err:
                    flash(str(err), "danger")

        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("users.profile", user_id=user.id))

    return render_template("users/edit.html", user=user, roles=RoleEnum.ALL)


@users_bp.route("/")
@login_required
@admin_required
def list_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("users/list.html", users=users)
