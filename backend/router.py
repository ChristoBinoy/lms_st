from sqlalchemy.orm import Session
from backend.models import Lead, ActivityLog

def assign_leads_round_robin(db: Session, current_session_agent: str = "SYSTEM_BOARDS"):
    """
    Advanced Routing Engine:
    1. Bypasses and locks 'Self-Sourced' leads to the session user.
    2. Segregates incoming traffic by priority (Premium processed first).
    3. Enforces capacity guardrails to prevent agent burnout.
    """

    # Step 1: Query unassigned leads, pulling "Premium" to the top, then "Standard"

    # We sort by lead_type descending so 'Premium' comes before 'Standard' alphabetically
    unassigned_leads = (
        db.query(Lead)
        .filter(Lead.assigned_agent_id == None)
        .order_by(Lead.lead_type.desc())
        .all()
    )

    
    if not unassigned_leads:

        return 0
        
    # Our active corporate sales team roster
    agents = ["AGENT_ALPHA", "AGENT_BETA", "AGENT_GAMMA"]
    MAX_CAPACITY = 3  # The maximum active leads an agent can hold at once
    
    assigned_count = 0
    
    for index, lead in enumerate(unassigned_leads):
        
        # --- RULE 1: SELF-SOURCED SESSION LOCK-IN ---
        if lead.lead_type == "Self-Sourced":
            assigned_agent = current_session_agent
            lead.assigned_agent_id = assigned_agent
            
            new_log = ActivityLog(
                lead_id=lead.id,
                agent_id=assigned_agent,
                action_type="Assignment",
                notes=f"Self-Sourced Lead locked directly to active session profile: {assigned_agent}"
            )
            db.add(new_log)
            assigned_count += 1
            continue
            
        # --- RULE 2: CAPACITY & PRIORITY ROUND-ROBIN ROUTING ---
        assigned_successfully = False
        attempts = 0
        
        # We loop through our agents array starting from our round-robin index point
        while attempts < len(agents):
            # Calculate the rotational candidate index
            candidate_agent = agents[(index + attempts) % len(agents)]
            
            # Real-time Capacity Check: Count how many active leads this agent is holding
            active_load = (
                db.query(Lead)
                .filter(
                    Lead.assigned_agent_id == candidate_agent,
                    Lead.pipeline_stage.in_(["Assigned", "Contacted", "In Negotiation"])
                )
                .count()
            )

            
            if active_load < MAX_CAPACITY:
                # Agent has open bandwidth! Complete the assignment transaction
                lead.assigned_agent_id = candidate_agent
                
                # Append a specialized note indicating if it was a high priority route
                priority_tag = "🌟 PREMIUM TRACK" if lead.lead_type == "Premium" else "STANDARD TRACK"

                
                new_log = ActivityLog(

                    lead_id=lead.id,

                    agent_id=candidate_agent,
                    action_type="Assignment",
                    notes=f"[{priority_tag}] Automatically routed to {candidate_agent}. Current workload: {active_load}/{MAX_CAPACITY} active leads."
                )
                db.add(new_log)
                assigned_successfully = True
                assigned_count += 1
                break  # Break out of the while loop since we found an available agent

                
            # If the candidate was full, step to the next agent in line
            attempts += 1
            
        # Optional Edge Case: If ALL agents are entirely full, leave the lead unassigned 

        # for safety rather than dumping it onto an overloaded agent

        if not assigned_successfully:
            continue
            

    db.commit()
    return assigned_count


