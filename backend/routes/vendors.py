from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Vendor, Invoice, AuditLog, User
from backend.schemas import VendorOut, VendorCreate
from backend.security import get_current_user
from backend.routes.auth import check_admin_user
from backend.services.validation import clean_numeric_string

router = APIRouter(prefix="/api/vendors", tags=["Vendors"])

@router.get("", response_model=List[VendorOut])
def get_vendors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns list of vendors along with total invoices count and accumulated purchase value.
    """
    vendors = db.query(Vendor).all()
    results = []
    
    for v in vendors:
        invoices = db.query(Invoice).filter(Invoice.vendor_id == v.id).all()
        total_count = len(invoices)
        
        # Calculate sum of total amount
        total_sum = 0.0
        currency_symbol = "₹"  # default
        
        for inv in invoices:
            total_sum += clean_numeric_string(inv.total_amount)
            if inv.total_amount and "$" in inv.total_amount:
                currency_symbol = "$"
                
        # Format total sum nicely
        if currency_symbol == "$":
            formatted_sum = f"${total_sum:,.2f}"
        else:
            formatted_sum = f"₹{total_sum:,.2f}"
            
        results.append({
            "id": v.id,
            "vendor_name": v.vendor_name,
            "gst_number": v.gst_number or "Unlisted",
            "contact": v.contact or "N/A",
            "total_invoices": total_count,
            "total_purchase_amount": formatted_sum,
            "created_at": v.created_at
        })
        
    return results

@router.post("", response_model=VendorOut)
def create_vendor(
    payload: VendorCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(check_admin_user)
):
    """
    Registers a new vendor profile in the ERP system. ADMIN ONLY.
    """
    existing = db.query(Vendor).filter(Vendor.vendor_name == payload.vendor_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Vendor name already exists.")
        
    v = Vendor(
        vendor_name=payload.vendor_name,
        gst_number=payload.gst_number,
        contact=payload.contact
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    
    # Audit log
    audit = AuditLog(
        user=admin_user.username,
        action="Vendor Create",
        details=f"Created vendor profile '{v.vendor_name}' with GST '{v.gst_number}'."
    )
    db.add(audit)
    db.commit()
    
    return {
        "id": v.id,
        "vendor_name": v.vendor_name,
        "gst_number": v.gst_number,
        "contact": v.contact,
        "total_invoices": 0,
        "total_purchase_amount": "₹0.00",
        "created_at": v.created_at
    }

@router.put("/{id}", response_model=VendorOut)
def update_vendor(
    id: int,
    payload: VendorCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(check_admin_user)
):
    """
    Modifies vendor contact or GST registration details. ADMIN ONLY.
    """
    v = db.query(Vendor).filter(Vendor.id == id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found.")
        
    v.vendor_name = payload.vendor_name
    v.gst_number = payload.gst_number
    v.contact = payload.contact
    
    db.commit()
    db.refresh(v)
    
    # Recalculate aggregates
    invoices = db.query(Invoice).filter(Invoice.vendor_id == v.id).all()
    total_count = len(invoices)
    total_sum = sum(clean_numeric_string(inv.total_amount) for inv in invoices)
    
    # Audit log
    audit = AuditLog(
        user=admin_user.username,
        action="Vendor Edit",
        details=f"Updated vendor details for '{v.vendor_name}'."
    )
    db.add(audit)
    db.commit()
    
    return {
        "id": v.id,
        "vendor_name": v.vendor_name,
        "gst_number": v.gst_number,
        "contact": v.contact,
        "total_invoices": total_count,
        "total_purchase_amount": f"₹{total_sum:,.2f}",
        "created_at": v.created_at
    }

@router.delete("/{id}")
def delete_vendor(
    id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(check_admin_user)
):
    """
    Deletes a vendor profile and cascades deletion of its invoices. ADMIN ONLY.
    """
    v = db.query(Vendor).filter(Vendor.id == id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found.")
        
    vendor_name = v.vendor_name
    db.delete(v)
    db.commit()
    
    # Audit log
    audit = AuditLog(
        user=admin_user.username,
        action="Vendor Delete",
        details=f"Deleted vendor '{vendor_name}' and all associated invoices."
    )
    db.add(audit)
    db.commit()
    
    return {"message": f"Successfully deleted vendor '{vendor_name}'."}
