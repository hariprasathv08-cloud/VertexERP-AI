import re
from typing import List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from backend.models import Invoice, Vendor

def clean_numeric_string(value_str: str) -> float:
    """
    Cleans a currency/amount string (e.g. "₹1,12,500.00", "$342.50", " 120.5 ")
    and converts it to a float. Returns 0.0 if parsing fails.
    """
    if not value_str:
        return 0.0
    # Remove everything except digits, dots, and minus signs
    cleaned = re.sub(r'[^\d\.\-]', '', str(value_str))
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0

def validate_invoice(
    db: Session,
    vendor_name: str,
    invoice_number: str,
    invoice_date: str,
    total_amount: str,
    line_items: List[Dict[str, Any]]
) -> Tuple[str, List[str]]:
    """
    Validates an invoice against business rules.
    Returns (status, list_of_validation_notes).
    Status can be 'Approved', 'Needs Review', or 'Rejected'.
    """
    notes = []
    is_duplicate = False
    
    # 1. Missing Fields Check
    missing_fields = []
    if not vendor_name or vendor_name == "Unknown Vendor":
        missing_fields.append("Vendor Name")
    if not invoice_number:
        missing_fields.append("Invoice Number")
    if not invoice_date:
        missing_fields.append("Invoice Date")
    if not total_amount or total_amount == "₹0.00":
        missing_fields.append("Total Amount")
        
    if missing_fields:
        notes.append(f"Warning: Core fields missing: {', '.join(missing_fields)}")

    # 2. Duplicate Detection
    if vendor_name and invoice_number and vendor_name != "Unknown Vendor":
        # Resolve vendor
        existing_vendor = db.query(Vendor).filter(Vendor.vendor_name == vendor_name).first()
        if existing_vendor:
            existing_invoice = db.query(Invoice).filter(
                Invoice.vendor_id == existing_vendor.id,
                Invoice.invoice_number == invoice_number
            ).first()
            if existing_invoice:
                notes.append(f"Error: Duplicate invoice detected. Vendor '{vendor_name}' and Invoice '{invoice_number}' already exist in database (Invoice ID: {existing_invoice.id}).")
                is_duplicate = True

    # 3. Calculation Check
    grand_total_val = clean_numeric_string(total_amount)
    line_items_total = 0.0
    math_errors = []

    for idx, item in enumerate(line_items):
        qty = float(item.get("quantity") or 0)
        u_price = clean_numeric_string(item.get("unit_price"))
        row_total = clean_numeric_string(item.get("total_price"))

        # Row check: Qty * Unit Price = Total Price
        expected_row_total = qty * u_price
        if expected_row_total > 0 and abs(expected_row_total - row_total) > 1.0:
            math_errors.append(f"Row {idx+1} math mismatch: Qty ({qty}) * Rate ({u_price}) = {expected_row_total:.2f}, but total listed is {row_total:.2f}.")
        
        line_items_total += row_total

    # Overall calculation sum vs grand total
    if grand_total_val > 0 and line_items and abs(line_items_total - grand_total_val) > 1.0:
        notes.append(f"Warning: Total calculation mismatch. Sum of line items ({line_items_total:.2f}) does not match listed Grand Total ({grand_total_val:.2f}).")
    
    if math_errors:
        notes.extend(math_errors[:3])

    # Determine status
    if is_duplicate:
        status = "Rejected"
    elif notes:
        status = "Needs Review"
    else:
        status = "Approved"

    return status, notes
