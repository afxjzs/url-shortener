"""Database models for URL Shortener service."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, UUID, ForeignKey, Index, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Shortcode(Base):
    """URL shortcode mapping."""
    __tablename__ = 'url_shortener_shortcodes'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shortcode = Column(String(255), unique=True, nullable=False, index=True)
    target_url = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    active = Column(Boolean, nullable=False, default=True)
    custom = Column(Boolean, nullable=False, default=False)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    
    clicks = relationship('Click', back_populates='shortcode', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Shortcode {self.shortcode}>'


class Click(Base):
    """Click tracking for shortcodes."""
    __tablename__ = 'url_shortener_clicks'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shortcode_id = Column(UUID(as_uuid=True), ForeignKey('url_shortener_shortcodes.id'), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    ip_address = Column(String(255), nullable=False)  # base64 encoded
    user_agent = Column(Text, nullable=True)
    referer = Column(Text, nullable=True)
    country = Column(String(2), nullable=True)
    city = Column(String(255), nullable=True)
    
    shortcode = relationship('Shortcode', back_populates='clicks')

    def __repr__(self):
        return f'<Click {self.shortcode_id} @ {self.timestamp}>'


__all__ = ['Base', 'Shortcode', 'Click']
