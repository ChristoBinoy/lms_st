import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base

# Function to generate a clean, unique string ID for every single lead
def generate_uuid():

    return str(uuid.uuid4())

class Lead(Base):
    __tablename__ = "leads"

    # 1. Primary & Shorthand Identifiers
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False, index=True) # Index makes lookups lighting fast
    email = Column(String, nullable=False, index=True)


    # 2. Pipeline State Management [cite: 6]
    pipeline_stage = Column(String, nullable=False, default="New") # New -> Contacted -> Interested -> Negotiating -> Closed/Lost
    lead_score = Column(Integer, nullable=False, default=0)


    # 3. Marketing Ingestion Attribution [cite: 158]
    first_touch_source = Column(String, nullable=False)
    last_touch_source = Column(String, nullable=False)

    lead_type = Column(String, nullable=False) # 'Paid' or 'Self-Sourced' [cite: 158]

    # 4. Operational Controls & Permissions [cite: 158, 177]
    assigned_agent_id = Column(String, nullable=True)
    assigned_tl_id = Column(String, nullable=True)
    contact_lock_status = Column(String, default="Unlocked")
    contact_lock_expires_at = Column(String, nullable=True)

    # 5. Timing, Compliance & SLA Variables [cite: 158, 183, 185]
    consent_timestamp = Column(String, nullable=False)
    consent_channel = Column(String, nullable=False)

    age_clock = Column(String, nullable=False) # Tracks last human interaction timestamp [cite: 158, 183]
    sla_clock = Column(String, nullable=False) # Tracks time stuck in current pipeline stage [cite: 185]
    contact_preference = Column(String, default="Call")
    preferred_contact_window = Column(String, default="Anytime")
    crm_sync_status = Column(Integer, default=0) # 0 for False, 1 for True

    # 6. Relationships (Allows Python to easily pull a lead's history using object properties)
    sources = relationship("LeadSource", back_populates="lead", cascade="all, delete-orphan")
    logs = relationship("ActivityLog", back_populates="lead", cascade="all, delete-orphan")

    # 7. Database Enforced Constraints
    __table_args__ = (
        UniqueConstraint('phone', 'email', name='_phone_email_uc'),
    )



class LeadSource(Base):
    __tablename__ = "lead_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(String, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    source_name = Column(String, nullable=False) # e.g., 'Google Ads', 'WhatsApp' [cite: 27]
    campaign_name = Column(String, nullable=True)
    submitted_at = Column(String, nullable=False, default=lambda: datetime.utcnow().isoformat())
    form_data_captured = Column(String, nullable=True) # Text representation of extra fields

    # Link back to the parent lead object
    lead = relationship("Lead", back_populates="sources")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(String, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(String, nullable=False)
    action_type = Column(String, nullable=False) # 'Call Outcome', 'Stage Change', 'Note Added' 
    old_value = Column(String, nullable=True)

    new_value = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    timestamp = Column(String, nullable=False, default=lambda: datetime.utcnow().isoformat())

    # Link back to the parent lead object
    lead = relationship("Lead", back_populates="logs")
