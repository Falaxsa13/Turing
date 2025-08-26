from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from app.db import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, unique=True, index=True, nullable=False)

    # Canvas settings
    canvas_base_url = Column(String, nullable=True)
    canvas_pat = Column(String, nullable=True)

    # Notion settings
    notion_token = Column(String, nullable=True)
    notion_parent_page_id = Column(String, nullable=True)

    # Google settings
    google_credentials = Column(Text, nullable=True)
    google_calendar_id = Column(String, nullable=True)

    # Sync tracking
    last_canvas_sync = Column(DateTime, nullable=True)
    last_notion_sync = Column(DateTime, nullable=True)
    last_google_sync = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
