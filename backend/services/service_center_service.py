"""
Service Center Service
Manages service center operations
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import get_settings
from backend.models import ServiceCenter, ServiceCenterCapacity, get_async_db_context
from backend.models.service_center import CenterStatus, CenterType
from backend.utils.helpers import (
    generate_id, timestamp_now, calculate_distance, get_bounding_box,
)
from backend.utils.exceptions import NotFoundException, DatabaseException

settings = get_settings()
logger = logging.getLogger(__name__)


class ServiceCenterService:
    """
    Service for managing service centers
    """

    def __init__(self):
        self.settings = get_settings()
        logger.info("ServiceCenterService initialized")

    async def create_service_center(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new service center"""
        try:
            center_id = generate_id(prefix="SC")

            async with get_async_db_context() as session:
                center = ServiceCenter(
                    center_id=center_id,
                    name=data["name"],
                    center_type=CenterType(
                        data.get("center_type", "AUTHORIZED_CENTER")
                    ),
                    status=CenterStatus.ACTIVE,
                    address_line1=data["address_line1"],
                    address_line2=data.get("address_line2"),
                    city=data["city"],
                    state=data.get("state"),
                    postal_code=data.get("postal_code"),
                    country=data.get("country", "USA"),
                    latitude=data.get("latitude"),
                    longitude=data.get("longitude"),
                    phone=data.get("phone"),
                    email=data.get("email"),
                    total_bays=data.get("total_bays", 5),
                    available_bays=data.get("total_bays", 5),
                    max_daily_appointments=data.get(
                        "max_daily_appointments", 20
                    ),
                    labor_rate_per_hour=data.get("labor_rate", 75.0),
                    operating_hours=data.get("operating_hours", {
                        "monday": {"open": "08:00", "close": "18:00"},
                        "tuesday": {"open": "08:00", "close": "18:00"},
                        "wednesday": {"open": "08:00", "close": "18:00"},
                        "thursday": {"open": "08:00", "close": "18:00"},
                        "friday": {"open": "08:00", "close": "18:00"},
                        "saturday": {"open": "09:00", "close": "14:00"},
                    }),
                    services_offered=data.get("services_offered"),
                    vehicle_makes_supported=data.get(
                        "vehicle_makes_supported"
                    ),
                    created_at=timestamp_now(),
                )

                session.add(center)
                await session.commit()
                await session.refresh(center)

                logger.info(f"Created service center: {center_id}")
                return center.to_dict()

        except Exception as e:
            logger.error(f"Error creating service center: {e}")
            raise DatabaseException(
                message="Failed to create service center",
                operation="create",
                original_error=e,
            )

    async def get_service_center(
        self, center_id: str
    ) -> Dict[str, Any]:
        """Get a service center by ID"""
        try:
            async with get_async_db_context() as session:
                result = await session.execute(
                    select(ServiceCenter).where(
                        ServiceCenter.center_id == center_id
                    )
                )
                center = result.scalar_one_or_none()

                if not center:
                    raise NotFoundException(
                        resource="Service Center",
                        resource_id=center_id,
                    )

                return center.to_dict()

        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error getting service center: {e}")
            raise DatabaseException(
                message="Failed to get service center",
                operation="read",
                original_error=e,
            )

    async def get_all_centers(
        self,
        status: Optional[str] = None,
        city: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get all service centers"""
        try:
            async with get_async_db_context() as session:
                query = select(ServiceCenter)

                if status:
                    query = query.where(
                        ServiceCenter.status == CenterStatus(status)
                    )
                if city:
                    query = query.where(
                        ServiceCenter.city.ilike(f"%{city}%")
                    )

                result = await session.execute(query)
                centers = result.scalars().all()

                return [c.to_dict() for c in centers]

        except Exception as e:
            logger.error(f"Error listing service centers: {e}")
            raise DatabaseException(
                message="Failed to list service centers",
                operation="read",
                original_error=e,
            )

    async def find_nearest_centers(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 50.0,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find nearest service centers"""
        try:
            async with get_async_db_context() as session:
                # Get bounding box
                min_lat, max_lat, min_lon, max_lon = get_bounding_box(
                    latitude, longitude, radius_km
                )

                result = await session.execute(
                    select(ServiceCenter).where(
                        and_(
                            ServiceCenter.status == CenterStatus.ACTIVE,
                            ServiceCenter.latitude.between(
                                min_lat, max_lat
                            ),
                            ServiceCenter.longitude.between(
                                min_lon, max_lon
                            ),
                        )
                    )
                )
                centers = result.scalars().all()

                # Calculate distances and sort
                centers_with_distance = []
                for center in centers:
                    if center.latitude and center.longitude:
                        distance = calculate_distance(
                            latitude,
                            longitude,
                            center.latitude,
                            center.longitude,
                        )
                        if distance <= radius_km:
                            center_data = center.to_dict()
                            center_data["distance_km"] = round(distance, 2)
                            centers_with_distance.append(center_data)

                # Sort by distance
                centers_with_distance.sort(
                    key=lambda x: x["distance_km"]
                )

                return centers_with_distance[:limit]

        except Exception as e:
            logger.error(f"Error finding nearest centers: {e}")
            raise DatabaseException(
                message="Failed to find nearest centers",
                operation="read",
                original_error=e,
            )

    async def seed_default_centers(self) -> List[Dict[str, Any]]:
        """Seed default service centers for development"""
        centers_data = [
            {
                "name": "AutoCare Downtown Service Center",
                "address_line1": "123 Main Street",
                "city": "New York",
                "state": "NY",
                "postal_code": "10001",
                "latitude": 40.7484,
                "longitude": -73.9967,
                "phone": "(212) 555-0101",
                "email": "downtown@autocare.com",
                "total_bays": 8,
                "labor_rate": 85.00,
            },
            {
                "name": "AutoCare Midtown Express",
                "address_line1": "456 5th Avenue",
                "city": "New York",
                "state": "NY",
                "postal_code": "10018",
                "latitude": 40.7549,
                "longitude": -73.9840,
                "phone": "(212) 555-0102",
                "email": "midtown@autocare.com",
                "total_bays": 6,
                "labor_rate": 90.00,
            },
            {
                "name": "AutoCare Brooklyn Hub",
                "address_line1": "789 Atlantic Avenue",
                "city": "Brooklyn",
                "state": "NY",
                "postal_code": "11217",
                "latitude": 40.6862,
                "longitude": -73.9776,
                "phone": "(718) 555-0103",
                "email": "brooklyn@autocare.com",
                "total_bays": 10,
                "labor_rate": 75.00,
            },
        ]

        created = []
        for data in centers_data:
            try:
                center = await self.create_service_center(data)
                created.append(center)
            except Exception as e:
                logger.warning(f"Failed to seed center {data['name']}: {e}")

        return created


# Singleton instance
_service_center_service: Optional[ServiceCenterService] = None


def get_service_center_service() -> ServiceCenterService:
    """Get or create service center service instance"""
    global _service_center_service
    if _service_center_service is None:
        _service_center_service = ServiceCenterService()
    return _service_center_service