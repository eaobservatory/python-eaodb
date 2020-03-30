# coding: utf-8
from sqlalchemy import Column, String
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class user(Base):
    __tablename__ = 'user'
    __table_args__ = {'schema': 'hedwig2omp'}

    hedwig_id = Column(INTEGER(11), primary_key=True)
    omp_id = Column(String(255), nullable=False)
