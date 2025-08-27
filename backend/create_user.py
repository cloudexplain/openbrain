#!/usr/bin/env python3
"""
Utility script to create users for SecondBrain application.

Usage:
    python create_user.py --username <username> --password <password>
    python create_user.py --interactive

This script will hash the password and insert the user into the database.
"""

import argparse
import asyncio
import getpass
import sys
import os
from uuid import uuid4

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import SQLAlchemy components
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import select, Column, String, DateTime
from datetime import datetime

# Import password hashing function and models
from app.core.utils import get_password_hash
from app.models.user import User


async def create_user(username: str, password: str):
    """Create a new user with hashed password"""
    
    # Get database URL from environment or use default
    import pdb; pdb.set_trace()
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://secondbrain:secondbrain_password@localhost:5432/secondbrain"
    )
    
    print(f"Database URL: {database_url}")
    
    # Create database connection
    engine = create_async_engine(database_url)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    import pdb; pdb.set_trace()
    async with AsyncSessionLocal() as db:
        try:
            # Check if user already exists
            result = await db.execute(select(User).where(User.username == username))
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print(f"❌ User '{username}' already exists!")
                return False
            
            # Hash the password
            hashed_password = get_password_hash(password)
            
            # Create new user
            new_user = User(
                id=uuid4(),
                username=username,
                password_hash=hashed_password
            )
            
            db.add(new_user)
            await db.commit()
            
            print(f"✅ User '{username}' created successfully!")
            print(f"   User ID: {new_user.id}")
            print(f"   Created at: {new_user.created_at}")
            return True
            
        except Exception as e:
            await db.rollback()
            print(f"❌ Failed to create user: {str(e)}")
            return False
        finally:
            await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Create a new user for SecondBrain")
    parser.add_argument("--username", help="Username for the new user")
    parser.add_argument("--password", help="Password for the new user")
    parser.add_argument("--interactive", "-i", action="store_true", 
                       help="Interactive mode - prompt for username and password")
    
    args = parser.parse_args()
    
    if args.interactive:
        # Interactive mode
        print("=== SecondBrain User Creation ===")
        print()
        username = input("Enter username: ").strip()
        if not username:
            print("❌ Username cannot be empty!")
            sys.exit(1)
        
        password = getpass.getpass("Enter password: ")
        confirm_password = getpass.getpass("Confirm password: ")
        
        if password != confirm_password:
            print("❌ Passwords don't match!")
            sys.exit(1)
        
        if len(password) < 6:
            print("❌ Password must be at least 6 characters long!")
            sys.exit(1)
            
    elif args.username and args.password:
        # Command line mode
        username = args.username
        password = args.password
        
    else:
        print("❌ Please provide either --username and --password, or use --interactive mode")
        parser.print_help()
        sys.exit(1)
    
    # Validate inputs
    if not username or not password:
        print("❌ Username and password cannot be empty!")
        sys.exit(1)
    
    # Create the user
    print(f"\nCreating user '{username}'...")
    success = asyncio.run(create_user(username, password))
    
    if success:
        print(f"\n🎉 User '{username}' is ready to use SecondBrain!")
        print("   They can now login at /login")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
