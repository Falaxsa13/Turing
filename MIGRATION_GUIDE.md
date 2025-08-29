# Migration Guide: Old Structure to New Structure

## Overview

This guide helps you migrate your existing code to use the new modular structure and core modules.

## Quick Start

### 1. **Update Imports in Existing Files**

#### Before (Old Structure)

```python
from app.config import settings
from app.logging import setup_logging
```

#### After (New Structure)

```python
from app.core.config import settings
from app.core.logging import setup_logging
```

### 2. **Replace Generic Exceptions**

#### Before

```python
raise Exception("User not found")
raise ValueError("Invalid email format")
```

#### After

```python
from app.core.exceptions import ValidationError, DatabaseError

raise ValidationError("Invalid email format", field="email", value=email)
raise DatabaseError("User not found", operation="get_user", collection="users")
```

### 3. **Use Standardized Response Models**

#### Before

```python
return {"success": True, "data": user_data}
return {"error": "User not found", "status": 404}
```

#### After

```python
from app.core.responses import success_response, error_response

return success_response(user_data, "User retrieved successfully")
return error_response("User not found", "USER_NOT_FOUND")
```

## Step-by-Step Migration

### Step 1: Update Configuration Usage

#### Old `app/config.py` (Legacy)

```python
# This file will be deprecated
from app.config import settings

canvas_url = settings.canvas_base_url
firebase_key = settings.firebase_api_key
```

#### New `app/core/config.py`

```python
from app.core.config import settings

canvas_url = settings.canvas.base_url
firebase_key = settings.firebase.api_key
```

### Step 2: Update Logging

#### Old Logging

```python
from app.logging import setup_logging
import logging

logger = logging.getLogger(__name__)
logger.info("Operation completed")
```

#### New Logging

```python
from app.core.logging import get_logger

logger = get_logger(__name__)
logger.info("Operation completed")
```

### Step 3: Update Exception Handling

#### Old Exception Handling

```python
try:
    result = some_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

#### New Exception Handling

```python
from app.core.exceptions import ExternalServiceError
from app.core.responses import error_response

try:
    result = some_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    raise ExternalServiceError(
        message="Operation failed",
        service="external_service",
        status_code=500
    )
```

### Step 4: Update Service Classes

#### Old Service

```python
class CanvasService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_courses(self):
        # Implementation
        pass
```

#### New Service

```python
from app.core.base import BaseService

class CanvasService(BaseService):
    def __init__(self):
        super().__init__()

    def get_courses(self):
        # Implementation
        pass
```

## File-by-File Migration

### `app/main.py` ✅ (Already Updated)

- Uses new core modules
- Factory pattern for app creation
- Structured logging
- API versioning

### `app/api/auth.py` (Needs Update)

```python
# Before
from app.auth import authenticate_user_with_firebase
from app.firebase import get_firebase_db

# After
from app.core.exceptions import AuthenticationError
from app.core.responses import success_response, error_response
from app.auth import authenticate_user_with_firebase
from app.firebase import get_firebase_db
```

### `app/firebase.py` (Needs Update)

```python
# Before
from app.config import settings
from loguru import logger

# After
from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import DatabaseError, ConfigurationError

logger = get_logger(__name__)
```

### `app/services/` (Needs Update)

```python
# Before
import logging

class SomeService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

# After
from app.core.base import BaseService

class SomeService(BaseService):
    def __init__(self):
        super().__init__()
```

## Testing the Migration

### 1. **Run the Application**

```bash
cd /Users/hansibarra/Documents/GitHub/Turing
python -m app.main
```

### 2. **Check for Import Errors**

Look for any import errors in the console output.

### 3. **Test API Endpoints**

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/health
```

### 4. **Check Logs**

Verify that logging is working with the new structure.

## Common Issues and Solutions

### Issue 1: Import Errors

**Error**: `ModuleNotFoundError: No module named 'app.core'`

**Solution**: Ensure the `app/core/` directory exists and has `__init__.py` files.

### Issue 2: Configuration Access

**Error**: `AttributeError: 'Settings' object has no attribute 'canvas'`

**Solution**: Update to use nested configuration:

```python
# Old
settings.canvas_base_url

# New
settings.canvas.base_url
```

### Issue 3: Logging Not Working

**Error**: No log output or incorrect format

**Solution**: Ensure logging is properly initialized:

```python
from app.core.logging import setup_logging, get_logger

setup_logging(log_level="INFO")
logger = get_logger(__name__)
```

## Gradual Migration Strategy

### Phase 1: Core Infrastructure ✅

- [x] Create core modules
- [x] Update main.py
- [x] Create base classes

### Phase 2: API Layer ✅ (Completed)

- [x] Update auth.py
- [x] Update canvas.py
- [x] Update notion.py
- [x] Update sync.py
- [x] Update setup.py
- [x] Update health.py

### Phase 3: Services Layer (Next)

- [ ] Update canvas services
- [ ] Update notion services
- [ ] Update sync services

### Phase 4: Utilities and Models

- [ ] Update utility functions
- [ ] Update data models
- [ ] Clean up legacy files

## Rollback Plan

If you encounter issues during migration:

1. **Keep the old files** until migration is complete
2. **Use feature flags** to switch between old and new implementations
3. **Test thoroughly** before removing old code
4. **Maintain backward compatibility** during transition

## Benefits After Migration

### **Immediate Benefits**

- Better error handling with custom exceptions
- Consistent logging across the application
- Centralized configuration management
- Standardized API responses

### **Long-term Benefits**

- Easier to add new features
- Better testing capabilities
- Improved code maintainability
- Clearer architecture patterns

## Need Help?

If you encounter issues during migration:

1. Check the console output for specific error messages
2. Verify all import paths are correct
3. Ensure the core modules are properly created
4. Test with a simple endpoint first

## Next Steps

After completing the migration:

1. **Remove legacy files**: `app/config.py`, `app/logging.py`
2. **Update documentation**: API docs, README
3. **Add tests**: Unit tests for new core modules
4. **Performance testing**: Ensure no performance regression
5. **Team training**: Share new patterns with team members
