#!/usr/bin/env python3
"""
Test script to verify the circular dependency fix for conversation deletion.

This test validates that conversations with display_file_id references 
can be deleted without encountering circular dependency errors.
"""
import sys
import os
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.db import crud, models
from app.db.models import ConversationType

def test_circular_dependency_fix():
    """Test that conversations with circular file references can be deleted."""
    
    print("=" * 60)
    print("CIRCULAR DEPENDENCY FIX VALIDATION TEST")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Create a test user first
        print("\n1. Creating test user...")
        test_user = models.User(
            username="testuser_circular", 
            email="test_circular@example.com", 
            hashed_password="test"
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        print(f"   ✓ Created test user with ID: {test_user.id}")
        
        # Create a test conversation
        print("\n2. Creating test conversation...")
        test_conversation = crud.create_conversation(db, test_user.id)
        conversation_id = test_conversation.id
        print(f"   ✓ Created conversation: {conversation_id}")
        
        # Create a test file storage record
        print("\n3. Creating test file storage...")
        test_file = models.FileStorage(
            user_id=test_user.id,
            conversation_id=conversation_id,
            filename="test_file.txt",
            original_filename="test_file.txt",
            file_path=f"{test_user.id}/{conversation_id}/test_file.txt",
            file_size=1024,  # Required field
            mime_type="text/plain",  # Required field  
            file_metadata={"test": True}
        )
        db.add(test_file)
        db.commit()
        db.refresh(test_file)
        print(f"   ✓ Created file with ID: {test_file.id}")
        
        # Create circular dependency by setting display_file_id
        print("\n4. Creating circular dependency...")
        test_conversation.display_file_id = test_file.id
        db.commit()
        print(f"   ✓ Set display_file_id = {test_file.id} on conversation")
        print(f"   ✓ Circular reference: Conversation -> File -> Conversation")
        
        # Verify the circular dependency exists
        db.refresh(test_conversation)
        print(f"\n5. Verifying circular dependency...")
        print(f"   - Conversation.display_file_id: {test_conversation.display_file_id}")
        print(f"   - File.conversation_id: {test_file.conversation_id}")
        print(f"   - Circular reference confirmed: {test_conversation.display_file_id == test_file.id}")
        
        # Test deletion with the fixed function
        print(f"\n6. Testing conversation deletion...")
        success = crud.delete_conversation(db, conversation_id)
        
        if success:
            print("   ✓ SUCCESS: Conversation deleted successfully!")
            
            # Verify complete deletion
            conversation_check = crud.get_conversation(db, conversation_id)
            file_check = db.query(models.FileStorage).filter(models.FileStorage.id == test_file.id).first()
            
            if conversation_check is None and file_check is None:
                print("   ✓ VERIFIED: Both conversation and file completely removed")
                print("\n🎉 CIRCULAR DEPENDENCY FIX IS WORKING CORRECTLY!")
                return True
            else:
                print("   ❌ ERROR: Some records still exist after deletion")
                return False
        else:
            print("   ❌ FAILED: Conversation deletion returned False")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR during test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup: try to delete test user if it still exists
        try:
            test_user_check = db.query(models.User).filter(models.User.username == "testuser_circular").first()
            if test_user_check:
                db.delete(test_user_check)
                db.commit()
                print(f"\n🧹 Cleaned up test user")
        except:
            pass
        
        db.close()

def test_normal_conversation_deletion():
    """Test that normal conversations without circular references still work."""
    
    print("\n" + "=" * 60)
    print("NORMAL CONVERSATION DELETION TEST")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Create a test user
        print("\n1. Creating test user...")
        test_user = models.User(
            username="testuser_normal", 
            email="test_normal@example.com", 
            hashed_password="test"
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        print(f"   ✓ Created test user with ID: {test_user.id}")
        
        # Create a normal conversation (no files, no circular refs)
        print("\n2. Creating normal conversation...")
        test_conversation = crud.create_conversation(db, test_user.id)
        conversation_id = test_conversation.id
        print(f"   ✓ Created conversation: {conversation_id}")
        
        # Add some messages
        print("\n3. Adding test messages...")
        from app.db import schemas
        
        message1 = crud.create_message(db, schemas.MessageCreate(
            conversation_id=conversation_id,
            role="user",
            content="Hello"
        ))
        
        message2 = crud.create_message(db, schemas.MessageCreate(
            conversation_id=conversation_id,
            role="assistant", 
            content="Hi there!"
        ))
        
        print(f"   ✓ Added 2 test messages")
        
        # Test deletion
        print(f"\n4. Testing normal conversation deletion...")
        success = crud.delete_conversation(db, conversation_id)
        
        if success:
            print("   ✓ SUCCESS: Normal conversation deleted successfully!")
            
            # Verify deletion
            conversation_check = crud.get_conversation(db, conversation_id)
            if conversation_check is None:
                print("   ✓ VERIFIED: Conversation completely removed")
                print("\n🎉 NORMAL DELETION STILL WORKS CORRECTLY!")
                return True
            else:
                print("   ❌ ERROR: Conversation still exists after deletion")
                return False
        else:
            print("   ❌ FAILED: Normal conversation deletion returned False")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR during normal test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        try:
            test_user_check = db.query(models.User).filter(models.User.username == "testuser_normal").first()
            if test_user_check:
                db.delete(test_user_check)
                db.commit()
                print(f"\n🧹 Cleaned up normal test user")
        except:
            pass
            
        db.close()

if __name__ == "__main__":
    print("Starting circular dependency fix validation tests...")
    
    # Test circular dependency fix
    circular_test_passed = test_circular_dependency_fix()
    
    # Test normal deletion still works
    normal_test_passed = test_normal_conversation_deletion()
    
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Circular dependency fix test: {'✅ PASSED' if circular_test_passed else '❌ FAILED'}")
    print(f"Normal conversation deletion test: {'✅ PASSED' if normal_test_passed else '❌ FAILED'}")
    
    if circular_test_passed and normal_test_passed:
        print("\n🎉 ALL TESTS PASSED! The circular dependency fix is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        sys.exit(1)
