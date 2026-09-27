"""Comments routes: task-level and project-level."""
from flask import Blueprint, abort, flash, redirect, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Comment, MemberStatusEnum, Project, Task

comments_bp = Blueprint("comments", __name__)


def _can_comment_on_project(project: Project) -> bool:
    """Members, group mentor, and admin can comment."""
    return project.is_member(current_user)


# ---------------------------------------------------------------------------
# Task-level comment
# ---------------------------------------------------------------------------

@comments_bp.route("/tasks/<int:task_id>/comments", methods=["POST"])
@login_required
def add_task_comment(task_id):
    task = db.session.get(Task, task_id) or abort(404)
    project = task.project
    if not _can_comment_on_project(project):
        abort(403)

    text = request.form.get("text", "").strip()
    if not text:
        flash("Comment cannot be empty.", "danger")
        return redirect(url_for("tasks.task_detail", task_id=task_id))

    comment = Comment(task_id=task_id, project_id=None, user_id=current_user.id, text=text)
    db.session.add(comment)
    db.session.commit()

    flash("Comment added.", "success")
    return redirect(url_for("tasks.task_detail", task_id=task_id))


# ---------------------------------------------------------------------------
# Project-level comment
# ---------------------------------------------------------------------------

@comments_bp.route("/projects/<int:project_id>/comments", methods=["POST"])
@login_required
def add_project_comment(project_id):
    project = db.session.get(Project, project_id) or abort(404)
    if not _can_comment_on_project(project):
        abort(403)

    text = request.form.get("text", "").strip()
    if not text:
        flash("Comment cannot be empty.", "danger")
        return redirect(url_for("projects.detail", project_id=project_id))

    comment = Comment(task_id=None, project_id=project_id, user_id=current_user.id, text=text)
    db.session.add(comment)
    db.session.commit()

    flash("Comment added.", "success")
    return redirect(url_for("projects.detail", project_id=project_id))
