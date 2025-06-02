from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
import asyncio

from app.db import crud, models, schemas
from app.config import settings
from app.services.llm_service import get_llm

class TitleGenerationService:
    """
    Service for automatically generating and updating conversation titles.
    
    Features:
    1. Initial title from first message
    2. Regular title updates every 5 exchanges 
    3. Title updates on significant topic shifts
    4. Final title generation at conversation end
    """
    
    MESSAGE_THRESHOLD = 5  # Update title after this many new message pairs
    
    @staticmethod
    async def generate_initial_title(db: Session, conversation_id: str) -> str:
        """
        Generate the initial title based on the first user message.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            
        Returns:
            Generated title
        """
        # Get conversation
        conversation = crud.get_conversation(db, conversation_id)
        if not conversation:
            return "New Conversation"
        
        # Get messages
        messages = crud.get_conversation_messages(db, conversation_id)
        
        # If no messages, return default
        if not messages:
            return "New Conversation"
        
        # Get the first user message
        user_messages = [msg for msg in messages if msg.role == "user"]
        if not user_messages:
            return "New Conversation"
        
        first_message = user_messages[0]
        
        # Create prompt for generating title from first message
        prompt = """Generate a short, descriptive title (2-5 words) for a conversation that starts with this message.
Focus only on the main topic or intent. Be concise and specific.
Use the same language as the user's message.

Message: "{message}"

Title: """
        
        # Get LLM with thinking disabled for title generation
        llm = get_llm(db, override_thinking=False)
        
        # Generate title
        message = HumanMessage(content=prompt.format(message=first_message.content))
        response = llm.invoke([message])
        title = response.content.strip('"\'.,;:!?-').strip()
        
        # Capitalize first letter
        if title and len(title) > 0:
            title = title[0].upper() + title[1:]
        
        # Update conversation
        conversation.headline = title
        db.commit()
        
        return title
    
    @staticmethod
    async def update_title_periodic(db: Session, conversation_id: str) -> str:
        """
        Update the title after a certain number of message exchanges.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            
        Returns:
            Updated title
        """
        # Get conversation
        conversation = crud.get_conversation(db, conversation_id)
        if not conversation:
            return "Conversation Not Found"
        
        # Get all messages
        messages = crud.get_conversation_messages(db, conversation_id)
        
        # Skip if not enough messages
        if len(messages) < 4:  # Need at least 2 exchanges (4 messages)
            return conversation.headline or "New Conversation"
        
        # Get the most recent messages (up to last 5 exchanges = 10 messages)
        recent_messages = messages[-10:]
        
        # Create prompt for updating title based on recent messages
        prompt = """Generate a short, descriptive title (2-5 words) for a conversation containing these messages.
Focus on the main topic or intent. Be concise and specific.
Use the same language as the user's messages.

Messages:
{messages}

Title: """
        
        formatted_messages = ""
        for msg in recent_messages:
            role = "User" if msg.role == "user" else "Assistant"
            formatted_messages += f"{role}: {msg.content[:200]}...\n"
        
        # Get LLM with thinking disabled for title generation
        llm = get_llm(db, override_thinking=False)
        
        # Generate title
        message = HumanMessage(content=prompt.format(messages=formatted_messages))
        response = llm.invoke([message])
        title = response.content.strip('"\'.,;:!?-').strip()
        
        # Capitalize first letter
        if title and len(title) > 0:
            title = title[0].upper() + title[1:]
        
        # Update conversation
        conversation.headline = title
        db.commit()
        
        return title
    
    @staticmethod
    async def detect_topic_shift(db: Session, conversation_id: str, last_user_message: str) -> bool:
        """
        Detect if there's a significant shift in conversation topic.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            last_user_message: The latest user message to check for topic shift
            
        Returns:
            True if a topic shift is detected, False otherwise
        """
        # Get conversation
        conversation = crud.get_conversation(db, conversation_id)
        if not conversation or not conversation.headline:
            return False
        
        # Get previous title
        current_title = conversation.headline
        
        # Create prompt to detect topic shift
        prompt = """Determine if there's a significant topic shift between the current conversation title and the new message.
Current title: "{title}"
New message: "{message}"

Is there a significant shift in topic? Answer YES or NO only."""
        
        # Get LLM with thinking disabled for title generation
        llm = get_llm(db, override_thinking=False)
        
        # Check for topic shift
        message = HumanMessage(content=prompt.format(title=current_title, message=last_user_message))
        response = llm.invoke([message])
        result = response.content.strip().upper()
        
        return "YES" in result
    
    @staticmethod
    async def update_title_on_shift(db: Session, conversation_id: str) -> str:
        """
        Update the title when a topic shift is detected.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            
        Returns:
            Updated title
        """
        # Similar to update_title_periodic but with a prompt focused on the new topic
        # Get conversation
        conversation = crud.get_conversation(db, conversation_id)
        if not conversation:
            return "Conversation Not Found"
        
        # Get all messages
        messages = crud.get_conversation_messages(db, conversation_id)
        
        # Get the most recent messages (last 3 exchanges = 6 messages)
        recent_messages = messages[-6:]
        
        # Create prompt for generating title with focus on topic shift
        prompt = """Generate a short, descriptive title (2-5 words) for a conversation that has shifted to a new topic.
Focus on the most recent topic or intent. Be concise and specific.
Use the same language as the user's messages.

Previous title: "{previous_title}"

Recent messages:
{messages}

New title reflecting the current topic: """
        
        formatted_messages = ""
        for msg in recent_messages:
            role = "User" if msg.role == "user" else "Assistant"
            formatted_messages += f"{role}: {msg.content[:200]}...\n"
        
        # Get LLM with thinking disabled for title generation
        llm = get_llm(db, override_thinking=False)
        
        # Generate title
        message = HumanMessage(content=prompt.format(
            previous_title=conversation.headline,
            messages=formatted_messages
        ))
        response = llm.invoke([message])
        title = response.content.strip('"\'.,;:!?-').strip()
        
        # Capitalize first letter
        if title and len(title) > 0:
            title = title[0].upper() + title[1:]
        
        # Update conversation
        conversation.headline = title
        db.commit()
        
        return title
    
    @staticmethod
    async def generate_final_title(db: Session, conversation_id: str) -> str:
        """
        Generate a comprehensive final title when the conversation ends.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            
        Returns:
            Final title
        """
        # Get conversation
        conversation = crud.get_conversation(db, conversation_id)
        if not conversation:
            return "Conversation Not Found"
        
        # Get all messages
        messages = crud.get_conversation_messages(db, conversation_id)
        
        # Create prompt for generating final title
        prompt = """Generate a short, comprehensive title (2-5 words) that captures the entire conversation.
Focus on the most significant topic or purpose. Be concise but descriptive.
Use the same language as the user's messages.

Conversation length: {message_count} messages
First user message: "{first_message}"
Last user message: "{last_message}"
Current title: "{current_title}"

Final comprehensive title: """
        
        # Find first and last user messages
        user_messages = [msg for msg in messages if msg.role == "user"]
        if not user_messages:
            return conversation.headline or "New Conversation"
        
        first_user_msg = user_messages[0].content
        last_user_msg = user_messages[-1].content
        
        # Get LLM with thinking disabled for title generation
        llm = get_llm(db, override_thinking=False)
        
        # Generate title
        message = HumanMessage(content=prompt.format(
            message_count=len(messages),
            first_message=first_user_msg[:200],
            last_message=last_user_msg[:200],
            current_title=conversation.headline or "Untitled"
        ))
        response = llm.invoke([message])
        title = response.content.strip('"\'.,;:!?-').strip()
        
        # Capitalize first letter
        if title and len(title) > 0:
            title = title[0].upper() + title[1:]
        
        # Update conversation
        conversation.headline = title
        db.commit()
        
        return title
    
    @staticmethod
    async def process_new_message(db: Session, conversation_id: str, user_message: str) -> None:
        """
        Process a new user message and update the title if needed.
        This should be called whenever a new user message is added.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            user_message: Content of the user message
        """
        # Get conversation
        conversation = crud.get_conversation(db, conversation_id)
        if not conversation:
            return
        
        # Get message count
        messages = crud.get_conversation_messages(db, conversation_id)
        message_count = len(messages)
        
        # Case 1: First message - generate initial title
        if message_count == 1 or not conversation.headline:
            await TitleGenerationService.generate_initial_title(db, conversation_id)
            return
        
        # Case 2: Check for topic shift
        topic_shift = await TitleGenerationService.detect_topic_shift(db, conversation_id, user_message)
        if topic_shift:
            await TitleGenerationService.update_title_on_shift(db, conversation_id)
            return
        
        # Case 3: Regular update after threshold
        # Count message pairs (user + assistant exchanges)
        message_pairs = message_count // 2
        if message_pairs % TitleGenerationService.MESSAGE_THRESHOLD == 0:
            await TitleGenerationService.update_title_periodic(db, conversation_id)
            return 