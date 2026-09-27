"""
Demo Seeder Script for Student Project Management Portal.
Populates realistic students, faculty mentors, groups, projects, tasks, milestones, and discussions.
"""
from datetime import date, datetime, timedelta, timezone
from app import create_app
from app.extensions import db
from app.models import (
    ActivityLog,
    Attachment,
    Comment,
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
    User,
)


def seed_database(app=None):
    if app is None:
        app = create_app("development")
    with app.app_context():
        print("--> Seeding Student Project Management Portal with realistic demo data...")

        # 1. Clear existing data safely
        db.drop_all()
        db.create_all()

        # 2. Users (Admin, Mentors, Students)
        admin = User(
            name="System Administrator",
            email="admin@studentportal.com",
            role=RoleEnum.ADMIN,
            bio="Portal administrator overseeing departmental capstone projects, academic compliance, and user roles.",
            github_url="https://github.com",
            linkedin_url="https://linkedin.com",
        )
        admin.set_password("password123")

        # Faculty Mentors
        mentor_sarah = User(
            name="Dr. Sarah Chen",
            email="sarah.chen@university.edu",
            role=RoleEnum.MENTOR,
            bio="Associate Professor of Computer Science specializing in Deep Learning, Computer Vision, and Medical Informatics.",
            github_url="https://github.com/sarahchen-ai",
            linkedin_url="https://linkedin.com/in/sarahchen-prof",
        )
        mentor_sarah.set_password("password123")

        mentor_marcus = User(
            name="Prof. Marcus Vance",
            email="marcus.vance@university.edu",
            role=RoleEnum.MENTOR,
            bio="Chair of Distributed Systems Lab. Research interests in Kubernetes orchestration, fault-tolerance, and microservices.",
            github_url="https://github.com/marcusvance",
            linkedin_url="https://linkedin.com/in/marcus-vance",
        )
        mentor_marcus.set_password("password123")

        mentor_elena = User(
            name="Dr. Elena Gomez",
            email="elena.gomez@university.edu",
            role=RoleEnum.MENTOR,
            bio="Senior Cryptography & Security Fellow. Focus on zero-knowledge proofs, privacy-preserving computation, and smart contract audits.",
            github_url="https://github.com/elenagomez-sec",
            linkedin_url="https://linkedin.com/in/elena-gomez-phd",
        )
        mentor_elena.set_password("password123")

        # Students
        student_alex = User(
            name="Alex Rivera",
            email="alex.rivera@student.edu",
            role=RoleEnum.STUDENT,
            bio="Final year CS student passionate about full-stack engineering, API design, and distributed microservices.",
            github_url="https://github.com/alexrivera-dev",
            linkedin_url="https://linkedin.com/in/alex-rivera-tech",
        )
        student_alex.set_password("password123")

        student_maya = User(
            name="Maya Patel",
            email="maya.patel@student.edu",
            role=RoleEnum.STUDENT,
            bio="Machine learning engineer focused on PyTorch pipelines, image classification, and automated model optimization.",
            github_url="https://github.com/mayapatel-ml",
            linkedin_url="https://linkedin.com/in/mayapatel-ai",
        )
        student_maya.set_password("password123")

        student_liam = User(
            name="Liam Johnson",
            email="liam.johnson@student.edu",
            role=RoleEnum.STUDENT,
            bio="DevOps and Cloud Architecture enthusiast. Specializing in Docker, Terraform, CI/CD, and system monitoring.",
            github_url="https://github.com/liamjohnson-ops",
            linkedin_url="https://linkedin.com/in/liam-johnson-devops",
        )
        student_liam.set_password("password123")

        student_chloe = User(
            name="Chloe Zhao",
            email="chloe.zhao@student.edu",
            role=RoleEnum.STUDENT,
            bio="Security and cryptography student researching decentralized audit mechanisms and zero-knowledge proofs.",
            github_url="https://github.com/chloezhao-sec",
            linkedin_url="https://linkedin.com/in/chloe-zhao-cyber",
        )
        student_chloe.set_password("password123")

        student_vinod = User(
            name="Vinod Kumar Chavan",
            email="vinod.chavan@student.edu",
            role=RoleEnum.STUDENT,
            bio="Full-Stack Developer & Systems Architect. Enthusiastic about responsive UI design, scalable Flask apps, and automated workflows.",
            github_url="https://github.com/vinodchavan",
            linkedin_url="https://linkedin.com/in/vinod-kumar-chavan",
        )
        student_vinod.set_password("password123")

        users = [
            admin, mentor_sarah, mentor_marcus, mentor_elena,
            student_alex, student_maya, student_liam, student_chloe, student_vinod
        ]
        db.session.add_all(users)
        db.session.commit()
        print(f"  [+] Created {len(users)} users (1 Admin, 3 Faculty Mentors, 5 Students).")

        # 3. Groups
        group_ai = Group(
            name="NeuralVision AI",
            description="Autonomous medical diagnostics research group leveraging multi-modal deep learning and explainable AI.",
            max_members=4,
            domain="ML/AI",
            tech_tags="PyTorch, OpenCV, Transformers, Flask, FastEmbed",
            leader_id=student_alex.id,
            mentor_id=mentor_sarah.id,
            status="active",
        )
        group_sec = Group(
            name="SecureLedger Web3",
            description="Developing privacy-preserving cryptographic audit logging for mission-critical enterprise systems.",
            max_members=4,
            domain="Cybersecurity",
            tech_tags="Rust, Cryptography, ZeroKnowledge, Python, WebSockets",
            leader_id=student_chloe.id,
            mentor_id=mentor_elena.id,
            status="active",
        )
        group_devops = Group(
            name="CloudPulse DevOps",
            description="High-availability cloud infrastructure orchestrator with automated failover and telemetry analytics.",
            max_members=5,
            domain="DevOps",
            tech_tags="Docker, Kubernetes, Terraform, Prometheus, Go, Flask",
            leader_id=student_liam.id,
            mentor_id=mentor_marcus.id,
            status="active",
        )
        db.session.add_all([group_ai, group_sec, group_devops])
        db.session.commit()

        # Memberships
        memberships = [
            # NeuralVision
            GroupMember(group_id=group_ai.id, student_id=student_alex.id, status=MemberStatusEnum.ACCEPTED),
            GroupMember(group_id=group_ai.id, student_id=student_maya.id, status=MemberStatusEnum.ACCEPTED),
            GroupMember(group_id=group_ai.id, student_id=student_vinod.id, status=MemberStatusEnum.ACCEPTED),
            # SecureLedger
            GroupMember(group_id=group_sec.id, student_id=student_chloe.id, status=MemberStatusEnum.ACCEPTED),
            GroupMember(group_id=group_sec.id, student_id=student_alex.id, status=MemberStatusEnum.ACCEPTED),
            GroupMember(group_id=group_sec.id, student_id=student_liam.id, status=MemberStatusEnum.ACCEPTED),
            # CloudPulse
            GroupMember(group_id=group_devops.id, student_id=student_liam.id, status=MemberStatusEnum.ACCEPTED),
            GroupMember(group_id=group_devops.id, student_id=student_vinod.id, status=MemberStatusEnum.ACCEPTED),
            GroupMember(group_id=group_devops.id, student_id=student_maya.id, status=MemberStatusEnum.ACCEPTED),
        ]
        db.session.add_all(memberships)
        db.session.commit()
        print("  [+] Created 3 Groups with accepted student members and assigned faculty mentors.")

        # 4. Projects
        p1 = Project(
            name="Automated Medical Imaging Diagnostic Assistant",
            description="Deep learning system capable of classifying X-ray anomalies and generating visual heatmaps for clinical staff.",
            status=ProjectStatusEnum.IN_PROGRESS,
            github_repo="https://github.com/neuralvision-ai/diagnostic-core",
            live_demo_url="https://neuralvision-assistant.demo.app",
            owner_id=student_alex.id,
            group_id=group_ai.id,
        )
        p2 = Project(
            name="Decentralized Zero-Knowledge Audit Trail",
            description="Verifiable, tamper-evident logging framework using zero-knowledge succinct non-interactive arguments.",
            status=ProjectStatusEnum.IN_PROGRESS,
            github_repo="https://github.com/secureledger/zk-audit",
            live_demo_url="https://zk-audit.live.dev",
            owner_id=student_chloe.id,
            group_id=group_sec.id,
        )
        p3 = Project(
            name="Distributed Microservices Reliability Engine",
            description="Continuous Chaos Engineering platform that injects controlled network latency and monitors recovery SLAs.",
            status=ProjectStatusEnum.IN_PROGRESS,
            github_repo="https://github.com/cloudpulse/chaos-engine",
            live_demo_url="https://cloudpulse-metrics.io",
            owner_id=student_liam.id,
            group_id=group_devops.id,
        )
        p4 = Project(
            name="Personal Capstone & Academic Portfolio",
            description="Modern interactive portfolio showcase highlighting undergraduate capstone deliverables and benchmarks.",
            status=ProjectStatusEnum.COMPLETED,
            github_repo="https://github.com/alexrivera-dev/portfolio",
            live_demo_url="https://alexrivera.me",
            owner_id=student_alex.id,
            group_id=None,
        )
        db.session.add_all([p1, p2, p3, p4])
        db.session.commit()
        print("  [+] Created 4 Projects (3 team projects, 1 personal capstone).")

        # 5. Milestones for Project 1
        today = date.today()
        m1 = Milestone(
            project_id=p1.id,
            title="Phase 1: Dataset curation and anonymization pipeline",
            description="Compile 15,000 anonymized chest X-ray scans with metadata sanitization compliant with HIPAA.",
            due_date=today - timedelta(days=20),
            is_completed=True,
            completed_at=datetime.now(timezone.utc) - timedelta(days=20),
        )
        m2 = Milestone(
            project_id=p1.id,
            title="Phase 2: Swin-Transformer vs ResNet baseline training",
            description="Attain >92% AUC on multiclass lung pathology validation subset.",
            due_date=today - timedelta(days=5),
            is_completed=True,
            completed_at=datetime.now(timezone.utc) - timedelta(days=5),
        )
        m3 = Milestone(
            project_id=p1.id,
            title="Phase 3: Fast inference REST API & Gradio Interactive Demo",
            description="Sub-150ms GPU inference latency with Gradio web visualization interface.",
            due_date=today + timedelta(days=12),
            is_completed=False,
        )
        m4 = Milestone(
            project_id=p1.id,
            title="Phase 4: Comprehensive Audit & Faculty Mentor Presentation",
            description="Prepare final research paper draft and live demo before Department Review Board.",
            due_date=today + timedelta(days=30),
            is_completed=False,
        )
        db.session.add_all([m1, m2, m3, m4])

        # 6. Tasks for Project 1 (Varied across To Do, In Progress, Done, with Priorities and Tags)
        t1 = Task(
            project_id=p1.id,
            title="Build DICOM image normalization & data augmentation pipeline",
            description="Standardize 16-bit grayscale DICOM scans into normalized floating-point tensors with CLAHE contrast enhancement.",
            status=TaskStatusEnum.DONE,
            priority=TaskPriorityEnum.HIGH,
            tags="data, preprocessing, opencv",
            assignee_id=student_maya.id,
            due_date=today - timedelta(days=15),
        )
        t2 = Task(
            project_id=p1.id,
            title="Train Swin-Transformer model on GPU cluster",
            description="Run 50-epoch distributed training with cross-entropy loss and cosine annealing schedule.",
            status=TaskStatusEnum.DONE,
            priority=TaskPriorityEnum.URGENT,
            tags="ml, pytorch, gpu",
            assignee_id=student_maya.id,
            due_date=today - timedelta(days=7),
        )
        t3 = Task(
            project_id=p1.id,
            title="Implement real-time Flask inference server with ONNX Runtime",
            description="Export trained model checkpoint to ONNX format and build lightweight HTTP endpoint accepting base64 images.",
            status=TaskStatusEnum.IN_PROGRESS,
            priority=TaskPriorityEnum.URGENT,
            tags="backend, api, onnx, flask",
            assignee_id=student_alex.id,
            due_date=today + timedelta(days=2),
        )
        t4 = Task(
            project_id=p1.id,
            title="Develop Drag-and-Drop Medical Image Radiologist UI",
            description="Build intuitive browser interface with instant heatmap overlay, zoom controls, and PDF diagnosis report export.",
            status=TaskStatusEnum.IN_PROGRESS,
            priority=TaskPriorityEnum.HIGH,
            tags="frontend, ui, drag-drop, visual",
            assignee_id=student_vinod.id,
            due_date=today + timedelta(days=5),
        )
        t5 = Task(
            project_id=p1.id,
            title="Security & patient privacy anonymization audit",
            description="Verify that no PHI (Protected Health Information) leaks through image metadata tags or HTTP logs.",
            status=TaskStatusEnum.TODO,
            priority=TaskPriorityEnum.HIGH,
            tags="security, hipaa, compliance",
            assignee_id=student_vinod.id,
            due_date=today + timedelta(days=10),
        )
        t6 = Task(
            project_id=p1.id,
            title="Write system documentation and latency benchmark report",
            description="Document API schema using OpenAPI / Swagger and record latency measurements across batch sizes 1 to 32.",
            status=TaskStatusEnum.TODO,
            priority=TaskPriorityEnum.MEDIUM,
            tags="docs, benchmarks, testing",
            assignee_id=student_alex.id,
            due_date=today + timedelta(days=14),
        )
        t7 = Task(
            project_id=p1.id,
            title="Setup automated GitHub Actions CI/CD test suite",
            description="Run unit tests on image transforms, PyTest API routes, and lint check on git push.",
            status=TaskStatusEnum.TODO,
            priority=TaskPriorityEnum.LOW,
            tags="ci/cd, devops, testing",
            assignee_id=student_alex.id,
            due_date=today + timedelta(days=18),
        )

        # Tasks for Project 2 (SecureLedger)
        t8 = Task(
            project_id=p2.id,
            title="Define Groth16 zk-SNARK cryptographic circuit",
            description="Implement verifiable constraint system in Circom for hash preimage verification.",
            status=TaskStatusEnum.IN_PROGRESS,
            priority=TaskPriorityEnum.URGENT,
            tags="cryptography, snark, rust",
            assignee_id=student_chloe.id,
            due_date=today + timedelta(days=4),
        )
        t9 = Task(
            project_id=p2.id,
            title="Build tamper-evident append-only ledger storage",
            description="Merkle tree storage engine with verifiable root hash generation.",
            status=TaskStatusEnum.DONE,
            priority=TaskPriorityEnum.HIGH,
            tags="database, merkle, storage",
            assignee_id=student_alex.id,
            due_date=today - timedelta(days=3),
        )
        t10 = Task(
            project_id=p2.id,
            title="Benchmarking proof verification gas & CPU costs",
            description="Measure verification throughput under 1,000 transactions per second workload.",
            status=TaskStatusEnum.TODO,
            priority=TaskPriorityEnum.MEDIUM,
            tags="benchmarks, performance",
            assignee_id=student_liam.id,
            due_date=today + timedelta(days=16),
        )

        # Tasks for Project 3 (CloudPulse)
        t11 = Task(
            project_id=p3.id,
            title="Configure Prometheus scrape targets and Grafana dashboards",
            description="Set up CPU, RAM, and network I/O exporters for simulated cluster nodes.",
            status=TaskStatusEnum.DONE,
            priority=TaskPriorityEnum.HIGH,
            tags="prometheus, grafana, metrics",
            assignee_id=student_liam.id,
            due_date=today - timedelta(days=4),
        )
        t12 = Task(
            project_id=p3.id,
            title="Chaos agent network packet dropper implementation",
            description="Simulate split-brain partitions by dropping 30% of sync packets between consensus nodes.",
            status=TaskStatusEnum.IN_PROGRESS,
            priority=TaskPriorityEnum.URGENT,
            tags="chaos, networking, reliability",
            assignee_id=student_vinod.id,
            due_date=today + timedelta(days=3),
        )

        db.session.add_all([t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12])
        db.session.commit()
        print("  [+] Created 12 Tasks across To Do, In Progress, and Completed states with priorities and tags.")

        # 7. Comments & Mentor Guidance
        c1 = Comment(
            project_id=p1.id,
            user_id=mentor_sarah.id,
            text="Excellent progress on the Swin-Transformer evaluation! Make sure to test sensitivity specifically on subtle ground-glass opacities before the mid-term demo.",
        )
        c2 = Comment(
            project_id=p1.id,
            user_id=student_alex.id,
            text="Thank you Dr. Chen! Maya has separated those cases into an isolated benchmark set. Vinod is currently wiring up the interactive heatmap overlay in the browser.",
        )
        c3 = Comment(
            task_id=t3.id,
            user_id=student_vinod.id,
            text="I've tested the ONNX runtime benchmark locally -- inference latency dropped from 380ms down to 110ms on CUDA! Ready to integrate with the frontend.",
        )
        c4 = Comment(
            project_id=p2.id,
            user_id=mentor_elena.id,
            text="Chloe and Alex: please double-check your curve parameter selection to ensure compliance with 128-bit quantum-resistant security standards.",
        )
        db.session.add_all([c1, c2, c3, c4])

        # 8. Activity Logs
        l1 = ActivityLog(task_id=t1.id, actor_id=student_maya.id, field_changed="created", old_value=None, new_value="todo")
        l2 = ActivityLog(task_id=t1.id, actor_id=student_maya.id, field_changed="status", old_value="in_progress", new_value="done")
        l3 = ActivityLog(task_id=t2.id, actor_id=student_maya.id, field_changed="status", old_value="in_progress", new_value="done")
        l4 = ActivityLog(task_id=t3.id, actor_id=student_alex.id, field_changed="status", old_value="todo", new_value="in_progress")
        l5 = ActivityLog(task_id=t4.id, actor_id=student_vinod.id, field_changed="status", old_value="todo", new_value="in_progress")
        db.session.add_all([l1, l2, l3, l4, l5])

        db.session.commit()
        print("  [+] Populated realistic comments and audit activity logs.")
        print("\nDatabase successfully seeded with demo data!")
        print("--------------------------------------------------")
        print("Demo User Credentials (Password for all: password123):")
        print("  * Admin:   admin@studentportal.com")
        print("  * Mentor:  sarah.chen@university.edu (Dr. Sarah Chen)")
        print("  * Mentor:  marcus.vance@university.edu (Prof. Marcus Vance)")
        print("  * Student: alex.rivera@student.edu (Team Leader)")
        print("  * Student: vinod.chavan@student.edu (Vinod Kumar Chavan)")
        print("  * Student: maya.patel@student.edu")
        print("--------------------------------------------------\n")


if __name__ == "__main__":
    seed_database()
