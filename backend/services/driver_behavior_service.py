"""
Driver Behavior Service
Analyzes and manages driver behavior data
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import get_settings
from backend.models import (
    DriverBehavior, DrivingEvent, Vehicle, get_async_db_context,
)
from backend.models.driver_behavior import (
    BehaviorRating, EventSeverity, EventType,
)
from backend.utils.helpers import generate_reference_number, timestamp_now
from backend.utils.exceptions import NotFoundException, DatabaseException

settings = get_settings()
logger = logging.getLogger(__name__)


class DriverBehaviorService:
    """
    Service for driver behavior analysis
    """

    def __init__(self):
        self.settings = get_settings()
        logger.info("DriverBehaviorService initialized")

    async def analyze_behavior(
        self,
        vehicle_id: str,
        period_type: str = "DAILY",
    ) -> Dict[str, Any]:
        """Analyze driver behavior for a vehicle"""
        try:
            behavior_id = generate_reference_number("DB")

            async with get_async_db_context() as session:
                # Get vehicle
                v_result = await session.execute(
                    select(Vehicle).where(
                        Vehicle.vehicle_id == vehicle_id
                    )
                )
                vehicle = v_result.scalar_one_or_none()
                if not vehicle:
                    raise NotFoundException(
                        resource="Vehicle", resource_id=vehicle_id
                    )

                # Calculate period
                now = timestamp_now()
                if period_type == "DAILY":
                    period_start = now - timedelta(days=1)
                elif period_type == "WEEKLY":
                    period_start = now - timedelta(weeks=1)
                else:
                    period_start = now - timedelta(days=30)

                # Generate simulated scores
                import random

                acceleration_score = round(random.uniform(60, 100), 1)
                braking_score = round(random.uniform(55, 100), 1)
                cornering_score = round(random.uniform(65, 100), 1)
                speed_score = round(random.uniform(50, 100), 1)
                fuel_score = round(random.uniform(60, 100), 1)
                safety_score = round(random.uniform(70, 100), 1)

                overall_score = round(
                    (
                        acceleration_score * 0.15
                        + braking_score * 0.20
                        + cornering_score * 0.15
                        + speed_score * 0.20
                        + fuel_score * 0.10
                        + safety_score * 0.20
                    ),
                    1,
                )

                # Determine rating
                if overall_score >= 90:
                    rating = BehaviorRating.EXCELLENT
                elif overall_score >= 75:
                    rating = BehaviorRating.GOOD
                elif overall_score >= 60:
                    rating = BehaviorRating.FAIR
                elif overall_score >= 40:
                    rating = BehaviorRating.POOR
                else:
                    rating = BehaviorRating.CRITICAL

                # Create behavior record
                behavior = DriverBehavior(
                    behavior_id=behavior_id,
                    vehicle_id=vehicle.id,
                    vehicle_uuid=vehicle_id,
                    period_start=period_start,
                    period_end=now,
                    period_type=period_type,
                    overall_score=overall_score,
                    rating=rating,
                    acceleration_score=acceleration_score,
                    braking_score=braking_score,
                    cornering_score=cornering_score,
                    speed_score=speed_score,
                    fuel_efficiency_score=fuel_score,
                    safety_score=safety_score,
                    total_distance_km=round(
                        random.uniform(20, 200), 1
                    ),
                    total_driving_time_minutes=random.randint(30, 480),
                    average_speed_kmh=round(
                        random.uniform(25, 80), 1
                    ),
                    max_speed_kmh=round(random.uniform(80, 160), 1),
                    harsh_acceleration_count=random.randint(0, 10),
                    harsh_braking_count=random.randint(0, 8),
                    harsh_cornering_count=random.randint(0, 5),
                    speeding_count=random.randint(0, 15),
                    total_events_count=random.randint(0, 30),
                    risk_score=round(100 - overall_score, 1),
                    score_trend="IMPROVING"
                    if overall_score > 75
                    else "STABLE",
                    recommendations=self._generate_recommendations(
                        acceleration_score,
                        braking_score,
                        speed_score,
                    ),
                    created_at=timestamp_now(),
                )

                session.add(behavior)
                await session.commit()
                await session.refresh(behavior)

                logger.info(
                    f"Analyzed behavior for {vehicle_id}: score={overall_score}"
                )
                return behavior.to_dict()

        except NotFoundException:
            raise
        except Exception as e:
            logger.error(
                f"Error analyzing behavior for {vehicle_id}: {e}"
            )
            raise DatabaseException(
                message="Failed to analyze driver behavior",
                operation="create",
                original_error=e,
            )

    async def get_behavior(
        self, vehicle_id: str, period_type: str = "DAILY"
    ) -> Optional[Dict[str, Any]]:
        """Get latest behavior analysis for a vehicle"""
        try:
            async with get_async_db_context() as session:
                result = await session.execute(
                    select(DriverBehavior)
                    .where(
                        and_(
                            DriverBehavior.vehicle_uuid == vehicle_id,
                            DriverBehavior.period_type == period_type,
                        )
                    )
                    .order_by(desc(DriverBehavior.created_at))
                    .limit(1)
                )
                behavior = result.scalar_one_or_none()

                if not behavior:
                    return None

                return behavior.to_dict()

        except Exception as e:
            logger.error(
                f"Error getting behavior for {vehicle_id}: {e}"
            )
            raise DatabaseException(
                message="Failed to get driver behavior",
                operation="read",
                original_error=e,
            )

    async def get_behavior_history(
        self,
        vehicle_id: str,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get behavior history for a vehicle"""
        try:
            async with get_async_db_context() as session:
                result = await session.execute(
                    select(DriverBehavior)
                    .where(
                        DriverBehavior.vehicle_uuid == vehicle_id
                    )
                    .order_by(desc(DriverBehavior.created_at))
                    .limit(limit)
                )
                behaviors = result.scalars().all()

                return [b.to_dict() for b in behaviors]

        except Exception as e:
            logger.error(
                f"Error getting behavior history for {vehicle_id}: {e}"
            )
            raise DatabaseException(
                message="Failed to get behavior history",
                operation="read",
                original_error=e,
            )

    def _generate_recommendations(
        self,
        acceleration_score: float,
        braking_score: float,
        speed_score: float,
    ) -> List[str]:
        """Generate driving recommendations"""
        recommendations = []

        if acceleration_score < 70:
            recommendations.append(
                "Avoid harsh acceleration. Gradually increase speed for better fuel efficiency."
            )
        if braking_score < 70:
            recommendations.append(
                "Maintain safe following distance. Apply brakes gradually."
            )
        if speed_score < 70:
            recommendations.append(
                "Reduce speed in urban areas. Follow posted speed limits."
            )

        if not recommendations:
            recommendations.append(
                "Excellent driving! Keep up the safe driving habits."
            )

        return recommendations


# Singleton instance
_driver_behavior_service: Optional[DriverBehaviorService] = None


def get_driver_behavior_service() -> DriverBehaviorService:
    """Get or create driver behavior service instance"""
    global _driver_behavior_service
    if _driver_behavior_service is None:
        _driver_behavior_service = DriverBehaviorService()
    return _driver_behavior_service