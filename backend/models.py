import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from backend.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="EMPLOYEE")  # ADMIN, EMPLOYEE
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    vendor_name = Column(String, unique=True, index=True, nullable=False)
    gst_number = Column(String, nullable=True)
    contact = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    invoices = relationship("Invoice", back_populates="vendor", cascade="all, delete-orphan")

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    invoice_number = Column(String, index=True, nullable=False)
    date = Column(String, nullable=True)  # Store as YYYY-MM-DD string
    tax_amount = Column(String, nullable=True)  # Store original currency formatted string
    total_amount = Column(String, nullable=True)  # Store original currency formatted string
    confidence = Column(String, nullable=True)  # Overall confidence percentage
    status = Column(String, default="Needs Review")  # Approved, Needs Review, Rejected
    sync_status = Column(String, default="Pending")  # Synced, Pending
    raw_text = Column(Text, nullable=True)  # Reconstructed invoice text
    payment_terms = Column(String, nullable=True)  # Store payment terms string
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    vendor = relationship("Vendor", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")

class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    description = Column(String, nullable=False)
    quantity = Column(Float, nullable=True)
    unit_price = Column(String, nullable=True)  # e.g., "$150.00" or "₹450.00"
    total_price = Column(String, nullable=True)  # e.g., "$6,000.00" or "₹1,12,500.00"

    # Relationships
    invoice = relationship("Invoice", back_populates="items")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String, nullable=False)  # User's username who triggered action
    action = Column(String, nullable=False)  # Login, Upload, Delete, Sync, etc.
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    details = Column(Text, nullable=True)
