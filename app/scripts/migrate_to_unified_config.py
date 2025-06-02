#!/usr/bin/env python3
"""
Migration Script for Unified Configuration

This script migrates data from the llm_configs table to the unified admin_config table.
Run this script after applying the alembic migration that adds the new columns to admin_config.
"""

import sys
import os
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.models.admin_config import AdminConfig

def migrate_llm_configs():
    """Migrate data from llm_configs to admin_config"""
    
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Get all LLM configs
        llm_configs = db.execute(text("SELECT * FROM llm_configs")).fetchall()
        
        print(f"Found {len(llm_configs)} LLM configurations to migrate")
        
        for config in llm_configs:
            # Extract data
            model_name = config.model_name
            temperature = config.temperature
            top_p = config.top_p
            max_tokens = config.max_tokens
            description = config.description or "Migrated from llm_configs"
            extra_params = config.extra_params
            
            # Create entries in admin_config
            db.execute(
                text("""
                INSERT INTO admin_config (key, value, value_type, description, category) 
                VALUES (:key, :value, :value_type, :description, :category)
                ON CONFLICT (key) DO UPDATE SET 
                    value = EXCLUDED.value, 
                    value_type = EXCLUDED.value_type,
                    description = EXCLUDED.description,
                    category = EXCLUDED.category
                """),
                {
                    "key": AdminConfig.KEY_LLM_MODEL,
                    "value": model_name,
                    "value_type": "string",
                    "description": f"LLM model name: {description}",
                    "category": "llm"
                }
            )
            
            db.execute(
                text("""
                INSERT INTO admin_config (key, value, value_type, description, category) 
                VALUES (:key, :value, :value_type, :description, :category)
                ON CONFLICT (key) DO UPDATE SET 
                    value = EXCLUDED.value, 
                    value_type = EXCLUDED.value_type,
                    description = EXCLUDED.description,
                    category = EXCLUDED.category
                """),
                {
                    "key": AdminConfig.KEY_LLM_TEMPERATURE,
                    "value": str(temperature),
                    "value_type": "float",
                    "description": "LLM temperature parameter",
                    "category": "llm"
                }
            )
            
            db.execute(
                text("""
                INSERT INTO admin_config (key, value, value_type, description, category) 
                VALUES (:key, :value, :value_type, :description, :category)
                ON CONFLICT (key) DO UPDATE SET 
                    value = EXCLUDED.value, 
                    value_type = EXCLUDED.value_type,
                    description = EXCLUDED.description,
                    category = EXCLUDED.category
                """),
                {
                    "key": AdminConfig.KEY_LLM_TOP_P,
                    "value": str(top_p),
                    "value_type": "float",
                    "description": "LLM top_p parameter",
                    "category": "llm"
                }
            )
            
            db.execute(
                text("""
                INSERT INTO admin_config (key, value, value_type, description, category) 
                VALUES (:key, :value, :value_type, :description, :category)
                ON CONFLICT (key) DO UPDATE SET 
                    value = EXCLUDED.value, 
                    value_type = EXCLUDED.value_type,
                    description = EXCLUDED.description,
                    category = EXCLUDED.category
                """),
                {
                    "key": AdminConfig.KEY_LLM_MAX_TOKENS,
                    "value": str(max_tokens),
                    "value_type": "int",
                    "description": "LLM max tokens parameter",
                    "category": "llm"
                }
            )
            
            # Handle extra params if present
            if extra_params:
                db.execute(
                    text("""
                    INSERT INTO admin_config (key, value, value_type, description, category) 
                    VALUES (:key, :value, :value_type, :description, :category)
                    ON CONFLICT (key) DO UPDATE SET 
                        value = EXCLUDED.value, 
                        value_type = EXCLUDED.value_type,
                        description = EXCLUDED.description,
                        category = EXCLUDED.category
                    """),
                    {
                        "key": "llm_extra_params",
                        "value": json.dumps(extra_params),
                        "value_type": "json",
                        "description": "Additional LLM parameters",
                        "category": "llm"
                    }
                )
            
            print(f"Migrated configuration for model: {model_name}")
        
        db.commit()
        print("Migration completed successfully")
        
    except Exception as e:
        db.rollback()
        print(f"Error during migration: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting migration to unified configuration...")
    migrate_llm_configs()
    print("Migration completed.") 