# migration_add_new_columns.py
from app import app, db
from sqlalchemy import text

def migrate_new_columns():
    with app.app_context():
        try:
            print("Adding new columns to application table...")
            
            # List of new columns to add
            new_columns = [
                'documents_checklist TEXT DEFAULT "{}"',
                'checklist_completed BOOLEAN DEFAULT FALSE',
                'kyc_identity_report TEXT DEFAULT "{}"',
                'kyc_address_report TEXT DEFAULT "{}"',
                'kyc_financial_report TEXT DEFAULT "{}"',
                'risk_analysis_report TEXT DEFAULT "{}"',
                'existing_loan_analysis TEXT DEFAULT "{}"',
                'combined_application_report TEXT DEFAULT "{}"',
                'emi_schedule TEXT DEFAULT "{}"'
            ]
            
            for column_def in new_columns:
                column_name = column_def.split(' ')[0]
                
                # Check if column exists
                result = db.session.execute(text(f"PRAGMA table_info(application)"))
                existing_columns = [row[1] for row in result]
                
                if column_name not in existing_columns:
                    print(f"Adding column: {column_name}")
                    db.session.execute(text(f'ALTER TABLE application ADD COLUMN {column_def}'))
            
            db.session.commit()
            print("Migration completed successfully!")
            
        except Exception as e:
            print(f"Migration failed: {e}")
            db.session.rollback()

if __name__ == "__main__":
    migrate_new_columns()