"""Mentor request routes: send, accept, reject."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.helpers import notify_mentor_decision, notify_mentor_request
from app.models import (
    Group,
    GroupMember,
    GroupStatusEnum,
    MemberStatusEnum,
    MentorRequest,
    MentorRequestStatusEnum,
    RoleEnum,
    User,
)

mentors_bp = Blueprint("mentors", __name__)


# ---------------------------------------------------------------------------
# Send mentor request (leader only)
# ---------------------------------------------------------------------------

@mentors_bp.route("/groups/<int:group_id>/mentor-request", methods=["POST"])
@login_required
def send_mentor_request(group_id):
    group = db.session.get(Group, group_id) or abort(404)

    if not (current_user.is_admin or group.leader_id == current_user.id):
        abort(403)

    # Must have at least 1 accepted member (beyond the leader)
    accepted_count = group.accepted_member_count()
    if accepted_count < 1:
        flash("Your group needs at least one accepted member before requesting a mentor.", "danger")
        return redirect(url_for("groups.detail", group_id=group_id))

    # Block if a pending request already exists
    pending = MentorRequest.query.filter_by(
        group_id=group_id, status=MentorRequestStatusEnum.PENDING
    ).first()
    if pending:
        flash("A mentor request is already pending for this group.", "warning")
        return redirect(url_for("groups.detail", group_id=group_id))

    mentor_id = request.form.get("mentor_id")
    if not mentor_id:
        flash("Select a mentor to request.", "danger")
        return redirect(url_for("groups.detail", group_id=group_id))

    mentor_id = int(mentor_id)
    mentor = db.session.get(User, mentor_id) or abort(404)
    if mentor.role != RoleEnum.MENTOR:
        flash("Selected user is not a mentor.", "danger")
        return redirect(url_for("groups.detail", group_id=group_id))

    mr = MentorRequest(
        group_id=group_id,
        mentor_id=mentor_id,
        status=MentorRequestStatusEnum.PENDING,
    )
    db.session.add(mr)
    db.session.flush()

    member_names = [m.student.name for m in group.members if m.status == MemberStatusEnum.ACCEPTED]
    notify_mentor_request(
        mentor_id=mentor_id,
        group_name=group.name,
        leader_name=group.leader.name,
        members=member_names,
        domain=group.domain or "",
        tech_tags=group.tech_tags or "",
        request_id=mr.id,
    )
    db.session.commit()

    flash(f"Mentor request sent to {mentor.name}.", "success")
    return redirect(url_for("groups.detail", group_id=group_id))


# ---------------------------------------------------------------------------
# Accept mentor request (mentor or admin)
# ---------------------------------------------------------------------------

@mentors_bp.route("/mentor-requests/<int:request_id>/accept", methods=["POST"])
@login_required
def accept_mentor_request(request_id):
    mr = db.session.get(MentorRequest, request_id) or abort(404)

    if not (current_user.is_admin or mr.mentor_id == current_user.id):
        abort(403)

    if mr.status != MentorRequestStatusEnum.PENDING:
        flash("This request is no longer pending.", "warning")
        return redirect(url_for("main.dashboard"))

    mr.status = MentorRequestStatusEnum.ACCEPTED
    group = mr.group
    group.mentor_id = mr.mentor_id
    group.status = GroupStatusEnum.ACTIVE

    mentor = db.session.get(User, mr.mentor_id)
    for member in group.members:
        if member.status == MemberStatusEnum.ACCEPTED:
            notify_mentor_decision(
                member.student_id, group.name, mentor.name, accepted=True
            )

    db.session.commit()
    flash(f"You are now mentoring '{group.name}'.", "success")
    return redirect(url_for("groups.detail", group_id=group.id))


# ---------------------------------------------------------------------------
# Reject mentor request (mentor or admin)
# ---------------------------------------------------------------------------

@mentors_bp.route("/mentor-requests/<int:request_id>/reject", methods=["POST"])
@login_required
def reject_mentor_request(request_id):
    mr = db.session.get(MentorRequest, request_id) or abort(404)

    if not (current_user.is_admin or mr.mentor_id == current_user.id):
        abort(403)

    if mr.status != MentorRequestStatusEnum.PENDING:
        flash("This request is no longer pending.", "warning")
        return redirect(url_for("main.dashboard"))

    mr.status = MentorRequestStatusEnum.REJECTED
    group = mr.group
    mentor = db.session.get(User, mr.mentor_id)

    # Notify leader only (so they can request a different mentor)
    notify_mentor_decision(group.leader_id, group.name, mentor.name, accepted=False)

    db.session.commit()
    flash("Mentor request rejected.", "info")
    return redirect(url_for("main.dashboard"))


# ---------------------------------------------------------------------------
# Pending requests view (for mentors)
# ---------------------------------------------------------------------------

@mentors_bp.route("/mentor-requests")
@login_required
def pending_requests():
    if current_user.is_student:
        abort(403)
    if current_user.is_admin:
        requests = MentorRequest.query.filter_by(
            status=MentorRequestStatusEnum.PENDING
        ).order_by(MentorRequest.requested_at.desc()).all()
    else:
        requests = MentorRequest.query.filter_by(
            mentor_id=current_user.id, status=MentorRequestStatusEnum.PENDING
        ).order_by(MentorRequest.requested_at.desc()).all()
    return render_template("mentors/requests.html", requests=requests)
