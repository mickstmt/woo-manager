from app import create_app, db
from sqlalchemy import text
import sys

app = create_app()

with app.app_context():
    try:
        # Read the SQL file
        with open(r'd:\Projects\python\flask\woocommerce-manager\sql_scripts\add_avatar_column_users.sql', 'r') as f:
            sql_statements = f.read().split(';')
            
        for statement in sql_statements:
            if statement.strip():
                print(f"Executing: {statement.strip()}")
                db.session.execute(text(statement))
        
        db.session.commit()
        print("Migration successful: avatar_file column added.")
    except Exception as e:
        print(f"Error during migration: {e}")
        # If column already exists (Error 1060), we can ignore it
        if "Duplicate column name" in str(e):
             print("Column already exists. Continuing.")
        else:
             db.session.rollback()
