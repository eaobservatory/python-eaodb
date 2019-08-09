# coding: utf-8
from sqlalchemy import Column, Date, DateTime, ForeignKey, String, Table, Text
from sqlalchemy.dialects.mysql import INTEGER, TINYINT
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class papers(Base):
    __tablename__ = 'papers'
    __table_args__ = {'schema': 'pigwidgeon'}

    id = Column(INTEGER(11), primary_key=True)
    bibcode = Column(String(20), nullable=False)
    title = Column(Text)
    abstract = Column(Text)
    pub_openaccess = Column(TINYINT(1))
    refereed = Column(TINYINT(1))
    doi = Column(String(100))
    pubdate = Column(Date, index=True)
    first_added = Column(DateTime)
    updated = Column(DateTime)

    searchs = relationship('searches', secondary='pigwidgeon.paper_search_association')


class searches(Base):
    __tablename__ = 'searches'
    __table_args__ = {'schema': 'pigwidgeon'}

    id = Column(INTEGER(11), primary_key=True)
    named = Column(String(50), nullable=False)
    ads_query = Column(Text)
    last_performed = Column(DateTime)
    startdate = Column(DateTime)
    timerange = Column(INTEGER(11))


class authors(Base):
    __tablename__ = 'authors'
    __table_args__ = {'schema': 'pigwidgeon'}

    id = Column(INTEGER(11), primary_key=True)
    paper_id = Column(ForeignKey('pigwidgeon.papers.id', ondelete='CASCADE'), index=True)
    author = Column(String(100))
    position_ = Column(INTEGER(11), nullable=False)
    affiliation = Column(Text)

    paper = relationship('papers')


class comments(Base):
    __tablename__ = 'comments'
    __table_args__ = {'schema': 'pigwidgeon'}

    id = Column(INTEGER(11), primary_key=True)
    search_id = Column(ForeignKey('pigwidgeon.searches.id'), nullable=False, index=True)
    paper_id = Column(ForeignKey('pigwidgeon.papers.id', ondelete='SET NULL'), index=True)
    username = Column(String(50), nullable=False)
    datetime = Column(DateTime)

    paper = relationship('papers')
    search = relationship('searches')


class identifiers(Base):
    __tablename__ = 'identifiers'
    __table_args__ = {'schema': 'pigwidgeon'}

    id = Column(INTEGER(11), primary_key=True)
    paper_id = Column(ForeignKey('pigwidgeon.papers.id', ondelete='CASCADE'), index=True)
    identifier = Column(String(100))

    paper = relationship('papers')


class info_sections(Base):
    __tablename__ = 'info_sections'
    __table_args__ = {'schema': 'pigwidgeon'}

    id = Column(INTEGER(11), primary_key=True)
    search_id = Column(ForeignKey('pigwidgeon.searches.id'), nullable=False, index=True)
    position_ = Column(INTEGER(11))
    name_ = Column(String(50))
    type_ = Column(INTEGER(11))
    instructiontext = Column(String(50))

    search = relationship('searches')


class keywords(Base):
    __tablename__ = 'keywords'
    __table_args__ = {'schema': 'pigwidgeon'}

    id = Column(INTEGER(11), primary_key=True)
    paper_id = Column(ForeignKey('pigwidgeon.papers.id', ondelete='CASCADE'), index=True)
    keyword = Column(String(200))

    paper = relationship('papers')


t_paper_search_association = Table(
    'paper_search_association', metadata,
    Column('paper_id', ForeignKey('pigwidgeon.papers.id', ondelete='CASCADE'), index=True),
    Column('search_id', ForeignKey('pigwidgeon.searches.id'), index=True),
    schema='pigwidgeon'
)


class paper_types(Base):
    __tablename__ = 'paper_types'
    __table_args__ = {'schema': 'pigwidgeon'}

    id = Column(INTEGER(11), primary_key=True)
    search_id = Column(ForeignKey('pigwidgeon.searches.id'), nullable=False, index=True)
    position_ = Column(INTEGER(11))
    name_ = Column(Text)
    radio = Column(TINYINT(1))

    search = relationship('searches')


class properties(Base):
    __tablename__ = 'properties'
    __table_args__ = {'schema': 'pigwidgeon'}

    id = Column(INTEGER(11), primary_key=True)
    paper_id = Column(ForeignKey('pigwidgeon.papers.id'), nullable=False, index=True)
    property = Column(String(30), nullable=False)

    paper = relationship('papers')


class info_sublists(Base):
    __tablename__ = 'info_sublists'
    __table_args__ = {'schema': 'pigwidgeon'}

    id = Column(INTEGER(11), primary_key=True)
    info_section_id = Column(ForeignKey('pigwidgeon.info_sections.id'), nullable=False, index=True)
    named = Column(String(50))
    position_ = Column(INTEGER(11))

    info_section = relationship('info_sections')


class papertype_value(Base):
    __tablename__ = 'papertype_value'
    __table_args__ = {'schema': 'pigwidgeon'}

    id = Column(INTEGER(11), primary_key=True)
    comment_id = Column(ForeignKey('pigwidgeon.comments.id'), nullable=False, index=True)
    papertype_id = Column(ForeignKey('pigwidgeon.paper_types.id'), nullable=False, index=True)

    comment = relationship('comments')
    papertype = relationship('paper_types')


class info_section_values(Base):
    __tablename__ = 'info_section_values'
    __table_args__ = {'schema': 'pigwidgeon'}

    id = Column(INTEGER(11), primary_key=True)
    info_section_id = Column(ForeignKey('pigwidgeon.info_sections.id'), nullable=False, index=True)
    comment_id = Column(ForeignKey('pigwidgeon.comments.id'), nullable=False, index=True)
    info_sublist_id = Column(ForeignKey('pigwidgeon.info_sublists.id'), index=True)
    entered_text = Column(Text)

    comment = relationship('comments')
    info_section = relationship('info_sections')
    info_sublist = relationship('info_sublists')
