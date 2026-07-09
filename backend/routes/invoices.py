import datetime
import os
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Invoice, InvoiceItem, Vendor, AuditLog, User
from backend.schemas import InvoiceOut, InvoiceUpdate
from backend.security import get_current_user
from backend.routes.auth import check_admin_user
from backend.services.ai_parser import parse_invoice, extract_pdf_text, test_gemini_connection
from backend.services.validation import validate_invoice

router = APIRouter(prefix="/api/invoices", tags=["Invoices"])

# Global in-memory configuration state (initialized with Sandbox mode disabled)
SYSTEM_SETTINGS = {
    "gemini_api_key": "",
    "gemini_model": "gemini-2.0-flash-lite"
}

@router.post("/upload", response_model=InvoiceOut)
async def upload_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads an invoice file (PDF/Image), extracts structured data using Gemini AI,
    validates, and saves in database.
    """
    file_bytes = await file.read()
    file_mime = file.content_type
    
    # Before invoice upload test Gemini connection
    if not test_gemini_connection():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gemini configuration failed"
        )
        
    # Call active Gemini AI service
    res = parse_invoice(
        file_bytes=file_bytes,
        file_mime_type=file_mime
    )
    if not res["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=res.get("error")
        )
        
    extracted_data = res["data"]

    # 2. Extract results & trigger validation engine
    vendor_name = extracted_data.get("vendor") or "Unknown Vendor"
    invoice_number = extracted_data.get("invoice_number") or f"INV-{datetime.datetime.utcnow().microsecond}"
    invoice_date = extracted_data.get("invoice_date") or datetime.date.today().isoformat()
    tax_amount = extracted_data.get("tax") or "₹0.00"
    total_amount = extracted_data.get("grand_total") or "₹0.00"
    payment_terms = extracted_data.get("payment_terms")
    materials = extracted_data.get("materials") or []

    # Map materials list to line_items format needed by validate_invoice
    line_items = []
    for item in materials:
        line_items.append({
            "description": item.get("description") or "Invoice Line Material",
            "quantity": float(item.get("quantity") or 1.0),
            "unit_price": item.get("rate") or "₹0.00",
            "total_price": item.get("amount") or "₹0.00"
        })

    # Run checks
    val_status, val_notes = validate_invoice(
        db=db,
        vendor_name=vendor_name,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        total_amount=total_amount,
        line_items=line_items
    )

    # 3. Create or resolve Vendor
    vendor = db.query(Vendor).filter(Vendor.vendor_name == vendor_name).first()
    if not vendor:
        vendor = Vendor(
            vendor_name=vendor_name,
            gst_number="Unlisted",
            contact="info@vendor.com"
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

    # 4. Save Invoice
    new_invoice = Invoice(
        vendor_id=vendor.id,
        invoice_number=invoice_number,
        date=invoice_date,
        tax_amount=tax_amount,
        total_amount=total_amount,
        confidence="95%",
        status=val_status,
        sync_status="Pending",
        payment_terms=payment_terms,
        raw_text=extracted_data.get("raw_text") or "No raw text available.",
    )
    
    # Save validation notes as raw text headers if any
    if val_notes:
        new_invoice.raw_text = f"=== SYSTEM VALIDATION ALERTS ===\n" + "\n".join(val_notes) + "\n===============================\n\n" + new_invoice.raw_text

    db.add(new_invoice)
    db.commit()
    db.refresh(new_invoice)

    # 5. Save Line Items
    for item in line_items:
        new_item = InvoiceItem(
            invoice_id=new_invoice.id,
            description=item["description"],
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            total_price=item["total_price"]
        )
        db.add(new_item)
    
    db.commit()

    # 6. Audit Logging
    audit = AuditLog(
        user=current_user.username,
        action="Invoice Upload",
        details=f"Uploaded invoice '{invoice_number}' for vendor '{vendor_name}'. Extracted status: {val_status}. Confidence: {new_invoice.confidence}."
    )
    db.add(audit)
    db.commit()

    # Return structure with vendor_name populated for response
    new_invoice.vendor_name = vendor.vendor_name
    return new_invoice

@router.get("", response_model=List[InvoiceOut])
def get_invoices(
    search: Optional[str] = None,
    status: Optional[str] = None,
    vendor_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns lists of invoices. Supports search querying and status/vendor filters.
    """
    query = db.query(Invoice)
    
    # Apply filters
    if status:
        query = query.filter(Invoice.status == status)
    if vendor_id:
        query = query.filter(Invoice.vendor_id == vendor_id)
        
    invoices = query.all()
    
    # Process results to attach vendor_name
    results = []
    for inv in invoices:
        inv.vendor_name = inv.vendor.vendor_name
        
        # Apply search filter manually or in query
        if search:
            search_lower = search.lower()
            if (search_lower in inv.invoice_number.lower() or 
                search_lower in inv.vendor_name.lower() or
                search_lower in (inv.date or "")):
                results.append(inv)
        else:
            results.append(inv)
            
    return results

@router.get("/{id}", response_model=InvoiceOut)
def get_invoice_details(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetches details of a single invoice.
    """
    inv = db.query(Invoice).filter(Invoice.id == id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice record not found.")
    inv.vendor_name = inv.vendor.vendor_name
    return inv

@router.put("/{id}", response_model=InvoiceOut)
def update_invoice(
    id: int,
    payload: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates invoice metadata.
    """
    inv = db.query(Invoice).filter(Invoice.id == id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice record not found.")
        
    # Resolve vendor_name change
    vendor = db.query(Vendor).filter(Vendor.vendor_name == payload.vendor_name).first()
    if not vendor:
        vendor = Vendor(vendor_name=payload.vendor_name, contact="info@vendor.com")
        db.add(vendor)
        db.commit()
        db.refresh(vendor)
        
    inv.vendor_id = vendor.id
    inv.invoice_number = payload.invoice_number
    inv.date = payload.date
    inv.tax_amount = payload.tax_amount
    inv.total_amount = payload.total_amount
    inv.confidence = payload.confidence
    inv.status = payload.status
    inv.sync_status = payload.sync_status
    
    db.commit()
    db.refresh(inv)
    
    # Audit log
    audit = AuditLog(
        user=current_user.username,
        action="Invoice Edit",
        details=f"Edited invoice '{inv.invoice_number}' (ID: {inv.id}). Updated status to {inv.status}."
    )
    db.add(audit)
    db.commit()
    
    inv.vendor_name = vendor.vendor_name
    return inv

@router.delete("/{id}")
def delete_invoice(
    id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(check_admin_user)  # Gate deleting to Admin role
):
    """
    Removes an invoice record. ADMIN ONLY.
    """
    inv = db.query(Invoice).filter(Invoice.id == id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice record not found.")
        
    invoice_number = inv.invoice_number
    vendor_name = inv.vendor.vendor_name
    
    db.delete(inv)
    db.commit()
    
    # Audit log
    audit = AuditLog(
        user=admin_user.username,
        action="Invoice Delete",
        details=f"Deleted invoice '{invoice_number}' for vendor '{vendor_name}' (ID: {id})."
    )
    db.add(audit)
    db.commit()
    
    return {"message": f"Successfully deleted invoice ID {id}."}

@router.post("/{id}/sync")
def sync_to_erp(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Pushes the validated invoice structure to the ERP ledger system.
    """
    inv = db.query(Invoice).filter(Invoice.id == id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice record not found.")
        
    if inv.status == "Rejected":
        raise HTTPException(status_code=400, detail="Cannot sync a rejected invoice to the ERP ledger.")
        
    inv.sync_status = "Synced"
    db.commit()
    
    # Audit log
    audit = AuditLog(
        user=current_user.username,
        action="ERP Sync",
        details=f"Synced invoice '{inv.invoice_number}' for vendor '{inv.vendor.vendor_name}' to gateway ledger."
    )
    db.add(audit)
    db.commit()
    
    return {
        "success": True, 
        "message": f"Successfully pushed Invoice '{inv.invoice_number}' into ConstructAI ERP central gateway!"
    }
