from datetime import datetime,timezone
from sqlalchemy.orm import Session
from .models import Lead,ActivityLog

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


def update_lead_stage(db: Session, lead_id: str, new_stage: str, current_user: str):
    """
    Updates a single lead's pipeline stage using a strict State Machine 
    validation wrapper and records the transaction ledger footprint.
    """
    # Step 1: Query the database for the single lead matching the lead_id
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    
    if not lead:
        return False
        
    # Step 2: Capture state snapshot before mutations happen
    old_stage = lead.pipeline_stage
    
    # --- STATE MACHINE VALIDATION GUARD ---
    ALLOWED_TRANSITIONS = {
        "Discovered": ["Assigned"],
        "Assigned": ["Contacted"],
        "Contacted": ["In Negotiation", "Won", "Lost"],
        "In Negotiation": ["Won", "Lost"],
        "Won": [],
        "Lost": ["Assigned"]
    }
    
    # Safety Check: If the old stage is corrupted/missing, handle it safely
    if old_stage not in ALLOWED_TRANSITIONS:
        old_stage = "Discovered"

    # Step 3: Enforce Transition Rules
    if new_stage in ALLOWED_TRANSITIONS[old_stage]:
        # Execution Phase A: Mutate the data row object
        lead.pipeline_stage = new_stage
        
        # Execution Phase B: Generate the immutable historical logging footprint
        new_log = ActivityLog(
            lead_id=lead.id,
            agent_id=current_user,
            action_type="Stage Transition",
            old_value=old_stage,
            new_value=new_stage,
            notes=f"State successfully advanced from {old_stage} to {new_stage}."
        )
        # Stage the log inside the successful execution block scope
        db.add(new_log)
    else:
        # Halt execution completely before any database writes occur
        raise ValueError(f"Illegal data transition! Cannot move from {old_stage} to {new_stage}")
        
    # Step 4: Safely lock both updates down to storage in a single unified database transaction
    db.commit()
    
    return True

def single_lead_input(db: Session, name: str, phone: str, email: str, source: str, lead_type: str, current_user: str):
    # Step 1: Duplicate Scan
    exist_lead = db.query(Lead).filter((Lead.email == email) | (Lead.phone == phone)).first()
    
    if exist_lead:
        # Step 2: Time Calculations
        current_time = datetime.now(timezone.utc)
        lead_last_touch = exist_lead.updated_at
        
        # Check if the timestamp from the DB lacks timezone info (naive datetime)
        if lead_last_touch.tzinfo is None:
            lead_last_touch = lead_last_touch.replace(tzinfo=timezone.utc)
            
        time_diff = current_time - lead_last_touch
        hours_neglected = time_diff.total_seconds() / 3600
        STALE_THRESHOLD_HOURS = 48

        # CASE 1: THE NEGLECT PENALTY (Stage check + Time check)
        if exist_lead.pipeline_stage in ["Assigned", "Discovered"] and hours_neglected >= STALE_THRESHOLD_HOURS:
            old_agent = exist_lead.assigned_agent_id
            
            # Reassign and upgrade to Self-Sourced track
            exist_lead.assigned_agent_id = current_user
            exist_lead.pipeline_stage = "Contacted"
            exist_lead.lead_type = lead_type
            exist_lead.updated_at = datetime.now() # Updates the tracking clock

            new_log = ActivityLog(
                lead_id=exist_lead.id,
                agent_id=current_user,
                action_type="Escalation Transfer",
                old_value=old_agent if old_agent else "UNASSIGNED",
                new_value=current_user,
                notes=f"Lead was neglected for {hours_neglected:.1f} hours. Ownership hijacked by {current_user}."
            )
            db.add(new_log)
            db.commit()
            return "REASSIGNED_TO_YOU"
            
        # CASE 2: ACTIVE DUPLICATE BLOCK
        else:
            return "ACTIVE_WITH_OTHER_AGENT"

    # --- CASE 3: COMPLETELY NEW LEAD (Now properly aligned outside the if block!) ---
    if lead_type == "Self-Sourced":
        assigned_agent = current_user
    else:
        assigned_agent = None

    new_lead = Lead(
        name=name, 
        phone=phone, 
        email=email, 
        source=source,
        lead_type=lead_type, 
        assigned_agent_id=assigned_agent, 
        pipeline_stage="Discovered"
    )
    db.add(new_lead)
    db.flush() # Secure the new unique ID in memory first

    new_log = ActivityLog(
        lead_id=new_lead.id, 
        agent_id=current_user, 
        action_type="Ingestion",
        notes=f"Fresh lead profile manually registered under {lead_type} track."
    )
    db.add(new_log)
    db.commit()
    
    return "SUCCESS"
