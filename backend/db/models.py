"""SQLAlchemy models for UFC Analytics Platform."""

from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, Boolean, 
    ForeignKey, Text, JSON, func
)
from sqlalchemy.orm import relationship
from .database import Base


class Fighter(Base):
    """UFC Fighter model matching Greco's CSV format."""
    
    __tablename__ = "fighter_details"
    
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    nickname = Column(String(100))
    url = Column(String(500), unique=True)
    
    # Tale of the Tape fields (stored as strings initially)
    height = Column(String(20))  # e.g., "5'11""
    weight = Column(String(20))  # e.g., "185 lbs"
    reach = Column(String(20))   # e.g., "75""
    stance = Column(String(50))
    dob = Column(String(50))     # Date of birth as string
    
    # Calculated fields for ML
    height_cm = Column(Float)
    weight_lbs = Column(Float)
    reach_inches = Column(Float)
    date_of_birth = Column(Date)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    fighter_a_fights = relationship("Fight", foreign_keys="Fight.fighter_a_id", back_populates="fighter_a")
    fighter_b_fights = relationship("Fight", foreign_keys="Fight.fighter_b_id", back_populates="fighter_b")
    won_fights = relationship("Fight", foreign_keys="Fight.winner_id", back_populates="winner")
    fight_stats = relationship("FightStat", back_populates="fighter")
    
    def __repr__(self):
        return f"<Fighter(id={self.id}, name='{self.first_name} {self.last_name}')>"
    
    @property
    def full_name(self):
        """Get full name of fighter."""
        parts = [self.first_name, self.last_name]
        return " ".join(filter(None, parts))


class Event(Base):
    """UFC Event model."""
    
    __tablename__ = "event_details"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    date = Column(Date)
    location = Column(String(255))
    url = Column(String(500), unique=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    fights = relationship("Fight", back_populates="event")
    
    def __repr__(self):
        return f"<Event(id={self.id}, name='{self.name}', date={self.date})>"


class Fight(Base):
    """UFC Fight model."""
    
    __tablename__ = "fight_details"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("event_details.id", ondelete="CASCADE"))
    
    # Fighter references (both names and IDs for flexibility)
    fighter_a_name = Column(String(255))
    fighter_b_name = Column(String(255))
    fighter_a_id = Column(Integer, ForeignKey("fighter_details.id", ondelete="SET NULL"))
    fighter_b_id = Column(Integer, ForeignKey("fighter_details.id", ondelete="SET NULL"))
    
    # Fight outcome
    winner_name = Column(String(255))
    winner_id = Column(Integer, ForeignKey("fighter_details.id", ondelete="SET NULL"))
    method = Column(String(100))
    round = Column(Integer)
    time = Column(String(20))  # Store as string initially (e.g., "2:34")
    weight_class = Column(String(100))
    title_fight = Column(Boolean, default=False)
    bout_order = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    event = relationship("Event", back_populates="fights")
    fighter_a = relationship("Fighter", foreign_keys=[fighter_a_id], back_populates="fighter_a_fights")
    fighter_b = relationship("Fighter", foreign_keys=[fighter_b_id], back_populates="fighter_b_fights")
    winner = relationship("Fighter", foreign_keys=[winner_id], back_populates="won_fights")
    fight_stats = relationship("FightStat", back_populates="fight")
    
    def __repr__(self):
        return f"<Fight(id={self.id}, fighters='{self.fighter_a_name} vs {self.fighter_b_name}')>"


class FightStat(Base):
    """UFC Fight Statistics model matching Greco's CSV format."""
    
    __tablename__ = "fight_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    event_name = Column(String(255))
    bout = Column(String(500))
    round = Column(Integer)
    fighter_name = Column(String(255))
    fighter_id = Column(Integer, ForeignKey("fighter_details.id", ondelete="SET NULL"))
    fight_id = Column(Integer, ForeignKey("fight_details.id", ondelete="CASCADE"))
    
    # Strike statistics (stored as strings from CSV)
    kd = Column(Integer)  # Knockdowns
    sig_str = Column(String(20))  # Significant strikes (e.g., "9 of 22")
    sig_str_pct = Column(String(10))  # Significant strike percentage
    total_str = Column(String(20))  # Total strikes
    td = Column(String(20))  # Takedowns (e.g., "0 of 2")
    td_pct = Column(String(10))  # Takedown percentage
    sub_att = Column(Integer)  # Submission attempts
    rev = Column(Integer)  # Reversals
    ctrl = Column(String(20))  # Control time (e.g., "0:39")
    
    # Strike location breakdown
    head = Column(String(20))  # Head strikes
    body = Column(String(20))  # Body strikes
    leg = Column(String(20))  # Leg strikes
    distance = Column(String(20))  # Distance strikes
    clinch = Column(String(20))  # Clinch strikes
    ground = Column(String(20))  # Ground strikes
    
    # Calculated fields for analysis
    sig_str_landed = Column(Integer)
    sig_str_attempted = Column(Integer)
    total_str_landed = Column(Integer)
    total_str_attempted = Column(Integer)
    td_landed = Column(Integer)
    td_attempted = Column(Integer)
    ctrl_time_seconds = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    fighter = relationship("Fighter", back_populates="fight_stats")
    fight = relationship("Fight", back_populates="fight_stats")
    
    def __repr__(self):
        return f"<FightStat(id={self.id}, fighter='{self.fighter_name}', round={self.round})>"


class FighterTott(Base):
    """Fighter Tale of the Tape data."""
    
    __tablename__ = "fighter_tott"
    
    id = Column(Integer, primary_key=True, index=True)
    data = Column(JSON)  # Store raw CSV row as JSON
    imported_at = Column(DateTime(timezone=True), server_default=func.now())


class FightResults(Base):
    """Fight results and outcome data."""
    
    __tablename__ = "fight_results"
    
    id = Column(Integer, primary_key=True, index=True)
    data = Column(JSON)  # Store raw CSV row as JSON
    imported_at = Column(DateTime(timezone=True), server_default=func.now())