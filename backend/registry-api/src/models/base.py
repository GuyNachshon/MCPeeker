"""SQLAlchemy base model.

Reference: FR-006 (PostgreSQL for transactional data)
"""
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
