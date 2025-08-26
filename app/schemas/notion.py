from pydantic import BaseModel
from typing import Dict, Any, List


# Request Models
class NotionTestRequest(BaseModel):
    notion_token: str
    notion_parent_page_id: str


class NotionEntryRequest(BaseModel):
    notion_token: str
    notion_parent_page_id: str
    entry_data: Dict[str, Any]


# Response Models
class NotionDatabaseInfo(BaseModel):
    id: str
    name: str
    found: bool
    properties_count: int


class NotionWorkspaceResponse(BaseModel):
    success: bool
    parent_page_id: str
    databases_found: int
    databases: List[NotionDatabaseInfo]
    message: str


class NotionSchemaResponse(BaseModel):
    success: bool
    databases_found: int
    schemas: Dict[str, Any]
    message: str


class NotionEntryResponse(BaseModel):
    success: bool
    message: str
    page_id: str
    note: str
