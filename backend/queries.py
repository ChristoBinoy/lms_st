from sqlalchemy.orm import Session
from .models import Lead

def get_all_leads_flat(db: Session):
    """
    Queries the database for all leads and structures them 
    into a simple list of dictionaries for the frontend layout.
    """

    leads = db.query(Lead).all()

    
    flat_leads = []
    for lead in leads:

        flat_leads.append({
            "Lead ID": lead.id[:8] + "...", # Shorten UUID for clean display

            "Name": lead.name,
            "Phone": lead.phone,
            "Email": lead.email,
            "Stage": lead.pipeline_stage,
            "Source": lead.first_touch_source,
            "Type": lead.lead_type
        })
        
    return flat_leads
