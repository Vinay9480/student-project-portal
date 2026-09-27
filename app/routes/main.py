"""Main / dashboard routes."""
from datetime import date
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.extensions import db
from app.models import (
    Group,
    GroupMember,
    MemberStatusEnum,
    Notification,
    Project,
    ProjectStatusEnum,
    Task,
    TaskPriorityEnum,
    TaskStatusEnum,
    User,
)

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("main/index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    # Projects the user can see
    if current_user.is_admin:
        projects = Project.query.order_by(Project.created_at.desc()).limit(12).all()
        all_visible_projects = Project.query.all()
    elif current_user.is_mentor:
        projects = Project.query.filter(
            Project.group.has(Group.mentor_id == current_user.id)
        ).order_by(Project.created_at.desc()).limit(12).all()
        all_visible_projects = projects
    else:
        member_group_ids = db.session.query(GroupMember.group_id).filter_by(
            student_id=current_user.id, status=MemberStatusEnum.ACCEPTED
        ).subquery()
        projects = Project.query.filter(
            or_(
                Project.owner_id == current_user.id,
                Project.group_id.in_(member_group_ids),
            )
        ).order_by(Project.created_at.desc()).limit(12).all()
        all_visible_projects = projects

    # Unread notification count
    unread_count = Notification.query.filter_by(
        user_id=current_user.id, read=False
    ).count()

    # Tasks assigned to current user
    my_tasks = Task.query.filter(
        Task.assignee_id == current_user.id,
        Task.status != TaskStatusEnum.DONE,
    ).order_by(Task.due_date.asc().nullslast()).limit(10).all()

    # My groups
    my_groups = current_user.accepted_groups()

    # Collect project IDs for analytics
    proj_ids = [p.id for p in all_visible_projects]

    if proj_ids:
        all_tasks = Task.query.filter(Task.project_id.in_(proj_ids)).all()
    else:
        all_tasks = []

    todo_count = sum(1 for t in all_tasks if t.status == TaskStatusEnum.TODO)
    in_prog_count = sum(1 for t in all_tasks if t.status == TaskStatusEnum.IN_PROGRESS)
    done_count = sum(1 for t in all_tasks if t.status == TaskStatusEnum.DONE)
    urgent_count = sum(1 for t in all_tasks if t.priority == TaskPriorityEnum.URGENT and t.status != TaskStatusEnum.DONE)
    overdue_count = sum(1 for t in all_tasks if t.is_overdue)

    priority_stats = {
        "urgent": sum(1 for t in all_tasks if t.priority == TaskPriorityEnum.URGENT),
        "high": sum(1 for t in all_tasks if t.priority == TaskPriorityEnum.HIGH),
        "medium": sum(1 for t in all_tasks if t.priority == TaskPriorityEnum.MEDIUM),
        "low": sum(1 for t in all_tasks if t.priority == TaskPriorityEnum.LOW),
    }

    total_tasks = len(all_tasks)
    overall_progress = round(done_count / total_tasks * 100, 1) if total_tasks > 0 else 0

    return render_template(
        "main/dashboard.html",
        projects=projects,
        unread_count=unread_count,
        my_tasks=my_tasks,
        my_groups=my_groups,
        todo_count=todo_count,
        in_prog_count=in_prog_count,
        done_count=done_count,
        urgent_count=urgent_count,
        overdue_count=overdue_count,
        total_tasks=total_tasks,
        priority_stats=priority_stats,
        overall_progress=overall_progress,
        today=date.today(),
    )


@main_bp.route("/api/quick-search")
@login_required
def quick_search():
    q = request.args.get("q", "").strip()
    if not q or len(q) < 2:
        return jsonify({"results": []})

    results = []

    # Search Projects
    projects = Project.query.filter(
        Project.name.ilike(f"%{q}%") | Project.description.ilike(f"%{q}%")
    ).limit(5).all()
    for p in projects:
        if p.is_member(current_user):
            results.append({
                "type": "Project",
                "icon": "📁",
                "title": p.name,
                "subtitle": f"{p.progress()}% completed · {p.group.name if p.group else 'Personal'}",
                "url": url_for("projects.detail", project_id=p.id),
            })

    # Search Tasks
    tasks = Task.query.filter(
        Task.title.ilike(f"%{q}%") | Task.description.ilike(f"%{q}%")
    ).limit(6).all()
    for t in tasks:
        if t.project.is_member(current_user):
            results.append({
                "type": "Task",
                "icon": "✅",
                "title": t.title,
                "subtitle": f"In {t.project.name} · Priority: {t.priority.upper()}",
                "url": url_for("tasks.task_detail", task_id=t.id),
            })

    # Search Groups
    groups = Group.query.filter(
        Group.name.ilike(f"%{q}%") | Group.domain.ilike(f"%{q}%") | Group.tech_tags.ilike(f"%{q}%")
    ).limit(4).all()
    for g in groups:
        results.append({
            "type": "Group",
            "icon": "👥",
            "title": g.name,
            "subtitle": f"{g.domain or 'General'} · {g.accepted_member_count()}/{g.max_members} members",
            "url": url_for("groups.detail", group_id=g.id),
        })

    return jsonify({"results": results})
