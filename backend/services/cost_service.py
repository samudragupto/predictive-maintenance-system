"""
Cost Estimation Service
AI-driven cost estimation for repairs and maintenance
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import random

from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import get_settings
from backend.models import (
    CostEstimate, CostItem, Vehicle, Diagnosis, get_async_db_context,
)
from backend.models.cost_estimate import EstimateStatus, CostCategory
from backend.utils.helpers import generate_reference_number, timestamp_now
from backend.utils.exceptions import (
    NotFoundException,
    DatabaseException,
    AgentException,
)

settings = get_settings()
logger = logging.getLogger(__name__)


# Parts database for simulation
PARTS_DATABASE = {
    "ENGINE": [
        {"name": "Engine Oil (5W-30, 5L)", "code": "ENG-OIL-001", "price": 45.00, "oem": True},
        {"name": "Oil Filter", "code": "ENG-FIL-001", "price": 15.00, "oem": True},
        {"name": "Air Filter", "code": "ENG-FIL-002", "price": 25.00, "oem": True},
        {"name": "Spark Plug Set", "code": "ENG-SPK-001", "price": 60.00, "oem": True},
        {"name": "Coolant (2L)", "code": "ENG-CLT-001", "price": 20.00, "oem": True},
        {"name": "Thermostat", "code": "ENG-THM-001", "price": 35.00, "oem": True},
        {"name": "Water Pump", "code": "ENG-WPM-001", "price": 120.00, "oem": True},
    ],
    "BRAKES": [
        {"name": "Front Brake Pad Set", "code": "BRK-PAD-001", "price": 85.00, "oem": True},
        {"name": "Rear Brake Pad Set", "code": "BRK-PAD-002", "price": 75.00, "oem": True},
        {"name": "Front Brake Rotor (pair)", "code": "BRK-ROT-001", "price": 150.00, "oem": True},
        {"name": "Rear Brake Rotor (pair)", "code": "BRK-ROT-002", "price": 130.00, "oem": True},
        {"name": "Brake Fluid (1L)", "code": "BRK-FLD-001", "price": 18.00, "oem": True},
    ],
    "BATTERY": [
        {"name": "Car Battery (12V 60Ah)", "code": "BAT-STD-001", "price": 150.00, "oem": True},
        {"name": "Battery Terminal Clamp Set", "code": "BAT-TRM-001", "price": 12.00, "oem": False},
        {"name": "Battery Cable", "code": "BAT-CBL-001", "price": 25.00, "oem": True},
    ],
    "OIL_SYSTEM": [
        {"name": "Engine Oil (5W-30, 5L)", "code": "OIL-SYN-001", "price": 55.00, "oem": True},
        {"name": "Oil Filter Premium", "code": "OIL-FIL-001", "price": 18.00, "oem": True},
        {"name": "Oil Pan Gasket", "code": "OIL-GSK-001", "price": 30.00, "oem": True},
    ],
    "TIRES": [
        {"name": "All-Season Tire", "code": "TIR-ALL-001", "price": 120.00, "oem": False},
        {"name": "Tire Valve Stem Set", "code": "TIR-VLV-001", "price": 8.00, "oem": False},
        {"name": "Wheel Alignment Service", "code": "TIR-ALN-001", "price": 80.00, "oem": False},
    ],
    "TRANSMISSION": [
        {"name": "Transmission Fluid (4L)", "code": "TRN-FLD-001", "price": 40.00, "oem": True},
        {"name": "Transmission Filter", "code": "TRN-FIL-001", "price": 35.00, "oem": True},
    ],
}

LABOR_RATES = {
    "ENGINE": {"hours": 2.0, "rate": 85.00, "level": "SENIOR"},
    "BRAKES": {"hours": 1.5, "rate": 75.00, "level": "SENIOR"},
    "BATTERY": {"hours": 0.5, "rate": 65.00, "level": "JUNIOR"},
    "OIL_SYSTEM": {"hours": 1.0, "rate": 65.00, "level": "JUNIOR"},
    "TIRES": {"hours": 1.0, "rate": 65.00, "level": "JUNIOR"},
    "TRANSMISSION": {"hours": 3.0, "rate": 95.00, "level": "SPECIALIST"},
    "DIAGNOSTICS": {"hours": 0.5, "rate": 75.00, "level": "SENIOR"},
}


class CostEstimationService:
    """
    Service for generating cost estimates
    """

    def __init__(self):
        self.settings = get_settings()
        self.default_labor_rate = self.settings.DEFAULT_LABOR_RATE_PER_HOUR
        self.markup_factor = self.settings.COST_ESTIMATION_MARKUP
        logger.info("CostEstimationService initialized")

    async def create_estimate(
        self,
        vehicle_id: str,
        diagnosis_id: Optional[str] = None,
        services_requested: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a cost estimate"""
        try:
            estimate_id = generate_reference_number("CE")
            components_to_service = []

            async with get_async_db_context() as session:
                # 1. Get vehicle data (Primitive values only)
                v_result = await session.execute(
                    select(Vehicle).where(Vehicle.vehicle_id == vehicle_id)
                )
                vehicle = v_result.scalar_one_or_none()
                if not vehicle:
                    raise NotFoundException(
                        resource="Vehicle", resource_id=vehicle_id
                    )
                
                # Extract needed values immediately to avoid lazy loading later
                v_db_id = vehicle.id
                v_uuid = vehicle.vehicle_id
                v_is_warranty = vehicle.is_under_warranty
                v_owner = vehicle.owner_name

                # 2. Get diagnosis data (Primitive values only)
                diagnosis_db_id = None
                if diagnosis_id:
                    d_result = await session.execute(
                        select(Diagnosis).where(
                            Diagnosis.diagnosis_id == diagnosis_id
                        )
                    )
                    diagnosis = d_result.scalar_one_or_none()
                    if diagnosis:
                        diagnosis_db_id = diagnosis.id
                        # Access this immediately
                        components_to_service = list(diagnosis.affected_components or [])

                # 3. Determine services
                if services_requested:
                    components_to_service = services_requested

                if not components_to_service:
                    components_to_service = ["DIAGNOSTICS"]

                # 4. Generate cost ITEMS (Pure Python logic, no DB access here)
                class DummyVehicle:
                    def __init__(self, warranty):
                        self.is_under_warranty = warranty
                
                dummy_v = DummyVehicle(v_is_warranty)
                
                cost_items_data = self._generate_cost_items(
                    components_to_service, dummy_v
                )

                # 5. Calculate totals (Pure Python)
                subtotal_parts = sum(i["total_price"] for i in cost_items_data if i["category"] == "PARTS")
                subtotal_labor = sum(i["total_price"] for i in cost_items_data if i["category"] == "LABOR")
                subtotal_other = sum(i["total_price"] for i in cost_items_data if i["category"] not in ["PARTS", "LABOR", "TAX"])

                subtotal = subtotal_parts + subtotal_labor + subtotal_other
                tax_rate = 8.5
                tax_amount = round(subtotal * (tax_rate / 100), 2)
                
                warranty_coverage = 0.0
                if v_is_warranty:
                    warranty_coverage = round(subtotal_parts * 0.5, 2)

                total = round(subtotal + tax_amount - warranty_coverage, 2)
                estimate_low = round(total * 0.85, 2)
                estimate_high = round(total * 1.20, 2)
                
                total_labor_hours = sum(
                    item.get("labor_hours", 0) for item in cost_items_data if item["category"] == "LABOR"
                )

                # 6. Create Estimate Record
                estimate = CostEstimate(
                    estimate_id=estimate_id,
                    vehicle_id=v_db_id,
                    vehicle_uuid=v_uuid,
                    diagnosis_id=diagnosis_db_id,
                    status=EstimateStatus.DRAFT,
                    subtotal_parts=subtotal_parts,
                    subtotal_labor=subtotal_labor,
                    subtotal_other=subtotal_other,
                    discount_amount=0.0,
                    tax_amount=tax_amount,
                    tax_rate=tax_rate,
                    total_estimate=total,
                    estimate_low=estimate_low,
                    estimate_high=estimate_high,
                    confidence_score=0.85,
                    estimated_labor_hours=total_labor_hours,
                    labor_rate_per_hour=self.default_labor_rate,
                    warranty_coverage_amount=warranty_coverage,
                    warranty_applicable=v_is_warranty,
                    service_type="REPAIR" if diagnosis_db_id else "MAINTENANCE",
                    ai_generated=True,
                    llm_model_used="rule_based_estimator_v1",
                    summary=self._generate_summary(components_to_service, total),
                    valid_from=timestamp_now(),
                    valid_until=timestamp_now() + timedelta(days=30),
                    created_at=timestamp_now(),
                )

                session.add(estimate)
                await session.flush() # Get ID

                # 7. Create Item Records
                saved_items = []
                for idx, item_data in enumerate(cost_items_data):
                    cost_item = CostItem(
                        estimate_id=estimate.id,
                        item_code=item_data.get("code"),
                        category=CostCategory(item_data["category"]),
                        name=item_data["name"],
                        description=item_data.get("description"),
                        quantity=item_data.get("quantity", 1),
                        unit=item_data.get("unit", "each"),
                        unit_price=item_data["unit_price"],
                        total_price=item_data["total_price"],
                        part_number=item_data.get("part_number"),
                        is_oem_part=item_data.get("is_oem", True),
                        labor_hours=item_data.get("labor_hours"),
                        labor_rate=item_data.get("labor_rate"),
                        technician_level=item_data.get("tech_level"),
                        warranty_covered=v_is_warranty and item_data["category"] == "PARTS",
                        is_required=item_data.get("required", True),
                        sort_order=idx,
                    )
                    session.add(cost_item)
                    # Create dictionary representation manually to return
                    saved_items.append(cost_item.to_dict())

                await session.commit()

                # 8. Return response manually
                response = estimate.to_dict()
                response["items"] = saved_items  # Inject items manually

                logger.info(f"Created cost estimate {estimate_id}: ${total}")
                return response

        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error creating cost estimate: {e}")
            raise AgentException(
                message="Failed to create cost estimate",
                agent_type="COST_AGENT",
                action="estimate",
            )

    async def get_estimate(self, estimate_id: str) -> Dict[str, Any]:
        """Get a cost estimate by ID"""
        try:
            async with get_async_db_context() as session:
                # Use selectinload to eagerly load items
                result = await session.execute(
                    select(CostEstimate)
                    .where(CostEstimate.estimate_id == estimate_id)
                    .options(selectinload(CostEstimate.items))
                )
                estimate = result.scalar_one_or_none()

                if not estimate:
                    raise NotFoundException(resource="Cost Estimate", resource_id=estimate_id)

                # Convert to dict
                data = estimate.to_dict()
                # Manually attach items from the loaded relationship
                data["items"] = [item.to_dict() for item in estimate.items]
                return data

        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error getting estimate {estimate_id}: {e}")
            raise DatabaseException(
                message="Failed to get cost estimate",
                operation="read",
                original_error=e,
            )

    async def get_vehicle_estimates(
        self,
        vehicle_id: str,
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """Get cost estimates for a vehicle"""
        try:
            async with get_async_db_context() as session:
                # Count total
                count_query = select(func.count(CostEstimate.id)).where(
                    CostEstimate.vehicle_uuid == vehicle_id
                )
                total_result = await session.execute(count_query)
                total = total_result.scalar() or 0

                # Fetch estimates with items eagerly loaded
                offset = (page - 1) * page_size
                query = (
                    select(CostEstimate)
                    .where(CostEstimate.vehicle_uuid == vehicle_id)
                    .order_by(desc(CostEstimate.created_at))
                    .offset(offset)
                    .limit(page_size)
                    .options(selectinload(CostEstimate.items))
                )

                result = await session.execute(query)
                estimates = result.scalars().all()

                # Manually serialize to avoid greenlet errors
                serialized_estimates = []
                for est in estimates:
                    est_dict = est.to_dict()
                    # Explicitly serialize the eagerly loaded items
                    est_dict["items"] = [item.to_dict() for item in est.items]
                    serialized_estimates.append(est_dict)

                return {
                    "success": True,
                    "data": serialized_estimates,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size,
                }

        except Exception as e:
            logger.error(f"Error getting estimates for {vehicle_id}: {e}")
            raise DatabaseException(
                message="Failed to get vehicle estimates",
                operation="read",
                original_error=e,
            )

    async def approve_estimate(
        self, estimate_id: str, approved_by: str
    ) -> Dict[str, Any]:
        """Approve a cost estimate"""
        try:
            async with get_async_db_context() as session:
                result = await session.execute(
                    select(CostEstimate)
                    .where(CostEstimate.estimate_id == estimate_id)
                    .options(selectinload(CostEstimate.items))
                )
                estimate = result.scalar_one_or_none()

                if not estimate:
                    raise NotFoundException(
                        resource="Cost Estimate",
                        resource_id=estimate_id,
                    )

                estimate.status = EstimateStatus.APPROVED
                estimate.approved_by = approved_by
                estimate.approved_at = timestamp_now()
                estimate.updated_at = timestamp_now()

                await session.commit()
                # No refresh needed if we modify in place
                
                return estimate.to_dict()

        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error approving estimate {estimate_id}: {e}")
            raise DatabaseException(
                message="Failed to approve estimate",
                operation="update",
                original_error=e,
            )

    def _generate_cost_items(
        self,
        components: List[str],
        vehicle: Vehicle,
    ) -> List[Dict[str, Any]]:
        """Generate cost items for given components"""
        items = []

        # Add diagnostic fee
        items.append(
            {
                "category": "LABOR",
                "name": "Diagnostic Inspection",
                "code": "DIAG-001",
                "unit_price": 50.00,
                "total_price": 50.00,
                "quantity": 1,
                "unit": "service",
                "labor_hours": 0.5,
                "labor_rate": 75.00,
                "tech_level": "SENIOR",
                "required": True,
            }
        )

        for component in components:
            component_upper = component.upper()

            # Add parts
            parts = PARTS_DATABASE.get(component_upper, [])
            for part in parts[:3]:  # Limit to top 3 parts per component
                items.append(
                    {
                        "category": "PARTS",
                        "name": part["name"],
                        "code": part["code"],
                        "part_number": part["code"],
                        "unit_price": part["price"],
                        "total_price": part["price"],
                        "quantity": 1,
                        "unit": "each",
                        "is_oem": part["oem"],
                        "required": True,
                    }
                )

            # Add labor
            labor = LABOR_RATES.get(
                component_upper, LABOR_RATES["DIAGNOSTICS"]
            )
            labor_total = round(labor["hours"] * labor["rate"], 2)
            items.append(
                {
                    "category": "LABOR",
                    "name": f"{component_upper} Service Labor",
                    "code": f"LBR-{component_upper[:3]}-001",
                    "unit_price": labor["rate"],
                    "total_price": labor_total,
                    "quantity": labor["hours"],
                    "unit": "hour",
                    "labor_hours": labor["hours"],
                    "labor_rate": labor["rate"],
                    "tech_level": labor["level"],
                    "required": True,
                }
            )

        # Add disposal fee
        items.append(
            {
                "category": "OTHER",
                "name": "Environmental Disposal Fee",
                "code": "ENV-DSP-001",
                "unit_price": 15.00,
                "total_price": 15.00,
                "quantity": 1,
                "unit": "service",
                "required": True,
            }
        )

        return items

    def _generate_summary(
        self, components: List[str], total: float
    ) -> str:
        """Generate estimate summary"""
        component_list = ", ".join(
            c.replace("_", " ").title() for c in components
        )
        return (
            f"Cost estimate for service covering: {component_list}. "
            f"Total estimated cost: ${total:.2f}. "
            f"Estimate valid for 30 days."
        )


# Singleton instance
_cost_service: Optional[CostEstimationService] = None


def get_cost_service() -> CostEstimationService:
    """Get or create cost estimation service instance"""
    global _cost_service
    if _cost_service is None:
        _cost_service = CostEstimationService()
    return _cost_service