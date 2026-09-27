"""Task board routes: CRUD, status transitions, overdue flagging, activity log, search/filter."""
from datetime import date

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.helpers import save_attachment
from app.models import (
    ActivityLog,
    Attachment,
    GroupMember,
    MemberStatusEnum,
    Project,
    Task,
    TaskPriorityEnum,
    TaskStatusEnum,
    User,
)

tasks_bp = Blueprint("tasks", __name__)


def _get_project_or_403(project_id: int) -> Project:
    project = db.session.get(Project, project_id) or abort(404)
    if not project.is_member(current_user):
        abort(403)
    return project


def _can_manage_task(project: Project) -> bool:
    """Owner or admin can create/delete tasks."""
    return current_user.is_admin or project.owner_id == current_user.id


def _get_members(project: Project) -> list[User]:
    """Return accepted members of the project's group (for assignment)."""
    if not project.group_id:
        owner = db.session.get(User, project.owner_id)
        return [owner] if owner else []
    return [
        m.student for m in project.group.members
        if m.status == MemberStatusEnum.ACCEPTED
    ]


# ---------------------------------------------------------------------------
# Task list with search/filter  (GET /projects/<id>/tasks)
# ---------------------------------------------------------------------------
@tasks_bp.route("/projects/<int:project_id>/tasks")
@login_required
def list_tasks(project_id):
    project = _get_project_or_403(project_id)

    status_filter = request.args.get("status", "").strip()
    q = request.args.get("q", "").strip()
    assignee_filter = request.args.get("assignee", "").strip()

    query = Task.query.filter_by(project_id=project_id)

    if status_filter and status_filter in TaskStatusEnum.ALL:
        query = query.filter(Task.status == status_filter)

    if q:
        query = query.filter(
            Task.title.ilike(f"%{q}%") | Task.description.ilike(f"%{q}%")
        )

    if assignee_filter:
        try:
            assignee_id = int(assignee_filter)
            query = query.filter(Task.assignee_id == assignee_id)
        except ValueError:
            pass

    tasks = query.order_by(Task.due_date.asc().nullslast(), Task.created_at.asc()).all()
    members = _get_members(project)

    return render_template(
        "tasks/list.html",
        project=project,
        tasks=tasks,
        members=members,
        statuses=TaskStatusEnum.ALL,
        status_filter=status_filter,
        q=q,
        assignee_filter=assignee_filter,
        today=date.today(),
        TaskStatusEnum=TaskStatusEnum,
    )


# ---------------------------------------------------------------------------
# Create task  (GET/POST /projects/<id>/tasks/new)
# ---------------------------------------------------------------------------
@tasks_bp.route("/projects/<int:project_id>/tasks/new", methods=["GET", "POST"])
@login_required
def create_task(project_id):
    project = _get_project_or_403(project_id)
    if not _can_manage_task(project):
        abort(403)

    members = _get_members(project)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        assignee_id = request.form.get("assignee_id") or None
        due_date_str = request.form.get("due_date", "").strip()
        status = request.form.get("status", TaskStatusEnum.TODO)
        priority = request.form.get("priority", TaskPriorityEnum.MEDIUM)
        tags = request.form.get("tags", "").strip()

        errors = []
        if not title:
            errors.append("Task title is required.")
        if len(title) > 200:
            errors.append("Title must be 200 characters or less.")
        if status not in TaskStatusEnum.ALL:
            errors.append("Invalid status value.")
        if priority not in TaskPriorityEnum.ALL:
            priority = TaskPriorityEnum.MEDIUM

        due_date = None
        if due_date_str:
            try:
                due_date = date.fromisoformat(due_date_str)
            except ValueError:
                errors.append("Invalid due date format (expected YYYY-MM-DD).")

        assignee_id_int = None
        if assignee_id:
            try:
                assignee_id_int = int(assignee_id)
                member_ids = {m.id for m in members}
                if assignee_id_int not in member_ids:
                    errors.append("Assignee must be a member of this project.")
            except ValueError:
                errors.append("Invalid assignee.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "tasks/form.html",
                project=project,
                members=members,
                statuses=TaskStatusEnum.ALL,
                priorities=TaskPriorityEnum.ALL,
                title=title,
                description=description,
                priority=priority,
                tags=tags,
            )

        task = Task(
            project_id=project_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            tags=tags,
            assignee_id=assignee_id_int,
            due_date=due_date,
        )
        db.session.add(task)
        db.session.flush()

        # Handle optional initial attachment
        if "attachment" in request.files:
            att_file = request.files["attachment"]
            if att_file and att_file.filename:
                try:
                    save_attachment(att_file, current_user.id, task_id=task.id, project_id=project.id)
                except ValueError as err:
                    flash(f"Attachment could not be saved: {err}", "warning")

        # Log creation
        log = ActivityLog(
            task_id=task.id,
            actor_id=current_user.id,
            field_changed="created",
            old_value=None,
            new_value=status,
        )
        db.session.add(log)
        db.session.commit()

        flash("Task created successfully.", "success")
        return redirect(url_for("tasks.task_detail", task_id=task.id))

    return render_template(
        "tasks/form.html",
        project=project,
        members=members,
        statuses=TaskStatusEnum.ALL,
        priorities=TaskPriorityEnum.ALL,
    )


# ---------------------------------------------------------------------------
# Task detail
# ---------------------------------------------------------------------------
@tasks_bp.route("/tasks/<int:task_id>")
@login_required
def task_detail(task_id):
    task = db.session.get(Task, task_id) or abort(404)
    project = task.project
    if not project.is_member(current_user):
        abort(403)

    members = _get_members(project)
    comments = task.comments
    activity = ActivityLog.query.filter_by(task_id=task_id).order_by(ActivityLog.changed_at.asc()).all()
    attachments = task.attachments.order_by(Attachment.created_at.desc()).all()

    return render_template(
        "tasks/detail.html",
        task=task,
        project=project,
        members=members,
        comments=comments,
        activity=activity,
        attachments=attachments,
        TaskStatusEnum=TaskStatusEnum,
        TaskPriorityEnum=TaskPriorityEnum,
        today=date.today(),
    )


# ---------------------------------------------------------------------------
# Edit task
# ---------------------------------------------------------------------------
@tasks_bp.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    task = db.session.get(Task, task_id) or abort(404)
    project = task.project
    if not project.is_member(current_user):
        abort(403)

    can_edit_all = current_user.is_admin or project.owner_id == current_user.id
    is_assignee = task.assignee_id == current_user.id

    if not can_edit_all and not is_assignee:
        abort(403)

    members = _get_members(project)

    if request.method == "POST":
        old_status = task.status
        old_assignee = task.assignee_id
        old_title = task.title
        old_priority = task.priority

        new_title = request.form.get("title", "").strip()
        new_description = request.form.get("description", "").strip()
        new_status = request.form.get("status", task.status)
        new_priority = request.form.get("priority", task.priority)
        new_tags = request.form.get("tags", "").strip()
        new_assignee_id = request.form.get("assignee_id") or None
        due_date_str = request.form.get("due_date", "")

        errors = []
        if can_edit_all:
            if not new_title:
                errors.append("Task title is required.")
            if len(new_title) > 200:
                errors.append("Title must be 200 characters or less.")
        if new_status not in TaskStatusEnum.ALL:
            errors.append("Invalid status value.")
        if new_priority not in TaskPriorityEnum.ALL:
            new_priority = task.priority

        due_date = task.due_date
        if due_date_str:
            try:
                due_date = date.fromisoformat(due_date_str)
            except ValueError:
                errors.append("Invalid due date format.")

        new_assignee_int = None
        if new_assignee_id and can_edit_all:
            try:
                new_assignee_int = int(new_assignee_id)
                member_ids = {m.id for m in members}
                if new_assignee_int not in member_ids:
                    errors.append("Assignee must be a project member.")
            except ValueError:
                errors.append("Invalid assignee.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "tasks/form.html",
                project=project,
                task=task,
                members=members,
                statuses=TaskStatusEnum.ALL,
                priorities=TaskPriorityEnum.ALL,
            )

        logs = []

        if can_edit_all:
            if task.title != new_title:
                logs.append(ActivityLog(task_id=task.id, actor_id=current_user.id,
                                        field_changed="title", old_value=old_title, new_value=new_title))
            task.title = new_title
            task.description = new_description
            task.due_date = due_date
            task.tags = new_tags
            if old_priority != new_priority:
                logs.append(ActivityLog(task_id=task.id, actor_id=current_user.id,
                                        field_changed="priority", old_value=old_priority, new_value=new_priority))
                task.priority = new_priority

            if new_assignee_id == "":
                if old_assignee is not None:
                    logs.append(ActivityLog(task_id=task.id, actor_id=current_user.id,
                                            field_changed="assignee", old_value=str(old_assignee), new_value=None))
                task.assignee_id = None
            elif new_assignee_int is not None:
                if old_assignee != new_assignee_int:
                    logs.append(ActivityLog(task_id=task.id, actor_id=current_user.id,
                                            field_changed="assignee",
                                            old_value=str(old_assignee), new_value=str(new_assignee_int)))
                task.assignee_id = new_assignee_int

        if task.status != new_status:
            logs.append(ActivityLog(task_id=task.id, actor_id=current_user.id,
                                    field_changed="status", old_value=old_status, new_value=new_status))
            task.status = new_status

        # Handle attachment if added
        if "attachment" in request.files:
            att_file = request.files["attachment"]
            if att_file and att_file.filename:
                try:
                    save_attachment(att_file, current_user.id, task_id=task.id, project_id=project.id)
                except ValueError as err:
                    flash(f"Attachment could not be saved: {err}", "warning")

        for log in logs:
            db.session.add(log)

        db.session.commit()
        flash("Task updated successfully.", "success")
        return redirect(url_for("tasks.task_detail", task_id=task.id))

    return render_template(
        "tasks/form.html",
        project=project,
        task=task,
        members=members,
        statuses=TaskStatusEnum.ALL,
        priorities=TaskPriorityEnum.ALL,
    )


# ---------------------------------------------------------------------------
# Delete task
# ---------------------------------------------------------------------------
@tasks_bp.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task(task_id):
    task = db.session.get(Task, task_id) or abort(404)
    project = task.project
    if not _can_manage_task(project):
        abort(403)

    project_id = project.id
    db.session.delete(task)
    db.session.commit()
    flash("Task deleted.", "success")
    return redirect(url_for("tasks.list_tasks", project_id=project_id))


# ---------------------------------------------------------------------------
# Quick status change via JS fetch (POST /tasks/<id>/quick-status)
# ---------------------------------------------------------------------------
@tasks_bp.route("/tasks/<int:task_id>/quick-status", methods=["POST"])
@login_required
def quick_status(task_id):
    task = db.session.get(Task, task_id) or abort(404)
    project = task.project
    if not project.is_member(current_user):
        abort(403)

    can_edit = (
        current_user.is_admin
        or project.owner_id == current_user.id
        or task.assignee_id == current_user.id
    )
    if not can_edit:
        abort(403)

    new_status = request.form.get("status", "")
    if new_status not in TaskStatusEnum.ALL:
        return jsonify({"error": "Invalid status"}), 400

    old_status = task.status
    if old_status != new_status:
        log = ActivityLog(
            task_id=task.id,
            actor_id=current_user.id,
            field_changed="status",
            old_value=old_status,
            new_value=new_status,
        )
        db.session.add(log)
        task.status = new_status
        db.session.commit()

    return jsonify({"status": new_status, "project_id": project.id, "progress": project.progress()})


# ---------------------------------------------------------------------------
# Interactive Kanban Drag & Drop move (POST /tasks/<id>/kanban-move)
# ---------------------------------------------------------------------------
@tasks_bp.route("/tasks/<int:task_id>/kanban-move", methods=["POST"])
@login_required
def kanban_move(task_id):
    task = db.session.get(Task, task_id) or abort(404)
    project = task.project
    if not project.is_member(current_user):
        return jsonify({"error": "Forbidden"}), 403

    can_edit = (
        current_user.is_admin
        or project.owner_id == current_user.id
        or task.assignee_id == current_user.id
    )
    if not can_edit:
        return jsonify({"error": "You do not have permission to move this task."}), 403

    data = request.get_json(silent=True) or request.form
    new_status = data.get("status")

    if not new_status or new_status not in TaskStatusEnum.ALL:
        return jsonify({"error": "Invalid status"}), 400

    old_status = task.status
    if old_status != new_status:
        log = ActivityLog(
            task_id=task.id,
            actor_id=current_user.id,
            field_changed="status",
            old_value=old_status,
            new_value=new_status,
        )
        db.session.add(log)
        task.status = new_status
        db.session.commit()

    return jsonify({
        "success": True,
        "task_id": task.id,
        "old_status": old_status,
        "new_status": new_status,
        "progress": project.progress(),
    })


# ---------------------------------------------------------------------------
# Task Attachments (Upload & Delete)
# ---------------------------------------------------------------------------
@tasks_bp.route("/tasks/<int:task_id>/attachments", methods=["POST"])
@login_required
def upload_task_attachment(task_id):
    task = db.session.get(Task, task_id) or abort(404)
    project = task.project
    if not project.is_member(current_user):
        abort(403)

    file = request.files.get("attachment")
    if not file or not file.filename:
        flash("Please select a valid file to upload.", "warning")
        return redirect(url_for("tasks.task_detail", task_id=task.id))

    try:
        save_attachment(file, current_user.id, task_id=task.id, project_id=project.id)
        flash("Attachment uploaded successfully.", "success")
    except ValueError as err:
        flash(str(err), "danger")

    return redirect(url_for("tasks.task_detail", task_id=task.id))


@tasks_bp.route("/attachments/<int:attachment_id>/delete", methods=["POST"])
@login_required
def delete_attachment(attachment_id):
    att = db.session.get(Attachment, attachment_id) or abort(404)
    project = att.project
    if not project or not project.is_member(current_user):
        abort(403)

    can_delete = current_user.is_admin or att.uploader_id == current_user.id or project.owner_id == current_user.id
    if not can_delete:
        abort(403)

    # Delete file on disk if exists
    try:
        from flask import current_app
        import os
        folder = current_app.config.get("ATTACHMENTS_FOLDER")
        if folder:
            path = os.path.join(folder, att.filename)
            if os.path.exists(path):
                os.remove(path)
    except Exception:
        pass

    target_task_id = att.task_id
    target_project_id = att.project_id
    db.session.delete(att)
    db.session.commit()
    flash("Attachment removed.", "info")

    if target_task_id:
        return redirect(url_for("tasks.task_detail", task_id=target_task_id))
    return redirect(url_for("projects.detail", project_id=target_project_id))
