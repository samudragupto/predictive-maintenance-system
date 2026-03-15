"""
Vehicle Service
Handles all vehicle-related business logic
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy import select, and_, or_, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.config.settings import get_settings
from backend.models import (
    Vehicle, VehicleStatus, get_async_db_context
)
from backend.models.vehicle import HealthStatus, FuelType
from backend.models.schemas import VehicleCreate, VehicleUpdate
from backend.utils.helpers import generate_id, timestamp_now
from backend.utils.validators import validate_vin
from backend.utils.exceptions import (
    NotFoundException,
    ValidationException,
    ConflictException,
    DatabaseException,
)

settings = get_settings()
logger = logging.getLogger(__name__)


class VehicleService:
    """
    Service for managing vehicles
    """

    def __init__(self):
        self.settings = get_settings()
        logger.info("VehicleService initialized")

    async def create_vehicle(self, data: VehicleCreate) -> Dict[str, Any]:
        """Create a new vehicle"""
        try:
            # Validate VIN
            is_valid, error_msg = validate_vin(data.vin)
            if not is_valid:
                raise ValidationException(message=error_msg, field="vin")

            async with get_async_db_context() as session:
                # Check if VIN already exists
                existing = await session.execute(
                    select(Vehicle).where(Vehicle.vin == data.vin.upper())
                )
                if existing.scalar_one_or_none():
                    raise ConflictException(
                        message=f"Vehicle with VIN '{data.vin}' already exists",
                        resource="Vehicle",
                    )

                # Generate vehicle ID
                vehicle_id = generate_id(prefix="VH")

                # Create vehicle
                vehicle = Vehicle(
                    vehicle_id=vehicle_id,
                    vin=data.vin.upper(),
                    make=data.make,
                    model=data.model,
                    year=data.year,
                    license_plate=data.license_plate,
                    fuel_type=FuelType(data.fuel_type) if data.fuel_type else FuelType.PETROL,
                    status=VehicleStatus.ACTIVE,
                    health_status=HealthStatus.UNKNOWN,
                    health_score=100.0,
                    owner_name=data.owner_name,
                    owner_contact=data.owner_contact,
                    fleet_id=data.fleet_id,
                    is_under_warranty=True,
                    created_at=timestamp_now(),
                    updated_at=timestamp_now(),
                )

                session.add(vehicle)
                await session.commit()
                await session.refresh(vehicle)

                logger.info(f"Created vehicle: {vehicle_id}")
                return vehicle.to_dict()

        except (ValidationException, ConflictException):
            raise
        except Exception as e:
            logger.error(f"Error creating vehicle: {e}")
            raise DatabaseException(
                message="Failed to create vehicle",
                operation="create",
                original_error=e,
            )

    async def get_vehicle(self, vehicle_id: str) -> Dict[str, Any]:
        """Get a vehicle by ID"""
        try:
            async with get_async_db_context() as session:
                result = await session.execute(
                    select(Vehicle).where(
                        and_(
                            or_(
                                Vehicle.vehicle_id == vehicle_id,
                                Vehicle.vin == vehicle_id.upper(),
                            ),
                            Vehicle.is_deleted == False,
                        )
                    )
                )
                vehicle = result.scalar_one_or_none()

                if not vehicle:
                    raise NotFoundException(
                        resource="Vehicle",
                        resource_id=vehicle_id,
                    )

                return vehicle.to_dict()

        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error getting vehicle {vehicle_id}: {e}")
            raise DatabaseException(
                message="Failed to retrieve vehicle",
                operation="read",
                original_error=e,
            )

    async def get_vehicles(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        health_status: Optional[str] = None,
        fleet_id: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        """Get paginated list of vehicles"""
        try:
            async with get_async_db_context() as session:
                # Build base query
                query = select(Vehicle).where(Vehicle.is_deleted == False)
                count_query = select(func.count(Vehicle.id)).where(
                    Vehicle.is_deleted == False
                )

                # Apply filters
                if status:
                    query = query.where(Vehicle.status == VehicleStatus(status))
                    count_query = count_query.where(
                        Vehicle.status == VehicleStatus(status)
                    )

                if health_status:
                    query = query.where(
                        Vehicle.health_status == HealthStatus(health_status)
                    )
                    count_query = count_query.where(
                        Vehicle.health_status == HealthStatus(health_status)
                    )

                if fleet_id:
                    query = query.where(Vehicle.fleet_id == fleet_id)
                    count_query = count_query.where(Vehicle.fleet_id == fleet_id)

                if search:
                    search_filter = or_(
                        Vehicle.vehicle_id.ilike(f"%{search}%"),
                        Vehicle.vin.ilike(f"%{search}%"),
                        Vehicle.make.ilike(f"%{search}%"),
                        Vehicle.model.ilike(f"%{search}%"),
                        Vehicle.license_plate.ilike(f"%{search}%"),
                        Vehicle.owner_name.ilike(f"%{search}%"),
                    )
                    query = query.where(search_filter)
                    count_query = count_query.where(search_filter)

                # Get total count
                total_result = await session.execute(count_query)
                total = total_result.scalar()

                # Apply sorting
                sort_column = getattr(Vehicle, sort_by, Vehicle.created_at)
                if sort_order.lower() == "desc":
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())

                # Apply pagination
                offset = (page - 1) * page_size
                query = query.offset(offset).limit(page_size)

                # Execute query
                result = await session.execute(query)
                vehicles = result.scalars().all()

                total_pages = (total + page_size - 1) // page_size

                return {
                    "success": True,
                    "data": [v.to_dict() for v in vehicles],
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                }

        except Exception as e:
            logger.error(f"Error listing vehicles: {e}")
            raise DatabaseException(
                message="Failed to list vehicles",
                operation="list",
                original_error=e,
            )

    async def update_vehicle(
        self, vehicle_id: str, data: VehicleUpdate
    ) -> Dict[str, Any]:
        """Update a vehicle"""
        try:
            async with get_async_db_context() as session:
                result = await session.execute(
                    select(Vehicle).where(
                        and_(
                            Vehicle.vehicle_id == vehicle_id,
                            Vehicle.is_deleted == False,
                        )
                    )
                )
                vehicle = result.scalar_one_or_none()

                if not vehicle:
                    raise NotFoundException(
                        resource="Vehicle",
                        resource_id=vehicle_id,
                    )

                # Update fields
                update_data = data.model_dump(exclude_unset=True)
                for field, value in update_data.items():
                    if value is not None:
                        if field == "status":
                            setattr(vehicle, field, VehicleStatus(value))
                        else:
                            setattr(vehicle, field, value)

                vehicle.updated_at = timestamp_now()
                await session.commit()
                await session.refresh(vehicle)

                logger.info(f"Updated vehicle: {vehicle_id}")
                return vehicle.to_dict()

        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error updating vehicle {vehicle_id}: {e}")
            raise DatabaseException(
                message="Failed to update vehicle",
                operation="update",
                original_error=e,
            )

    async def delete_vehicle(self, vehicle_id: str) -> Dict[str, Any]:
        """Soft delete a vehicle"""
        try:
            async with get_async_db_context() as session:
                result = await session.execute(
                    select(Vehicle).where(
                        and_(
                            Vehicle.vehicle_id == vehicle_id,
                            Vehicle.is_deleted == False,
                        )
                    )
                )
                vehicle = result.scalar_one_or_none()

                if not vehicle:
                    raise NotFoundException(
                        resource="Vehicle",
                        resource_id=vehicle_id,
                    )

                vehicle.is_deleted = True
                vehicle.deleted_at = timestamp_now()
                vehicle.status = VehicleStatus.DECOMMISSIONED
                vehicle.updated_at = timestamp_now()

                await session.commit()

                logger.info(f"Soft deleted vehicle: {vehicle_id}")
                return {"success": True, "message": f"Vehicle {vehicle_id} deleted"}

        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error deleting vehicle {vehicle_id}: {e}")
            raise DatabaseException(
                message="Failed to delete vehicle",
                operation="delete",
                original_error=e,
            )

    async def update_health_score(
        self, vehicle_id: str, health_score: float
    ) -> Dict[str, Any]:
        """Update vehicle health score"""
        try:
            async with get_async_db_context() as session:
                result = await session.execute(
                    select(Vehicle).where(Vehicle.vehicle_id == vehicle_id)
                )
                vehicle = result.scalar_one_or_none()

                if not vehicle:
                    raise NotFoundException(
                        resource="Vehicle", resource_id=vehicle_id
                    )

                vehicle.update_health_status(health_score)
                vehicle.updated_at = timestamp_now()

                await session.commit()
                await session.refresh(vehicle)

                logger.info(
                    f"Updated health score for {vehicle_id}: {health_score}"
                )
                return vehicle.to_dict()

        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error updating health score for {vehicle_id}: {e}")
            raise DatabaseException(
                message="Failed to update health score",
                operation="update",
                original_error=e,
            )

    async def get_fleet_overview(
        self, fleet_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get fleet overview statistics"""
        try:
            async with get_async_db_context() as session:
                base_filter = Vehicle.is_deleted == False
                if fleet_id:
                    base_filter = and_(base_filter, Vehicle.fleet_id == fleet_id)

                # Total vehicles
                total_result = await session.execute(
                    select(func.count(Vehicle.id)).where(base_filter)
                )
                total = total_result.scalar() or 0

                # Active vehicles
                active_result = await session.execute(
                    select(func.count(Vehicle.id)).where(
                        and_(base_filter, Vehicle.status == VehicleStatus.ACTIVE)
                    )
                )
                active = active_result.scalar() or 0

                # In service
                in_service_result = await session.execute(
                    select(func.count(Vehicle.id)).where(
                        and_(
                            base_filter,
                            Vehicle.status == VehicleStatus.IN_SERVICE,
                        )
                    )
                )
                in_service = in_service_result.scalar() or 0

                # Health distribution
                healthy_result = await session.execute(
                    select(func.count(Vehicle.id)).where(
                        and_(
                            base_filter,
                            Vehicle.health_status == HealthStatus.HEALTHY,
                        )
                    )
                )
                healthy = healthy_result.scalar() or 0

                warning_result = await session.execute(
                    select(func.count(Vehicle.id)).where(
                        and_(
                            base_filter,
                            Vehicle.health_status == HealthStatus.WARNING,
                        )
                    )
                )
                warning = warning_result.scalar() or 0

                critical_result = await session.execute(
                    select(func.count(Vehicle.id)).where(
                        and_(
                            base_filter,
                            Vehicle.health_status == HealthStatus.CRITICAL,
                        )
                    )
                )
                critical = critical_result.scalar() or 0

                # Average health score
                avg_result = await session.execute(
                    select(func.avg(Vehicle.health_score)).where(base_filter)
                )
                avg_health = round(avg_result.scalar() or 0, 2)

                return {
                    "total_vehicles": total,
                    "active_vehicles": active,
                    "vehicles_in_service": in_service,
                    "healthy_vehicles": healthy,
                    "warning_vehicles": warning,
                    "critical_vehicles": critical,
                    "average_health_score": avg_health,
                }

        except Exception as e:
            logger.error(f"Error getting fleet overview: {e}")
            raise DatabaseException(
                message="Failed to get fleet overview",
                operation="read",
                original_error=e,
            )

    async def get_vehicles_needing_service(
        self, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get vehicles that need service"""
        try:
            async with get_async_db_context() as session:
                now = timestamp_now()

                result = await session.execute(
                    select(Vehicle)
                    .where(
                        and_(
                            Vehicle.is_deleted == False,
                            Vehicle.status == VehicleStatus.ACTIVE,
                            or_(
                                Vehicle.health_status.in_(
                                    [HealthStatus.WARNING, HealthStatus.CRITICAL]
                                ),
                                Vehicle.next_service_due_date <= now,
                            ),
                        )
                    )
                    .order_by(Vehicle.health_score.asc())
                    .limit(limit)
                )
                vehicles = result.scalars().all()

                return [v.to_dict() for v in vehicles]

        except Exception as e:
            logger.error(f"Error getting vehicles needing service: {e}")
            raise DatabaseException(
                message="Failed to get vehicles needing service",
                operation="read",
                original_error=e,
            )


# Singleton instance
_vehicle_service: Optional[VehicleService] = None


def get_vehicle_service() -> VehicleService:
    """Get or create vehicle service instance"""
    global _vehicle_service
    if _vehicle_service is None:
        _vehicle_service = VehicleService()
    return _vehicle_service