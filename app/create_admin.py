#!/usr/bin/env python3
"""
Script to create initial admin user for the inventory management system
"""

import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app'))

from core.database import get_db
from database.models.user import User
from core.security import security
from sqlalchemy.orm import Session

def create_admin_user():
    """Create initial admin user"""

    # Get database session
    db_session = next(get_db())

    try:
        # Check if admin user already exists
        existing_admin = db_session.query(User).filter(User.benutzername == 'admin').first()
        if existing_admin:
            print("Admin user already exists!")
            return

        # Create admin user
        admin_user = User(
            benutzername='admin',
            email='admin@company.com',
            passwort_hash=security.hash_password('admin123'),  # Default password
            vorname='Admin',
            nachname='User',
            rolle='admin',
            ist_aktiv=True,
            telefon='+49 123 456789',
            abteilung='IT',
            notizen='Initial admin user'
        )

        db_session.add(admin_user)
        db_session.commit()

        print("✅ Admin user created successfully!")
        print("Username: admin")
        print("Password: admin123")
        print("Email: admin@company.com")
        print("\n⚠️  Please change the default password after first login!")

    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db_session.rollback()
    finally:
        db_session.close()

def create_sample_users():
    """Create some sample users for testing"""

    db_session = next(get_db())

    sample_users = [
        {
            'benutzername': 'netzwerker1',
            'email': 'netzwerker@company.com',
            'passwort': 'netzwerk123',
            'vorname': 'Max',
            'nachname': 'Mustermann',
            'rolle': 'netzwerker',
            'telefon': '+49 123 456790',
            'abteilung': 'Netzwerk'
        },
        {
            'benutzername': 'azubi1',
            'email': 'azubi@company.com',
            'passwort': 'azubi123',
            'vorname': 'Lisa',
            'nachname': 'Müller',
            'rolle': 'auszubildende',
            'telefon': '+49 123 456791',
            'abteilung': 'IT'
        }
    ]

    try:
        for user_data in sample_users:
            # Check if user already exists
            existing_user = db_session.query(User).filter(User.benutzername == user_data['benutzername']).first()
            if existing_user:
                print(f"User {user_data['benutzername']} already exists, skipping...")
                continue

            user = User(
                benutzername=user_data['benutzername'],
                email=user_data['email'],
                passwort_hash=security.hash_password(user_data['passwort']),
                vorname=user_data['vorname'],
                nachname=user_data['nachname'],
                rolle=user_data['rolle'],
                ist_aktiv=True,
                telefon=user_data['telefon'],
                abteilung=user_data['abteilung'],
                notizen='Sample user for testing'
            )

            db_session.add(user)
            print(f"✅ Created user: {user_data['benutzername']} (password: {user_data['passwort']})")

        db_session.commit()
        print("\n🎉 Sample users created successfully!")

    except Exception as e:
        print(f"❌ Error creating sample users: {e}")
        db_session.rollback()
    finally:
        db_session.close()

if __name__ == "__main__":
    print("🚀 Creating initial users for Inventory Management System...")
    print("=" * 60)

    # Create admin user
    create_admin_user()
    print()

    # Ask if user wants to create sample users
    if len(sys.argv) > 1 and sys.argv[1] == '--with-samples':
        create_sample_users()
    else:
        print("💡 To create sample users, run: python create_admin.py --with-samples")