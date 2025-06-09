import uuid
from typing import Dict, List, Optional, Generator
from sqlalchemy.orm import Session
import asyncio

from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain_openai import ChatOpenAI
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.callbacks.base import BaseCallbackHandler

from app.config import settings
from app.db import crud, models, schemas
from app.services.rag_config_service import RAGConfigService
from app.utils.title_utils import clean_title

# Store conversation memory
conversations: Dict[str, ConversationBufferMemory] = {}

# Store persistent user information
user_info: Dict[int, Dict[str, str]] = {}

class StreamingCallbackHandler(BaseCallbackHandler):
    """Custom callback handler for streaming LLM responses."""
    
    def __init__(self):
        self.tokens = []
        self.full_response = ""
        self.conversation_id = None
        
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Called when the LLM produces a new token."""
        self.tokens.append(token)
        self.full_response += token
        
    def on_llm_end(self, response, **kwargs) -> None:
        """Called when LLM ends generating."""
        pass
        
    def on_llm_error(self, error, **kwargs) -> None:
        """Called when LLM errors."""
        pass
    
    def get_full_response(self) -> str:
        """Get the complete response as a string."""
        return self.full_response

def get_llm(db: Session, streaming: bool = False, override_thinking: Optional[bool] = None):
    """
    Initialize and return the LLM model using configuration from the database
    
    Args:
        db: Database session
        streaming: Whether to enable streaming mode
        override_thinking: Override the enable_thinking setting from config (useful for specific use cases)
        
    Returns:
        Configured LLM instance
    """
    # Get the LLM config from the database (there's only one)
    config = crud.get_active_llm_config(db)
    
    # If no config exists, create a default one
    if not config:
        config = crud.create_default_llm_config(db)
    
    print(f"DEBUG: Using LLM config: model={config.model_name}, temp={config.temperature}, top_p={config.top_p}")
    
    # Create model params from config
    model_params = {
        "model_name": config.model_name,
        "temperature": config.temperature,
        "top_p": config.top_p,
    }
    
    # Add max_tokens if set
    if config.max_tokens:
        model_params["max_tokens"] = config.max_tokens
    
    # Handle enable_thinking parameter
    enable_thinking = override_thinking if override_thinking is not None else getattr(config, 'enable_thinking', False)
    
    # Add extra parameters from the config (like base_url and api_key)
    if config.extra_params:
        # If base_url is in extra_params, use it
        if "base_url" in config.extra_params:
            model_params["base_url"] = config.extra_params["base_url"]
        
        # If api_key is in extra_params, use it
        if "api_key" in config.extra_params:
            model_params["api_key"] = config.extra_params["api_key"]
        
        # Add any other extra parameters
        for key, value in config.extra_params.items():
            if key not in ["base_url", "api_key"]:
                model_params[key] = value
    
    # If no API key is provided, use the one from settings
    if "api_key" not in model_params:
        model_params["api_key"] = settings.OPENAI_API_KEY
    
    # If no base_url is provided, use the one from settings
    if "base_url" not in model_params:
        model_params["base_url"] = settings.OPENAI_API_BASE
    
    # Add thinking configuration to extra_body
    if "extra_body" not in model_params:
        model_params["extra_body"] = {}
    
    # Set chat_template_kwargs with enable_thinking
    if "chat_template_kwargs" not in model_params["extra_body"]:
        model_params["extra_body"]["chat_template_kwargs"] = {}
    
    model_params["extra_body"]["chat_template_kwargs"]["enable_thinking"] = enable_thinking
    
    # If streaming is enabled, add the streaming parameter and callback
    if streaming:
        model_params["streaming"] = True
        # Don't set callback handler here, we'll pass it separately
    
    # Initialize the model
    return ChatOpenAI(**model_params)

def extract_user_info(messages: List[models.Message]) -> Dict[str, str]:
    """
    Extract user information (like name, preferences) from conversation messages
    
    Args:
        messages: List of conversation messages
        
    Returns:
        Dictionary of extracted user information
    """
    info = {}
    
    # Look for patterns that might indicate user information
    name_patterns = [
        r"(?:my name is|i am|i'm|call me) ([A-Z][a-z]+)",
        r"(?:this is) ([A-Z][a-z]+)(?: speaking)?",
    ]
    
    for msg in messages:
        if msg.role == "user":
            # Extract potential name mentions
            for pattern in name_patterns:
                import re
                matches = re.findall(pattern, msg.content, re.IGNORECASE)
                if matches:
                    info["name"] = matches[0].strip()
                    break
    
    return info

def get_system_prompt(db: Session) -> Optional[str]:
    """
    Get the configurable system prompt for regular chat.
    
    Args:
        db: Database session
        
    Returns:
        System prompt string if configured, None otherwise
    """
    return RAGConfigService.get_regular_chat_prompt(db)

def get_conversation_memory(db: Session, conversation_id: str = None, user_id: int = None):
    """
    Get or create a conversation with its memory
    
    Args:
        db: Database session
        conversation_id: ID of existing conversation
        user_id: User ID for creating a new conversation
        
    Returns:
        Tuple of (conversation_memory, conversation_id, is_new_conversation)
    """
    is_new_conversation = False
    
    # Try to get existing conversation
    if conversation_id:
        db_conversation = crud.get_conversation(db, conversation_id)
    else:
        db_conversation = None
    
    # Create new conversation if needed
    if not db_conversation and user_id:
        db_conversation = crud.create_conversation(db, user_id)
        is_new_conversation = True
        conversation_id = db_conversation.id
    elif not db_conversation:
        # If no user_id and no valid conversation_id, we can't proceed
        raise ValueError("Either conversation_id or user_id must be provided")
    else:
        conversation_id = db_conversation.id
    
    # Create memory and load messages from database
    memory = ConversationBufferMemory()
    
    # Load existing messages if this is not a new conversation
    if not is_new_conversation:
        messages = crud.get_conversation_messages(db, conversation_id)
        for msg in messages:
            if msg.role == "user":
                memory.chat_memory.add_user_message(msg.content)
            elif msg.role == "assistant":
                memory.chat_memory.add_ai_message(msg.content)
        
        # Extract user information from this conversation's messages
        # and update the persistent user info
        if user_id and messages:
            if user_id not in user_info:
                user_info[user_id] = {}
            
            extracted_info = extract_user_info(messages)
            user_info[user_id].update(extracted_info)
    
    # If this is a new conversation but we have user info from previous conversations,
    # inject that information into the system prompt
    if is_new_conversation and user_id in user_info and user_info[user_id]:
        user_data = user_info[user_id]
        
        # Create a system message with user information
        system_msg = "System: This is important user information I know:\n"
        
        if "name" in user_data:
            system_msg += f"- User's name is {user_data['name']}\n"
        
        # Add other user info as needed
        
        # Add this as the first message in the conversation memory
        memory.chat_memory.add_ai_message(system_msg)
    
    return memory, conversation_id, is_new_conversation

async def get_llm_response(db: Session, user_id: int, message: str, conversation_id: Optional[str] = None, meta_data: Optional[dict] = None):
    """Get a response from the LLM and store it in the database"""
    print(f"DEBUG: Starting get_llm_response with message: {message[:30]}...")
    
    # Get or create conversation with memory
    memory, conversation_id, is_new = get_conversation_memory(
        db, conversation_id, user_id
    )
    print(f"DEBUG: Got conversation memory, conversation_id: {conversation_id}")
    
    # Update conversation meta_data if provided
    if meta_data and conversation_id:
        crud.update_conversation(db, conversation_id, meta_data)
    
    # Save user message to database
    user_message = schemas.MessageCreate(
        conversation_id=conversation_id,
        role="user",
        content=message
    )
    created_msg = crud.create_message(db, user_message)
    print(f"DEBUG: Saved user message to database, id: {created_msg.id}")
    
    # Update memory with the user message (important for context)
    memory.chat_memory.add_user_message(message)
    
    # Get LLM with configuration
    llm = get_llm(db)
    print(f"DEBUG: Got LLM instance: {llm}")
    
    # Convert memory messages to the format expected by the LLM
    messages = []
    
    # Add system prompt if configured
    system_prompt = get_system_prompt(db)
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    
    for msg in memory.chat_memory.messages:
        if isinstance(msg, HumanMessage):
            messages.append(HumanMessage(content=msg.content))
        elif isinstance(msg, AIMessage):
            messages.append(AIMessage(content=msg.content))
    
    print(f"DEBUG: Prepared {len(messages)} messages for LLM")
    
    try:
        # Get response from LLM with full conversation context
        # Use LangChain's native async method instead of asyncio.to_thread
        print(f"DEBUG: Calling LLM.ainvoke with {len(messages)} messages")
        response_obj = await llm.ainvoke(messages)
        print(f"DEBUG: Got response from LLM: {response_obj}")
        response = response_obj.content
        print(f"DEBUG: Response content: {response[:50]}...")
    except Exception as e:
        print(f"ERROR: Exception calling LLM: {str(e)}")
        response = "Sorry, I encountered an error while processing your request."
    
    # Save assistant response to database
    assistant_message = schemas.MessageCreate(
        conversation_id=conversation_id,
        role="assistant",
        content=response
    )
    crud.create_message(db, assistant_message)
    print(f"DEBUG: Saved assistant response to database")
    
    # Update the memory with the assistant's response
    memory.chat_memory.add_ai_message(response)
    
    # Return just the response string, not a dictionary
    return response

async def get_streaming_llm_response(db: Session, user_id: int, message: str, conversation_id: Optional[str] = None, meta_data: Optional[dict] = None, save_user_message: bool = True):
    """Get a streaming response from the LLM and store it in the database when complete"""
    # Get or create conversation with memory
    memory, conversation_id, is_new = get_conversation_memory(
        db, conversation_id, user_id
    )
    
    # Update conversation meta_data if provided
    if meta_data and conversation_id:
        crud.update_conversation(db, conversation_id, meta_data)
    
    # Save user message to database if requested
    if save_user_message:
        user_message = schemas.MessageCreate(
            conversation_id=conversation_id,
            role="user",
            content=message
        )
        created_msg = crud.create_message(db, user_message)
    
    # Update memory with the user message (important for context)
    memory.chat_memory.add_user_message(message)
    
    # Get LLM with streaming enabled
    llm = get_llm(db, streaming=True)
    
    # Collect the full response for storing in the database
    full_response = []
    
    # Stream directly using LangChain's native async streaming
    try:
        # Convert memory messages to the format expected by the LLM
        messages = []
        
        # Add system prompt if configured
        system_prompt = get_system_prompt(db)
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        
        for msg in memory.chat_memory.messages:
            if isinstance(msg, HumanMessage):
                messages.append(HumanMessage(content=msg.content))
            elif isinstance(msg, AIMessage):
                messages.append(AIMessage(content=msg.content))
        
        # Use LangChain's native async streaming method
        async for chunk in llm.astream(messages):
            token = chunk.content
            full_response.append(token)
            # Yield each token for streaming to the client
            yield token
        
        # Combine all tokens into the complete response
        complete_response = "".join(full_response)
            
        # Save assistant response to database
        assistant_message = schemas.MessageCreate(
            conversation_id=conversation_id,
            role="assistant",
            content=complete_response
        )
        crud.create_message(db, assistant_message)
        
        # Update the memory with the assistant's response
        memory.chat_memory.add_ai_message(complete_response)
    except Exception as e:
        # Log the exception and re-raise
        print(f"Error in streaming response: {str(e)}")
        raise

async def generate_conversation_headline(db: Session, conversation_id: str) -> str:
    """
    Generate a simple topic label for the conversation
    
    Args:
        db: Database session
        conversation_id: ID of the conversation
        
    Returns:
        Short topic label for the conversation
    """
    # Get the conversation and its messages
    conversation = crud.get_conversation(db, conversation_id)
    if not conversation:
        raise ValueError(f"Conversation with ID {conversation_id} not found")
    
    # Get all messages
    all_messages = crud.get_conversation_messages(db, conversation_id)
    if not all_messages:
        return "New Conversation"
    
    # Filter to just get user messages
    user_messages = [msg for msg in all_messages if msg.role == "user"]
    if not user_messages:
        return "New Conversation"
    
    # Use first 3 user messages only
    messages = user_messages[:3]
    
    # Simple prompt
    prompt = """What is the main topic of these messages in 2-5 words? 
Just the core topic, no extra words.
Do not use any special characters, markdown symbols, arrows, or formatting.

Use the user language for the headline/summary.
Examples:
Messages about Python programming → "Python Programming"
Messages about climate change → "Climate Change"
Messages about ITDEL University → "ITDEL University"
Messages about DGX vs HGX → "DGX vs HGX"

Messages:
"""
    
    # Add user messages to the prompt
    for msg in messages:
        prompt += f"- {msg.content}\n"
    
    prompt += "\nTopic: "
    
    # Get LLM with configuration and thinking disabled for headline generation
    llm = get_llm(db, override_thinking=False)
    
    # Generate topic
    message = HumanMessage(content=prompt)
    response = llm.invoke([message])
    topic = clean_title(response.content)
    
    # Update the conversation
    conversation.headline = topic
    db.commit()
    
    return topic 