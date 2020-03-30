# coding: utf-8
from sqlalchemy import CHAR, Column, Date, DateTime, Float, ForeignKey, Index, String, TIMESTAMP, Text, text
from sqlalchemy.dialects.mysql import INTEGER, TINYINT
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class job(Base):
    __tablename__ = 'job'
    __table_args__ = (
        Index('job_location_id', 'location', 'foreign_id', unique=True),
        {'schema': 'jsa_proc'}
    )

    id = Column(INTEGER(11), primary_key=True)
    tag = Column(String(80), nullable=False, unique=True)
    state = Column(CHAR(1), nullable=False, index=True, server_default=text("'?'"))
    state_prev = Column(CHAR(1), nullable=False, server_default=text("'?'"))
    location = Column(String(80), nullable=False, index=True)
    foreign_id = Column(String(80), index=True)
    mode = Column(String(10), nullable=False)
    parameters = Column(Text)
    priority = Column(INTEGER(11), nullable=False, index=True, server_default=text("0"))
    task = Column(String(80), nullable=False, index=True)
    qa_state = Column(CHAR(1), nullable=False, index=True, server_default=text("'?'"))


class task(Base):
    __tablename__ = 'task'
    __table_args__ = {'schema': 'jsa_proc'}

    id = Column(INTEGER(11), primary_key=True)
    taskname = Column(String(80), nullable=False, unique=True)
    etransfer = Column(TINYINT(1))
    starlink = Column(String(255))
    version = Column(INTEGER(11))
    command_run = Column(String(255))
    command_xfer = Column(String(255))
    raw_output = Column(TINYINT(1))
    command_ingest = Column(String(255))
    log_ingest = Column(String(255))


class input_file(Base):
    __tablename__ = 'input_file'
    __table_args__ = (
        Index('input_file_job_file', 'job_id', 'filename', unique=True),
        {'schema': 'jsa_proc'}
    )

    id = Column(INTEGER(11), primary_key=True)
    job_id = Column(ForeignKey('jsa_proc.job.id'), nullable=False, index=True)
    filename = Column(String(80), nullable=False)

    job = relationship('job')


class log(Base):
    __tablename__ = 'log'
    __table_args__ = {'schema': 'jsa_proc'}

    id = Column(INTEGER(11), primary_key=True)
    job_id = Column(ForeignKey('jsa_proc.job.id'), nullable=False, index=True)
    datetime = Column(TIMESTAMP, nullable=False, server_default=text("current_timestamp()"))
    state_prev = Column(CHAR(1), nullable=False, server_default=text("'?'"))
    state_new = Column(CHAR(1), nullable=False, index=True, server_default=text("'?'"))
    message = Column(Text, nullable=False)
    host = Column(String(80), nullable=False, server_default=text("'unknown'"))
    username = Column(String(80), nullable=False, server_default=text("'unknown'"))

    job = relationship('job')


class log_file(Base):
    __tablename__ = 'log_file'
    __table_args__ = {'schema': 'jsa_proc'}

    id = Column(INTEGER(11), primary_key=True)
    job_id = Column(ForeignKey('jsa_proc.job.id'), nullable=False, index=True)
    filename = Column(String(120), nullable=False)

    job = relationship('job')


class note(Base):
    __tablename__ = 'note'
    __table_args__ = {'schema': 'jsa_proc'}

    id = Column(INTEGER(11), primary_key=True)
    job_id = Column(ForeignKey('jsa_proc.job.id'), nullable=False, index=True)
    datetime = Column(TIMESTAMP, nullable=False, server_default=text("current_timestamp()"))
    message = Column(Text, nullable=False)
    username = Column(String(80), nullable=False, server_default=text("'unknown'"))

    job = relationship('job')


class obs(Base):
    __tablename__ = 'obs'
    __table_args__ = (
        Index('obs_job_obsidss', 'job_id', 'obsidss', unique=True),
        {'schema': 'jsa_proc'}
    )

    id = Column(INTEGER(11), primary_key=True)
    job_id = Column(ForeignKey('jsa_proc.job.id'), nullable=False, index=True)
    obsid = Column(String(80), nullable=False)
    obsidss = Column(String(80), nullable=False)
    utdate = Column(Date, nullable=False, index=True)
    obsnum = Column(INTEGER(11), nullable=False)
    instrument = Column(String(80), nullable=False)
    backend = Column(String(80), nullable=False)
    subsys = Column(String(80), nullable=False)
    project = Column(String(80), index=True)
    survey = Column(String(80))
    scanmode = Column(String(80))
    sourcename = Column(String(80))
    obstype = Column(String(80))
    association = Column(String(80))
    date_obs = Column(DateTime, nullable=False)
    omp_status = Column(INTEGER(11), nullable=False, server_default=text("0"))
    tau = Column(Float)
    seeing = Column(Float)
    date_end = Column(DateTime)

    job = relationship('job')


class obsidss(Base):
    __tablename__ = 'obsidss'
    __table_args__ = (
        Index('job_id_obsidss', 'job_id', 'obsid_subsysnr', unique=True),
        {'schema': 'jsa_proc'}
    )

    id = Column(INTEGER(11), primary_key=True)
    job_id = Column(ForeignKey('jsa_proc.job.id'), nullable=False)
    obsid_subsysnr = Column(String(50), nullable=False, index=True)
    obsid = Column(String(48), nullable=False)

    job = relationship('job')


class output_file(Base):
    __tablename__ = 'output_file'
    __table_args__ = (
        Index('output_file_job_file', 'job_id', 'filename', unique=True),
        {'schema': 'jsa_proc'}
    )

    id = Column(INTEGER(11), primary_key=True)
    job_id = Column(ForeignKey('jsa_proc.job.id'), nullable=False, index=True)
    filename = Column(String(120), nullable=False)
    md5 = Column(String(40))

    job = relationship('job')


class parent(Base):
    __tablename__ = 'parent'
    __table_args__ = (
        Index('parent_parent_job', 'job_id', 'parent', unique=True),
        {'schema': 'jsa_proc'}
    )

    id = Column(INTEGER(11), primary_key=True)
    job_id = Column(ForeignKey('jsa_proc.job.id'), nullable=False, index=True)
    parent = Column(ForeignKey('jsa_proc.job.id'), nullable=False, index=True)
    filter = Column(String(80), nullable=False, server_default=text("''"))

    job = relationship('job', primaryjoin='parent.job_id == job.id')
    job1 = relationship('job', primaryjoin='parent.parent == job.id')


class qa(Base):
    __tablename__ = 'qa'
    __table_args__ = {'schema': 'jsa_proc'}

    id = Column(INTEGER(11), primary_key=True)
    job_id = Column(ForeignKey('jsa_proc.job.id'), nullable=False, index=True)
    datetime = Column(TIMESTAMP, nullable=False, server_default=text("current_timestamp()"))
    status = Column(CHAR(1), nullable=False, server_default=text("'?'"))
    message = Column(Text, nullable=False)
    username = Column(String(80), nullable=False, server_default=text("'unknown'"))

    job = relationship('job')


class tile(Base):
    __tablename__ = 'tile'
    __table_args__ = (
        Index('tile_job_tile', 'job_id', 'tile', unique=True),
        {'schema': 'jsa_proc'}
    )

    id = Column(INTEGER(11), primary_key=True)
    job_id = Column(ForeignKey('jsa_proc.job.id'), nullable=False, index=True)
    tile = Column(INTEGER(11), nullable=False, index=True)

    job = relationship('job')
