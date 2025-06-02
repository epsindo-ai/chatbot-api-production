# Enable Thinking Functionality Guide

## Overview

The `enable_thinking` parameter has been added to the LLM configuration to control whether the model uses its thinking capability. This feature allows you to:

1. **Globally control thinking** via admin configuration
2. **Override thinking** for specific use cases (like headline generation)
3. **Ensure compatibility** with models that support thinking capabilities

## Database Changes

### New Column
- Added `enable_thinking` column to `llm_config` table
- Type: `BOOLEAN` with default value `FALSE`
- Migration: `7f9b5b6f8faf_add_enable_thinking_to_llm_config.py`

### Schema Updates
- Updated `LLMConfigBase`, `LLMConfigCreate`, and `LLMConfigUpdate` schemas
- Added `enable_thinking` field to all LLM config endpoints

## API Changes

### Admin Endpoints

#### Get LLM Config
```bash
GET /api/llm-config/
```
Response now includes:
```json
{
  "name": "Default LLM Config",
  "model_name": "Qwen/Qwen3-8B",
  "temperature": 0.7,
  "top_p": 0.8,
  "max_tokens": 8192,
  "enable_thinking": false,
  "extra_params": {
    "base_url": "http://192.168.1.10:33315/v1",
    "api_key": "EMPTY"
  }
}
```

#### Update LLM Config
```bash
PUT /api/llm-config/
Content-Type: application/json

{
  "enable_thinking": true
}
```

#### Public Config Endpoint
```bash
GET /api/llm-config/public
```
Response now includes:
```json
{
  "model_name": "Qwen/Qwen3-8B",
  "temperature": 0.7,
  "top_p": 0.8,
  "max_tokens": 8192,
  "enable_thinking": false
}
```

## Implementation Details

### LLM Service Changes

The `get_llm()` function now supports an `override_thinking` parameter:

```python
def get_llm(db: Session, streaming: bool = False, override_thinking: Optional[bool] = None):
    """
    Initialize and return the LLM model using configuration from the database
    
    Args:
        db: Database session
        streaming: Whether to enable streaming mode
        override_thinking: Override the enable_thinking setting from config
        
    Returns:
        Configured LLM instance
    """
```

### OpenAI Client Configuration

The thinking capability is controlled via the `extra_body` parameter:

```python
model_params["extra_body"] = {
    "chat_template_kwargs": {
        "enable_thinking": enable_thinking
    }
}
```

This matches your example:
```python
chat_response = client.chat.completions.create(
    model="Qwen/Qwen3-8B",
    messages=[...],
    extra_body={
        "chat_template_kwargs": {"enable_thinking": False},
    },
)
```

### Headline Generation

All headline/title generation functions automatically disable thinking:

```python
# In TitleGenerationService
llm = get_llm(db, override_thinking=False)

# In generate_conversation_headline
llm = get_llm(db, override_thinking=False)
```

This ensures that headline generation never uses thinking mode, which could break the endpoint.

## Usage Examples

### 1. Enable Thinking Globally

```bash
curl -X PUT "http://localhost:8000/api/llm-config/" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enable_thinking": true}'
```

### 2. Disable Thinking Globally

```bash
curl -X PUT "http://localhost:8000/api/llm-config/" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enable_thinking": false}'
```

### 3. Check Current Setting

```bash
curl -X GET "http://localhost:8000/api/llm-config/public" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Use in Code

```python
from app.services.llm_service import get_llm

# Use global setting
llm = get_llm(db)

# Force thinking disabled (for headlines, etc.)
llm = get_llm(db, override_thinking=False)

# Force thinking enabled (override global setting)
llm = get_llm(db, override_thinking=True)
```

## Automatic Behavior

### Headline Generation
- **Always disables thinking** regardless of global setting
- Prevents thinking output from breaking headline endpoints
- Applies to:
  - `generate_conversation_headline()`
  - `TitleGenerationService.generate_initial_title()`
  - `TitleGenerationService.update_title_periodic()`
  - `TitleGenerationService.detect_topic_shift()`
  - `TitleGenerationService.update_title_on_shift()`
  - `TitleGenerationService.generate_final_title()`

### Regular Chat
- **Uses global setting** from LLM config
- Can be overridden per request if needed
- Applies to:
  - `get_llm_response()`
  - `get_streaming_llm_response()`
  - RAG chat responses

## Migration Notes

### Existing Installations
1. Run the migration: `alembic upgrade head`
2. The `enable_thinking` column will be added with default value `FALSE`
3. Existing functionality remains unchanged
4. Admin can enable thinking via the API

### Default Behavior
- New installations default to `enable_thinking = FALSE`
- This ensures backward compatibility
- Thinking must be explicitly enabled by admin

## Troubleshooting

### Common Issues

1. **Migration fails**: Ensure database is accessible and no other processes are using it
2. **Config not updating**: Check admin permissions and database connection
3. **Thinking not working**: Verify model supports thinking and config is enabled

### Verification

Check if thinking is properly configured:

```python
from app.db import crud
from app.db.database import get_db

db = next(get_db())
config = crud.get_llm_config(db)
print(f"Thinking enabled: {config.enable_thinking}")
```

## Security Considerations

- Only admin users can modify the `enable_thinking` setting
- Regular users can view the setting via the public endpoint
- The setting affects all users globally
- Headline generation is always protected (thinking disabled)

## Performance Impact

- **Thinking enabled**: May increase response time and token usage
- **Thinking disabled**: Standard performance
- **Headline generation**: Always optimized (no thinking overhead)

The implementation ensures that critical functions like headline generation are never impacted by thinking mode, while providing flexibility for regular chat interactions. 