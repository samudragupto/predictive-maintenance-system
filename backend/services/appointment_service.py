"""
Appointment Service
Handles scheduling and management of service appointments
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import get_settings
from backend.models import (
    ServiceAppointment, ServiceCenter, Vehicle,
    Diagnosis, CostEstimate, get_async_db_context,
)
from backend.models.service_appointment import (
    AppointmentStatus, AppointmentType, UrgencyLevel,
)
from backend.models.service_center import CenterStatus
from backend.utils.helpers import (
    generate_reference_number, timestamp_now, calculate_distance,
)
from backend.utils.exceptions import (
    NotFoundException,
    ConflictException,
    ValidationException,
    DatabaseException,
    AgentException,
)

settings = get_settings()
logger = logging.getLogger(__name__)


class AppointmentService:
    """
    Service for managing appointments
    """

    def __init__(self):
        self.settings = get_settings()
        logger.info("AppointmentService initialized")

    async def create_appointment(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new appointment"""
        try:
            appointment_id = generate_reference_number("APT")

            async with get_async_db_context() as session:
                # Validate vehicle
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

                # Validate service center
                sc_result = await session.execute(
                    select(ServiceCenter).where(
                        ServiceCenter.id == data["service_center_id"]
                    )
                )
                service_center = sc_result.scalar_one_or_none()
                if not service_center:
                    raise NotFoundException(
                        resource="Service Center",
                        resource_id=str(data["service_center_id"]),
                    )

                # Parse scheduled date
                scheduled_date = data.get("scheduled_date")
                if isinstance(scheduled_date, str):
                    scheduled_date = datetime.fromisoformat(
                        scheduled_date.replace("Z", "+00:00")
                    )

                # Check for conflicting appointments
                existing = await session.execute(
                    select(ServiceAppointment).where(
                        and_(
                            ServiceAppointment.vehicle_uuid == data["vehicle_id"],
                            ServiceAppointment.scheduled_date == scheduled_date,
                            ServiceAppointment.status.notin_(
                                [
                                    AppointmentStatus.CANCELLED,
                                    AppointmentStatus.COMPLETED,
                                ]
                            ),
                        )
                    )
                )
                if existing.scalar_one_or_none():
                    raise ConflictException(
                        message="Vehicle already has an appointment at this time"
                    )

                # Create appointment
                appointment = ServiceAppointment(
                    appointment_id=appointment_id,
                    vehicle_id=vehicle.id,
                    vehicle_uuid=data["vehicle_id"],
                    service_center_id=data["service_center_id"],
                    status=AppointmentStatus.SCHEDULED,
                    appointment_type=AppointmentType(
                        data.get(
                            "appointment_type", "SCHEDULED_MAINTENANCE"
                        )
                    ),
                    urgency=UrgencyLevel(data.get("urgency", "MEDIUM")),
                    scheduled_date=scheduled_date,
                    estimated_duration_minutes=data.get(
                        "estimated_duration_minutes", 60
                    ),
                    service_description=data.get("service_description"),
                    ai_scheduled=data.get("ai_scheduled", False),
                    scheduling_reason=data.get("scheduling_reason"),
                    customer_name=data.get("customer_name", vehicle.owner_name),
                    customer_phone=data.get("customer_phone", vehicle.owner_contact),
                    customer_email=data.get("customer_email"),
                    customer_notes=data.get("customer_notes"),
                    created_at=timestamp_now(),
                    created_by=data.get("created_by", "system"),
                )

                session.add(appointment)
                await session.commit()
                await session.refresh(appointment)

                logger.info(f"Created appointment {appointment_id}")
                return appointment.to_dict()

        except (NotFoundException, ConflictException, ValidationException):
            raise
        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            raise DatabaseException(
                message="Failed to create appointment",
                operation="create",
                original_error=e,
            )

    async def auto_schedule(
        self,
        vehicle_id: str,
        diagnosis_id: Optional[str] = None,
        urgency: str = "MEDIUM",
    ) -> Dict[str, Any]:
        """Automatically schedule a service appointment"""
        try:
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

                # Find nearest available service center
                sc_result = await session.execute(
                    select(ServiceCenter).where(
                        ServiceCenter.status == CenterStatus.ACTIVE
                    )
                )
                centers = sc_result.scalars().all()

                if not centers:
                    raise NotFoundException(
                        resource="Service Center",
                        resource_id="any available",
                    )

                # Pick the best center
                best_center = centers[0]
                if vehicle.last_latitude and vehicle.last_longitude:
                    best_center = min(
                        [c for c in centers if c.latitude and c.longitude],
                        key=lambda c: calculate_distance(
                            vehicle.last_latitude,
                            vehicle.last_longitude,
                            c.latitude,
                            c.longitude,
                        ),
                        default=centers[0],
                    )

                # Determine scheduled date based on urgency
                urgency_days = {
                    "CRITICAL": 1,
                    "HIGH": 3,
                    "MEDIUM": 7,
                    "LOW": 14,
                }
                days_out = urgency_days.get(urgency, 7)
                scheduled_date = timestamp_now() + timedelta(days=days_out)

                # Set to 9 AM
                scheduled_date = scheduled_date.replace(
                    hour=9, minute=0, second=0, microsecond=0
                )

                # Skip weekends
                while scheduled_date.weekday() >= 5:
                    scheduled_date += timedelta(days=1)

                # Create the appointment
                appointment_data = {
                    "vehicle_id": vehicle_id,
                    "service_center_id": best_center.id,
                    "appointment_type": "PREDICTIVE_MAINTENANCE",
                    "urgency": urgency,
                    "scheduled_date": scheduled_date,
                    "estimated_duration_minutes": 90,
                    "service_description": f"AI-scheduled {urgency.lower()} priority maintenance",
                    "ai_scheduled": True,
                    "scheduling_reason": f"Auto-scheduled based on diagnosis. Urgency: {urgency}",
                    "created_by": "scheduling_agent",
                }

                result = await self.create_appointment(appointment_data)

                return {
                    **result,
                    "service_center_name": best_center.name,
                    "auto_scheduled": True,
                }

        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error auto-scheduling for {vehicle_id}: {e}")
            raise AgentException(
                message="Failed to auto-schedule appointment",
                agent_type="SCHEDULING_AGENT",
                action="auto_schedule",
            )

    async def get_appointment(
        self, appointment_id: str
    ) -> Dict[str, Any]:
        """Get an appointment by ID"""
        try:
            async with get_async_db_context() as session:
                result = await session.execute(
                    select(ServiceAppointment).where(
                        ServiceAppointment.appointment_id == appointment_id
                    )
                )
                appointment = result.scalar_one_or_none()

                if not appointment:
                    raise NotFoundException(
                        resource="Appointment",
                        resource_id=appointment_id,
                    )

                return appointment.to_dict()

        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error getting appointment {appointment_id}: {e}")
            raise DatabaseException(
                message="Failed to get appointment",
                operation="read",
                original_error=e,
            )

    async def get_appointments(
        self,
        page: int = 1,
        page_size: int = 20,
        vehicle_id: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get paginated appointments"""
        try:
            async with get_async_db_context() as session:
                query = select(ServiceAppointment)
                count_query = select(func.count(ServiceAppointment.id))

                if vehicle_id:
                    query = query.where(
                        ServiceAppointment.vehicle_uuid == vehicle_id
                    )
                    count_query = count_query.where(
                        ServiceAppointment.vehicle_uuid == vehicle_id
                    )

                if status:
                    query = query.where(
                        ServiceAppointment.status == AppointmentStatus(status)
                    )
                    count_query = count_query.where(
                        ServiceAppointment.status == AppointmentStatus(status)
                    )

                if date_from:
                    query = query.where(
                        ServiceAppointment.scheduled_date >= date_from
                    )
                    count_query = count_query.where(
                        ServiceAppointment.scheduled_date >= date_from
                    )

                if date_to:
                    query = query.where(
                        ServiceAppointment.scheduled_date <= date_to
                    )
                    count_query = count_query.where(
                        ServiceAppointment.scheduled_date <= date_to
                    )

                total_result = await session.execute(count_query)
                total = total_result.scalar() or 0

                offset = (page - 1) * page_size
                query = (
                    query.order_by(desc(ServiceAppointment.scheduled_date))
                    .offset(offset)
                    .limit(page_size)
                )

                result = await session.execute(query)
                appointments = result.scalars().all()

                return {
                    "success": True,
                    "data": [a.to_dict() for a in appointments],
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size,
                }

        except Exception as e:
            logger.error(f"Error listing appointments: {e}")
            raise DatabaseException(
                message="Failed to list appointments",
                operation="read",
                original_error=e,
            )

    async def update_appointment_status(
        self,
        appointment_id: str,
        new_status: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update appointment status"""
        try:
            async with get_async_db_context() as session:
                result = await session.execute(
                    select(ServiceAppointment).where(
                        ServiceAppointment.appointment_id == appointment_id
                    )
                )
                appointment = result.scalar_one_or_none()

                if not appointment:
                    raise NotFoundException(
                        resource="Appointment",
                        resource_id=appointment_id,
                    )

                new_status_enum = AppointmentStatus(new_status)
                appointment.status = new_status_enum
                appointment.updated_at = timestamp_now()

                if new_status_enum == AppointmentStatus.CHECKED_IN:
                    appointment.check_in_time = timestamp_now()
                elif new_status_enum == AppointmentStatus.IN_PROGRESS:
                    appointment.service_start_time = timestamp_now()
                elif new_status_enum == AppointmentStatus.COMPLETED:
                    appointment.service_end_time = timestamp_now()
                    appointment.check_out_time = timestamp_now()
                    if notes:
                        appointment.completion_notes = notes
                elif new_status_enum == AppointmentStatus.CANCELLED:
                    appointment.cancelled_at = timestamp_now()
                    appointment.cancellation_reason = notes

                await session.commit()
                await session.refresh(appointment)

                logger.info(
                    f"Updated appointment {appointment_id} status to {new_status}"
                )
                return appointment.to_dict()

        except NotFoundException:
            raise
        except Exception as e:
            logger.error(
                f"Error updating appointment {appointment_id}: {e}"
            )
            raise DatabaseException(
                message="Failed to update appointment",
                operation="update",
                original_error=e,
            )

    async def get_upcoming_appointments(
        self, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get upcoming appointments"""
        try:
            async with get_async_db_context() as session:
                now = timestamp_now()
                result = await session.execute(
                    select(ServiceAppointment)
                    .where(
                        and_(
                            ServiceAppointment.scheduled_date >= now,
                            ServiceAppointment.status.in_(
                                [
                                    AppointmentStatus.SCHEDULED,
                                    AppointmentStatus.CONFIRMED,
                                    AppointmentStatus.PENDING,
                                ]
                            ),
                        )
                    )
                    .order_by(ServiceAppointment.scheduled_date.asc())
                    .limit(limit)
                )
                appointments = result.scalars().all()

                return [a.to_dict() for a in appointments]

        except Exception as e:
            logger.error(f"Error getting upcoming appointments: {e}")
            raise DatabaseException(
                message="Failed to get upcoming appointments",
                operation="read",
                original_error=e,
            )


# Singleton instance
_appointment_service: Optional[AppointmentService] = None


def get_appointment_service() -> AppointmentService:
    """Get or create appointment service instance"""
    global _appointment_service
    if _appointment_service is None:
        _appointment_service = AppointmentService()
    return _appointment_service