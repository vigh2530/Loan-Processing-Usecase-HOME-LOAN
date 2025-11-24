# create_admin.py

import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Admin

def create_admin_user():
    """Create a default admin user if none exists"""
    try:
        with app.app_context():
            # Check if any admin users exist
            admin_count = Admin.query.count()
            
            if admin_count == 0:
                # Create default admin user
                default_admin = Admin(
                    username='admin',
                    email='admin@casafinance.com'
                )
                default_admin.set_password('admin123')  # Default password
                
                db.session.add(default_admin)
                db.session.commit()
                print("✅ Default admin user created!")
                print("   Username: admin")
                print("   Password: admin123")
            else:
                print(f"✅ {admin_count} admin user(s) already exist in database")
                
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
if __name__ == '__main__':
    create_admin_user()