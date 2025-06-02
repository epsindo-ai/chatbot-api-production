from typing import List
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langchain_core.chat_history import BaseChatMessageHistory

class CustomMessageHistory(BaseChatMessageHistory):
    """ChatMessageHistory backed by our PostgreSQL database."""

    def __init__(self, session_id: str, db=None):
        """Initialize with session id and database session.
        
        Args:
            session_id: Conversation ID to use for message lookup
            db: Database session to use
        """
        self.session_id = session_id
        self.db = db
    
    @property
    def messages(self) -> List[BaseMessage]:
        """Retrieve messages from the database."""
        if not self.db:
            print("WARNING: No database session provided to CustomMessageHistory")
            return []
        
        from app.db import crud
        
        # Get messages from db
        db_messages = crud.get_conversation_messages(self.db, self.session_id)
        
        # Convert to langchain message format
        result = []
        for msg in db_messages:
            if msg.role == "user":
                result.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                result.append(AIMessage(content=msg.content))
                
        return result
    
    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the store.
        
        Args:
            message: Message to add
        """
        if not self.db:
            print("WARNING: No database session provided to CustomMessageHistory")
            return
        
        from app.db import crud, schemas
        
        if isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant" 
        else:
            role = "system"
        
        # Create message in db
        message_create = schemas.MessageCreate(
            conversation_id=self.session_id,
            role=role,
            content=message.content
        )
        crud.create_message(self.db, message_create)
    
    def clear(self) -> None:
        """Clear session memory from the store."""
        # We don't allow clearing messages from the database
        pass 