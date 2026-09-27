"""Project CRUD routes."""
from datetime import date, datetime, timezone
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.helpers import save_attachment
from app.models import (
    Attachment,
    Group,
    GroupMember,
    MemberStatusEnum,
    Milestone,
    Project,
    ProjectStatusEnum,
    RoleEnum,
    Task,
    TaskPriorityEnum,
    TaskStatusEnum,
)

projects_bp = Blueprint("projects", __name__, url_prefix="/projects")


def _can_edit_project(project: Project) -> bool:
    """Only owner or admin can edit/delete."""
    return current_user.is_admin or project.owner_id == current_user.id


@projects_bp.route("/")
@login_required
def list_projects():
    if current_user.is_admin:
        projects = Project.query.order_by(Project.created_at.desc()).all()
    else:
        from sqlalchemy import or_
        member_group_ids = db.session.query(GroupMember.group_id).filter_by(
            student_id=current_user.id, status=MemberStatusEnum.ACCEPTED
        ).subquery()
        projects = Project.query.filter(
            or_(
                Project.owner_id == current_user.id,
                Project.group_id.in_(member_group_ids),
                (Project.group.has(Group.mentor_id == current_user.id) if current_user.is_mentor else False)
            )
        ).order_by(Project.created_at.desc()).all()
    return render_template("projects/list.html", projects=projects, ProjectStatusEnum=ProjectStatusEnum)


@projects_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_project():
    # Only students (and admins) can create projects per permission table
    if current_user.is_mentor:
        abort(403)

    if current_user.is_admin:
        available_groups = Group.query.all()
    else:
        available_groups = Group.query.filter_by(leader_id=current_user.id).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        status = request.form.get("status", ProjectStatusEnum.IN_PROGRESS)
        github_repo = request.form.get("github_repo", "").strip()
        live_demo_url = request.form.get("live_demo_url", "").strip()
        group_id = request.form.get("group_id") or None
        if group_id:
            group_id = int(group_id)

        errors = []
        if not name:
            errors.append("Project name is required.")
        if len(name) > 200:
            errors.append("Project name must be 200 characters or less.")
        if group_id:
            grp = db.session.get(Group, group_id)
            if not grp:
                errors.append("Selected group not found.")
            elif not current_user.is_admin and grp.leader_id != current_user.id:
                errors.append("You can only link a project to a group you lead.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("projects/form.html", available_groups=available_groups,
                                   name=name, description=description, status=status,
                                   github_repo=github_repo, live_demo_url=live_demo_url,
                                   ProjectStatusEnum=ProjectStatusEnum)

        project = Project(
            name=name,
            description=description,
            status=status if status in ProjectStatusEnum.ALL else ProjectStatusEnum.IN_PROGRESS,
            github_repo=github_repo or None,
            live_demo_url=live_demo_url or None,
            owner_id=current_user.id,
            group_id=group_id,
        )
        db.session.add(project)
        db.session.commit()
        flash("Project created successfully.", "success")
        return redirect(url_for("projects.detail", project_id=project.id))

    return render_template("projects/form.html", available_groups=available_groups,
                           ProjectStatusEnum=ProjectStatusEnum)


@projects_bp.route("/<int:project_id>")
@login_required
def detail(project_id):
    project = db.session.get(Project, project_id) or abort(404)
    if not project.is_member(current_user):
        abort(403)

    tasks = project.tasks.order_by(Task.order.asc(), Task.created_at.asc()).all()
    todo_tasks = [t for t in tasks if t.status == TaskStatusEnum.TODO]
    inprogress_tasks = [t for t in tasks if t.status == TaskStatusEnum.IN_PROGRESS]
    done_tasks = [t for t in tasks if t.status == TaskStatusEnum.DONE]

    progress = project.progress()

    project_comments = (
        project.comments.order_by(db.desc("created_at")).all()
        if hasattr(project.comments, "order_by")
        else []
    )

    members = []
    if project.group_id and project.group:
        members = [
            m.student for m in project.group.members
            if m.status == MemberStatusEnum.ACCEPTED
        ]
    elif project.owner:
        members = [project.owner]

    milestones = project.milestones.order_by(Milestone.due_date.asc().nullslast(), Milestone.created_at.asc()).all()
    attachments = project.attachments.order_by(Attachment.created_at.desc()).all()

    return render_template(
        "projects/detail.html",
        project=project,
        tasks=tasks,
        todo_tasks=todo_tasks,
        inprogress_tasks=inprogress_tasks,
        done_tasks=done_tasks,
        progress=progress,
        members=members,
        project_comments=project_comments,
        milestones=milestones,
        attachments=attachments,
        TaskStatusEnum=TaskStatusEnum,
        TaskPriorityEnum=TaskPriorityEnum,
        ProjectStatusEnum=ProjectStatusEnum,
        today=date.today(),
    )


@projects_bp.route("/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
def edit_project(project_id):
    project = db.session.get(Project, project_id) or abort(404)
    if not _can_edit_project(project):
        abort(403)

    if current_user.is_admin:
        available_groups = Group.query.all()
    else:
        available_groups = Group.query.filter_by(leader_id=current_user.id).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        status = request.form.get("status", project.status)
        github_repo = request.form.get("github_repo", "").strip()
        live_demo_url = request.form.get("live_demo_url", "").strip()
        group_id = request.form.get("group_id") or None
        if group_id:
            group_id = int(group_id)

        errors = []
        if not name:
            errors.append("Project name is required.")
        if len(name) > 200:
            errors.append("Project name must be 200 characters or less.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("projects/form.html", project=project,
                                   available_groups=available_groups,
                                   name=name, description=description,
                                   ProjectStatusEnum=ProjectStatusEnum)

        project.name = name
        project.description = description
        project.status = status if status in ProjectStatusEnum.ALL else project.status
        project.github_repo = github_repo or None
        project.live_demo_url = live_demo_url or None
        project.group_id = group_id
        db.session.commit()
        flash("Project updated successfully.", "success")
        return redirect(url_for("projects.detail", project_id=project.id))

    return render_template("projects/form.html", project=project,
                           available_groups=available_groups,
                           ProjectStatusEnum=ProjectStatusEnum)


@projects_bp.route("/<int:project_id>/delete", methods=["POST"])
@login_required
def delete_project(project_id):
    project = db.session.get(Project, project_id) or abort(404)
    if not _can_edit_project(project):
        abort(403)
    db.session.delete(project)
    db.session.commit()
    flash("Project deleted.", "success")
    return redirect(url_for("projects.list_projects"))


@projects_bp.route("/<int:project_id>/progress")
@login_required
def progress(project_id):
    project = db.session.get(Project, project_id) or abort(404)
    if not project.is_member(current_user):
        abort(403)
    return {"progress": project.progress(), "project_id": project_id}


# ---------------------------------------------------------------------------
# Project Milestones
# ---------------------------------------------------------------------------
@projects_bp.route("/<int:project_id>/milestones", methods=["POST"])
@login_required
def add_milestone(project_id):
    project = db.session.get(Project, project_id) or abort(404)
    if not _can_edit_project(project):
        abort(403)

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    due_date_str = request.form.get("due_date", "").strip()

    if not title:
        flash("Milestone title is required.", "danger")
        return redirect(url_for("projects.detail", project_id=project.id))

    due_date = None
    if due_date_str:
        try:
            due_date = date.fromisoformat(due_date_str)
        except ValueError:
            pass

    m = Milestone(project_id=project.id, title=title, description=description, due_date=due_date)
    db.session.add(m)
    db.session.commit()
    flash("Milestone added.", "success")
    return redirect(url_for("projects.detail", project_id=project.id))


@projects_bp.route("/<int:project_id>/milestones/<int:milestone_id>/toggle", methods=["POST"])
@login_required
def toggle_milestone(project_id, milestone_id):
    project = db.session.get(Project, project_id) or abort(404)
    if not project.is_member(current_user):
        abort(403)

    m = db.session.get(Milestone, milestone_id) or abort(404)
    if m.project_id != project.id:
        abort(400)

    m.is_completed = not m.is_completed
    m.completed_at = datetime.now(timezone.utc) if m.is_completed else None
    db.session.commit()
    flash(f"Milestone marked as {'completed' if m.is_completed else 'incomplete'}.", "info")
    return redirect(url_for("projects.detail", project_id=project.id))


@projects_bp.route("/<int:project_id>/milestones/<int:milestone_id>/delete", methods=["POST"])
@login_required
def delete_milestone(project_id, milestone_id):
    project = db.session.get(Project, project_id) or abort(404)
    if not _can_edit_project(project):
        abort(403)

    m = db.session.get(Milestone, milestone_id) or abort(404)
    if m.project_id == project.id:
        db.session.delete(m)
        db.session.commit()
        flash("Milestone removed.", "info")

    return redirect(url_for("projects.detail", project_id=project.id))


# ---------------------------------------------------------------------------
# Project Attachments
# ---------------------------------------------------------------------------
@projects_bp.route("/<int:project_id>/attachments", methods=["POST"])
@login_required
def upload_project_attachment(project_id):
    project = db.session.get(Project, project_id) or abort(404)
    if not project.is_member(current_user):
        abort(403)

    file = request.files.get("attachment")
    if not file or not file.filename:
        flash("Please select a file to upload.", "warning")
        return redirect(url_for("projects.detail", project_id=project.id))

    try:
        save_attachment(file, current_user.id, project_id=project.id)
        flash("Project attachment uploaded.", "success")
    except ValueError as err:
        flash(str(err), "danger")

    return redirect(url_for("projects.detail", project_id=project.id))
