from database import engine, Base
import models

def create_tables():
    print("Initializing database generation sequence...")
    # This checks what models inherit from Base and creates them if they don't exist
    Base.metadata.create_all(bind=engine)
    print("Success! Your 'lms.db' file has been securely created.")

if __name__ == "__main__":
    create_tables()
