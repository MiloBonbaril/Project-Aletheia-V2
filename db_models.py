#
# alembic/models.py
# used for Alembic autogeneration support and model metadata declaration
#

from sqlalchemy import Column, Integer, String, Text, DateTime, ARRAY, func, MetaData, PrimaryKeyConstraint
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_'%(constraint_name)s'",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    })


class LongTermMemory(Base):
    __tablename__ = 'LongTermMemory'

    id = Column(Integer, primary_key=True, index=True, unique=True)
    content = Column(Text, nullable=False)
    author = Column(String(255), nullable=False)
    timestamp = Column(DateTime, nullable=False, server_default=func.now())
    source = Column(String(255), nullable=True)
    tags = Column(ARRAY(String(50)), nullable=True)
