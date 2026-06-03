import pandas as pd
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from .models import Lead, LeadSource, ActivityLog

def process_bulk_csv(file_path: str, db: Session, chunk_size: int = 500):
    """
    Reads a clean CSV file and streams it into the database 
    using high-performance batch processing.
    """
    current_time = datetime.utcnow().isoformat()
    total_inserted = 0
    total_skipped = 0


    # 1. Read CSV in chunks using Pandas to save system memory
    for chunk in pd.read_csv(file_path, chunksize=chunk_size):
        
        # We start a database transaction block for this specific batch
        try:
            for index, row in chunk.iterrows():
                phone_str = str(row['phone']).strip()
                email_str = str(row['email']).strip()

                # Deduplication Check: Look for an existing phone or email match
                existing_lead = db.query(Lead).filter(
                    (Lead.phone == phone_str) | (Lead.email == email_str)
                ).first()

                if existing_lead:
                    # Lead exists: Record the additional marketing source encounter
                    new_source = LeadSource(
                        lead_id=existing_lead.id,
                        source_name=row['source'],
                        submitted_at=current_time
                    )
                    db.add(new_source)
                    
                    # Update the last touch metric on the main profile
                    existing_lead.last_touch_source = row['source']
                    total_skipped += 1
                    continue

                # Brand New Lead Generation Sequence
                lead_id = str(uuid.uuid4())
                new_lead = Lead(
                    id=lead_id,
                    name=row['name'],
                    phone=phone_str,
                    email=email_str,
                    first_touch_source=row['source'],
                    last_touch_source=row['source'],
                    lead_type=row.get('lead_type', 'Paid'),
                    consent_timestamp=current_time,
                    consent_channel="Bulk Upload",
                    age_clock=current_time,
                    sla_clock=current_time
                )
                db.add(new_lead)

                # Track the original source entry link
                first_source = LeadSource(
                    lead_id=lead_id,
                    source_name=row['source'],
                    submitted_at=current_time
                )
                db.add(first_source)

                total_inserted += 1

            # Save the entire batch of 500 records to the database file in one go

            db.commit()

        except Exception as e:
            # If anything catastrophic happens, discard the current batch to prevent data corruption
            db.rollback()
            print(f"Error processing batch: {e}")
            raise e

    return {"inserted": total_inserted, "duplicates_merged": total_skipped}
