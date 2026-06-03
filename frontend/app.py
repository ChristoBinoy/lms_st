import streamlit as st
import pandas as pd
import sys
import os

# Append the parent directory to the path so Streamlit can discover the backend folder modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import SessionLocal

from backend.importer import process_bulk_csv

# Configure the main application layout
st.set_page_config(page_title="LMS Core Portal", layout="centered")


st.title("📥 Lead Management System")
st.subheader("Bulk Data Import Engine")
st.write("Upload a standardized marketing campaign file (.csv) to batch-populate your ingestion queue.")

# 1. Render the native file uploader component
uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])

if uploaded_file is not None:
    st.success("File uploaded successfully into local memory buffer!")

    
    # Preview the file data matrix to the user before running the import engine
    try:
        preview_df = pd.read_csv(uploaded_file)
        st.write("### Data Preview (First 5 Rows)", preview_df.head())
        
        # Verify that the file has our strictly required headers
        required_headers = ['name', 'phone', 'email', 'source']
        missing_headers = [h for h in required_headers if h not in preview_df.columns]
        
        if missing_headers:
            st.error(f"Import halted! Missing required column headers: {missing_headers}")
        else:
            # 2. Add an explicit execution button to prevent accidental clicks
            if st.button("🚀 Execute Safe Batch Import"):
                
                # Reset file pointer back to the beginning after reading it for the preview
                uploaded_file.seek(0)

                
                # Save the uploaded buffer file temporarily to disk so our batch engine can stream it
                temp_filename = "temp_bulk_import.csv"
                with open(temp_filename, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                st.info("Batch processing transaction sequence initialized...")
                
                # 3. Spin up an isolated transactional database session
                db_session = SessionLocal()
                
                try:
                    # Execute your high-performance batch processing function
                    results = process_bulk_csv(temp_filename, db_session, chunk_size=500)
                    
                    # Display real-world performance metrics directly on the dashboard
                    st.balloons()
                    st.success(f"### Import Complete! \n"
                               f"* **New Profiles Created:** {results['inserted']} \n"
                               f"* **Duplicate Matches Merged into Activity Logs:** {results['duplicates_merged']}")
                    
                except Exception as error:
                    st.error(f"A structural processing error occurred during runtime: {error}")
                
                finally:
                    # Always clean up system resources and close connection pools
                    db_session.close()
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)

                        
    except Exception as parse_error:
        st.error(f"Could not read file layout format: {parse_error}")
