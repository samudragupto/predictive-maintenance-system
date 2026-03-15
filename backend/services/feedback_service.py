"""
Feedback Service
Manages post-service feedback and RCA/CAPA processes
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import get_settings
from backend.models import (
    Feedback, RCAReport, CAPAAction, Vehicle, get_async_db_context,
)
from backend.models.feedback import (
    FeedbackType, FeedbackSentiment, RCAStatus, CAPAStatus, CAPAType,
)
from backend.utils.helpers import generate_reference_number, timestamp_now
from backend.utils.exceptions import NotFoundException, DatabaseException

settings = get_settings()
logger = logging.getLogger(__name__)


class FeedbackService:
    """
    Service for managing feedback, RCA, and CAPA
    """

    def __init__(self):
        self.settings = get_settings()
        logger.info("FeedbackService initialized")

    async def create_feedback(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new feedback entry"""
        try:
            feedback_id = generate_reference_number("FB")

            async with get_async_db_context() as session:
                # Get vehicle
                v_result = await session.execute(
                    select(Vehicle).where(
                        Vehicle.vehicle_id == data["vehicle_id"]
                    )
                )
                vehicle = v_result.scalar_one_or_none()
                if not vehicle:
                    raise NotFoundException(
                        resource="Vehicle",
                        resource_id=data["vehicle_id"],
                    )

                # Determine sentiment
                overall_rating = data.get("overall_rating")
                sentiment = None
                if overall_rating:
                    if overall_rating >= 4:
                        sentiment = FeedbackSentiment.POSITIVE
                    elif overall_rating >= 3:
                        sentiment = FeedbackSentiment.NEUTRAL
                    else:
                        sentiment = FeedbackSentiment.NEGATIVE

                # Calculate cost variance if both available
                cost_variance = None
                cost_variance_percent = None
                estimated_cost = data.get("estimated_cost")
                actual_cost = data.get("actual_cost")
                if estimated_cost and actual_cost:
                    cost_variance = actual_cost - estimated_cost
                    if estimated_cost > 0:
                        cost_variance_percent = (
                            cost_variance / estimated_cost
                        ) * 100

                feedback = Feedback(
                    feedback_id=feedback_id,
                    vehicle_id=vehicle.id,
                    vehicle_uuid=data["vehicle_id"],
                    feedback_type=FeedbackType(
                        data.get("feedback_type", "SERVICE_FEEDBACK")
                    ),
                    overall_rating=overall_rating,
                    service_quality_rating=data.get(
                        "service_quality_rating"
                    ),
                    timeliness_rating=data.get("timeliness_rating"),
                    communication_rating=data.get(
                        "communication_rating"
                    ),
                    value_for_money_rating=data.get(
                        "value_for_money_rating"
                    ),
                    nps_score=data.get("nps_score"),
                    customer_comments=data.get("customer_comments"),
                    sentiment=sentiment,
                    issue_resolved=data.get("issue_resolved"),
                    first_time_fix=data.get("first_time_fix"),
                    prediction_was_accurate=data.get(
                        "prediction_was_accurate"
                    ),
                    actual_issue_description=data.get(
                        "actual_issue_description"
                    ),
                    estimated_cost=estimated_cost,
                    actual_cost=actual_cost,
                    cost_variance=cost_variance,
                    cost_variance_percent=cost_variance_percent,
                    feedback_source=data.get("feedback_source", "APP"),
                    feedback_date=timestamp_now(),
                    created_at=timestamp_now(),
                )

                # Check if RCA should be triggered
                if sentiment == FeedbackSentiment.NEGATIVE or (
                    data.get("prediction_was_accurate") is False
                ):
                    feedback.triggers_rca = True

                session.add(feedback)
                await session.commit()
                await session.refresh(feedback)

                # Auto-create RCA if triggered
                if feedback.triggers_rca:
                    await self._auto_create_rca(session, feedback)

                logger.info(f"Created feedback: {feedback_id}")
                return feedback.to_dict()

        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error creating feedback: {e}")
            raise DatabaseException(
                message="Failed to create feedback",
                operation="create",
                original_error=e,
            )

    async def get_feedback(self, feedback_id: str) -> Dict[str, Any]:
        """Get feedback by ID"""
        try:
            async with get_async_db_context() as session:
                result = await session.execute(
                    select(Feedback).where(
                        Feedback.feedback_id == feedback_id
                    )
                )
                feedback = result.scalar_one_or_none()
                if not feedback:
                    raise NotFoundException(
                        resource="Feedback",
                        resource_id=feedback_id,
                    )
                return feedback.to_dict()

        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error getting feedback: {e}")
            raise DatabaseException(
                message="Failed to get feedback",
                operation="read",
                original_error=e,
            )

    async def get_vehicle_feedbacks(
        self,
        vehicle_id: str,
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """Get feedbacks for a vehicle"""
        try:
            async with get_async_db_context() as session:
                query = select(Feedback).where(
                    Feedback.vehicle_uuid == vehicle_id
                )
                count_query = select(func.count(Feedback.id)).where(
                    Feedback.vehicle_uuid == vehicle_id
                )

                total_result = await session.execute(count_query)
                total = total_result.scalar() or 0

                offset = (page - 1) * page_size
                query = (
                    query.order_by(desc(Feedback.created_at))
                    .offset(offset)
                    .limit(page_size)
                )

                result = await session.execute(query)
                feedbacks = result.scalars().all()

                return {
                    "success": True,
                    "data": [f.to_dict() for f in feedbacks],
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size,
                }

        except Exception as e:
            logger.error(
                f"Error getting feedbacks for {vehicle_id}: {e}"
            )
            raise DatabaseException(
                message="Failed to get vehicle feedbacks",
                operation="read",
                original_error=e,
            )

    async def create_rca(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an RCA report"""
        try:
            rca_id = generate_reference_number("RCA")

            async with get_async_db_context() as session:
                rca = RCAReport(
                    rca_id=rca_id,
                    trigger_type=data.get("trigger_type", "MANUAL"),
                    trigger_reference_id=data.get("trigger_reference_id"),
                    status=RCAStatus.OPEN,
                    priority=data.get("priority", "MEDIUM"),
                    problem_title=data["problem_title"],
                    problem_description=data["problem_description"],
                    vehicles_affected_count=data.get(
                        "vehicles_affected_count", 1
                    ),
                    affected_vehicle_ids=data.get(
                        "affected_vehicle_ids"
                    ),
                    issue_reported_date=timestamp_now(),
                    assigned_to=data.get("assigned_to"),
                    assigned_team=data.get("assigned_team"),
                    created_at=timestamp_now(),
                )

                session.add(rca)
                await session.commit()
                await session.refresh(rca)

                logger.info(f"Created RCA report: {rca_id}")
                return rca.to_dict()

        except Exception as e:
            logger.error(f"Error creating RCA: {e}")
            raise DatabaseException(
                message="Failed to create RCA report",
                operation="create",
                original_error=e,
            )

    async def get_rca_reports(
        self,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get RCA reports"""
        try:
            async with get_async_db_context() as session:
                query = select(RCAReport)

                if status:
                    query = query.where(
                        RCAReport.status == RCAStatus(status)
                    )

                query = (
                    query.order_by(desc(RCAReport.created_at))
                    .limit(limit)
                )

                result = await session.execute(query)
                reports = result.scalars().all()

                return [r.to_dict() for r in reports]

        except Exception as e:
            logger.error(f"Error getting RCA reports: {e}")
            raise DatabaseException(
                message="Failed to get RCA reports",
                operation="read",
                original_error=e,
            )

    async def create_capa(
        self, rca_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a CAPA action"""
        try:
            capa_id = generate_reference_number("CAPA")

            async with get_async_db_context() as session:
                # Get RCA report
                rca_result = await session.execute(
                    select(RCAReport).where(RCAReport.rca_id == rca_id)
                )
                rca = rca_result.scalar_one_or_none()
                if not rca:
                    raise NotFoundException(
                        resource="RCA Report", resource_id=rca_id
                    )

                capa = CAPAAction(
                    capa_id=capa_id,
                    rca_id=rca.id,
                    capa_type=CAPAType(
                        data.get("capa_type", "CORRECTIVE")
                    ),
                    status=CAPAStatus.PLANNED,
                    priority=data.get("priority", "MEDIUM"),
                    action_title=data["action_title"],
                    action_description=data["action_description"],
                    expected_outcome=data.get("expected_outcome"),
                    scope=data.get("scope", "SHORT_TERM"),
                    assigned_to=data.get("assigned_to"),
                    planned_start_date=data.get("planned_start_date"),
                    planned_completion_date=data.get(
                        "planned_completion_date"
                    ),
                    estimated_cost=data.get("estimated_cost"),
                    created_at=timestamp_now(),
                )

                session.add(capa)
                await session.commit()
                await session.refresh(capa)

                logger.info(f"Created CAPA: {capa_id}")
                return capa.to_dict()

        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error creating CAPA: {e}")
            raise DatabaseException(
                message="Failed to create CAPA",
                operation="create",
                original_error=e,
            )

    async def _auto_create_rca(
        self, session: AsyncSession, feedback: Feedback
    ) -> None:
        """Auto-create RCA from negative feedback"""
        try:
            rca_id = generate_reference_number("RCA")

            reason = "Negative customer feedback"
            if feedback.prediction_was_accurate is False:
                reason = "Prediction accuracy issue"

            rca = RCAReport(
                rca_id=rca_id,
                trigger_type="FEEDBACK",
                trigger_reference_id=feedback.feedback_id,
                status=RCAStatus.OPEN,
                priority="HIGH",
                problem_title=f"Feedback Issue - {feedback.vehicle_uuid}",
                problem_description=(
                    f"Auto-generated RCA from feedback {feedback.feedback_id}. "
                    f"Reason: {reason}. "
                    f"Customer comment: {feedback.customer_comments or 'N/A'}"
                ),
                affected_vehicle_ids=[feedback.vehicle_uuid],
                issue_reported_date=timestamp_now(),
                created_at=timestamp_now(),
            )

            session.add(rca)
            await session.flush()

            feedback.rca_id = rca.id

            logger.info(
                f"Auto-created RCA {rca_id} from feedback {feedback.feedback_id}"
            )

        except Exception as e:
            logger.error(f"Error auto-creating RCA: {e}")

    async def get_feedback_stats(self) -> Dict[str, Any]:
        """Get feedback statistics"""
        try:
            async with get_async_db_context() as session:
                total_result = await session.execute(
                    select(func.count(Feedback.id))
                )
                total = total_result.scalar() or 0

                avg_rating_result = await session.execute(
                    select(func.avg(Feedback.overall_rating)).where(
                        Feedback.overall_rating.isnot(None)
                    )
                )
                avg_rating = round(
                    avg_rating_result.scalar() or 0, 2
                )

                positive_result = await session.execute(
                    select(func.count(Feedback.id)).where(
                        Feedback.sentiment == FeedbackSentiment.POSITIVE
                    )
                )
                positive = positive_result.scalar() or 0

                negative_result = await session.execute(
                    select(func.count(Feedback.id)).where(
                        Feedback.sentiment == FeedbackSentiment.NEGATIVE
                    )
                )
                negative = negative_result.scalar() or 0

                resolved_result = await session.execute(
                    select(func.count(Feedback.id)).where(
                        Feedback.issue_resolved == True
                    )
                )
                resolved = resolved_result.scalar() or 0

                return {
                    "total_feedbacks": total,
                    "average_rating": avg_rating,
                    "positive_count": positive,
                    "negative_count": negative,
                    "issues_resolved": resolved,
                    "resolution_rate": round(
                        (resolved / total * 100) if total > 0 else 0, 1
                    ),
                }

        except Exception as e:
            logger.error(f"Error getting feedback stats: {e}")
            raise DatabaseException(
                message="Failed to get feedback stats",
                operation="read",
                original_error=e,
            )


# Singleton instance
_feedback_service: Optional[FeedbackService] = None


def get_feedback_service() -> FeedbackService:
    """Get or create feedback service instance"""
    global _feedback_service
    if _feedback_service is None:
        _feedback_service = FeedbackService()
    return _feedback_service