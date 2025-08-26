# Canvas Sync - Clean Modular Architecture

## 🏗️ **Architecture Overview**

This application follows a clean, modular architecture with clear separation of concerns for maintainability and scalability.

```
app/
├── api/                    # 🌐 API Routes (by feature)
├── services/               # 🔧 Business Logic Services
├── models/                 # 💾 Database Models
├── schemas/                # 📋 API Request/Response Models
├── utils/                  # 🛠️ Utility Functions
├── main.py                 # 🚀 FastAPI Application Entry Point
├── config.py               # ⚙️ Configuration Settings
├── db.py                   # 🗄️ Database Setup
└── logging.py              # 📝 Logging Configuration
```

## 📁 **Directory Structure**

### **API Layer (`app/api/`)**

- **`health.py`** - Health check endpoints
- **`setup.py`** - User setup and configuration
- **`canvas.py`** - Canvas-related endpoints
- **`notion.py`** - Notion integration endpoints
- **`sync.py`** - Synchronization endpoints

### **Services Layer (`app/services/`)**

Business logic separated by domain:

#### **Canvas Services (`app/services/canvas/`)**

- **`client.py`** - Canvas API client for authenticated requests
- **`professor_detector.py`** - Sections-based professor detection
- **`course_mapper.py`** - Maps Canvas courses to Notion format
- **`sync_service.py`** - Orchestrates Canvas operations

#### **Sync Services (`app/services/sync/`)**

- **`coordinator.py`** - Main sync coordinator between Canvas and Notion

### **Models Layer (`app/models/`)**

- **`user_settings.py`** - SQLAlchemy database models

### **Schemas Layer (`app/schemas/`)**

Pydantic models for API validation:

- **`setup.py`** - Setup request/response schemas
- **`notion.py`** - Notion API schemas
- **`sync.py`** - Sync operation schemas

### **Utils Layer (`app/utils/`)**

- **`date_utils.py`** - Date/time utility functions
- **`notion_helper.py`** - Notion workspace management (to be refactored)

## 🎯 **Key Benefits**

### **1. Separation of Concerns**

- **API routes** handle HTTP requests/responses
- **Services** contain business logic
- **Models** define data structure
- **Schemas** validate input/output

### **2. Testability**

- Each service can be unit tested independently
- Clear dependencies make mocking easy
- Business logic separated from API concerns

### **3. Maintainability**

- Small, focused files (< 200 lines each)
- Clear module boundaries
- Easy to locate specific functionality

### **4. Scalability**

- New features can be added without touching existing code
- Services can be easily extracted to microservices
- Clear interfaces between components

## 🔄 **Data Flow**

```
HTTP Request → API Route → Service → External API/Database → Response
```

### **Example: Canvas Sync Flow**

1. **API** (`sync.py`) receives sync request
2. **Coordinator** (`coordinator.py`) orchestrates the sync
3. **Canvas Service** (`sync_service.py`) fetches course data
4. **Professor Detector** (`professor_detector.py`) finds actual professors
5. **Course Mapper** (`course_mapper.py`) formats data for Notion
6. **Notion Helper** creates entries in Notion databases
7. **API** returns structured response

## 🧪 **Testing Strategy**

```python
# Example: Testing professor detection
async def test_professor_detection():
    canvas_client = Mock(CanvasAPIClient)
    detector = ProfessorDetector(canvas_client)

    # Test sections-based detection
    professors = await detector.get_professors_from_sections("12345")
    assert len(professors) > 0
    assert professors[0]["role"] == "Teacher"
```

## 🚀 **Usage Examples**

### **Canvas Professor Detection**

```bash
curl -X POST "http://localhost:8000/canvas/test-professors?course_id=486340&user_email=user@example.com"
```

### **Canvas to Notion Sync**

```bash
curl -X POST "http://localhost:8000/sync/start" \
  -H "Content-Type: application/json" \
  -d '{"user_email": "user@example.com"}'
```

## 📈 **Future Improvements**

1. **Extract Notion Services** - Refactor `notion_helper.py` into focused services
2. **Add Google Calendar Services** - Create `services/google/` module
3. **Event-Driven Architecture** - Add event bus for service communication
4. **Caching Layer** - Add Redis for API response caching
5. **Background Jobs** - Add Celery for async processing

## 🔧 **Development**

### **Adding New Features**

1. Create new service in appropriate domain folder
2. Add API route in relevant router
3. Define schemas for request/response
4. Update `__init__.py` files to expose new components

### **Code Style**

- Services should be stateless when possible
- Use dependency injection for external dependencies
- Keep functions focused and single-purpose
- Add comprehensive docstrings and type hints

This architecture provides a solid foundation for scaling the Canvas Sync application while maintaining code quality and developer productivity.
