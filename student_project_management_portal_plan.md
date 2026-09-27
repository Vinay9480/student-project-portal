# Student Project Management Portal — Full Project Plan

## 1. Project Overview

**Level:** 1–2
**Goal:** Build a web application where users can create projects, form student groups, assign tasks, update status, request mentor guidance, and view progress.

**Objective:** A portfolio-ready, full-stack web application demonstrating frontend, backend, database, and API design skills. Students can form teams (groups), manage projects and tasks within those teams, and request a mentor to guide their group. Mentors and admins have appropriately scoped oversight.

**Scope limitations (keep v1 simple):**
- Single organization only.
- No payments, complex chat, or microservices until the basic portal is stable.
- Group "join requests" (open visibility) are NOT included in v1 — groups are invite-only, leader-controlled.
- Password reset / "forgot password" flow is explicitly deferred (see Section 9).

---

## 2. Tech Stack

- **Backend:** Python, Flask, Flask-SQLAlchemy
- **Auth:** Flask-Login (session-based) with password hashing (werkzeug/bcrypt)
- **Database:** SQLite (dev), structured so it can migrate to PostgreSQL later
- **Frontend:** Flask + Jinja2 templates, plain HTML/CSS/JavaScript (no frontend framework)
- **Version control:** Git
- **Deployment target:** Render or Railway (SQLite as single file works at this scale)
- **Dev environment note:** Developed on Windows; use PowerShell (`Invoke-RestMethod`) for manual API testing, not curl.

---

## 3. Roles & Permissions

Three roles: **Student**, **Mentor**, **Admin**. Organization-realistic permission model (chosen deliberately for the richest test matrix):

| Action | Student | Mentor | Admin |
|---|---|---|---|
| Create a project | Own projects only | ❌ | ✅ any |
| Edit/delete a project | Only if owner | ❌ | ✅ any |
| View a project | If accepted member of the linked group, or owner | If assigned as that group's mentor | ✅ any |
| Create/manage tasks | Within own project/group | ❌ (comment only) | ✅ any |
| Change task status | If assignee or project owner | ❌ | ✅ any |
| Comment (task or project) | ✅ if member | ✅ if assigned mentor | ✅ any |
| Create a group | ✅ (becomes leader) | ❌ | ✅ (admin oversight) |
| Invite group members | Leader only | ❌ | ✅ |
| Remove member / transfer leadership | Leader only | ❌ | ✅ |
| Leave a group | ✅ (any member, with rule — see 5.5) | ❌ | ✅ |
| Delete/disband a group | Leader only | ❌ | ✅ |
| Send mentor request | Leader only | ❌ | ✅ |
| Accept/Reject mentor request | ❌ | ✅ (the requested mentor) | ✅ |
| Manage users | ❌ | ❌ | ✅ full CRUD |

**Security rule:** Role field can never be self-escalated via API — role changes are admin-only, enforced server-side regardless of client payload.

---

## 4. Database Schema

### 4.1 Core tables

```
User
- id (PK)
- name
- email (unique)
- password_hash
- role (enum: student / mentor / admin)
- created_at

Project
- id (PK)
- name
- description
- owner_id (FK User) -- creator; kept for projects made before a group exists
- group_id (FK Group, nullable) -- once set, this is the authoritative access-control link
- created_at

-- NOTE: There is no separate ProjectMember table. Once a Project has a group_id,
-- who can access it is derived entirely from that Group's GroupMember rows
-- (status='accepted') plus Group.mentor_id. This avoids the two tables
-- disagreeing about who's on the team. A project with no group_id (rare,
-- e.g. an admin-created solo project) falls back to owner_id-only access.

Task
- id (PK)
- project_id (FK Project)
- title
- description
- status (enum: todo / in_progress / done)
- assignee_id (FK User, nullable)
- due_date
- created_at

Comment
- id (PK)
- task_id (FK Task, nullable)
- project_id (FK Project, nullable)   -- exactly ONE of task_id / project_id is set
- user_id (FK User)
- text
- created_at
```

### 4.2 Group & Mentor tables

```
Group
- id (PK)
- name (required)
- description (optional)
- image_url (optional)
- max_members (required, integer, >= 1)
- domain (e.g. Web Dev, ML/AI, Systems — dropdown)
- tech_tags (free text / multi-select)
- leader_id (FK User)
- mentor_id (FK User, nullable) -- set once a mentor request is accepted
- status (enum: forming / active / completed)
- created_at

GroupMember
- id (PK)
- group_id (FK Group)
- student_id (FK User)
- status (enum: invited / accepted / declined)
- invited_at
- UNIQUE constraint on (group_id, student_id) -- no duplicate invites

MentorRequest
- id (PK)
- group_id (FK Group)
- mentor_id (FK User)
- status (enum: pending / accepted / rejected)
- requested_at
- UNIQUE constraint: only one 'pending' request per group at a time

Notification
- id (PK)
- user_id (FK User) -- recipient
- type (enum: group_invite / invite_response / member_left / mentor_request / mentor_decision)
- payload (JSON: group name, leader name, mentor name, student name, etc.)
- read (boolean, default false)
- created_at
```

---

## 5. Feature Workflows

### 5.1 Group Creation (Student → Leader)
1. Student fills group creation form:
   - Group name (required)
   - Description (optional)
   - Group image upload (optional)
   - Max members (required — leader sets the cap, e.g. 4)
   - Domain/category (dropdown)
   - Tech stack tags
2. `Group` row created; creator becomes `leader_id`.
3. Leader is auto-added to `GroupMember` with `status='accepted'`.
4. Group `status = 'forming'`.

### 5.2 Inviting Members
1. **Only the leader** can send invites.
2. Members can informally suggest a name to the leader (simple UI prompt/message to leader — not a separate DB-tracked workflow).
3. Invite blocked if `accepted` member count already equals `max_members`.
4. On invite: `GroupMember(status='invited')` created + a `Notification(type='group_invite')` sent to the invitee, showing **group name** and **leader name**.
5. Invitee sees notification with **Accept / Decline** buttons.
   - Accept → `GroupMember.status = 'accepted'`.
   - Decline → `GroupMember.status = 'declined'` (leader may re-invite later — this updates the same row, no duplicate).
6. **Either way, the leader receives a `Notification(type='invite_response')`** showing the invitee's name and whether they accepted or declined, so the leader isn't left checking manually.

### 5.3 Multi-Group Membership
- A student **may join multiple groups** (no hard cap on number of groups).
- Any profile view (by another student or a mentor) must display **"Groups joined: N"** with the list of group names — visibility is required, not hidden.
- Only `accepted` memberships count toward this total (not pending invites).

### 5.4 Leader Controls
- **Remove a member:** frees a slot in `max_members`; that member's tasks in the group's project become **unassigned** (manual reassignment by the leader — no auto-reassignment). The removed member receives a `Notification(type='member_left')`.
- **Transfer leadership:** `Group.leader_id` updates to another `accepted` member; the old leader remains a regular member unless they separately leave. The new leader gains invite/mentor-request/removal rights; the old leader loses them immediately.

### 5.5 Leaving a Group
- Any accepted member (including the leader) may leave voluntarily.
- **If the leaving member is the leader and other accepted members remain:** they must transfer leadership first (Section 5.4) — the system blocks a leader from leaving while still holding the role.
- **If the leader is the sole remaining member:** leaving is treated as disbanding the group (Section 5.6).
- When any non-leader member leaves, remaining leader/members get a `Notification(type='member_left')`, and that member's tasks are unassigned for manual reassignment, same as a removal.

### 5.6 Group Deletion / Disbanding
- **Only the leader** (or an admin) can delete/disband a group.
- On deletion: the group's `GroupMember`, `MentorRequest`, and `Notification` records tied to it are cleaned up; the linked `Project` and its `Task`/`Comment` records are also removed, since they exist only in the context of that group.
- A confirmation step is required in the UI before deletion, since this is destructive and cascades.
- All former members and the assigned mentor (if any) receive a notification that the group was disbanded.

### 5.7 Mentor Request
1. **Only the leader** can send a mentor request (requires ≥1 accepted member in the group).
2. Blocked if a `MentorRequest` for this group is already `pending`.
3. Mentor receives `Notification(type='mentor_request')` showing group name, leader name, member list, domain, and tech tags.
4. Mentor responds Accept/Reject:
   - Accept → `Group.mentor_id` set, `MentorRequest.status='accepted'`, group `status='active'`, all members get `Notification(type='mentor_decision')`.
   - Reject → `MentorRequest.status='rejected'`; leader may send a new request to a different mentor.

### 5.8 Task Management
- Tasks created under a project by the owner (or via the linked group's project).
- Assigned to a project/group member only (validation: assignee must be a member).
- Status: `todo` → `in_progress` → `done`, changeable by assignee or project owner.
- Overdue tasks (`due_date` passed and status != done) are flagged in the UI.
- Every status change is written to an activity/audit trail (timestamp, who, what changed) for viva demonstration purposes.

### 5.9 Comments
- Comments can be posted at **task level** or **project level** (never both on the same row — exactly one of `task_id`/`project_id` is populated).
- Only project/group members (and the assigned mentor) can comment.
- Empty comments rejected server-side.

### 5.10 Progress Chart
- Formula: `progress % = (tasks with status='done') / (total tasks in project) * 100`
- Project with zero tasks displays 0% (must not divide by zero).
- Chart re-renders whenever a task's status changes (Chart.js or a simple CSS progress bar).

### 5.11 Search & Filters
- Combinable query parameters on task listing endpoint, e.g.:
  `GET /tasks?status=in_progress&q=login&assignee=3`
- Empty search term returns all tasks (no filter applied).
- No matches → empty array, not an error.
- All queries parameterized (SQLAlchemy ORM) to prevent SQL injection.

---

## 6. API Endpoints (high-level)

```
Auth
POST   /register
POST   /login
POST   /logout

Users
GET    /users/<id>              -- profile view, includes groups joined count/list
PATCH  /users/<id>               -- admin only, role changes

Projects
GET    /projects
POST   /projects
GET    /projects/<id>
PUT    /projects/<id>
DELETE /projects/<id>

Tasks
GET    /projects/<id>/tasks?status=&q=&assignee=
POST   /projects/<id>/tasks
PUT    /tasks/<id>
DELETE /tasks/<id>

Comments
POST   /tasks/<id>/comments
POST   /projects/<id>/comments
GET    /tasks/<id>/comments
GET    /projects/<id>/comments

Groups
POST   /groups                       -- create (leader)
GET    /groups/<id>
POST   /groups/<id>/invite           -- leader only, body: student_id
POST   /groups/<id>/members/<sid>/remove   -- leader only
POST   /groups/<id>/leave            -- self, subject to 5.5 rules
POST   /groups/<id>/transfer-leadership    -- leader only, body: new_leader_id
DELETE /groups/<id>                  -- leader only, disband (5.6)
GET    /groups/<id>/members

Group Invites (student side)
POST   /invites/<id>/accept
POST   /invites/<id>/decline

Mentor Requests
POST   /groups/<id>/mentor-request   -- leader only, body: mentor_id
POST   /mentor-requests/<id>/accept  -- mentor only
POST   /mentor-requests/<id>/reject  -- mentor only

Notifications
GET    /notifications
POST   /notifications/<id>/read

Progress
GET    /projects/<id>/progress
```

---

## 7. Milestones (Build Order)

1. **DB & Models** — all tables above, migrations set up.
2. **Authentication** — register/login/logout, password hashing, role field.
3. **Role Permissions** — middleware/decorators enforcing the permission table in Section 3.
4. **Project CRUD** — create/edit/delete/list, ownership checks.
5. **Group System** — creation form, invite flow, accept/decline (+ leader notified of response), multi-group profile display, leader controls (remove/transfer), leaving a group, group deletion/disbanding.
6. **Mentor Request System** — request, accept/reject, group status transition to `active`.
7. **Task Board** — CRUD, assignment validated against membership, status transitions, overdue flagging, activity log.
8. **Search & Filters** — combinable query params.
9. **Comments** — task-level and project-level.
10. **Progress Chart** — computed percentage, live update.
11. **Validation & Error Handling** — consistent JSON error format, XSS escaping, server-side validation as source of truth.
12. **Deployment** — requirements.txt, .env for secrets, README with setup + full API route list, deploy to Render/Railway.

---

## 8. Full Test Case List

### DB & Models
- Creating a user with a duplicate email fails.
- Deleting a project correctly cascades or blocks task deletion (decide and enforce consistently).
- Task status field only accepts enum values (`todo`/`in_progress`/`done`).
- A project with no `group_id` correctly falls back to owner-only access (no group-derived membership).

### Authentication
- Login with wrong password is rejected.
- Expired/invalid session blocks access to protected routes.
- Role cannot be self-escalated via API payload (e.g. student POSTing `role: admin` is ignored/rejected).

### Role Permissions
- Student hitting an admin-only endpoint receives 403.
- Mentor cannot delete a project.
- Admin actions are logged.

### Project CRUD
- Non-member cannot view a private project.
- Deleting a project the user doesn't own is blocked.
- Project name validation (non-empty, max length enforced).

### Group System
- Group creation rejects missing name or `max_members < 1`.
- Leader is auto-added as an `accepted` member on creation.
- Invited student who previously declined can be re-invited without a duplicate row (unique constraint honored via update, not insert).
- Inviting the same student twice while `invited`/`accepted` does not create duplicate `GroupMember` rows.
- Invite blocked once `accepted` member count equals `max_members`.
- Leader receives a notification when an invitee accepts or declines.
- Profile "Groups joined" count only includes `accepted` memberships, not pending invites.
- A student can be an accepted member of multiple groups simultaneously, and this is visible to any viewer.
- Removing a member frees a slot, unassigns their tasks (leader must manually reassign — verify no auto-reassignment occurs), and notifies the removed member.
- A member leaving voluntarily triggers the same unassignment + notification behavior as removal.
- A leader attempting to leave while other accepted members remain is blocked until they transfer leadership.
- A sole-member leader leaving triggers group disbanding, not a leaderless group.
- Leadership transfer: old leader immediately loses invite/mentor-request/removal rights; new leader gains them.
- Deleting a group cascades to its linked project, tasks, comments, and mentor requests, and notifies all former members/mentor.
- Only the leader (or admin) can delete a group; a regular member attempting it gets 403.
- Group image upload rejects non-image files and oversized files.
- Non-leader member attempting to invite/remove/transfer/mentor-request receives 403.

### Mentor Request
- Cannot send a mentor request while one is already `pending` for that group.
- Mentor can Accept or Reject; rejection allows the leader to request a different mentor.
- Accepting sets `Group.mentor_id`, updates group `status` to `active`, and notifies all members.
- Mentor request cannot be sent by a non-leader group member.

### Task Board
- Task cannot be assigned to a non-member of the project/group.
- Overdue tasks (past due_date, not done) are flagged correctly.
- Every status change is recorded in the activity trail with correct timestamp and actor.

### Search & Filters
- Empty search term returns all matching tasks.
- Filter combination with no matches returns an empty array, not a 500 error.
- SQL injection attempt in the search string is safely handled (parameterized queries).

### Progress Chart
- Project with zero tasks shows 0% (no division-by-zero error).
- Chart/progress bar updates immediately after a task's status changes.

### Comments
- Empty comment text is rejected.
- Comment always shows correct author and timestamp.
- Only project/group members (and assigned mentor) can post a comment.
- A comment row never has both `task_id` and `project_id` set simultaneously.

### Validation & Error Handling
- Missing required field returns HTTP 400 with a clear, consistent error message.
- Malformed due date is rejected.
- XSS payload in any text field (task title, comment, group description) is escaped on render, not executed.

### Deployment
- Fresh clone + `pip install -r requirements.txt` + `flask run` works with no manual DB setup steps (use `db.create_all()` or a migration script on first run).
- README documents every API route from Section 6.

---

## 9. Open Items for Later (explicitly deferred, not forgotten)

- Group "open visibility" / student-initiated join requests (currently invite-only per decision).
- Payments, chat, and microservices — explicitly out of scope for v1 per original brief.
- Whether informal member-to-leader "suggest a member" prompts should become a tracked DB entity (currently just a UI message, not persisted).
- Password reset / "forgot password" flow — not designed yet; needs a decision before auth is considered complete.

---

*This document reflects every decision made during planning discussion, including the corrections made after a full review pass (leader notifications on invite response, resolving the Project/Group membership authority conflict, adding leave-group and group-deletion flows, and flagging password reset as a deferred item). Any future change to roles, group rules, or workflow should be updated here before implementation continues, so the plan stays the single source of truth.*
