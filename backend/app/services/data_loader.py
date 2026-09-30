import asyncio
import json
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ApprovalRule, GovernmentService, KnowledgeDocument, Scheme
from app.rag.pipeline import RAGPipeline


def _read_json(filepath: str):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def _read_text(filepath: str) -> str:
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


class RuleLoadingService:
    """Service for loading rules and schemes data"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def load_approval_rules(self, filepath: str):
        """Load approval rules from JSON file"""
        rules_data = await asyncio.to_thread(_read_json, filepath)
        
        # The JSON catalog uses stable rule IDs (for example ``rule_002``) while
        # the database model intentionally uses generated UUIDs. Normalize catalog
        # dependencies to rule names so the graph can resolve them without relying
        # on a discarded external identifier.
        rule_name_by_catalog_id = {
            str(rule_data.get('id')): rule_data['name']
            for rule_data in rules_data
            if rule_data.get('id') and rule_data.get('name')
        }

        for rule_data in rules_data:
            result = await self.db.execute(
                select(ApprovalRule).where(
                    ApprovalRule.name == rule_data['name']
                )
            )
            existing = result.scalar_one_or_none()
            raw_dependencies = rule_data.get('dependencies', []) or []
            if isinstance(raw_dependencies, str):
                raw_dependencies = [raw_dependencies]
            normalized_dependencies = [
                rule_name_by_catalog_id.get(str(dep), str(dep))
                for dep in raw_dependencies
            ]

            if existing:
                # Repair older seeded rows that retained the catalog IDs.
                if existing.dependencies != normalized_dependencies:
                    existing.dependencies = normalized_dependencies
                continue

            rule = ApprovalRule(
                name=rule_data['name'],
                department=rule_data['department'],
                sector=rule_data.get('sector'),
                conditions=rule_data['conditions'],
                is_mandatory=rule_data.get('is_mandatory', False),
                required_documents=rule_data.get('required_documents', []),
                dependencies=normalized_dependencies,
                estimated_processing_days=rule_data.get('estimated_processing_days'),
                renewal_period_days=rule_data.get('renewal_period_days'),
                risk_level=rule_data.get('risk_level', 'MEDIUM'),
                source=rule_data.get('source'),
                source_url=rule_data.get('source_url'),
            )

            self.db.add(rule)
        
        await self.db.commit()
    
    async def load_schemes(self, filepath: str):
        """Load schemes from JSON file"""
        schemes_data = await asyncio.to_thread(_read_json, filepath)
        
        for scheme_data in schemes_data:
            # Check if scheme exists
            result = await self.db.execute(
                select(Scheme).where(Scheme.name == scheme_data['name'])
            )
            
            if result.scalar_one_or_none():
                continue  # Skip existing
            
            scheme = Scheme(
                name=scheme_data['name'],
                department=scheme_data['department'],
                sector=scheme_data.get('sector'),
                location=scheme_data.get('location'),
                min_investment=scheme_data.get('min_investment'),
                max_investment=scheme_data.get('max_investment'),
                eligible_entity=scheme_data.get('eligible_entity'),
                employee_requirement=scheme_data.get('employee_requirement'),
                benefits=scheme_data.get('benefits', []),
                application_period=scheme_data.get('application_period'),
                required_documents=scheme_data.get('required_documents', []),
                source=scheme_data.get('source'),
                source_url=scheme_data.get('source_url'),
            )
            
            self.db.add(scheme)
        
        await self.db.commit()
    
    async def load_explore_services(self, filepath: str):
        """Load the Explore Government Services catalog from a JSON file.

        Idempotent by ``slug``. A service referencing a rule by name resolves to
        that rule's id at load time (rules load first, so they exist already).
        """
        services_data = await asyncio.to_thread(_read_json, filepath)
        for svc_data in services_data:
            result = await self.db.execute(
                select(GovernmentService).where(
                    GovernmentService.slug == svc_data['slug']
                )
            )
            if result.scalar_one_or_none():
                continue

            rule_id = None
            rule_name = svc_data.get('link_approval_rule')
            if rule_name:
                result = await self.db.execute(
                    select(ApprovalRule).where(ApprovalRule.name == rule_name)
                )
                rule = result.scalar_one_or_none()
                rule_id = rule.id if rule else None

            service = GovernmentService(
                slug=svc_data['slug'],
                name=svc_data['name'],
                description=svc_data.get('description'),
                category=svc_data['category'],
                authority=svc_data['authority'],
                department=svc_data['department'],
                service_type=svc_data.get('service_type', 'APPROVAL'),
                application_mode=svc_data.get('application_mode', 'GUIDED'),
                official_reference=svc_data.get('official_reference'),
                external_portal_url=svc_data.get('external_portal_url'),
                applicable_documents=svc_data.get('applicable_documents', []),
                fees=svc_data.get('fees'),
                eligibility_summary=svc_data.get('eligibility_summary'),
                risk_level=svc_data.get('risk_level', 'MEDIUM'),
                sla_days=svc_data.get('sla_days'),
                renewal_period_days=svc_data.get('renewal_period_days'),
                approval_rule_id=rule_id,
                gateway_system=svc_data.get('gateway_system'),
                is_demo=svc_data.get('is_demo', False),
                is_active=svc_data.get('is_active', True),
            )

            self.db.add(service)

        await self.db.commit()

    def _guess_department(self, title: str) -> str:
        keywords = {
            "mpcb": "Maharashtra Pollution Control Board",
            "factory": "Directorate of Industrial Safety and Health",
            "boiler": "Directorate of Steam Boilers",
            "fire": "Fire Services Department",
            "labour": "Labour Department",
            "gst": "GST Department",
            "shops": "Labour Department",
            "electricity": "Electricity Regulatory Commission",
        }
        lowered = title.lower()
        for token, department in keywords.items():
            if token in lowered:
                return department
        return "Regulatory Authority"
    
    async def load_knowledge_documents(self, directory: str):
        """Load regulation knowledge documents from a directory (one file per doc)."""
        if not directory or not os.path.isdir(directory):
            return
        
        pipeline = RAGPipeline(self.db)
        for filename in sorted(os.listdir(directory)):
            if not filename.lower().endswith(('.txt', '.md')):
                continue
            
            filepath = os.path.join(directory, filename)
            text = (await asyncio.to_thread(_read_text, filepath)).strip()
            if not text:
                continue
            
            title = os.path.splitext(filename.replace('_', ' '))[0].title()
            
            result = await self.db.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.title == title)
            )
            if result.scalar_one_or_none():
                continue  # Skip existing
            
            await pipeline.ingest_document(
                title=title,
                text=text,
                metadata={
                    "document_type": "REGULATION",
                    "department": self._guess_department(title),
                    "jurisdiction": "Maharashtra",
                    "source_url": None,
                },
            )
