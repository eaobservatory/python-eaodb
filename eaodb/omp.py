# coding: utf-8
from sqlalchemy import Column, DateTime, Float, Index, String, Table, Text, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, LONGTEXT, TINYINT
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class affiliationalloc(Base):
    __tablename__ = 'ompaffiliationalloc'
    __table_args__ = {'schema': 'omp'}

    telescope = Column(String(32), primary_key=True, nullable=False)
    semester = Column(String(32), primary_key=True, nullable=False)
    affiliation = Column(String(32), primary_key=True, nullable=False)
    allocation = Column(Float(asdecimal=True), nullable=False)
    observed = Column(Float(asdecimal=True), nullable=False, server_default=text("0"))


class fault(Base):
    __tablename__ = 'ompfault'
    __table_args__ = {'schema': 'omp'}

    faultid = Column(Float(asdecimal=True), primary_key=True, unique=True)
    category = Column(String(32), nullable=False)
    subject = Column(String(128), index=True)
    faultdate = Column(DateTime)
    type = Column(INTEGER(11), nullable=False)
    fsystem = Column(INTEGER(11), nullable=False)
    status = Column(INTEGER(11), nullable=False)
    urgency = Column(INTEGER(11), nullable=False)
    timelost = Column(Float(asdecimal=True), nullable=False)
    entity = Column(String(64))
    condition = Column(INTEGER(11))
    location = Column(INTEGER(11))
    shifttype = Column(String(70))
    remote = Column(String(70))


class faultassoc(Base):
    __tablename__ = 'ompfaultassoc'
    __table_args__ = {'schema': 'omp'}

    associd = Column(BIGINT(20), primary_key=True, unique=True)
    faultid = Column(Float(asdecimal=True), nullable=False, index=True)
    projectid = Column(String(32), nullable=False, index=True)


class faultbody(Base):
    __tablename__ = 'ompfaultbody'
    __table_args__ = {'schema': 'omp'}

    respid = Column(BIGINT(20), primary_key=True)
    faultid = Column(Float(asdecimal=True), nullable=False, index=True)
    date = Column(DateTime, nullable=False)
    author = Column(String(32), nullable=False)
    isfault = Column(INTEGER(11), nullable=False)
    text = Column(LONGTEXT, nullable=False, index=True)


class feedback(Base):
    __tablename__ = 'ompfeedback'
    __table_args__ = {'schema': 'omp'}

    commid = Column(BIGINT(20), primary_key=True)
    projectid = Column(String(32), nullable=False, index=True)
    author = Column(String(32))
    date = Column(DateTime, nullable=False, index=True)
    subject = Column(String(128))
    program = Column(String(50), nullable=False)
    sourceinfo = Column(String(60), nullable=False)
    status = Column(INTEGER(11))
    text = Column(LONGTEXT, nullable=False)
    msgtype = Column(INTEGER(11))
    entrynum = Column(BIGINT(20))


t_ompkey = Table(
    'ompkey', metadata,
    Column('keystring', String(64), nullable=False),
    Column('expiry', DateTime, nullable=False),
    schema='omp'
)


class msb(Base):
    __tablename__ = 'ompmsb'
    __table_args__ = {'schema': 'omp'}

    msbid = Column(BIGINT(20), primary_key=True, unique=True)
    projectid = Column(String(32), nullable=False, index=True)
    remaining = Column(INTEGER(11), nullable=False, index=True)
    checksum = Column(String(64), nullable=False)
    obscount = Column(INTEGER(11), nullable=False, index=True)
    taumin = Column(Float(asdecimal=True), nullable=False, index=True)
    taumax = Column(Float(asdecimal=True), nullable=False, index=True)
    seeingmin = Column(Float(asdecimal=True), nullable=False, index=True)
    seeingmax = Column(Float(asdecimal=True), nullable=False, index=True)
    priority = Column(INTEGER(11), nullable=False)
    telescope = Column(String(16), nullable=False, index=True)
    moonmax = Column(INTEGER(11), nullable=False, index=True)
    cloudmax = Column(INTEGER(11), nullable=False, index=True)
    timeest = Column(Float(asdecimal=True), nullable=False, index=True)
    title = Column(String(255))
    datemin = Column(DateTime, nullable=False, index=True)
    datemax = Column(DateTime, nullable=False, index=True)
    minel = Column(Float(asdecimal=True))
    maxel = Column(Float(asdecimal=True))
    approach = Column(INTEGER(11))
    moonmin = Column(INTEGER(11), nullable=False, index=True)
    cloudmin = Column(INTEGER(11), nullable=False, index=True)
    skymin = Column(Float(asdecimal=True), nullable=False, index=True)
    skymax = Column(Float(asdecimal=True), nullable=False, index=True)


class msbdone(Base):
    __tablename__ = 'ompmsbdone'
    __table_args__ = {'schema': 'omp'}

    commid = Column(BIGINT(20), primary_key=True, unique=True)
    checksum = Column(String(64), nullable=False)
    status = Column(INTEGER(11), nullable=False)
    projectid = Column(String(32), nullable=False, index=True)
    date = Column(DateTime, nullable=False)
    target = Column(String(64), nullable=False)
    instrument = Column(String(64), nullable=False)
    waveband = Column(String(64), nullable=False)
    comment = Column(LONGTEXT, nullable=False)
    title = Column(String(255))
    userid = Column(String(32))
    msbtid = Column(String(32), index=True)


class obs(Base):
    __tablename__ = 'ompobs'
    __table_args__ = {'schema': 'omp'}

    msbid = Column(INTEGER(11), nullable=False, index=True)
    projectid = Column(String(32), nullable=False, index=True)
    instrument = Column(String(32), nullable=False, index=True)
    type = Column(String(32), nullable=False)
    pol = Column(TINYINT(4), nullable=False)
    wavelength = Column(Float(asdecimal=True), nullable=False)
    disperser = Column(String(32))
    coordstype = Column(String(32), nullable=False)
    target = Column(String(32), nullable=False)
    ra2000 = Column(Float(asdecimal=True))
    dec2000 = Column(Float(asdecimal=True))
    el1 = Column(Float(asdecimal=True))
    el2 = Column(Float(asdecimal=True))
    el3 = Column(Float(asdecimal=True))
    el4 = Column(Float(asdecimal=True))
    el5 = Column(Float(asdecimal=True))
    el6 = Column(Float(asdecimal=True))
    el7 = Column(Float(asdecimal=True))
    el8 = Column(Float(asdecimal=True))
    timeest = Column(Float(asdecimal=True), nullable=False)
    obsid = Column(BIGINT(20), primary_key=True)


class obslog(Base):
    __tablename__ = 'ompobslog'
    __table_args__ = {'schema': 'omp'}

    obslogid = Column(BIGINT(20), primary_key=True, unique=True)
    runnr = Column(INTEGER(11), nullable=False)
    instrument = Column(String(32), nullable=False)
    telescope = Column(String(32))
    date = Column(DateTime, nullable=False)
    obsactive = Column(INTEGER(11), nullable=False)
    commentdate = Column(DateTime, nullable=False)
    commentauthor = Column(String(32), nullable=False)
    commenttext = Column(LONGTEXT)
    commentstatus = Column(INTEGER(11), nullable=False)
    obsid = Column(String(48), index=True)


class proj(Base):
    __tablename__ = 'ompproj'
    __table_args__ = {'schema': 'omp'}

    projectid = Column(String(32), primary_key=True, unique=True)
    pi = Column(String(32), nullable=False)
    title = Column(String(255))
    semester = Column(String(10), nullable=False, index=True)
    encrypted = Column(String(20), nullable=False)
    allocated = Column(Float(asdecimal=True), nullable=False, index=True)
    remaining = Column(Float(asdecimal=True), nullable=False, index=True)
    pending = Column(Float(asdecimal=True), nullable=False, index=True)
    telescope = Column(String(16), nullable=False, index=True)
    taumin = Column(Float(asdecimal=True), nullable=False)
    taumax = Column(Float(asdecimal=True), nullable=False)
    seeingmin = Column(Float(asdecimal=True), nullable=False)
    seeingmax = Column(Float(asdecimal=True), nullable=False)
    cloudmax = Column(INTEGER(11), nullable=False)
    state = Column(TINYINT(4), nullable=False)
    cloudmin = Column(INTEGER(11), nullable=False)
    skymin = Column(Float(asdecimal=True), nullable=False)
    skymax = Column(Float(asdecimal=True), nullable=False)


class projaffiliation(Base):
    __tablename__ = 'ompprojaffiliation'
    __table_args__ = (
        Index('ompprojaffiliation_proj_aff', 'projectid', 'affiliation', unique=True),
        {'schema': 'omp'}
    )

    projectid = Column(String(32), primary_key=True, nullable=False)
    affiliation = Column(String(32), primary_key=True, nullable=False)
    fraction = Column(Float(asdecimal=True), nullable=False)


class projqueue(Base):
    __tablename__ = 'ompprojqueue'
    __table_args__ = {'schema': 'omp'}

    uniqid = Column(BIGINT(20), primary_key=True)
    projectid = Column(String(32), nullable=False, index=True)
    country = Column(String(32), nullable=False, index=True)
    tagpriority = Column(INTEGER(11), nullable=False, index=True)
    isprimary = Column(TINYINT(4), nullable=False)
    tagadj = Column(INTEGER(11), nullable=False, index=True)


class projuser(Base):
    __tablename__ = 'ompprojuser'
    __table_args__ = (
        Index('idx_ompprojuser_2', 'projectid', 'userid', 'capacity', unique=True),
        {'schema': 'omp'}
    )

    uniqid = Column(BIGINT(20), primary_key=True, unique=True)
    projectid = Column(String(32), nullable=False)
    userid = Column(String(32), nullable=False)
    capacity = Column(String(16), nullable=False)
    contactable = Column(TINYINT(4), nullable=False)
    capacity_order = Column(TINYINT(3), nullable=False, server_default=text("0"))
    affiliation = Column(String(32))


t_ompsciprog = Table(
    'ompsciprog', metadata,
    Column('projectid', String(32), nullable=False),
    Column('timestamp', INTEGER(11), nullable=False),
    Column('sciprog', LONGTEXT, nullable=False),
    schema='omp'
)


class shiftlog(Base):
    __tablename__ = 'ompshiftlog'
    __table_args__ = {'schema': 'omp'}

    shiftid = Column(BIGINT(20), primary_key=True, unique=True)
    date = Column(DateTime, nullable=False)
    author = Column(String(32), nullable=False)
    telescope = Column(String(32), nullable=False)
    text = Column(LONGTEXT, nullable=False)


class timeacct(Base):
    __tablename__ = 'omptimeacct'
    __table_args__ = {'schema': 'omp'}

    date = Column(DateTime, primary_key=True, nullable=False)
    projectid = Column(String(32), primary_key=True, nullable=False)
    timespent = Column(INTEGER(11), nullable=False)
    confirmed = Column(TINYINT(4), nullable=False)
    shifttype = Column(String(70), primary_key=True, nullable=False, server_default=text("''"))
    comment = Column(Text)


t_omptle = Table(
    'omptle', metadata,
    Column('target', String(32), nullable=False, unique=True),
    Column('el1', Float(asdecimal=True), nullable=False),
    Column('el2', Float(asdecimal=True), nullable=False),
    Column('el3', Float(asdecimal=True), nullable=False),
    Column('el4', Float(asdecimal=True), nullable=False),
    Column('el5', Float(asdecimal=True), nullable=False),
    Column('el6', Float(asdecimal=True), nullable=False),
    Column('el7', Float(asdecimal=True), nullable=False),
    Column('el8', Float(asdecimal=True), nullable=False),
    Column('retrieved', DateTime, nullable=False),
    schema='omp'
)


class user(Base):
    __tablename__ = 'ompuser'
    __table_args__ = {'schema': 'omp'}

    userid = Column(String(32), primary_key=True, unique=True)
    uname = Column(String(255), nullable=False)
    email = Column(String(64))
    alias = Column(String(32))
    cadcuser = Column(String(20))
    obfuscated = Column(TINYINT(4), nullable=False, server_default=text("0"))
    no_fault_cc = Column(TINYINT(4), nullable=False, server_default=text("0"))
