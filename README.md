# Student Project Management Portal

A full-stack web application where students form groups, manage projects and tasks, and connect with mentor guidance. Built with Python / Flask, SQLite, and plain HTML/CSS/JS.

---

## Tech Stack

| Layer       | Technology                                      |
|-------------|------------------------------------------------|
| Backend     | Python 3.10+, Flask 3.0, Flask-SQLAlchemy 3.1  |
| Auth        | Flask-Login (session-based), Werkzeug hashing  |
| Database    | SQLite (dev) — schema is PostgreSQL-compatible  |
| Frontend    | Jinja2 templates, plain HTML/CSS/JS, Chart.js  |
| Migrations  | Flask-Migrate (Alembic)                        |
| CSRF        | Flask-WTF                                      |

---

## Roles

| Role    | Key capabilities                                               |
|---------|----------------------------------------------------------------|
| Student | Create groups/projects, invite members, manage tasks, comments |
| Mentor  | Accept/reject mentor requests, comment on assigned groups      |
| Admin   | Full CRUD on all resources, role management                    |

Role escalation via API payload is blocked server-side on every route.

---

## Quick Start

### 1. Clone / enter the project

```powershell
cd "d:\Student management system"
```

### 2. Create and activate a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env` and edit as needed (already present with safe defaults for dev):

```
SECRET_KEY=change-me-in-production-use-a-long-random-string
DATABASE_URL=sqlite:///student_portal.db
FLASK_APP=run.py
FLASK_ENV=development
FLASK_DEBUG=1
MAX_CONTENT_LENGTH=2097152
```

### 5. Run the development server

```powershell
flask run
```

The database tables are created automatically on first run (`db.create_all()` is called in the app factory).

Open your browser at **http://127.0.0.1:5000**.

### 6. (Optional) Initialize migrations

```powershell
flask db init
flask db migrate -m "initial"
flask db upgrade
```

---

## Project Structure

```
Student management system/
├── run.py                   # Entry point
├── config.py                # Config classes (dev / prod)
├── requirements.txt
├── .env                     # Environment variables (not committed in prod)
├── instance/
│   └── student_portal.db    # SQLite database (auto-created)
└── app/
    ├── __init__.py          # App factory
    ├── extensions.py        # db, login_manager, migrate, csrf
    ├── models.py            # All SQLAlchemy models + enums
    ├── helpers.py           # Permission decorators, notification factory, image upload
    ├── errors.py            # HTTP error handlers
    ├── routes/
    │   ├── main.py          # Dashboard, landing page
    │   ├── auth.py          # Register, login, logout
    │   ├── users.py         # Profile view, admin user edit
    │   ├── projects.py      # Project CRUD
    │   ├── tasks.py         # Task board + search/filter + activity log
    │   ├── groups.py        # Group lifecycle (create → disband)
    │   ├── mentors.py       # Mentor request send/accept/reject
    │   ├── comments.py      # Task-level and project-level comments
    │   └── notifications.py # Notification list, mark read
    ├── templates/
    │   ├── base.html
    │   ├── main/            # index.html, dashboard.html
    │   ├── auth/            # login.html, register.html
    │   ├── projects/        # list, form, detail
    │   ├── tasks/           # list, form, detail
    │   ├── groups/          # list, form, detail
    │   ├── users/           # profile, edit, list
    │   ├── mentors/         # requests.html
    │   ├── notifications/   # list.html
    │   └── errors/          # 400, 403, 404, 413, 500
    └── static/
        ├── css/main.css
        ├── js/main.js
        └── img/groups/      # Uploaded group images
```

---

## Database Schema

```
User            id, name, email (unique), password_hash, role, created_at
Project         id, name, description, owner_id→User, group_id→Group(nullable), created_at
Task            id, project_id→Project, title, description, status, assignee_id→User, due_date, created_at
Comment         id, task_id→Task(nullable), project_id→Project(nullable), user_id→User, text, created_at
Group           id, name, description, image_url, max_members, domain, tech_tags,
                leader_id→User, mentor_id→User(nullable), status, created_at
GroupMember     id, group_id→Group, student_id→User, status, invited_at
                UNIQUE(group_id, student_id)
MentorRequest   id, group_id→Group, mentor_id→User, status, requested_at
Notification    id, user_id→User, type, payload(JSON), read, created_at
ActivityLog     id, task_id→Task, actor_id→User, field_changed, old_value, new_value, changed_at
```

Access control on projects is derived entirely from `GroupMember` rows (`status='accepted'`) plus `Group.mentor_id`. No separate ProjectMember table.

---

## Full API / Route Reference

### Auth
| Method | URL                    | Description                  | Auth required |
|--------|------------------------|------------------------------|---------------|
| GET    | `/auth/register`       | Registration form            | No            |
| POST   | `/auth/register`       | Create account               | No            |
| GET    | `/auth/login`          | Login form                   | No            |
| POST   | `/auth/login`          | Authenticate and start session | No          |
| POST   | `/auth/logout`         | End session                  | Yes           |

### Users
| Method | URL                    | Description                     | Auth / Role  |
|--------|------------------------|---------------------------------|--------------|
| GET    | `/users/`              | List all users                  | Admin        |
| GET    | `/users/<id>`          | User profile (groups count/list)| Any          |
| GET    | `/users/<id>/edit`     | Edit user form                  | Admin        |
| POST   | `/users/<id>/edit`     | Save user name / role           | Admin        |

### Projects
| Method | URL                        | Description                          | Auth / Role            |
|--------|----------------------------|--------------------------------------|------------------------|
| GET    | `/projects/`               | List visible projects                | Any                    |
| GET    | `/projects/new`            | New project form                     | Student / Admin        |
| POST   | `/projects/new`            | Create project                       | Student / Admin        |
| GET    | `/projects/<id>`           | Project detail + tasks + comments    | Member / Admin         |
| GET    | `/projects/<id>/edit`      | Edit form                            | Owner / Admin          |
| POST   | `/projects/<id>/edit`      | Update project                       | Owner / Admin          |
| POST   | `/projects/<id>/delete`    | Delete project                       | Owner / Admin          |
| GET    | `/projects/<id>/progress`  | JSON `{progress, project_id}`        | Member / Admin         |

### Tasks
| Method | URL                                           | Description                   | Auth / Role              |
|--------|-----------------------------------------------|-------------------------------|--------------------------|
| GET    | `/projects/<id>/tasks`                        | Task list with search/filter  | Member / Admin           |
| GET    | `/projects/<id>/tasks?status=&q=&assignee=`   | Filtered task list            | Member / Admin           |
| GET    | `/projects/<id>/tasks/new`                    | New task form                 | Owner / Admin            |
| POST   | `/projects/<id>/tasks/new`                    | Create task                   | Owner / Admin            |
| GET    | `/tasks/<id>`                                 | Task detail + comments + log  | Member / Admin           |
| GET    | `/tasks/<id>/edit`                            | Edit form                     | Owner / Assignee / Admin |
| POST   | `/tasks/<id>/edit`                            | Update task                   | Owner / Assignee / Admin |
| POST   | `/tasks/<id>/delete`                          | Delete task                   | Owner / Admin            |
| POST   | `/tasks/<id>/quick-status`                    | JS status change (JSON resp)  | Owner / Assignee / Admin |

### Comments
| Method | URL                            | Description            | Auth / Role    |
|--------|--------------------------------|------------------------|----------------|
| POST   | `/tasks/<id>/comments`         | Add task comment       | Member / Admin |
| POST   | `/projects/<id>/comments`      | Add project comment    | Member / Admin |

### Groups
| Method | URL                                         | Description                   | Auth / Role      |
|--------|---------------------------------------------|-------------------------------|------------------|
| GET    | `/groups/`                                  | List my groups                | Any              |
| GET    | `/groups/new`                               | Create group form             | Student / Admin  |
| POST   | `/groups/new`                               | Create group                  | Student / Admin  |
| GET    | `/groups/<id>`                              | Group detail                  | Member / Admin   |
| GET    | `/groups/<id>/members`                      | Members JSON                  | Member / Admin   |
| POST   | `/groups/<id>/invite`                       | Invite student                | Leader / Admin   |
| POST   | `/groups/<id>/members/<sid>/remove`         | Remove member                 | Leader / Admin   |
| POST   | `/groups/<id>/leave`                        | Leave group                   | Member           |
| POST   | `/groups/<id>/transfer-leadership`          | Transfer leadership           | Leader / Admin   |
| POST   | `/groups/<id>/delete`                       | Disband group + cascade       | Leader / Admin   |

### Group Invites
| Method | URL                            | Description       | Auth / Role      |
|--------|--------------------------------|-------------------|------------------|
| POST   | `/groups/invites/<id>/accept`  | Accept invite     | Invitee          |
| POST   | `/groups/invites/<id>/decline` | Decline invite    | Invitee          |

### Mentor Requests
| Method | URL                                    | Description                    | Auth / Role         |
|--------|----------------------------------------|--------------------------------|---------------------|
| POST   | `/groups/<id>/mentor-request`          | Send mentor request            | Leader / Admin      |
| GET    | `/mentor-requests`                     | Pending requests list          | Mentor / Admin      |
| POST   | `/mentor-requests/<id>/accept`         | Accept — sets mentor + active  | Mentor / Admin      |
| POST   | `/mentor-requests/<id>/reject`         | Reject request                 | Mentor / Admin      |

### Notifications
| Method | URL                                 | Description             | Auth |
|--------|-------------------------------------|-------------------------|------|
| GET    | `/notifications/`                   | All notifications       | Any  |
| POST   | `/notifications/<id>/read`          | Mark one read           | Any  |
| POST   | `/notifications/mark-all-read`      | Mark all read           | Any  |

---

## Key Business Rules (enforced server-side)

- Role cannot be self-escalated: students may only register as `student` or `mentor`; `admin` role is set by an existing admin only.
- Group capacity: invites are blocked once `accepted` count == `max_members`.
- Invite upsert: re-inviting a declined student updates the existing `GroupMember` row; no duplicate rows allowed (unique constraint on `group_id, student_id`).
- Task assignment: assignee must be an accepted group member; validated on create and edit.
- Leader leave rule: a leader with other accepted members must transfer leadership first.
- Sole-member leader leaving = group disbanding.
- Group disbanding cascades to linked projects → tasks → comments → mentor requests.
- Member removal / voluntary leave: the member's tasks are unassigned (no auto-reassignment).
- Overdue flagging: `task.is_overdue` — `due_date` is in the past and status is not `done`.
- Progress: `done_tasks / total_tasks * 100`; zero tasks → 0% (no division-by-zero).
- Comments: exactly one of `task_id` / `project_id` is non-null per row; empty text rejected.
- Only one `pending` MentorRequest per group at a time.
- Activity log: every task field change (status, title, assignee) is recorded with actor + timestamp.

---

## Security Notes

- Passwords are hashed with Werkzeug's PBKDF2-SHA256 (`generate_password_hash`).
- All forms are CSRF-protected via Flask-WTF (`{{ csrf_token() }}`).
- All DB queries use SQLAlchemy ORM (parameterised) — no raw SQL, no SQL injection surface.
- Jinja2 auto-escapes all template variables by default — XSS payloads are escaped on render.
- File uploads: extension whitelist (png/jpg/jpeg/gif/webp) + 2 MB size cap enforced before saving.
- `MAX_CONTENT_LENGTH` is set in config; Flask returns 413 automatically for oversized requests.

---

## Deployment to Vercel (with Vercel Postgres)

This repository is pre-configured with `vercel.json` and `api/index.py` for 1-click deployment on **Vercel** with **Vercel Postgres (Neon)**.

### Step 1: Push Repository to GitHub
1. Create a new repository on your GitHub account (e.g. `student-project-portal`).
2. Run the following commands in your terminal:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Student Project Portal with Vercel support"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git push -u origin main
   ```

### Step 2: Import into Vercel
1. Go to [vercel.com/new](https://vercel.com/new) and log in.
2. Select your newly pushed GitHub repository and click **Import**.
3. In Project Settings, set Framework Preset to **Other** (Root directory: `./`).

### Step 3: Connect Vercel Postgres Storage
1. On your Vercel Project Dashboard, navigate to the **Storage** tab.
2. Click **Create Database** -> select **Postgres** (powered by Neon).
3. Accept the default name and region -> click **Create & Continue**.
4. Click **Connect to Project** and select your project.
5. Vercel will automatically inject `POSTGRES_URL` and `DATABASE_URL` into your project's Environment Variables!

### Step 4: Deploy & Auto-Seed
1. Trigger a redeploy (or push a new commit).
2. On initial startup, the portal will automatically:
   - Create all PostgreSQL tables
   - Seed the demo accounts (Student Leader, Faculty Mentor, Admin)
3. Visit your live production URL (e.g., `https://your-project.vercel.app`)!

---

## Deployment (Render / Railway)

1. Set environment variables in the platform dashboard:
   - `SECRET_KEY` — a long random string (never use the default)
   - `DATABASE_URL` — PostgreSQL URL provided by the platform
   - `FLASK_ENV=production`

2. Build command: `pip install -r requirements.txt`

3. Start command: `flask run --host=0.0.0.0 --port=$PORT`
   (or use gunicorn: `gunicorn run:app`)

4. On first deploy, tables are created automatically by `db.create_all()` in the app factory.

---

## Manual API Testing (PowerShell)

```powershell
# Register
Invoke-RestMethod -Uri http://127.0.0.1:5000/auth/register -Method Post `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "name=Alice&email=alice@example.com&password=secret1&confirm_password=secret1&role=student"

# Progress endpoint (after login session is established via browser)
Invoke-RestMethod -Uri http://127.0.0.1:5000/projects/1/progress
```

---

## Deferred Items (v2)

- Password reset / "forgot password" flow.
- Open group visibility + student-initiated join requests (currently invite-only).
- Payments, microservices, real-time chat.
- Persisted "suggest a member" message from student to leader.
