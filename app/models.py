"""
Database models for the Student Project Management Portal.
All tables from the project plan Section 4.
"""
import json
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


# ---------------------------------------------------------------------------
# Enums (stored as strings in SQLite/Postgres)
# ---------------------------------------------------------------------------
class RoleEnum:
    STUDENT = "student"
    MENTOR = "mentor"
    ADMIN = "admin"
    ALL = [STUDENT, MENTOR, ADMIN]


class TaskStatusEnum:
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    ALL = [TODO, IN_PROGRESS, DONE]


class TaskPriorityEnum:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    ALL = [LOW, MEDIUM, HIGH, URGENT]


class ProjectStatusEnum:
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    ALL = [PLANNING, IN_PROGRESS, COMPLETED, ON_HOLD]


class GroupStatusEnum:
    FORMING = "forming"
    ACTIVE = "active"
    COMPLETED = "completed"
    ALL = [FORMING, ACTIVE, COMPLETED]


class MemberStatusEnum:
    INVITED = "invited"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    ALL = [INVITED, ACCEPTED, DECLINED]


class MentorRequestStatusEnum:
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ALL = [PENDING, ACCEPTED, REJECTED]


class NotificationTypeEnum:
    GROUP_INVITE = "group_invite"
    INVITE_RESPONSE = "invite_response"
    MEMBER_LEFT = "member_left"
    MENTOR_REQUEST = "mentor_request"
    MENTOR_DECISION = "mentor_decision"
    GROUP_DISBANDED = "group_disbanded"
    ALL = [GROUP_INVITE, INVITE_RESPONSE, MEMBER_LEFT, MENTOR_REQUEST, MENTOR_DECISION, GROUP_DISBANDED]


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), nullable=False, default=RoleEnum.STUDENT)
    avatar_url = db.Column(db.String(300), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    github_url = db.Column(db.String(200), nullable=True)
    linkedin_url = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    owned_projects = db.relationship("Project", back_populates="owner", foreign_keys="Project.owner_id", lazy="dynamic")
    led_groups = db.relationship("Group", back_populates="leader", foreign_keys="Group.leader_id", lazy="dynamic")
    mentored_groups = db.relationship("Group", back_populates="mentor", foreign_keys="Group.mentor_id", lazy="dynamic")
    group_memberships = db.relationship("GroupMember", back_populates="student", foreign_keys="GroupMember.student_id", lazy="dynamic")
    assigned_tasks = db.relationship("Task", back_populates="assignee", foreign_keys="Task.assignee_id", lazy="dynamic")
    comments = db.relationship("Comment", back_populates="author", lazy="dynamic")
    notifications = db.relationship("Notification", back_populates="recipient", lazy="dynamic")
    activity_logs = db.relationship("ActivityLog", back_populates="actor", lazy="dynamic")
    mentor_requests_received = db.relationship("MentorRequest", back_populates="mentor", foreign_keys="MentorRequest.mentor_id", lazy="dynamic")
    uploaded_attachments = db.relationship("Attachment", back_populates="uploader", lazy="dynamic")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_student(self):
        return self.role == RoleEnum.STUDENT

    @property
    def is_mentor(self):
        return self.role == RoleEnum.MENTOR

    @property
    def is_admin(self):
        return self.role == RoleEnum.ADMIN

    @property
    def initials(self):
        parts = (self.name or "").strip().split()
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    def accepted_groups(self):
        """Return all groups this user is an accepted member or mentor of."""
        if self.is_mentor:
            return self.mentored_groups.all()
        return (
            db.session.query(Group)
            .join(GroupMember, GroupMember.group_id == Group.id)
            .filter(
                GroupMember.student_id == self.id,
                GroupMember.status == MemberStatusEnum.ACCEPTED,
            )
            .all()
        )

    def accepted_group_count(self):
        if self.is_mentor:
            return self.mentored_groups.count()
        return (
            GroupMember.query
            .filter_by(student_id=self.id, status=MemberStatusEnum.ACCEPTED)
            .count()
        )

    def __repr__(self):
        return f"<User {self.id} {self.email} [{self.role}]>"


# ---------------------------------------------------------------------------
# Group
# ---------------------------------------------------------------------------
DOMAIN_CHOICES = [
    "Web Dev", "ML/AI", "Systems", "Mobile", "Data Science",
    "Cybersecurity", "Game Dev", "DevOps", "Other",
]


class Group(db.Model):
    __tablename__ = "group"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(300), nullable=True)
    max_members = db.Column(db.Integer, nullable=False)
    domain = db.Column(db.String(50), nullable=True)
    tech_tags = db.Column(db.String(500), nullable=True)   # comma-separated
    leader_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    mentor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    status = db.Column(db.String(15), nullable=False, default=GroupStatusEnum.FORMING)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    leader = db.relationship("User", back_populates="led_groups", foreign_keys=[leader_id])
    mentor = db.relationship("User", back_populates="mentored_groups", foreign_keys=[mentor_id])
    members = db.relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    projects = db.relationship("Project", back_populates="group", lazy="dynamic")
    mentor_requests = db.relationship("MentorRequest", back_populates="group", cascade="all, delete-orphan")

    def accepted_member_count(self):
        return sum(1 for m in self.members if m.status == MemberStatusEnum.ACCEPTED)

    def accepted_members(self):
        return [m for m in self.members if m.status == MemberStatusEnum.ACCEPTED]

    def get_tech_tags_list(self):
        if not self.tech_tags:
            return []
        return [t.strip() for t in self.tech_tags.split(",") if t.strip()]

    def __repr__(self):
        return f"<Group {self.id} '{self.name}'>"


# ---------------------------------------------------------------------------
# GroupMember
# ---------------------------------------------------------------------------
class GroupMember(db.Model):
    __tablename__ = "group_member"
    __table_args__ = (
        db.UniqueConstraint("group_id", "student_id", name="uq_group_member"),
    )

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id", ondelete="CASCADE"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(10), nullable=False, default=MemberStatusEnum.INVITED)
    invited_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    group = db.relationship("Group", back_populates="members")
    student = db.relationship("User", back_populates="group_memberships", foreign_keys=[student_id])

    def __repr__(self):
        return f"<GroupMember group={self.group_id} student={self.student_id} status={self.status}>"


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------
class Project(db.Model):
    __tablename__ = "project"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default=ProjectStatusEnum.IN_PROGRESS)
    github_repo = db.Column(db.String(255), nullable=True)
    live_demo_url = db.Column(db.String(255), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    owner = db.relationship("User", back_populates="owned_projects", foreign_keys=[owner_id])
    group = db.relationship("Group", back_populates="projects", foreign_keys=[group_id])
    tasks = db.relationship("Task", back_populates="project", cascade="all, delete-orphan", lazy="dynamic")
    milestones = db.relationship("Milestone", back_populates="project", cascade="all, delete-orphan", lazy="dynamic")
    attachments = db.relationship("Attachment", back_populates="project", cascade="all, delete-orphan", lazy="dynamic")
    comments = db.relationship(
        "Comment",
        primaryjoin="and_(Comment.project_id == Project.id, Comment.task_id == None)",
        foreign_keys="Comment.project_id",
        lazy="dynamic",
        overlaps="task,project_comments",
    )

    def is_member(self, user: "User") -> bool:
        """Check if user has access to this project."""
        if user.is_admin:
            return True
        if self.owner_id == user.id:
            return True
        if self.group_id:
            # Access via group membership
            membership = GroupMember.query.filter_by(
                group_id=self.group_id,
                student_id=user.id,
                status=MemberStatusEnum.ACCEPTED,
            ).first()
            if membership:
                return True
            # Assigned mentor also has access
            if self.group and self.group.mentor_id == user.id:
                return True
        return False

    def progress(self):
        total = self.tasks.count()
        if total == 0:
            return 0
        done = self.tasks.filter_by(status=TaskStatusEnum.DONE).count()
        return round(done / total * 100, 1)

    def __repr__(self):
        return f"<Project {self.id} '{self.name}'>"


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------
class Task(db.Model):
    __tablename__ = "task"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(15), nullable=False, default=TaskStatusEnum.TODO)
    priority = db.Column(db.String(10), nullable=False, default=TaskPriorityEnum.MEDIUM)
    tags = db.Column(db.String(300), nullable=True)
    order = db.Column(db.Integer, nullable=False, default=0)
    assignee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    project = db.relationship("Project", back_populates="tasks")
    assignee = db.relationship("User", back_populates="assigned_tasks", foreign_keys=[assignee_id])
    comments = db.relationship("Comment", back_populates="task", cascade="all, delete-orphan",
                               primaryjoin="Comment.task_id == Task.id", foreign_keys="Comment.task_id")
    activity_logs = db.relationship("ActivityLog", back_populates="task", cascade="all, delete-orphan")
    attachments = db.relationship("Attachment", back_populates="task", cascade="all, delete-orphan", lazy="dynamic")

    @property
    def is_overdue(self):
        if self.due_date and self.status != TaskStatusEnum.DONE:
            return self.due_date < datetime.now(timezone.utc).date()
        return False

    def get_tags_list(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    def __repr__(self):
        return f"<Task {self.id} '{self.title}' [{self.status}]>"


# ---------------------------------------------------------------------------
# Comment
# ---------------------------------------------------------------------------
class Comment(db.Model):
    __tablename__ = "comment"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id", ondelete="CASCADE"), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id", ondelete="CASCADE"), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    task = db.relationship("Task", back_populates="comments", foreign_keys=[task_id], overlaps="project_comments")
    project = db.relationship("Project", foreign_keys=[project_id], overlaps="comments,project_comments")
    author = db.relationship("User", back_populates="comments")

    def __repr__(self):
        return f"<Comment {self.id} by user={self.user_id}>"


# ---------------------------------------------------------------------------
# MentorRequest
# ---------------------------------------------------------------------------
class MentorRequest(db.Model):
    __tablename__ = "mentor_request"

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id", ondelete="CASCADE"), nullable=False)
    mentor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(10), nullable=False, default=MentorRequestStatusEnum.PENDING)
    requested_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    group = db.relationship("Group", back_populates="mentor_requests")
    mentor = db.relationship("User", back_populates="mentor_requests_received", foreign_keys=[mentor_id])

    def __repr__(self):
        return f"<MentorRequest group={self.group_id} mentor={self.mentor_id} status={self.status}>"


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------
class Notification(db.Model):
    __tablename__ = "notification"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    type = db.Column(db.String(30), nullable=False)
    payload = db.Column(db.Text, nullable=True)   # JSON blob
    read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    recipient = db.relationship("User", back_populates="notifications")

    def get_payload(self):
        if self.payload:
            try:
                return json.loads(self.payload)
            except (ValueError, TypeError):
                return {}
        return {}

    def set_payload(self, data: dict):
        self.payload = json.dumps(data)

    def __repr__(self):
        return f"<Notification {self.id} user={self.user_id} type={self.type} read={self.read}>"


# ---------------------------------------------------------------------------
# ActivityLog  (audit trail for task status changes)
# ---------------------------------------------------------------------------
class ActivityLog(db.Model):
    __tablename__ = "activity_log"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id", ondelete="CASCADE"), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    field_changed = db.Column(db.String(50), nullable=False)   # e.g. "status"
    old_value = db.Column(db.String(100), nullable=True)
    new_value = db.Column(db.String(100), nullable=True)
    changed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    task = db.relationship("Task", back_populates="activity_logs")
    actor = db.relationship("User", back_populates="activity_logs")

    def __repr__(self):
        return f"<ActivityLog task={self.task_id} by={self.actor_id} {self.field_changed}: {self.old_value}→{self.new_value}>"


# ---------------------------------------------------------------------------
# Milestone
# ---------------------------------------------------------------------------
class Milestone(db.Model):
    __tablename__ = "milestone"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    is_completed = db.Column(db.Boolean, nullable=False, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    project = db.relationship("Project", back_populates="milestones")

    def __repr__(self):
        return f"<Milestone {self.id} '{self.title}' project={self.project_id}>"


# ---------------------------------------------------------------------------
# Attachment
# ---------------------------------------------------------------------------
class Attachment(db.Model):
    __tablename__ = "attachment"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False, default=0)
    mime_type = db.Column(db.String(100), nullable=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id", ondelete="CASCADE"), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id", ondelete="CASCADE"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    uploader = db.relationship("User", back_populates="uploaded_attachments", foreign_keys=[uploader_id])
    task = db.relationship("Task", back_populates="attachments")
    project = db.relationship("Project", back_populates="attachments")

    @property
    def formatted_size(self):
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{round(self.file_size / 1024, 1)} KB"
        return f"{round(self.file_size / (1024 * 1024), 1)} MB"

    @property
    def extension(self):
        if "." in self.original_name:
            return self.original_name.rsplit(".", 1)[1].lower()
        return ""

    def __repr__(self):
        return f"<Attachment {self.id} '{self.original_name}'>"
