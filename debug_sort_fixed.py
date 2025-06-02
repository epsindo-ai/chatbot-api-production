#!/usr/bin/env python3
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
import os
import sys

# Add the app directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db import models, crud
from app.config import settings

# Create database connection
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def print_conversations():
    print("Fetching conversations with FIXED sorting (nullslast)...")
    conversations = db.query(models.Conversation).order_by(
        models.Conversation.updated_at.desc().nullslast(), 
        models.Conversation.created_at.desc()
    ).limit(10).all()
    
    print(f"Found {len(conversations)} conversations")
    print("ID | Created At | Updated At")
    print("-" * 60)
    
    for c in conversations:
        print(f"{c.id} | {c.created_at} | {c.updated_at}")

if __name__ == "__main__":
    print_conversations()
    db.close() 