"""
Group system routes:
  create, view, invite, accept/decline invite, remove member,
  transfer leadership, leave group, disband group.
"""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.helpers import (
    notify_group_disbanded,
    notify_group_invite,
    notify_invite_response,
    notify_member_left,
    save_group_image,
)
from app.models import (
    DOMAIN_CHOICES,
    Group,
    GroupMember,
    GroupStatusEnum,
    MemberStatusEnum,
    MentorRequest,
    MentorRequestStatusEnum,
    Project,
    RoleEnum,
    Task,
    User,
)

groups_bp = Blueprint("groups", __name__, url_prefix="/groups")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_group_or_404(group_id: int) -> Group:
    return db.session.get(Group, group_id) or abort(404)


def _is_leader(group: Group) -> bool:
    return current_user.is_admin or group.leader_id == current_user.id


def _accepted_member_ids(group: Group) -> set:
    return {m.student_id for m in group.members if m.status == MemberStatusEnum.ACCEPTED}


# ---------------------------------------------------------------------------
# List / Create
# ---------------------------------------------------------------------------

@groups_bp.route("/")
@login_required
def list_groups():
    if current_user.is_admin:
        groups = Group.query.order_by(Group.created_at.desc()).all()
    else:
        # Groups where user is accepted member (or leader)
        member_group_ids = db.session.query(GroupMember.group_id).filter_by(
            student_id=current_user.id, status=MemberStatusEnum.ACCEPTED
        )
        groups = Group.query.filter(Group.id.in_(member_group_ids)).order_by(Group.created_at.desc()).all()
    return render_template("groups/list.html", groups=groups)


@groups_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_group():
    if current_user.is_mentor:
        abort(403)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        max_members = request.form.get("max_members", "").strip()
        domain = request.form.get("domain", "").strip()
        tech_tags = request.form.get("tech_tags", "").strip()
        image_file = request.files.get("image")

        errors = []
        if not name:
            errors.append("Group name is required.")
        try:
            max_members_int = int(max_members)
            if max_members_int < 1:
                errors.append("Max members must be at least 1.")
        except (ValueError, TypeError):
            errors.append("Max members must be a valid number.")
            max_members_int = 1

        image_url = None
        if image_file and image_file.filename:
            try:
                image_url = save_group_image(image_file)
            except ValueError as exc:
                errors.append(str(exc))

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("groups/form.html", domains=DOMAIN_CHOICES,
                                   name=name, description=description,
                                   max_members=max_members, domain=domain, tech_tags=tech_tags)

        group = Group(
            name=name,
            description=description,
            image_url=image_url,
            max_members=max_members_int,
            domain=domain or None,
            tech_tags=tech_tags or None,
            leader_id=current_user.id,
            status=GroupStatusEnum.FORMING,
        )
        db.session.add(group)
        db.session.flush()

        # Auto-add leader as accepted member
        membership = GroupMember(
            group_id=group.id,
            student_id=current_user.id,
            status=MemberStatusEnum.ACCEPTED,
        )
        db.session.add(membership)
        db.session.commit()

        flash("Group created! You are now the leader.", "success")
        return redirect(url_for("groups.detail", group_id=group.id))

    return render_template("groups/form.html", domains=DOMAIN_CHOICES)


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------

@groups_bp.route("/<int:group_id>")
@login_required
def detail(group_id):
    group = _get_group_or_404(group_id)

    # Access: admin, any accepted member, or the assigned mentor
    accepted_ids = _accepted_member_ids(group)
    is_mentor = group.mentor_id == current_user.id
    if not current_user.is_admin and current_user.id not in accepted_ids and not is_mentor:
        abort(403)

    pending_invite = GroupMember.query.filter_by(
        group_id=group_id, student_id=current_user.id, status=MemberStatusEnum.INVITED
    ).first()

    # For invite form — students not already in the group
    students = (
        User.query.filter_by(role=RoleEnum.STUDENT)
        .filter(~User.id.in_(accepted_ids | {group.leader_id}))
        .all()
        if _is_leader(group) else []
    )

    mentors = User.query.filter_by(role=RoleEnum.MENTOR).all() if _is_leader(group) else []

    pending_request = MentorRequest.query.filter_by(
        group_id=group_id, status=MentorRequestStatusEnum.PENDING
    ).first()

    return render_template(
        "groups/detail.html",
        group=group,
        members=group.members,
        students=students,
        mentors=mentors,
        pending_request=pending_request,
        is_leader=_is_leader(group),
        is_member=current_user.id in accepted_ids,
        pending_invite=pending_invite,
        MemberStatusEnum=MemberStatusEnum,
    )


# ---------------------------------------------------------------------------
# Members list (API-style, used by JS)
# ---------------------------------------------------------------------------

@groups_bp.route("/<int:group_id>/members")
@login_required
def members(group_id):
    group = _get_group_or_404(group_id)
    accepted_ids = _accepted_member_ids(group)
    if not current_user.is_admin and current_user.id not in accepted_ids:
        abort(403)
    data = [
        {"id": m.student_id, "name": m.student.name, "status": m.status}
        for m in group.members
    ]
    return {"members": data}


# ---------------------------------------------------------------------------
# Invite
# ---------------------------------------------------------------------------

@groups_bp.route("/<int:group_id>/invite", methods=["POST"])
@login_required
def invite_member(group_id):
    group = _get_group_or_404(group_id)
    if not _is_leader(group):
        abort(403)

    student_id = request.form.get("student_id")
    if not student_id:
        flash("Select a student to invite.", "danger")
        return redirect(url_for("groups.detail", group_id=group_id))

    student_id = int(student_id)
    student = db.session.get(User, student_id) or abort(404)

    if student.role != RoleEnum.STUDENT:
        flash("Only students can be invited.", "danger")
        return redirect(url_for("groups.detail", group_id=group_id))

    # Check capacity
    if group.accepted_member_count() >= group.max_members:
        flash("Group is already at max capacity.", "danger")
        return redirect(url_for("groups.detail", group_id=group_id))

    # Upsert: re-invite if previously declined or not present
    existing = GroupMember.query.filter_by(group_id=group_id, student_id=student_id).first()
    if existing:
        if existing.status == MemberStatusEnum.ACCEPTED:
            flash(f"{student.name} is already a member.", "warning")
            return redirect(url_for("groups.detail", group_id=group_id))
        if existing.status == MemberStatusEnum.INVITED:
            flash(f"{student.name} already has a pending invite.", "warning")
            return redirect(url_for("groups.detail", group_id=group_id))
        # declined → re-invite (update same row)
        existing.status = MemberStatusEnum.INVITED
        invite = existing
    else:
        invite = GroupMember(group_id=group_id, student_id=student_id, status=MemberStatusEnum.INVITED)
        db.session.add(invite)

    db.session.flush()
    notify_group_invite(student_id, group.name, group.leader.name, invite.id)
    db.session.commit()

    flash(f"Invite sent to {student.name}.", "success")
    return redirect(url_for("groups.detail", group_id=group_id))


# ---------------------------------------------------------------------------
# Accept / Decline invite
# ---------------------------------------------------------------------------

@groups_bp.route("/invites/<int:invite_id>/accept", methods=["POST"])
@login_required
def accept_invite(invite_id):
    invite = db.session.get(GroupMember, invite_id) or abort(404)
    if invite.student_id != current_user.id:
        abort(403)
    if invite.status != MemberStatusEnum.INVITED:
        flash("This invite is no longer valid.", "warning")
        return redirect(url_for("main.dashboard"))

    invite.status = MemberStatusEnum.ACCEPTED
    notify_invite_response(invite.group.leader_id, current_user.name, invite.group.name, accepted=True)
    db.session.commit()

    flash(f"You have joined '{invite.group.name}'!", "success")
    return redirect(url_for("groups.detail", group_id=invite.group_id))


@groups_bp.route("/invites/<int:invite_id>/decline", methods=["POST"])
@login_required
def decline_invite(invite_id):
    invite = db.session.get(GroupMember, invite_id) or abort(404)
    if invite.student_id != current_user.id:
        abort(403)
    if invite.status != MemberStatusEnum.INVITED:
        flash("This invite is no longer valid.", "warning")
        return redirect(url_for("main.dashboard"))

    invite.status = MemberStatusEnum.DECLINED
    notify_invite_response(invite.group.leader_id, current_user.name, invite.group.name, accepted=False)
    db.session.commit()

    flash(f"Invite to '{invite.group.name}' declined.", "info")
    return redirect(url_for("main.dashboard"))


# ---------------------------------------------------------------------------
# Remove member (leader only)
# ---------------------------------------------------------------------------

@groups_bp.route("/<int:group_id>/members/<int:student_id>/remove", methods=["POST"])
@login_required
def remove_member(group_id, student_id):
    group = _get_group_or_404(group_id)
    if not _is_leader(group):
        abort(403)

    if student_id == group.leader_id and not current_user.is_admin:
        flash("Cannot remove the leader via this action.", "danger")
        return redirect(url_for("groups.detail", group_id=group_id))

    membership = GroupMember.query.filter_by(
        group_id=group_id, student_id=student_id, status=MemberStatusEnum.ACCEPTED
    ).first() or abort(404)

    student = membership.student
    _unassign_tasks(group, student_id)

    db.session.delete(membership)
    notify_member_left(student_id, student.name, group.name)
    db.session.commit()

    flash(f"{student.name} has been removed from the group.", "success")
    return redirect(url_for("groups.detail", group_id=group_id))


# ---------------------------------------------------------------------------
# Leave group (self)
# ---------------------------------------------------------------------------

@groups_bp.route("/<int:group_id>/leave", methods=["POST"])
@login_required
def leave_group(group_id):
    group = _get_group_or_404(group_id)

    membership = GroupMember.query.filter_by(
        group_id=group_id, student_id=current_user.id, status=MemberStatusEnum.ACCEPTED
    ).first()
    if not membership:
        flash("You are not a member of this group.", "danger")
        return redirect(url_for("main.dashboard"))

    accepted_members = group.accepted_members()
    is_sole_member = len(accepted_members) == 1

    if group.leader_id == current_user.id:
        if is_sole_member:
            # Sole member leaving = disband
            return _disband_group(group)
        else:
            flash("Transfer leadership before leaving the group.", "danger")
            return redirect(url_for("groups.detail", group_id=group_id))

    # Non-leader leaving
    _unassign_tasks(group, current_user.id)
    db.session.delete(membership)

    # Notify remaining members
    for m in group.accepted_members():
        if m.student_id != current_user.id:
            notify_member_left(m.student_id, current_user.name, group.name)

    db.session.commit()
    flash(f"You have left '{group.name}'.", "info")
    return redirect(url_for("main.dashboard"))


# ---------------------------------------------------------------------------
# Transfer leadership (leader only)
# ---------------------------------------------------------------------------

@groups_bp.route("/<int:group_id>/transfer-leadership", methods=["POST"])
@login_required
def transfer_leadership(group_id):
    group = _get_group_or_404(group_id)
    if not _is_leader(group):
        abort(403)

    new_leader_id = request.form.get("new_leader_id")
    if not new_leader_id:
        flash("Select a new leader.", "danger")
        return redirect(url_for("groups.detail", group_id=group_id))

    new_leader_id = int(new_leader_id)
    if new_leader_id == group.leader_id:
        flash("That member is already the leader.", "warning")
        return redirect(url_for("groups.detail", group_id=group_id))

    membership = GroupMember.query.filter_by(
        group_id=group_id, student_id=new_leader_id, status=MemberStatusEnum.ACCEPTED
    ).first()
    if not membership:
        flash("Selected user is not an accepted group member.", "danger")
        return redirect(url_for("groups.detail", group_id=group_id))

    group.leader_id = new_leader_id
    db.session.commit()

    new_leader = db.session.get(User, new_leader_id)
    flash(f"Leadership transferred to {new_leader.name}.", "success")
    return redirect(url_for("groups.detail", group_id=group_id))


# ---------------------------------------------------------------------------
# Disband / Delete group (leader or admin)
# ---------------------------------------------------------------------------

@groups_bp.route("/<int:group_id>/delete", methods=["POST"])
@login_required
def delete_group(group_id):
    group = _get_group_or_404(group_id)
    if not _is_leader(group):
        abort(403)
    return _disband_group(group)


def _disband_group(group: Group):
    """Notify all members/mentor and cascade delete the group."""
    group_name = group.name

    # Collect recipients before deletion
    recipient_ids = {m.student_id for m in group.members}
    if group.mentor_id:
        recipient_ids.add(group.mentor_id)
    recipient_ids.discard(current_user.id)  # don't notify self

    # Cascade: delete linked projects (tasks/comments cascade via DB)
    for project in group.projects.all():
        db.session.delete(project)

    db.session.delete(group)
    db.session.flush()

    for rid in recipient_ids:
        notify_group_disbanded(rid, group_name, current_user.name)

    db.session.commit()
    flash(f"Group '{group_name}' has been disbanded.", "success")
    return redirect(url_for("groups.list_groups"))


# ---------------------------------------------------------------------------
# Internal helper: unassign tasks for a member leaving/removed
# ---------------------------------------------------------------------------

def _unassign_tasks(group: Group, student_id: int):
    """Set assignee_id=None for all tasks in the group's projects assigned to this student."""
    for project in group.projects.all():
        for task in project.tasks.filter_by(assignee_id=student_id).all():
            task.assignee_id = None
