import streamlit as st
import pandas as pd

import sys
import os

# Append parent directory to path for backend discovery

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import SessionLocal,engine,Base
from backend.models import Lead,ActivityLog
from backend.importer import process_bulk_csv
from backend.queries import get_all_leads_flat,update_lead_stage,single_lead_input # Import our new query function
from backend.router import assign_leads_round_robin

import backend.models # Crucial: This forces Python to read your model blueprints!


# Configure main app page layout
st.set_page_config(page_title="LMS Core Portal", layout="wide") # 'wide' layout is perfect for data tables!

# 2. TRIGGER THE AUTOMATIC TABLE GENERATION LOGIC HERE
Base.metadata.create_all(bind=engine)

# 1. Sidebar Navigation Menu
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["📋 Leads Dashboard", "📥 Bulk Data Import"])

# -------------------------------------------------------------------------
# PAGE 1: LEADS DASHBOARD
# -------------------------------------------------------------------------
if page == "📋 Leads Dashboard":
    st.title("📋 Lead Management System Dashboard")
    st.subheader("Live Operational Database View")

    

    # Spin up an isolated read session
    db_session = SessionLocal()
    try:
        # Fetch data matrix from backend
        data = get_all_leads_flat(db_session)

        
        if not data:
            st.info("The system database is currently empty. Head over to the 'Bulk Data Import' tab to ingest data files.")
        else:
            # Convert list of dictionaries cleanly into a Pandas DataFrame for UI rendering
            df = pd.DataFrame(data)
            
            # Display summary metrics tags at the top
            col1, col2 = st.columns(2)
            col1.metric("Total Ingested Leads", len(df))
            col2.metric("Active Marketing Channels", len(df["Source"].unique()))
            
            st.write("---")
            
            # Render the data table with sorting and filtering capability natively built-in
            st.dataframe(df, use_container_width=True, hide_index=True)
            
    except Exception as e:
        st.error(f"Failed to read data from local storage engine: {e}")
    finally:
        db_session.close()

st.title("📋 Lead Management System Dashboard")

# 1. Simulate an enterprise active user session context switcher
current_user = st.sidebar.selectbox(
    "👤 Active Session Profile:",
    ["AGENT_ALPHA", "AGENT_BETA", "AGENT_GAMMA", "SYSTEM_ADMIN"]
)
st.caption(f"Active Session Context: **{current_user}**")

# Add a dedicated action button for your backend logic
if st.button("🔄 Run Assignment Engine"):
    # Right below your "Run Assignment Engine" button block in frontend/app.py


    st.write("---")

    # 1. Create a collapsible drop-down panel for clean workspace management
    with st.expander("➕ Manually Add Single Lead Profile"):
        st.markdown("### Customer Discovery Profile Ingestion")
    
        # Create two layout columns for the input boxes
        form_col1, form_col2 = st.columns(2)
    

        with form_col1:

            new_name = st.text_input("Customer Full Name", placeholder="e.g. Siddharth Menon")
            new_phone = st.text_input("Primary Contact Phone Number", placeholder="e.g. 9446012345")
            new_email = st.text_input("Secure Email Address", placeholder="e.g. sid@example.com")
        

        with form_col2:

            # Let users select the marketing context channel
            new_source = st.selectbox("Marketing Traffic Source Channel", ["Meta Ads", "Website Form", "Cold Outbound", "Direct Referral", "WhatsApp Channel"])
        
            # Let users define the lead classification type

            new_lead_type = st.selectbox("Lead Priority / Track Classification", ["Standard", "Premium", "Self-Sourced"])
    
        # 2. The Execution Trigger Button
        if st.button("🚀 Register and Route Profile"):
            # Basic validation guard: Don't let them hit the backend with empty core values
            if not new_name or not new_phone or not new_email:
                st.warning("⚠️ Data validation failure: Name, Phone, and Email fields are strictly required.")
            else:
                # Instantiate an on-demand private database connection transaction session
                form_db = SessionLocal()
                try:
                    # 3. Call your customized backend verification logic!
                    result = single_lead_input(
                        db=form_db,
                        name=new_name,
                        phone=new_phone,
                        email=new_email,
                        source=new_source,
                        lead_type=new_lead_type,
                        current_user=current_user # Passes the active profile running the browser session
                    )

                
                    # 4. Handle and evaluate responses mapped from your state-machine logic rules
                    if result == "SUCCESS":
                        st.success(f"🎉 Lead successfully captured! Registered under the baseline track queue.")
                        st.rerun()
                    
                    elif result == "REASSIGNED_TO_YOU":
                        st.info(f"⚡ SLA Breach Guard Triggered: This lead was neglected by its previous owner. Ownership has been securely transferred directly to your account profile.")
                        st.rerun()
                    
                    elif result == "ACTIVE_WITH_OTHER_AGENT":
                        st.error(f"❌ Hijack Attempt Blocked: This customer profile is already actively engaged in transactions with another sales agent. Current assignment stands firm.")
                    
                except Exception as e:
                    st.error(f"System application exception occurred: {e}")
                finally:
                    form_db.close()


    db_session = SessionLocal()
    try:
        # Call your backend routing function on demand
        assigned_count = assign_leads_round_robin(db_session,current_session_agent=current_user)
        
        if assigned_count > 0:
            st.success(f"Success! {assigned_count} unassigned leads have been routed to active agents.")
            st.rerun() # Refreshes the dashboard grid view to show the new assignments live!
        else:
            st.info("All leads are currently fully assigned. No routing required.")
    except Exception as e:
        st.error(f"Routing execution engine failure: {e}")
    finally:
        db_session.close()


# -------------------------------------------------------------------------
# PAGE 2: BULK DATA IMPORT (Your previous code, wrapped in an if-statement)
# -------------------------------------------------------------------------
elif page == "📥 Bulk Data Import":

    st.title("📥 Ingestion Engine Portal")
    st.subheader("Bulk Data File Parser")

    st.write("Upload a standardized marketing campaign file (.csv) to batch-populate your database queue.")


    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])


    if uploaded_file is not None:
        st.success("File uploaded successfully into local memory buffer!")
        try:
            preview_df = pd.read_csv(uploaded_file)
            st.write("### Data Preview (First 5 Rows)", preview_df.head())
            
            required_headers = ['name', 'phone', 'email', 'source']
            missing_headers = [h for h in required_headers if h not in preview_df.columns]
            

            if missing_headers:
                st.error(f"Import halted! Missing required column headers: {missing_headers}")

            else:
                if st.button("🚀 Execute Safe Batch Import"):
                    uploaded_file.seek(0)
                    temp_filename = "temp_bulk_import.csv"
                    with open(temp_filename, "wb") as f:

                        f.write(uploaded_file.getbuffer())
                    
                    st.info("Batch processing transaction sequence initialized...")
                    db_session = SessionLocal()
                    try:
                        results = process_bulk_csv(temp_filename, db_session, chunk_size=500)

                        st.success(f"### Import Complete! \n"
                                   f"* **New Profiles Created:** {results['inserted']} \n"
                                   f"* **Duplicate Matches Merged:** {results['duplicates_merged']}")
                    except Exception as error:
                        st.error(f"A structural processing error occurred: {error}")
                    finally:
                        db_session.close()
                        if os.path.exists(temp_filename):
                            os.remove(temp_filename)
                            
        except Exception as parse_error:
            st.error(f"Could not read file layout format: {parse_error}")


# --- NEW SECTION: INTERACTIVE PIPELINE MANAGER GRID ---
st.write("---")
st.subheader("Active Operational Roster Queue")

db_session = SessionLocal()
try:
    # Fetch all leads currently locked in storage
    # Make sure 'get_all_leads_flat' or a standard query is used to grab your leads array
    leads_list = db_session.query(Lead).all()
    
    if not leads_list:
        st.info("No lead data available in the current partition.")
    else:
        # Loop through each record to generate an interactive control card row
        for lead in leads_list:
            # Container border boxes separate each client record visually
            with st.container(border=True):
                # Split the container row into 3 distinct functional columns layout
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.markdown(f"### **{lead.name}**")
                    st.text(f"📞 {lead.phone} | ✉️ {lead.email}")
                    st.caption(f"Current Stage: :blue[{lead.pipeline_stage}] | Handler: **{lead.assigned_agent_id}**")
                    
                with col2:
                    # 1. DEFINE THE VALID PIPELINE DICTIONARY TO FILTER THE UI DYNAMICALLY
                    ALLOWED_TRANSITIONS = {
                    "Discovered": ["Assigned"],
                    "Assigned": ["Contacted"],
                    "Contacted": ["In Negotiation", "Won", "Lost"],
                    "In Negotiation": ["Won", "Lost"],
                    "Won": [],
                    "Lost": ["Assigned"]
                    }
            
                     # Fetch the current stage of the lead
                    current_stage = lead.pipeline_stage if lead.pipeline_stage in ALLOWED_TRANSITIONS else "Discovered"
            
                    # Smart UI Filter: The dropdown options will ALWAYS include the current stage,
                    # plus only the valid next stages allowed by your state machine rules!
                    ui_options = [current_stage] + ALLOWED_TRANSITIONS[current_stage]
            
                    selected_stage = st.selectbox(
                        f"Advance Pipeline Step",
                        options=ui_options,
                        index=0, # Default to the current stage
                        key=f"stage_select_{lead.id}"
                    )
                    
                with col3:
                    st.write("") # Quick spacing layout padding offset
                    st.write("") 
                    # If the chosen dropdown stage does not match what's currently in the database, show an update action button
                    # Only render the button if the user has selected a modification
                    if selected_stage != lead.pipeline_stage:
                        if st.button("💾 Apply Change", key=f"btn_save_{lead.id}"):
                            try:
                                from backend.queries import update_lead_stage
                        
                                 # Execute the backend validation transition
                                success = update_lead_stage(db_session, lead_id=lead.id, new_stage=selected_stage, current_user=current_user)
                        
                                if success:
                                     st.success("Transition Captured!")
                                     st.rerun()
                            
                            except ValueError as ve:
                                 # 2. CAPTURE THE BACKEND STATE MACHINE ERROR AND RENDER A CLEAN WARNING BOX
                                 st.error(f"⚠️ Rule Violation: {ve}")
finally:
    db_session.close()
