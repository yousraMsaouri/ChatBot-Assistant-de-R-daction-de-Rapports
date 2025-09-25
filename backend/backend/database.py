# backend/database.py
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserReport(Base):
    __tablename__ = "user_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    report_name = Column(String)
    plan_json = Column(Text)
    generated_at = Column(DateTime, default=datetime.utcnow)
    downloaded = Column(Boolean, default=False)
    email_sent = Column(Boolean, default=False)
    call_scheduled = Column(Boolean, default=False)
    file_path = Column(String)

class UserMessage(Base):
    __tablename__ = "user_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    message = Column(Text, nullable=False)
    sender = Column(String, nullable=False)  # "user" ou "bot"
    timestamp = Column(DateTime, default=datetime.utcnow)
    
# Créer les tables
Base.metadata.create_all(bind=engine)

# Fonction utilitaire pour obtenir la DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()