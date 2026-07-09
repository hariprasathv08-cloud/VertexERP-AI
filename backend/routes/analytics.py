from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from collections import defaultdict
from backend.database import get_db
from backend.models import Invoice, Vendor, User
from backend.security import get_current_user
from backend.services.validation import clean_numeric_string

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("")
def get_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns analytics KPIs and dataset structures for Chart.js rendering on frontend.
    """
    invoices = db.query(Invoice).all()
    vendors = db.query(Vendor).all()
    
    # 1. Calculate General KPIs
    total_invoices_count = len(invoices)
    total_vendors_count = len(vendors)
    
    processed_count = sum(1 for inv in invoices if inv.status == "Approved")
    pending_count = sum(1 for inv in invoices if inv.status == "Needs Review")
    rejected_count = sum(1 for inv in invoices if inv.status == "Rejected")
    
    total_expense = 0.0
    total_confidence = 0.0
    confidence_count = 0
    
    for inv in invoices:
        amount = clean_numeric_string(inv.total_amount)
        total_expense += amount
        
        # Calculate average AI confidence
        if inv.confidence:
            clean_c = inv.confidence.replace("%", "")
            try:
                total_confidence += float(clean_c)
                confidence_count += 1
            except ValueError:
                pass
                
    avg_accuracy = (total_confidence / confidence_count) if confidence_count > 0 else 98.0
    
    # 2. Monthly Expenses Chart Dataset (Last 6 months)
    monthly_data = defaultdict(float)
    for inv in invoices:
        if inv.date:
            # Try to grab "YYYY-MM"
            month = inv.date[:7]
            if len(month) == 7 and month[4] == "-":
                monthly_data[month] += clean_numeric_string(inv.total_amount)
        else:
            # Fallback to created_at month
            month = inv.created_at.strftime("%Y-%m")
            monthly_data[month] += clean_numeric_string(inv.total_amount)
            
    # Sort monthly data chronologically
    sorted_months = sorted(monthly_data.keys())[-6:]
    monthly_labels = sorted_months
    monthly_values = [monthly_data[m] for m in sorted_months]
    
    # If no monthly data, seed with current month so charts are not blank
    if not monthly_labels:
        import datetime
        curr = datetime.date.today().strftime("%Y-%m")
        monthly_labels = [curr]
        monthly_values = [0.0]

    # 3. Vendor Spending Chart Dataset
    vendor_spending = defaultdict(float)
    for inv in invoices:
        vendor_name = inv.vendor.vendor_name
        vendor_spending[vendor_name] += clean_numeric_string(inv.total_amount)
        
    sorted_vendors = sorted(vendor_spending.items(), key=lambda x: x[1], reverse=True)
    
    vendor_labels = []
    vendor_values = []
    
    # Limit to top 5 vendors and bucket others
    for idx, (name, val) in enumerate(sorted_vendors):
        if idx < 5:
            vendor_labels.append(name)
            vendor_values.append(val)
        else:
            if "Others" not in vendor_labels:
                vendor_labels.append("Others")
                vendor_values.append(val)
            else:
                others_idx = vendor_labels.index("Others")
                vendor_values[others_idx] += val

    # 4. Invoice Status Dataset
    status_labels = ["Approved", "Needs Review", "Rejected"]
    status_values = [processed_count, pending_count, rejected_count]

    # Format numbers for dashboard view
    formatted_expense = f"₹{total_expense:,.2f}"

    # Calculate monthly growth rate dynamically
    import datetime
    today = datetime.date.today()
    curr_month = today.strftime("%Y-%m")
    # Find previous month
    first_of_this_month = today.replace(day=1)
    prev_month_date = first_of_this_month - datetime.timedelta(days=1)
    prev_month = prev_month_date.strftime("%Y-%m")
    
    curr_val = monthly_data.get(curr_month, 0.0)
    prev_val = monthly_data.get(prev_month, 0.0)
    
    if prev_val > 0.0:
        growth = ((curr_val - prev_val) / prev_val) * 100.0
        growth_sign = "+" if growth >= 0 else ""
        monthly_growth = f"{growth_sign}{growth:.1f}%"
    else:
        monthly_growth = "+0.0%" if curr_val == 0.0 else "+100.0%"

    return {
        "kpis": {
            "total_invoices": total_invoices_count,
            "processed_invoices": processed_count,
            "pending_review": pending_count,
            "total_expense": formatted_expense,
            "total_vendors": total_vendors_count,
            "avg_accuracy": f"{avg_accuracy:.1f}%",
            "monthly_growth": monthly_growth
        },
        "charts": {
            "monthly_expenses": {
                "labels": monthly_labels,
                "data": [round(val, 2) for val in monthly_values]
            },
            "vendor_spending": {
                "labels": vendor_labels,
                "data": [round(val, 2) for val in vendor_values]
            },
            "invoice_status": {
                "labels": status_labels,
                "data": status_values
            }
        }
    }
