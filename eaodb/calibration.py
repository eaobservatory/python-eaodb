# coding: utf-8
from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, String, TIMESTAMP, text
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class chosenobs(Base):
    __tablename__ = 'chosenobs'
    __table_args__ = (
        Index('uc_obsid_subsysnr_purpose', 'obsid', 'subsysnr', 'purpose', unique=True),
        {'schema': 'calibration'}
    )

    id = Column(INTEGER(11), primary_key=True)
    obsid = Column(String(30))
    subsysnr = Column(INTEGER(11))
    purpose = Column(String(30))


class loginfo(Base):
    __tablename__ = 'loginfo'
    __table_args__ = (
        Index('logsource', 'logsource', 'sourceid', unique=True),
        {'schema': 'calibration'}
    )

    id = Column(INTEGER(11), primary_key=True)
    logsource = Column(String(20), nullable=False)
    sourceid = Column(INTEGER(11), nullable=False)
    updated = Column(TIMESTAMP, nullable=False, server_default=text("current_timestamp()"))


class calstats(Base):
    __tablename__ = 'calstats'
    __table_args__ = {'schema': 'calibration'}

    id = Column(INTEGER(11), primary_key=True)
    loginfo_id = Column(ForeignKey('calibration.loginfo.id', ondelete='CASCADE'), nullable=False, index=True)
    obsid = Column(String(30))
    ut = Column(DateTime)
    obsnum = Column(INTEGER(11))
    targetname = Column(String(30))
    mode = Column(String(20))
    filter = Column(INTEGER(11))
    elevation = Column(Float(asdecimal=True))
    airmass = Column(Float(asdecimal=True))
    trans = Column(Float(asdecimal=True))
    tau225 = Column(Float(asdecimal=True))
    tau = Column(Float(asdecimal=True))
    flux_ap = Column(Float(asdecimal=True))
    err_ap = Column(Float(asdecimal=True))
    noise = Column(Float(asdecimal=True))
    peak_obs = Column(Float(asdecimal=True))
    peak_fit = Column(Float(asdecimal=True))
    fcfasec = Column(Float(asdecimal=True))
    fcfasec_err = Column(Float(asdecimal=True))
    fcfbeam = Column(Float(asdecimal=True))
    fcfbeam_err = Column(Float(asdecimal=True))
    fcfmatch = Column(Float(asdecimal=True))
    fcfmatch_err = Column(Float(asdecimal=True))
    fwhmmain = Column(Float(asdecimal=True))
    error_beam = Column(Float(asdecimal=True))
    grouptype = Column(String(10))

    loginfo = relationship('loginfo')


class efficiency(Base):
    __tablename__ = 'efficiency'
    __table_args__ = {'schema': 'calibration'}

    id = Column(INTEGER(11), primary_key=True)
    loginfo_id = Column(ForeignKey('calibration.loginfo.id', ondelete='CASCADE'), nullable=False, index=True)
    obsid = Column(String(30))
    ut = Column(DateTime)
    obsnum = Column(INTEGER(11))
    instrument = Column(String(30))
    inttime = Column(Float(asdecimal=True))
    airmass = Column(Float(asdecimal=True))
    tau = Column(Float(asdecimal=True))
    file = Column(String(30))
    planet = Column(String(30))
    filter = Column(Float(asdecimal=True))
    flux_in_beam = Column(Float(asdecimal=True))
    brightness_temp = Column(Float(asdecimal=True))
    semidiameter = Column(Float(asdecimal=True))
    beamwidth = Column(Float(asdecimal=True))
    mean_tstara = Column(Float(asdecimal=True))
    sigma_tstara = Column(Float(asdecimal=True))
    eta_mb = Column(Float(asdecimal=True))
    eta_ap = Column(Float(asdecimal=True))
    grouptype = Column(String(10))

    loginfo = relationship('loginfo')


class mapstats(Base):
    __tablename__ = 'mapstats'
    __table_args__ = {'schema': 'calibration'}

    id = Column(INTEGER(11), primary_key=True)
    loginfo_id = Column(ForeignKey('calibration.loginfo.id', ondelete='CASCADE'), nullable=False, index=True)
    obsid = Column(String(30))
    ut = Column(DateTime)
    obsnum = Column(INTEGER(11))
    targetname = Column(String(30))
    mode = Column(String(20))
    filter = Column(INTEGER(11))
    elevation = Column(Float(asdecimal=True))
    airmass = Column(Float(asdecimal=True))
    trans = Column(Float(asdecimal=True))
    tau225 = Column(Float(asdecimal=True))
    tau = Column(Float(asdecimal=True))
    t_elapsed = Column(Float(asdecimal=True))
    t_exp = Column(Float(asdecimal=True))
    rms = Column(Float(asdecimal=True))
    rms_units = Column(String(10))
    nefd = Column(Float(asdecimal=True))
    nefd_units = Column(String(20))
    ra = Column(String(20))
    dec_ = Column(String(20))
    mapsize = Column(Float(asdecimal=True))
    pixscale = Column(Float(asdecimal=True))
    project = Column(String(10))
    recipe = Column(String(30))
    filename = Column(String(30))
    grouptype = Column(String(10))

    loginfo = relationship('loginfo')


class nefd(Base):
    __tablename__ = 'nefd'
    __table_args__ = {'schema': 'calibration'}

    id = Column(INTEGER(11), primary_key=True)
    loginfo_id = Column(ForeignKey('calibration.loginfo.id', ondelete='CASCADE'), nullable=False, index=True)
    obsid = Column(String(30))
    ut = Column(DateTime)
    obsnum = Column(INTEGER(11))
    targetname = Column(String(30))
    mode = Column(String(20))
    filter = Column(INTEGER(11))
    elevation = Column(Float(asdecimal=True))
    tau225 = Column(Float(asdecimal=True))
    tau = Column(Float(asdecimal=True))
    nefd = Column(Float(asdecimal=True))
    zenith_nefd = Column(Float(asdecimal=True))
    effective_nefd = Column(Float(asdecimal=True))
    nbol = Column(INTEGER(11))
    grouptype = Column(String(10))

    loginfo = relationship('loginfo')


class noise(Base):
    __tablename__ = 'noise'
    __table_args__ = {'schema': 'calibration'}

    id = Column(INTEGER(11), primary_key=True)
    loginfo_id = Column(ForeignKey('calibration.loginfo.id', ondelete='CASCADE'), nullable=False, index=True)
    obsid = Column(String(30))
    ut = Column(DateTime)
    obsnum = Column(INTEGER(11))
    targetname = Column(String(30))
    mode = Column(String(20))
    filter = Column(INTEGER(11))
    elevation = Column(Float(asdecimal=True))
    tau225 = Column(Float(asdecimal=True))
    tau = Column(Float(asdecimal=True))
    sigma = Column(Float(asdecimal=True))
    grouptype = Column(String(10))
    file = Column(String(50))

    loginfo = relationship('loginfo')


class noisestats(Base):
    __tablename__ = 'noisestats'
    __table_args__ = {'schema': 'calibration'}

    id = Column(INTEGER(11), primary_key=True)
    loginfo_id = Column(ForeignKey('calibration.loginfo.id', ondelete='CASCADE'), nullable=False, index=True)
    obsid = Column(String(30))
    ut = Column(DateTime)
    obsnum = Column(INTEGER(11))
    exp_time = Column(Float(asdecimal=True))
    airmass = Column(Float(asdecimal=True))
    tau = Column(Float(asdecimal=True))
    file = Column(String(30))
    median_tsys = Column(Float(asdecimal=True))
    rms_baseline = Column(Float(asdecimal=True))
    rms_mean = Column(Float(asdecimal=True))
    grouptype = Column(String(10))

    loginfo = relationship('loginfo')


class receptor(Base):
    __tablename__ = 'receptor'
    __table_args__ = {'schema': 'calibration'}

    id = Column(INTEGER(11), primary_key=True)
    loginfo_id = Column(ForeignKey('calibration.loginfo.id'), nullable=False, index=True)
    obsid_subsysnr = Column(String(30))
    hybrid = Column(INTEGER(11))
    transition = Column(String(20))
    molecule = Column(String(2))
    bandwidth = Column(String(20))
    receptor = Column(String(10))
    restfreq = Column(Float(asdecimal=True))
    tsys = Column(Float(asdecimal=True))
    rms = Column(Float(asdecimal=True))

    loginfo = relationship('loginfo')


class removedobs(Base):
    __tablename__ = 'removedobs'
    __table_args__ = {'schema': 'calibration'}

    id = Column(INTEGER(11), primary_key=True)
    loginfo_id = Column(ForeignKey('calibration.loginfo.id', ondelete='CASCADE'), index=True)
    obsid_subsysnr = Column(String(30))
    utdate = Column(INTEGER(11))
    obsnum = Column(INTEGER(11))
    subsys = Column(INTEGER(11))

    loginfo = relationship('loginfo')


class standard(Base):
    __tablename__ = 'standard'
    __table_args__ = {'schema': 'calibration'}

    id = Column(INTEGER(11), primary_key=True)
    loginfo_id = Column(ForeignKey('calibration.loginfo.id', ondelete='CASCADE'), nullable=False, index=True)
    obsid = Column(String(30))
    ut = Column(DateTime)
    obsnum = Column(INTEGER(11))
    subsys = Column(INTEGER(11))
    file = Column(String(30))
    instrument = Column(String(30))
    lofreq = Column(Float(asdecimal=True))
    targetname = Column(String(30))
    molecule = Column(String(10))
    line = Column(String(20))
    mode = Column(String(10))
    bandwidth = Column(String(20))
    sideband = Column(String(3))
    tau = Column(Float(asdecimal=True))
    elevation = Column(Float(asdecimal=True))
    integint = Column(Float(asdecimal=True))
    peak = Column(Float(asdecimal=True))
    l_bound = Column(Float(asdecimal=True))
    h_bound = Column(Float(asdecimal=True))
    grouptype = Column(String(10))
    integ_percent = Column(Float(asdecimal=True))
    peak_percent = Column(Float(asdecimal=True))

    loginfo = relationship('loginfo')
