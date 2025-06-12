import os
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from the correct path
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

class Settings(BaseModel):
    # App Settings
    APP_NAME: str = os.getenv("APP_NAME", "LLM Chatbot API")
    
    # JWT Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "default_jwt_key_change_in_production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "2400"))
    
    # Database Settings
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "myuser")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "mysecretpassword")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "192.168.1.10")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "35433")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "chatbot")
    
    # LLM Settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "EMPTY")
    OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE", "http://192.168.1.10:33315/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "epsindo.ai/qwen2.5-14b-inst-awq")
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    LLM_TOP_P: float = float(os.getenv("LLM_TOP_P", "0.95"))
    LLM_CONFIG_NAME: str = os.getenv("LLM_CONFIG_NAME", "Epsindo LLM Configuration")
    
    # Minio Settings (for file storage)
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "192.168.1.10:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_DEFAULT_BUCKET: str = os.getenv("MINIO_DEFAULT_BUCKET", "documents")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "False").lower() == "true"
    
    # RAG Settings
    REMOTE_EMBEDDER_URL: str = os.getenv("REMOTE_EMBEDDER_URL", "http://192.168.1.10:33325/embeddings")
    MILVUS_URI: str = os.getenv("MILVUS_URI", "http://localhost:19530")
    DEFAULT_COLLECTION: str = os.getenv("DEFAULT_COLLECTION", "default_collection") 
    RETRIEVER_TOP_K: int = int(os.getenv("RETRIEVER_TOP_K", "10"))
    
    # Infinity Embeddings Settings
    INFINITY_EMBEDDINGS_MODEL: str = os.getenv("INFINITY_EMBEDDINGS_MODEL", "stella-en-1.5B")
    INFINITY_API_URL: str = os.getenv("INFINITY_API_URL", "http://192.168.1.10:33325")
    USE_INFINITY_EMBEDDINGS: bool = os.getenv("USE_INFINITY_EMBEDDINGS", "True").lower() == "true"
    
    # Docling Settings
    DOCLING_PARSER_PATH: str = os.getenv("DOCLING_PARSER_PATH", "/root/.cache/docling/models")
    DOCLING_EMBED_MODEL: str = os.getenv("DOCLING_EMBED_MODEL", "/app/stella-embed-tokenizer")
    DOCLING_USE_GPU: bool = os.getenv("DOCLING_USE_GPU", "True").lower() == "true"
    
    # Build database URL
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

settings = Settings()