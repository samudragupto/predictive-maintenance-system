"""
Cost Estimation Model
Stores AI-generated cost estimates for repairs and maintenance
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, Enum as SQLEnum, ForeignKey, Index, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, Any, List
import enum

from . import Base


class EstimateStatus(str, enum.Enum):
    """Cost estimate status"""
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REVISED = "REVISED"
    EXPIRED = "EXPIRED"
    INVOICED = "INVOICED"


class CostCategory(str, enum.Enum):
    """Cost category"""
    PARTS = "PARTS"
    LABOR = "LABOR"
    DIAGNOSTIC = "DIAGNOSTIC"
    FLUIDS = "FLUIDS"
    DISPOSAL = "DISPOSAL"
    TAX = "TAX"
    OTHER = "OTHER"


class CostEstimate(Base):
    """
    Cost Estimate Entity
    AI-generated cost estimation for service/repair
    """
    __tablename__ = "cost_estimates"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Reference
    estimate_id = Column(String(50), unique=True, nullable=False, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    vehicle_uuid = Column(String(50), nullable=False)
    diagnosis_id = Column(Integer, ForeignKey("diagnoses.id"), nullable=True)
    appointment_id = Column(Integer, ForeignKey("service_appointments.id"), nullable=True)
    
    # Status
    status = Column(SQLEnum(EstimateStatus), default=EstimateStatus.DRAFT)
    
    # Cost Summary
    subtotal_parts = Column(Float, default=0.0)
    subtotal_labor = Column(Float, default=0.0)
    subtotal_other = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    discount_percent = Column(Float, nullable=True)
    tax_amount = Column(Float, default=0.0)
    tax_rate = Column(Float, nullable=True)
    total_estimate = Column(Float, nullable=False)
    
    # Estimate Range
    estimate_low = Column(Float, nullable=True)
    estimate_high = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)  # 0.0 to 1.0
    
    # Currency
    currency = Column(String(3), default="INR")  # Default to INR
    
    # Labor Details
    estimated_labor_hours = Column(Float, nullable=True)
    labor_rate_per_hour = Column(Float, nullable=True)
    
    # Warranty Coverage
    warranty_coverage_amount = Column(Float, default=0.0)
    warranty_applicable = Column(Boolean, default=False)
    warranty_notes = Column(Text, nullable=True)
    
    # Service Type
    service_type = Column(String(50), nullable=True)  # REPAIR, MAINTENANCE, INSPECTION
    repair_complexity = Column(String(20), nullable=True)  # SIMPLE, MODERATE, COMPLEX
    
    # AI Generation Info
    ai_generated = Column(Boolean, default=True)
    llm_model_used = Column(String(100), nullable=True)
    generation_prompt = Column(Text, nullable=True)
    
    # Description
    summary = Column(Text, nullable=True)
    detailed_breakdown = Column(Text, nullable=True)
    customer_notes = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)
    
    # Validity
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    
    # Approval
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # Comparison to Actual
    actual_total = Column(Float, nullable=True)
    variance_amount = Column(Float, nullable=True)
    variance_percent = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    vehicle = relationship("Vehicle", back_populates="cost_estimates")
    diagnosis = relationship("Diagnosis", back_populates="cost_estimate")
    items = relationship("CostItem", back_populates="estimate", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_estimate_vehicle", "vehicle_id"),
        Index("idx_estimate_status", "status"),
        Index("idx_estimate_created", "created_at"),
    )
    
    def __repr__(self):
        return f"<CostEstimate(id={self.estimate_id}, total={self.total_estimate} {self.currency})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "estimate_id": self.estimate_id,
            "vehicle_id": self.vehicle_uuid,
            "status": self.status.value if self.status else None,
            "subtotal_parts": self.subtotal_parts,
            "subtotal_labor": self.subtotal_labor,
            "subtotal_other": self.subtotal_other,
            "discount_amount": self.discount_amount,
            "tax_amount": self.tax_amount,
            "total_estimate": self.total_estimate,
            "estimate_range": {
                "low": self.estimate_low,
                "high": self.estimate_high,
            },
            "confidence_score": self.confidence_score,
            "estimated_labor_hours": self.estimated_labor_hours,
            "warranty_coverage": self.warranty_coverage_amount,
            "summary": self.summary,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            # NOTE: items are NOT included here to prevent async errors. 
            # They must be attached manually by the service layer.
            "items": [], 
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "currency": self.currency
        }
    
    def calculate_totals(self):
        """Recalculate totals from items"""
        self.subtotal_parts = sum(
            item.total_price for item in self.items 
            if item.category == CostCategory.PARTS
        )
        self.subtotal_labor = sum(
            item.total_price for item in self.items 
            if item.category == CostCategory.LABOR
        )
        self.subtotal_other = sum(
            item.total_price for item in self.items 
            if item.category not in [CostCategory.PARTS, CostCategory.LABOR, CostCategory.TAX]
        )
        
        subtotal = self.subtotal_parts + self.subtotal_labor + self.subtotal_other
        after_discount = subtotal - self.discount_amount
        
        if self.tax_rate:
            self.tax_amount = after_discount * (self.tax_rate / 100)
        
        self.total_estimate = after_discount + self.tax_amount - self.warranty_coverage_amount


class CostItem(Base):
    """
    Cost Item
    Individual line items in a cost estimate
    """
    __tablename__ = "cost_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    estimate_id = Column(Integer, ForeignKey("cost_estimates.id", ondelete="CASCADE"), nullable=False)
    
    # Item Details
    item_code = Column(String(50), nullable=True)
    category = Column(SQLEnum(CostCategory), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Pricing
    quantity = Column(Float, default=1.0)
    unit = Column(String(20), default="each")  # each, hour, liter, etc.
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    
    # Part Details (if applicable)
    part_number = Column(String(50), nullable=True)
    manufacturer = Column(String(100), nullable=True)
    is_oem_part = Column(Boolean, default=True)
    
    # Labor Details (if applicable)
    labor_hours = Column(Float, nullable=True)
    labor_rate = Column(Float, nullable=True)
    technician_level = Column(String(20), nullable=True)  # JUNIOR, SENIOR, SPECIALIST
    
    # Warranty
    warranty_covered = Column(Boolean, default=False)
    warranty_coverage_percent = Column(Float, nullable=True)
    
    # Availability
    in_stock = Column(Boolean, nullable=True)
    lead_time_days = Column(Integer, nullable=True)
    
    # Optional/Required
    is_required = Column(Boolean, default=True)
    is_recommended = Column(Boolean, default=False)
    
    # Sorting
    sort_order = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    estimate = relationship("CostEstimate", back_populates="items")
    
    def __repr__(self):
        return f"<CostItem(name={self.name}, total={self.total_price})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "estimate_id": self.estimate_id,
            "item_code": self.item_code,
            "category": self.category.value if self.category else None,
            "name": self.name,
            "description": self.description,
            "quantity": self.quantity,
            "unit": self.unit,
            "unit_price": self.unit_price,
            "total_price": self.total_price,
            "part_number": self.part_number,
            "is_oem_part": self.is_oem_part,
            "labor_hours": self.labor_hours,
            "labor_rate": self.labor_rate,
            "technician_level": self.technician_level,
            "warranty_covered": self.warranty_covered,
            "is_required": self.is_required,
            "sort_order": self.sort_order,
        }