import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from db.database import engine
from db import models
from config import settings

def update_model_name():
    """
    Update LLM model name in all configurations to match settings
    """
    # Get a database session
    db = Session(engine)
    
    try:
        # Get all LLM configs
        configs = db.query(models.LLMConfig).all()
        
        if not configs:
            print("No LLM configurations found in the database.")
            return False
        
        # Current model name from settings
        current_model = settings.LLM_MODEL
        
        # Update all configs
        updated_count = 0
        for config in configs:
            # Check if model name is different from settings
            if config.model_name != current_model:
                old_name = config.model_name
                config.model_name = current_model
                updated_count += 1
                print(f"Updated config '{config.name}': {old_name} → {current_model}")
        
        # Commit changes if any updates were made
        if updated_count > 0:
            db.commit()
            print(f"Updated {updated_count} configuration(s) with model name: {current_model}")
        else:
            print("All configurations already have the correct model name.")
        
        return True
    except Exception as e:
        print(f"Error updating model names: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = update_model_name()
    
    if not success:
        sys.exit(1) 