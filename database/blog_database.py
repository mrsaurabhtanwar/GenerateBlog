import os

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
from datetime import datetime

from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = (BASE_DIR / "database" / "blogs_database.db").as_posix()
DB_URL = os.getenv("SQL_DB_URL", f"sqlite:///{DEFAULT_DB_PATH}")

engine = create_engine(DB_URL)
sessionLocal = sessionmaker(bind=engine, autoflush=True)
Base = declarative_base()

class BLOGTABLE(Base):
    
    __tablename__ = "blogs_table"
    id = Column(Integer, autoincrement=True, primary_key=True)
    blog_id = Column(String, unique=True, nullable=False)
    topic = Column(String, nullable=False)
    web_results = Column(String)
    web_links = Column(Text)
    outline = Column(String, nullable=False)
    blog = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
Base.metadata.create_all(bind=engine)


        
