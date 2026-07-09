from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

# --- TOKEN SCHEMAS ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# --- USER SCHEMAS ---
class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str
    role: Optional[str] = "EMPLOYEE"  # ADMIN, EMPLOYEE

class UserOut(UserBase):
    id: int
    role: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- INVOICE ITEM SCHEMAS ---
class InvoiceItemBase(BaseModel):
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[str] = None
    total_price: Optional[str] = None

class InvoiceItemCreate(InvoiceItemBase):
    pass

class InvoiceItemOut(InvoiceItemBase):
    id: int
    invoice_id: int

    class Config:
        from_attributes = True

# --- INVOICE SCHEMAS ---
class InvoiceBase(BaseModel):
    invoice_number: str
    date: Optional[str] = None
    tax_amount: Optional[str] = None
    total_amount: Optional[str] = None
    confidence: Optional[str] = None
    status: Optional[str] = "Needs Review"
    sync_status: Optional[str] = "Pending"
    raw_text: Optional[str] = None
    payment_terms: Optional[str] = None

class InvoiceCreate(InvoiceBase):
    vendor_name: str
    items: List[InvoiceItemCreate]

class InvoiceUpdate(BaseModel):
    vendor_name: str
    invoice_number: str
    date: Optional[str] = None
    tax_amount: Optional[str] = None
    total_amount: Optional[str] = None
    confidence: Optional[str] = None
    status: Optional[str] = "Needs Review"
    sync_status: Optional[str] = "Pending"
    payment_terms: Optional[str] = None

class InvoiceOut(InvoiceBase):
    id: int
    vendor_id: int
    vendor_name: str
    created_at: datetime
    items: List[InvoiceItemOut]

    class Config:
        from_attributes = True

# --- VENDOR SCHEMAS ---
class VendorBase(BaseModel):
    vendor_name: str
    gst_number: Optional[str] = None
    contact: Optional[str] = None

class VendorCreate(VendorBase):
    pass

class VendorOut(VendorBase):
    id: int
    total_invoices: int
    total_purchase_amount: str  # Formatted grand total sum or numeric representation
    created_at: datetime

    class Config:
        from_attributes = True

# --- AUDIT LOG SCHEMAS ---
class AuditLogOut(BaseModel):
    id: int
    user: str
    action: str
    timestamp: datetime
    details: Optional[str] = None

    class Config:
        from_attributes = True

# --- SETTINGS SCHEMAS ---
class SettingsUpdate(BaseModel):
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None

class SettingsOut(BaseModel):
    has_key: bool
    gemini_model: Optional[str] = None
