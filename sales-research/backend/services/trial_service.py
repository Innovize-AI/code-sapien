import logging
import os
import json
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, or_, desc
from db.models import (
    Organization, OrganizationSettings, Profile,
    ResearchReport, LeadSubmission, Competitor, 
    IdentifiedProfile, Activity, AutopilotRule,
    UserSettings, CompetitorAnalysis, CRMContext
)
from services.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)

class TrialService:
    def __init__(self):
        self.knowledge_service = KnowledgeService()

    async def onboard_trial_organization(self, db: AsyncSession, organization_id: str, user_id: str) -> bool:
        """
        Comprehensive onboarding for a trial organization.
        Handles:
        1. Settings lookup/creation.
        2. Pinecone index provisioning.
        3. Legacy data stitching.
        4. Metadata updates.
        """
        from uuid import UUID
        u_id = UUID(user_id) if isinstance(user_id, str) else user_id
        org_id = UUID(organization_id) if isinstance(organization_id, str) else organization_id

        try:
            # 1. Fetch or Create Organization Settings
            # Look for settings linked to this ORG first (shared settings)
            # Then fallback to settings owned by this USER
            settings_res = await db.execute(
                select(OrganizationSettings)
                .where(or_(
                    OrganizationSettings.organization_id == org_id,
                    OrganizationSettings.owner_id == u_id,
                    OrganizationSettings.owner_id.in_(
                        select(Profile.id).where(Profile.organization_id == org_id)
                    )
                ))
                .order_by(desc(OrganizationSettings.organization_id), desc(OrganizationSettings.owner_id))
            )
            settings = settings_res.scalars().first()
            
            if not settings:
                # Look for orphaned settings (no owner, no org)
                orph_res = await db.execute(select(OrganizationSettings).where(OrganizationSettings.organization_id == None, OrganizationSettings.owner_id == None))
                settings = orph_res.scalars().first()
                
                if not settings:
                    logger.info(f"Creating new settings for org {org_id}")
                    settings = OrganizationSettings(organization_id=org_id, owner_id=u_id)
                    db.add(settings)
                else:
                    logger.info(f"Claiming orphaned settings for {u_id}")
                    settings.organization_id = org_id
                    settings.owner_id = u_id
            else:
                # Ensure organization_id is set
                if settings.organization_id != org_id:
                    settings.organization_id = org_id
                if settings.owner_id is None:
                    settings.owner_id = u_id

            # 2. Pinecone Index Provisioning
            index_name = f"tr-{str(org_id)}"
            if settings.pinecone_index_name != index_name:
                logger.info(f"Provisioning Pinecone index {index_name} for organization {org_id}")
                success = await self.knowledge_service.create_trial_index(index_name)
                if not success:
                    logger.error(f"Failed to provision Pinecone index for organization {org_id}")
                    return False
                settings.pinecone_index_name = index_name

            # 3. Legacy Data Stitching
            logger.info(f"Stitching legacy data for user {u_id} into org {org_id}")
            await self.stitch_legacy_data(db, u_id, org_id)

            # 4. Update Metadata
            settings.onboarding_complete = 1
            
            result = await db.execute(select(Profile).where(Profile.id == u_id))
            profile = result.scalars().first()
            if profile:
                metadata = json.loads(profile.profile_metadata or "{}") if isinstance(profile.profile_metadata, str) else (profile.profile_metadata or {})
                metadata["is_trial"] = True
                metadata["migration_complete"] = True
                profile.profile_metadata = json.dumps(metadata)

            await db.commit()
            logger.info(f"Successfully onboarded organization {org_id} to trial.")
            return True

        except Exception as e:
            logger.error(f"Error during trial onboarding: {e}")
            await db.rollback()
            return False

    async def stitch_legacy_data(self, db: AsyncSession, user_id: Any, org_id: Any):
        """
        Backfills organization_id for all historical records created by this user.
        """
        stitching_map = {
            ResearchReport: "created_by_id",
            LeadSubmission: "created_by_id",
            Competitor: "created_by_id",
            IdentifiedProfile: "created_by_id",
            Activity: "created_by_id",
            AutopilotRule: "created_by_id",
            UserSettings: "user_id",
            OrganizationSettings: "owner_id",
            CompetitorAnalysis: "organization_id"
        }
        
        for table, col_name in stitching_map.items():
            try:
                match_col = getattr(table, col_name, None)
                if match_col is not None:
                    if col_name == "organization_id":
                        stmt = update(table).where(table.organization_id == None).values(organization_id=org_id)
                        await db.execute(stmt)
                        continue
                    
                    stmt = (
                        update(table)
                        .where(match_col == user_id)
                        .where(table.organization_id == None)
                        .values(organization_id=org_id)
                    )
                    await db.execute(stmt)

                    # Deep Stitching logic
                    if table == IdentifiedProfile:
                        deep_stmt = (
                            update(IdentifiedProfile)
                            .where(IdentifiedProfile.organization_id == None)
                            .where(
                                IdentifiedProfile.linkedin_url.in_(
                                    select(ResearchReport.linkedin_url)
                                    .where(ResearchReport.organization_id == org_id)
                                )
                            )
                            .values(organization_id=org_id)
                        )
                        await db.execute(deep_stmt)

            except Exception as e:
                logger.error(f"Error stitching table {table.__tablename__}: {e}")

trial_service = TrialService()
