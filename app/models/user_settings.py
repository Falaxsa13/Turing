from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.db import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, unique=True, index=True, nullable=False)

    # Canvas configuration
    canvas_base_url = Column(String, nullable=True)
    canvas_pat = Column(String, nullable=True)  # Personal Access Token

    # Notion configuration
    notion_token = Column(String, nullable=True)
    notion_parent_page_id = Column(String, nullable=True)  # Parent page instead of specific database

    # Google Calendar configuration
    google_credentials = Column(Text, nullable=True)  # JSON credentials
    google_calendar_id = Column(String, nullable=True)

    # Sync timestamps
    last_canvas_sync = Column(DateTime, nullable=True)
    last_notion_sync = Column(DateTime, nullable=True)
    last_google_sync = Column(DateTime, nullable=True)
    last_assignment_sync = Column(DateTime, nullable=True)

    # Audit timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
