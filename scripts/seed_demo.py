"""Seed a rich demo dataset (spec §43) so the SIH demo flows are one-click.

Creates (idempotently):
  * a demo entrepreneur user, ABC Textiles Pvt Ltd
  * the "ABC Textiles Pvt Ltd - New Dyes Unit" project
  * applicable approvals via the ApprovalEngine
  * deterministic submittal/status story tracked against the prototype government systems
  * a few demo business documents (with extracted fields for the doc-AI flow)

Run:
    python scripts/seed_demo.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))  # ensures `app` is importable


async def seed() -> dict:
    from sqlalchemy import select
    from app.models import (
        UserRole,
        Project,
        Approval,
        Document,
        ApprovalStatus,
        User,
        BusinessProfile,
        Grievance,
        KnowledgeDocument,
        KnowledgeChunk,
        GrievanceEvent,
        business_profile_documents,
        InspectionVisit,
        InspectionVisitStatus,
        Notification,
        Scheme,
        IncentiveApplicationCase,
        inspection_visit_approvals,
    )
    from app.core.database import AsyncSessionLocal
    from app.core.security import hash_password
    from app.services.auth import AuthService
    from app.services.project import ProjectService
    from app.schemas import UserRegister, ProjectOnboarding
    from app.rules.approval_engine import ApprovalEngine
    from app.services.gov_sync_service import GovSyncService
    from app.services.gateway_service import GatewayService
    from app.integrations.government_adapters import system_for_department
    from app.services.incentive_readiness import IncentiveReadinessService
    from app.services.application_preparation import ApplicationPreparationService

    DEMO_EMAIL = os.environ.get("DEMO_EMAIL", "demo@abctextiles.in")
    DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "Demo@12345")

    async with AsyncSessionLocal() as db:
        # 1. Demo user (idempotent)
        auth = AuthService(db)
        try:
            user = await auth.register_user(UserRegister(
                email=DEMO_EMAIL,
                name="Rohit Sharma",
                phone="9876543210",
                password=DEMO_PASSWORD,
                role=UserRole.ENTREPRENEUR,
            ))
            created_user = True
        except ValueError:
            user = await auth.get_user_by_email(DEMO_EMAIL)
            created_user = False

        # 1b. Demo officer + admin provisioning (idempotent). These bypass the
        # public self-registration path (which is ENTREPRENEUR-only) and are the
        # sanctioned way to create privileged accounts for the demo.
        privileged = (
            ("officer@udoyogsetu.demo", "Officer", UserRole.OFFICER, os.environ.get("OFFICER_PASSWORD", "Officer@12345")),
            ("admin@udoyogsetu.demo", "Admin", UserRole.ADMIN, os.environ.get("ADMIN_PASSWORD", "Admin@12345")),
        )
        created_privileged = []
        for priv_email, priv_name, priv_role, priv_password in privileged:
            result = await db.execute(select(User).where(User.email == priv_email))
            existing = result.scalar_one_or_none()
            if existing is None:
                db.add(User(
                    email=priv_email,
                    name=priv_name,
                    phone="9876500000",
                    password_hash=hash_password(priv_password),
                    role=priv_role,
                    is_active=True,
                ))
                created_privileged.append(priv_role.value)
        if created_privileged:
            await db.commit()

        officer_result = await db.execute(
            select(User).where(User.email == "officer@udoyogsetu.demo")
        )
        demo_officer = officer_result.scalar_one_or_none()

        # 2. Project (idempotent by name)
        svc = ProjectService(db)
        existing = await svc.list_user_projects(user.id)
        project = next((p for p in existing if p.name == "ABC Textiles Pvt Ltd - New Dyes Unit"), None)
        if project is None:
            project = await svc.create_project(ProjectOnboarding(
                project_name="ABC Textiles Pvt Ltd - New Dyes Unit",
                company_name="ABC Textiles Pvt Ltd",
                business_type="manufacturing",
                industry="Textile",
                sector="Textile",
                project_stage="implementation",
                investment_amount=350000000,
                location_state="Maharashtra",
                location_district="Nashik",
                location_city="Nashik",
                location_industrial_area="MIDC Ambad",
                location_midc_estate="Ambad",
                land_type="industrial_plot",
                employees=120,
                production_type="Textile processing",
                hazardous_materials=True,
                has_boiler=True,
                electricity_load=1200,
                water_consumption=250,
                pollution_potential="high",
                building_type="industrial",
                is_new=True,
            ), user_id=user.id)
            created_project = True
        else:
            created_project = False

        # 2b. Business profile + reusable Data Vault seed (idempotent).
        profile_result = await db.execute(
            select(BusinessProfile).where(BusinessProfile.user_id == user.id)
        )
        profile = profile_result.scalar_one_or_none()
        if profile is None:
            profile = BusinessProfile(
                user_id=user.id,
                company_name="ABC Textiles Pvt Ltd",
                business_type="manufacturing",
                industry="Textile",
                sector="Textile",
                pan="ABCTA1234F",
                gstin="27ABCTA1234F1Z5",
                udyam_number="UDYAM-MH-18-0001234",
                registered_address="Plot 12, Industrial Estate, Nashik, Maharashtra",
                registered_state="Maharashtra",
                registered_district="Nashik",
                registered_city="Nashik",
                registered_pincode="422007",
                verification_status={
                    "pan": {
                        "status": "FORMAT_VALIDATED",
                        "source": "Local format validation",
                        "verified_at": None,
                    },
                    "gstin": {
                        "status": "FORMAT_VALIDATED",
                        "source": "Local format validation",
                        "verified_at": None,
                    },
                    "udyam_number": {
                        "status": "FORMAT_VALIDATED",
                        "source": "Local presence check",
                        "verified_at": None,
                    },
                },
                verification_details={},
            )
            db.add(profile)
            await db.flush()

        # 3. Determine applicable approvals (only if none exist yet - idempotent)
        result = await db.execute(
            select(Approval).where(Approval.project_id == project.id)
        )
        approval_rows = result.scalars().all()
        if not approval_rows:
            engine = ApprovalEngine(db)
            await engine.determine_approvals(project.id)
            result = await db.execute(
                select(Approval).where(Approval.project_id == project.id)
            )
            approval_rows = result.scalars().all()

        # 4. Set the demo status story (spec §43) per department/system,
        #    submitting + tracking those approvals against the mock gov systems:
        #      MIDC  -> APPROVED      Fire -> APPROVED      DISH -> UNDER_REVIEW (processing)
        #      MPCB  -> QUERY_RAISED  Boiler -> NOT_STARTED others -> SUBMITTED
        gov_service = GovSyncService(db)
        _demo_status_by_system = {
            "midc": "APPROVED",
            "fire": "APPROVED",
            "maitri": "UNDER_REVIEW",   # DISH / factory licence
            "mpcb": "QUERY_RAISED",     # Consent to Establish query
            "boiler": "NOT_STARTED",
        }
        submitted = 0
        demo_submission_errors = []
        for approval in approval_rows:
            system = system_for_department(approval.department) or "maitri"
            demo_status = _demo_status_by_system.get(system, "SUBMITTED")

            if demo_status == "NOT_STARTED":
                approval.status = ApprovalStatus.NOT_STARTED
                continue

            approval.status = ApprovalStatus[str(demo_status)]
            approval.submitted_at = approval.submitted_at or datetime.now(timezone.utc)
            if demo_status == "APPROVED":
                approval.approved_at = approval.approved_at or datetime.now(timezone.utc)
            try:
                sub = await GatewayService().submit(system, {"sla_days": approval.estimated_processing_days or 30, "application_key": str(approval.id)})
                gov_id = (sub or {}).get("application_id") or ((sub or {}).get("data") or {}).get("application_id")
                if gov_id:
                    approval.application_id = gov_id
                    await gov_service.track(approval, system, gov_id)
                    submitted += 1
            except Exception as exc:
                demo_submission_errors.append({"approval_id": str(approval.id), "system": system, "error": str(exc)})
        # Keep one approved Fire approval close to its configured renewal window so
        # the Step-13 compliance screen demonstrates the full renewal lifecycle.
        fire_approval = next((a for a in approval_rows if "fire" in (a.department or "").lower() and a.status == ApprovalStatus.APPROVED), None)
        if fire_approval and fire_approval.renewal_period_days:
            fire_approval.approved_at = (datetime.now(timezone.utc) - timedelta(days=max(1, fire_approval.renewal_period_days - 30))).replace(tzinfo=None)
        await db.commit()

        # 5. Demo documents (with extracted fields for the doc-AI flow)
        demo_docs = [
            {
                "file_name": "mpcb_consent_to_establish.pdf",
                "content_type": "application/pdf",
                "doc_type": "MPCB CONSENT",
                "fields": {
                    "document_type": "MPCB CONSENT",
                    "name": "ABC Textiles Pvt Ltd",
                    "registration_number": "MPCB-PNE-2024-001",
                    "expiry_date": "2027-04-15",
                    "authority": "MPCB",
                },
            },
            {
                "file_name": "factory_license_DISH.pdf",
                "content_type": "application/pdf",
                "doc_type": "FACTORY LICENSE",
                "fields": {
                    "document_type": "FACTORY LICENSE",
                    "name": "ABC Textiles Pvt Ltd",
                    "registration_number": "FL-2024-PN-5582",
                    "issue_date": "2024-01-15",
                    "expiry_date": "2025-01-14",
                    "authority": "DISH",
                },
            },
        ]
        seed_docs = 0
        for d in demo_docs:
            result = await db.execute(
                select(Document).where(
                    Document.project_id == project.id,
                    Document.file_name == d["file_name"],
                )
            )
            if result.scalar_one_or_none() is None:
                db.add(Document(
                    project_id=project.id,
                    file_name=d["file_name"],
                    file_path=f"demo/{d['file_name']}",
                    file_type=d["content_type"],
                    file_size=1024,
                    status="PROCESSING",
                    extracted_fields=d["fields"],
                    custom_metadata={"document_type": d["doc_type"], "demo": True},
                ))
                seed_docs += 1
        await db.commit()

        # Promote seeded documents into the business-level Data Vault.
        if profile:
            document_result = await db.execute(
                select(Document).where(
                    Document.project_id == project.id,
                    Document.file_name.in_([d["file_name"] for d in demo_docs]),
                )
            )
            for document in document_result.scalars().all():
                link = await db.execute(
                    select(business_profile_documents.c.document_id).where(
                        business_profile_documents.c.business_profile_id == profile.id,
                        business_profile_documents.c.document_id == document.id,
                    )
                )
                if link.first() is None:
                    await db.execute(
                        business_profile_documents.insert().values(
                            business_profile_id=profile.id,
                            document_id=document.id,
                            added_at=datetime.now(timezone.utc),
                        )
                    )
            await db.commit()

        # 6. Seed one grievance so the SIH demo can show the delay -> escalation journey.
        # This is local prototype case management only; no external grievance system is called.
        demo_grievance_created = False
        mpcb_approval = next(
            (a for a in approval_rows if "mpcb" in (a.department or "").lower() and "establish" in (a.name or "").lower()),
            None,
        )
        if mpcb_approval:
            grievance_result = await db.execute(
                select(Grievance).where(
                    Grievance.user_id == user.id,
                    Grievance.approval_id == mpcb_approval.id,
                    Grievance.subject == "MPCB application status update required",
                ).limit(1)
            )
            existing_grievance = grievance_result.scalar_one_or_none()
            if existing_grievance is None:
                now = datetime.utcnow()
                grievance = Grievance(
                    user_id=user.id,
                    project_id=project.id,
                    approval_id=mpcb_approval.id,
                    application_id=mpcb_approval.application_id,
                    department=mpcb_approval.department,
                    category="SLA Concern",
                    subject="MPCB application status update required",
                    description="The application has been under review and the applicant needs a status update before the configured processing target is reached.",
                    priority="HIGH",
                    status="OPEN",
                    escalation_level=0,
                    response_target_at=now + timedelta(days=3),
                )
                db.add(grievance)
                await db.flush()
                db.add(GrievanceEvent(
                    grievance_id=grievance.id,
                    actor_user_id=user.id,
                    event_type="CREATED",
                    from_status=None,
                    to_status="OPEN",
                    note="Demo grievance seeded for SIH walkthrough; prototype case management only.",
                ))
                await db.commit()
                demo_grievance_created = True

        # 7. Seed one inspection visit so the SIH demo opens with a real planner state.
        # This is local prototype scheduling only; it does not call a government system.
        demo_inspection_created = False
        factory_approval = next(
            (a for a in approval_rows if (a.name or "").lower().startswith("factory license")),
            None,
        )
        if factory_approval and factory_approval.status in {
            ApprovalStatus.SUBMITTED, ApprovalStatus.UNDER_REVIEW, ApprovalStatus.INSPECTION
        }:
            existing_visit = await db.execute(
                select(InspectionVisit)
                .join(
                    inspection_visit_approvals,
                    inspection_visit_approvals.c.inspection_visit_id == InspectionVisit.id,
                )
                .where(
                    inspection_visit_approvals.c.approval_id == factory_approval.id,
                    InspectionVisit.status == InspectionVisitStatus.SCHEDULED.value,
                )
                .limit(1)
            )
            if existing_visit.scalar_one_or_none() is None:
                start = (datetime.now(timezone.utc) + timedelta(days=2)).replace(
                    hour=10, minute=0, second=0, microsecond=0, tzinfo=None
                )
                visit = InspectionVisit(
                    project_id=project.id,
                    assigned_officer_id=demo_officer.id if demo_officer else None,
                    scheduled_start=start,
                    scheduled_end=start + timedelta(hours=1),
                    status=InspectionVisitStatus.SCHEDULED.value,
                    location="MIDC Ambad, Nashik, Maharashtra",
                    notes="Demo inspection visit for SIH walkthrough; prototype schedule only.",
                    checklist=[
                        {"id": "site-access", "label": "Site access and inspection area confirmed", "completed": False},
                        {"id": "identity-docs", "label": "Company/project identity documents available", "completed": False},
                        {"id": "safety-equipment", "label": "Workplace safety equipment and controls visible", "completed": False},
                        {"id": "worker-safety", "label": "Worker safety arrangements documented", "completed": False},
                    ],
                    coordination_note="Demo single-approval site visit.",
                )
                db.add(visit)
                await db.flush()
                await db.execute(
                    inspection_visit_approvals.insert().values(
                        inspection_visit_id=visit.id,
                        approval_id=factory_approval.id,
                    )
                )
                if factory_approval.status in {ApprovalStatus.SUBMITTED, ApprovalStatus.UNDER_REVIEW}:
                    factory_approval.status = ApprovalStatus.INSPECTION
                await db.commit()
                demo_inspection_created = True

        # 8. Seed a compact notification inbox for the SIH walkthrough.
        # Notifications are local in-app events; none are sent to external channels.
        from app.notifications.service import NotificationService
        notification_service = NotificationService(db)
        demo_notifications_created = 0
        demo_notification_specs = []
        mpcb_approval = next(
            (a for a in approval_rows if "mpcb" in (a.department or "").lower() and "establish" in (a.name or "").lower()),
            None,
        )
        if mpcb_approval:
            demo_notification_specs.append({
                "title": "MPCB Query Requires Action",
                "message": "A department query is available for your MPCB application. Review the Query Center and prepare your response.",
                "category": "query",
                "severity": "warning",
                "project_id": project.id,
                "reference_id": str(mpcb_approval.id),
            })
            demo_notification_specs.append({
                "title": "MPCB Application Status Updated",
                "message": "Your MPCB application is currently shown as QUERY RAISED in the prototype journey.",
                "category": "approval",
                "severity": "warning",
                "project_id": project.id,
                "reference_id": str(mpcb_approval.id),
            })
        if demo_inspection_created:
            visit_result = await db.execute(
                select(InspectionVisit).where(
                    InspectionVisit.project_id == project.id,
                    InspectionVisit.status == InspectionVisitStatus.SCHEDULED.value,
                ).order_by(InspectionVisit.created_at.desc()).limit(1)
            )
            visit = visit_result.scalar_one_or_none()
            if visit:
                demo_notification_specs.append({
                    "title": "Inspection Scheduled",
                    "message": f"An inspection visit is scheduled for {visit.scheduled_start.strftime('%d %b %Y, %H:%M')} at {visit.location}.",
                    "category": "inspection",
                    "severity": "info",
                    "project_id": project.id,
                    "reference_id": str(visit.id),
                })
        grievance_result = await db.execute(
            select(Grievance).where(
                Grievance.user_id == user.id,
                Grievance.project_id == project.id,
                Grievance.subject == "MPCB application status update required",
            ).order_by(Grievance.created_at.desc()).limit(1)
        )
        demo_grievance = grievance_result.scalar_one_or_none()
        if demo_grievance:
            demo_notification_specs.append({
                "title": "Grievance Opened",
                "message": "Your MPCB status grievance is open and tracked in the UdyogSetu case-management workflow.",
                "category": "grievance",
                "severity": "info",
                "project_id": project.id,
                "reference_id": str(demo_grievance.id),
            })

        for spec in demo_notification_specs:
            existing = await db.execute(
                select(Notification).where(
                    Notification.user_id == user.id,
                    Notification.title == spec["title"],
                    Notification.reference_id == spec["reference_id"],
                ).limit(1)
            )
            if existing.scalar_one_or_none() is None:
                await notification_service.create(**{**spec, "user_id": user.id})
                demo_notifications_created += 1

        # 8b. Seed one application-preparation draft for the SIH walkthrough.
        # Uses an unsubmitted approval so the Step-5 prefill/readiness flow is visible.
        application_preparation_seeded = False
        preparation_approval = next(
            (a for a in approval_rows if a.status == ApprovalStatus.NOT_STARTED),
            None,
        )
        if preparation_approval:
            try:
                prep = ApplicationPreparationService(db)
                await prep.save(
                    preparation_approval.id, user.id,
                    overrides={}, reset_fields=[], document_ids=[], mark_prepared=False,
                )
                application_preparation_seeded = True
            except ValueError:
                pass

        # 9. Seed a versioned regulatory update so the Step-14 center can be
        # demonstrated without presenting fictional content as an official notice.
        # These records are deliberately labelled as prototype knowledge-base data.
        demo_regulatory_created = False
        demo_regulatory_title = "MPCB Consent Rules — Prototype 2026 Update"
        regulatory_result = await db.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.title == demo_regulatory_title).limit(1)
        )
        current_regulation = regulatory_result.scalar_one_or_none()
        if current_regulation is None:
            now = datetime.utcnow()
            previous_effective = now - timedelta(days=120)
            current_effective = now - timedelta(days=7)
            previous = KnowledgeDocument(
                title="MPCB Consent Rules — Prototype 2026 Baseline",
                department="MPCB",
                document_type="REGULATION",
                version="2026.0",
                jurisdiction="Maharashtra",
                sector="Textile",
                effective_date=previous_effective,
                effective_to=current_effective - timedelta(seconds=1),
                is_latest=False,
                text=(
                    "# Applicability\n"
                    "Textile processing projects with pollution potential require consent before establishment.\n\n"
                    "# Documents\n"
                    "Submit the process flow diagram and pollution-control documentation."
                ),
            )
            db.add(previous)
            await db.flush()
            current = KnowledgeDocument(
                title=demo_regulatory_title,
                department="MPCB",
                document_type="REGULATION",
                version="2026.1",
                jurisdiction="Maharashtra",
                sector="Textile",
                effective_date=current_effective,
                is_latest=True,
                supersedes_document_id=previous.id,
                text=(
                    "# Applicability\n"
                    "Textile processing projects with pollution potential require consent before establishment.\n\n"
                    "# Documents\n"
                    "Submit the process flow diagram, pollution-control documentation, and the updated water-balance record.\n\n"
                    "# Inspection\n"
                    "Inspection readiness evidence should be available when requested during review."
                ),
            )
            db.add(current)
            await db.flush()
            previous.superseded_by_document_id = current.id
            db.add_all([
                KnowledgeChunk(
                    document_id=previous.id,
                    chunk_index=0,
                    text=previous.text,
                    custom_metadata={"demo": True, "prototype": True},
                ),
                KnowledgeChunk(
                    document_id=current.id,
                    chunk_index=0,
                    text=current.text,
                    custom_metadata={"demo": True, "prototype": True},
                ),
            ])
            await db.commit()
            current_regulation = current
            demo_regulatory_created = True

        if current_regulation:
            regulatory_notification = {
                "title": "Regulatory Update Available",
                "message": "A versioned prototype knowledge-base update is available for MPCB Consent Rules. Review what changed and potential project impact.",
                "category": "regulatory",
                "severity": "info",
                "project_id": project.id,
                "reference_id": str(current_regulation.id),
            }
            existing_reg_notification = await db.execute(
                select(Notification).where(
                    Notification.user_id == user.id,
                    Notification.title == regulatory_notification["title"],
                    Notification.reference_id == regulatory_notification["reference_id"],
                ).limit(1)
            )
            if existing_reg_notification.scalar_one_or_none() is None:
                await notification_service.create(**{**regulatory_notification, "user_id": user.id})
                demo_notifications_created += 1

        # 9. Seed one incentive preparation case when the configured catalogue contains
        # the PSI entry. This is idempotent and remains a local prototype record; no
        # government application is transmitted.
        incentive_case_created = False
        psi_result = await db.execute(
            select(Scheme).where(
                Scheme.is_active.is_(True),
                Scheme.name == "Packaged Scheme of Incentives (PSI)",
            ).limit(1)
        )
        psi_scheme = psi_result.scalar_one_or_none()
        if psi_scheme:
            case_result = await db.execute(
                select(IncentiveApplicationCase).where(
                    IncentiveApplicationCase.project_id == project.id,
                    IncentiveApplicationCase.scheme_id == psi_scheme.id,
                ).limit(1)
            )
            incentive_case = case_result.scalar_one_or_none()
            if incentive_case is None:
                try:
                    await IncentiveReadinessService(db).prepare_case(
                        project.id, psi_scheme.id, user.id, document_ids=[],
                        notes="Prototype SIH demo preparation case.",
                    )
                    incentive_case_created = True
                except ValueError:
                    # The scheme may no longer match a modified demo project.
                    pass

        return {
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD,
            "user_created": created_user,
            "project_created": created_project,
            "project_id": str(project.id),
            "approvals_determined": len(approval_rows),
            "approvals_submitted": submitted,
            "demo_documents_seeded": seed_docs,
            "demo_grievance_created": demo_grievance_created,
            "officer_email": "officer@udoyogsetu.demo",
            "admin_email": "admin@udoyogsetu.demo",
            "privileged_created": created_privileged,
            "demo_inspection_created": demo_inspection_created,
            "demo_notifications_created": demo_notifications_created,
            "incentive_case_created": incentive_case_created,
            "application_preparation_seeded": application_preparation_seeded,
            "demo_submission_errors": demo_submission_errors,
        }


def main() -> int:
    report = asyncio.run(seed())
    print("=" * 60)
    print("DEMO DATA SEEDED")
    print("=" * 60)
    print(f"Login email : {report['email']}")
    print(f"Password    : {report['password']}")
    print(f"Officer login : {report['officer_email']}")
    print(f"Admin login   : {report['admin_email']}")
    print(f"Project ID  : {report['project_id']}")
    print(f"Approvals   : {report['approvals_determined']} determined, "
          f"{report['approvals_submitted']} submitted")
    print(f"Demo docs   : {report['demo_documents_seeded']}")
    print(f"Privileged accounts created: {report['privileged_created'] or 'none (existed)'}")
    print(f"Demo inspection created: {report['demo_inspection_created']}")
    print(f"Demo notifications created: {report['demo_notifications_created']}")
    print(f"Demo application preparation seeded: {report['application_preparation_seeded']}")
    print(f"Demo submission errors: {report['demo_submission_errors'] or 'none'}")
    print(f"Demo incentive case created: {report['incentive_case_created']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
