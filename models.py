#
# alembic/models.py
# used for Alembic autogeneration support and model metadata declaration
#

from sqlalchemy import Column, Integer, String, Text, DateTime, ARRAY, func
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

class LongTermMemory(Base):
    __tablename__ = 'LongTermMemory'

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    author = Column(String(255), nullable=False)
    timestamp = Column(DateTime, nullable=False, server_default=func.now())
    source = Column(String(255), nullable=True)
    tags = Column(ARRAY(String(50)), nullable=True)