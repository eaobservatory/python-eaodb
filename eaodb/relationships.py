# coding: utf-8
from sqlalchemy.orm import relationship, column_property, foreign, remote, object_session
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import select, outerjoin, func, case, and_, text
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import joinedload, backref
from collections import OrderedDict, namedtuple
import decimal


# Tidy this up better?
try:
    from . import jcmt, omp, jsa_proc, calibration
    from constants import MSBDONESTATUS, FEEDBACKSTATUS, OMPState, Bands
except ImportError:
    from eaodb import jcmt, omp, jsa_proc, calibration
    from eaodb.constants import MSBDONESTATUS, FEEDBACKSTATUS, OMPState, Bands



""" This file extends the auto-generated database classes for the
OMP/JCMT etc database tables to include the foreign relationships
between them, and also to provide convenience functions."""

ACSIS_CALTABLES = ('efficiency','noisestats', 'receptor', 'standard')
SCUBA2_CALTABLES = ('calstats', 'nefd', 'noise')

# calstats, nefd, noise: GROUPTYPE OBS, obsid, filter


# Need obsid_subsysnr in efficiency, noisestats, standard.
# receptor has it already.




# Note that this is not correct for everything in the OMP: some have an
# older form that uses the obsid?
PREVIEW_FORMAT = 'jcmt{instletter}{utdate}_{:05d}_{subsys}_reduced_obs_000_preview_64.png'
OLD_PREVIEW_FORMAT_ACSIS='jcmt_{obsid}_reduced-{freq}-{bwmode}-{subsys}_preview_64.png'
OLD_PREVIEW_FORMAT_SCUBA2='jcmt_{obsid}_reduced-{subsys}_preview_64.png'

# How far away from the observation timestamp do we allow the WVM to
# have been taken from. (in seconds)
_TIMESTAMP_OFFSET_ALLOWANCE = 2 * 60




# Note the names of these classes must be different from the ones
# defined in jcmt/omp etc, or extend_existing must be True, and then the
# obsid, obsid_subsysnr have to be redefined and it will complain.
class FILES(jcmt.FILES):
    __tablename__ = 'FILES'
    __table_args__ = (
        {'schema':'jcmt', 'extend_existing':True}
    )

    def __repr__(self):
        return "<{}({})>".format(self.__class__.__name__, self.file_id)

class JsaProcJob(jsa_proc.job):
    __tablename__ = 'job'
    __table_args__ = (
        {'schema':'jsa_proc', 'extend_existing':False})
    outputs = relationship(jsa_proc.output_file,
                           primaryjoin=jsa_proc.job.id==jsa_proc.output_file.job_id,
                           foreign_keys=[jsa_proc.output_file.job_id])
    previews = relationship(jsa_proc.output_file,
                              primaryjoin=and_(jsa_proc.job.id==jsa_proc.output_file.job_id,
                                        jsa_proc.output_file.filename.like("%obs%256%.png")),
                              foreign_keys=[jsa_proc.output_file.job_id])



class Scuba2(jcmt.SCUBA2):

    __tablename__ = 'SCUBA2'
    __table_args__ = (
        {'schema':'jcmt', 'extend_existing':False}
    )
    files = relationship(FILES,
                         primaryjoin=jcmt.SCUBA2.obsid_subsysnr==foreign(FILES.obsid_subsysnr),
                         foreign_keys=[FILES.obsid_subsysnr],
                         order_by=FILES.nsubscan)

    processing_jobs = relationship(JsaProcJob,
                                   secondary=jsa_proc.obsidss.__table__,
                                   primaryjoin=jcmt.SCUBA2.obsid_subsysnr==foreign(jsa_proc.obsidss.obsid_subsysnr),
                                   secondaryjoin=and_(
                                       foreign(jsa_proc.obsidss.job_id)==remote(jsa_proc.job.id),
                                       jsa_proc.job.task.in_(['jcmt-nightly', 'jcmt-reproc'])),
                               )
    def get_previewname(self, obs):
        return PREVIEW_FORMAT.format(obs.obsnum,
                                     instletter='s',
                                     utdate=obs.utdate,
                                     subsys=self.filter)

    def __repr__(self):
        return "<{}({})>".format(self.__class__.__name__, self.obsid_subsysnr)

class Acsis(jcmt.ACSIS):

    __tablename__ = 'ACSIS'
    __table_args__ = (
        {'schema':'jcmt', 'extend_existing':False}
    )
    files = relationship(FILES,
                         primaryjoin=jcmt.ACSIS.obsid_subsysnr==foreign(FILES.obsid_subsysnr),
                         foreign_keys=[FILES.obsid_subsysnr],
                         order_by = FILES.nsubscan)

    processing_jobs = relationship(JsaProcJob,
                                   secondary=jsa_proc.obsidss.__table__,
                                   primaryjoin=jcmt.ACSIS.obsid_subsysnr==foreign(jsa_proc.obsidss.obsid_subsysnr),
                                   secondaryjoin=and_(
                                       foreign(jsa_proc.obsidss.job_id)==remote(jsa_proc.job.id),
                                       jsa_proc.job.task=='jcmt-nightly'),
                               )
    def get_previewname(self, obs):
        return PREVIEW_FORMAT.format(obs.obsnum,
                                     instletter='h',
                                     utdate=obs.utdate,
                                     subsys='{:02d}'.format(self.subsysnr))
    def __repr__(self):
        return "<{}({})>".format(self.__class__.__name__,
                                 self.obsid_subsysnr)


# HELPER FUNCTIONS FOR Obs Class
# Select function to get the latest obslog comment.
latest_obslog = select([func.max(omp.obslog.obslogid).label('max_obslogid'),
                            omp.obslog.obsid]
                           ).group_by(omp.obslog.obsid).alias('latest_obslog')

# Need to return 0 for status of  observations with no comments.
def commentstatus_getset_factory(collection_type, proxy):
    def getter(obj):
        if obj is None:
            return OMPState.get_name(0)
        return OMPState.get_name(getattr(obj, proxy.value_attr))
    def setter(obj, value):
        setattr(obj, proxy.value_attr, value)
    return getter, setter




class Obs(jcmt.COMMON):
    __tablename__ = 'COMMON'
    __table_args__ = (
        {'schema':'jcmt', 'extend_existing':False}
    )

    duration = column_property(func.timestampdiff(text('SECOND'),
                               jcmt.COMMON.date_obs, jcmt.COMMON.date_end))
    scanmode = column_property(case([(jcmt.COMMON.sam_mode=='scan', jcmt.COMMON.scan_pat)],
                                        else_=jcmt.COMMON.sam_mode))
    scuba2 = relationship(Scuba2, primaryjoin=jcmt.COMMON.obsid==Scuba2.obsid,
                          foreign_keys=[Scuba2.obsid],
                          order_by = Scuba2.obsid_subsysnr)
    acsis = relationship(Acsis, primaryjoin=jcmt.COMMON.obsid==Acsis.obsid,
                         foreign_keys=[Acsis.obsid],
                         order_by = Acsis.obsid_subsysnr)


    obslog_comments = relationship(omp.obslog,
                                   primaryjoin=jcmt.COMMON.obsid==omp.obslog.obsid,
                                   foreign_keys=[omp.obslog.obsid],
                                   order_by=omp.obslog.obslogid)

    latest_ompcomment = relationship(omp.obslog,
                                     secondary=latest_obslog,
                                     primaryjoin=latest_obslog.c.obsid==jcmt.COMMON.obsid,
                                     secondaryjoin=latest_obslog.c.max_obslogid==omp.obslog.obslogid,
                                     uselist=False, viewonly=True, lazy='joined')

    ompstatus = association_proxy('latest_ompcomment', 'commentstatus',
                                      getset_factory=commentstatus_getset_factory)


    @hybrid_property
    def instrument(self):
        if self.instrume == 'SCUBA-2':
            if self.inbeam and 'pol' in self.inbeam:
                if 'fts' not in self.inbeam:
                    return 'POL-2'
                else:
                    return 'POL-2-FTS-2'
            elif self.inbeam and 'fts' in self.inbeam:
                return 'FTS-2'
        if self.inbeam != None and self.inbeam != 'shutter':
            return self.instrume + '-'+self.inbeam
        return self.instrume

    @instrument.expression
    def instrument(cls):
        return case([ (and_(jcmt.COMMON.instrume=='SCUBA-2',
                     jcmt.COMMON.inbeam.like('%pol%'),
                     jcmt.COMMON.inbeam.notlike('%fts%')),
                     'POL-2'),
                (and_(jcmt.COMMON.instrume=='SCUBA-2',\
                      jcmt.COMMON.inbeam.notlike('%pol%'),
                      jcmt.COMMON.inbeam.like('%fts%')),
                     'FTS-2'),
                (and_(jcmt.COMMON.instrume=='SCUBA-2',
                      jcmt.COMMON.inbeam.like('%pol%'),
                      jcmt.COMMON.inbeam.like('%fts%')),
                     'POL-2-FTS-2'),
                (and_(jcmt.COMMON.inbeam != None),
                     jcmt.COMMON.instrume + jcmt.COMMON.inbeam),
                   ],
            else_=jcmt.COMMON.instrume)



    def get_processing_links(self):
        values = []
        for subsys in self._inst_info:
            procjob = next((s for s in subsys.processing_jobs), None)
            if procjob:
                values.append((procjob.id, subsys.get_previewname(self)))
            else:
                values.append([])
        return values

    @property
    def _inst_info(self):
        if self.backend=='SCUBA-2':
            return self.scuba2
        else:
            return self.acsis

    @property
    def log_mode(self):
        objects = []
        if self.obs_type != 'science':
            objects+=[self.obs_type]
        if self.scan_pattern:
            objects += [self.scan_pattern]
        elif self.sam_mode:
            objects += [self.sam_mode]
        if self.sw_mode and self.sw_mode not in['none','self', 'spin']:
            objects += [self.sw_mode]
        return '_'.join(objects)

    @property
    def scan_pattern(self):
        if self.scan_pat == 'DISCRETE_BOUSTROPHEDON':
            scan_pattern = 'raster'
        elif self.scan_pat == 'CV_DAISY':
            if self.instrument == 'POL-2':
                scan_pattern = 'pol-daisy'
            else:
                scan_pattern = 'daisy'
        elif self.scan_pat == 'CURVY_PONG':
            scan_pattern = 'pong-{:.0f}'.format(self.map_wdth)
        else:
            scan_pattern = self.scan_pat

        return scan_pattern

    # These could be turned into column_property objects if performance demands...
    @property
    def avwvm(self):
        """
        The average JCMT WVM

        Returns NONE if start or end value is more than 2 minutes from
        start or end of observation, or start or end value is None.
        """
        if  self.wvmtauen and self.wvmtaust and self.wvmdatst and self.wvmdaten and \
            abs((self.wvmdatst - self.date_obs).total_seconds()) <= _TIMESTAMP_OFFSET_ALLOWANCE \
            and \
            abs((self.wvmdaten - self.date_end).total_seconds()) <= _TIMESTAMP_OFFSET_ALLOWANCE:

            return (self.wvmtauen + self.wvmtaust)/decimal.Decimal(2.0)
        else:
            return None

    @property
    def avseeing(self):
        """
        The average JCMT seeing

        Returns NONE if start or end value is more than 2 minutes from
        start or end of observation, or start or end value is None.
        """
        if  self.seeingen and self.seeingst and self.seedatst and self.seedaten and \
            abs((self.seedatst - self.date_obs).total_seconds()) <= _TIMESTAMP_OFFSET_ALLOWANCE and \
            abs((self.seedaten - self.date_end).total_seconds()) <= _TIMESTAMP_OFFSET_ALLOWANCE:

            return (self.seeingen + self.seeingst)/decimal.Decimal(2.0)
        else:
            return None

    @property
    def band(self):
        """ Weather band based on average JCMT WVM"""
        if self.avwvm:
            return Bands.get_band(self.avwvm)
        else:
            return None

    @property
    def results(self):
        """ Get any results ingested into the calibration database"""
        results = {}
        if self.backend == 'SCUBA-2':
            tables = SCUBA2_CALTABLES
        else:
            tables = ACSIS_CALTABLES
        for tabname in tables:
            table = getattr(calibration, tabname)
            if tabname != 'receptor':
                q = object_session(self).query(table).filter(table.obsid==self.obsid).filter(table.grouptype=='OBS')
            else:
                obsid_subsysnrs = [i.obsid_subsysnr for i in self.acsis]
                q = object_session(self).query(table).filter(table.obsid_subsysnr.in_(obsid_subsysnrs))
            q = q.join(calibration.loginfo, table.loginfo_id==calibration.loginfo.id)
            q = q.filter(calibration.loginfo.logsource.in_(['jsaproc-jcmt-nightly', 'jsaproc-jcmt-reproc']))
            results[tabname] = q.all()
        return results
            

    def __repr__(self):
        return "<{}({}: {}/{}/{}/{})>".format(self.__class__.__name__,self.obsid,
                                              self.ompstatus, self.instrument,
                                                  self.obs_type, self.object)
                            
class ProjUser(omp.projuser):

    __tablename__ = 'ompprojuser'
    __table_args__ = (
        {'schema':'omp', 'extend_existing':True})

    user = relationship(omp.user,
                         primaryjoin=omp.projuser.userid==omp.user.userid,
                         foreign_keys=[omp.user.userid], uselist=False,
                        lazy='joined')

    def __repr__(self):
        return "<{}({}: {})>".format(self.__class__.__name__, self.user.uname, self.capacity)


class ProjQueue(omp.projqueue):

    __tablename__ = 'ompprojqueue'
    __table_args__ = (
        {'schema':'omp', 'extend_existing':True})

    def __repr__(self):
        return "<{}({}: {}+{})>".format(self.__class__.__name__,
                                        self.country, self.tagpriority, self.tagadj)

class ObsMSB(omp.obs):
    __tablename__ = 'ompobs'
    __table_args__ = (
        {'schema':'omp', 'extend_existing':True})

    @property
    def full_instrument(self):
        if self.instrument=='SCUBA-2' and self.pol==1:
            return 'POL-2'
        else:
            return self.instrument
    def __repr__(self):
        return "<{}({}: {} {})>".format(self.__class__.__name__, self.target, self.full_instrument)

    
class MSBScheduled(omp.msb):
    __tablename__ = 'ompmsb'
    __table_args__ = (
        {'schema':'omp', 'extend_existing':True})

    plannedobs = relationship(ObsMSB,
                              primaryjoin=omp.msb.msbid==omp.obs.msbid,
                                foreign_keys=omp.obs.msbid)
    def __repr__(self):
        return "<{}({}: {} {})>".format(self.__class__.__name__, self.projectid, self.title,
                                           self.remaining)

    
class MSBDone(omp.msbdone):
    __tablename__ = 'ompmsbdone'
    __table_args__ = (
        {'schema':'omp', 'extend_existing':True})

    observations = relationship(Obs,
                              primaryjoin=omp.msbdone.msbtid==Obs.msbtid,
                                foreign_keys=Obs.msbtid)

    @property
    def statustext(self):
        return MSBDONESTATUS.get(self.status, 'UNKNOWN')

    def __repr__(self):
        return "<{}({}: {}/{} {})>".format(self.__class__.__name__, self.projectid, self.title,
                                           self.target, MSBDONESTATUS.get(self.status, '??'))

class TimeAcct(omp.timeacct):
    __tablename__ = 'omptimeacct'
    __table_args__ = (
        {'schema':'omp', 'extend_existing':True})
    def __repr__(self):
        return '<{}( {}/{}/{}/{:.1f} hrs>'.format(self.__class__.__name__,
                                                  self.projectid,
                                                  self.date.strftime('%Y-%m-%d') if self.date else '?',
                                                  self.shifttype if self.shifttype else '?',
                                                  self.timespent/(60.0*60.0))
class Feedback(omp.feedback):
    __tablename__ = 'ompfeedback'
    __table_args__ = (
        {'schema':'omp', 'extend_existing':True})

    def __repr__(self):
        return '<{}( {}/{}: {}/{} >'.format(self.__class__.__name__,
                                                  self.projectid,
                                                  self.date.strftime('%Y-%m-%d') if self.date else '?',
                                                  FEEDBACKSTATUS.get(self.status, 'UNKNOWN'),
                                                  self.subject.replace('\n', ''))


msbdone_summary = namedtuple('MSBDoneSummary', 'checksum status title instrument waveband target projectid msb_count observationcount') 

class Project(omp.proj):
    __tablename__ = 'ompproj'
    __table_args__ = (
        {'schema':'omp', 'extend_existing':False}
    )

    observations = relationship(Obs,
                                primaryjoin=omp.proj.projectid==jcmt.COMMON.project,
                                foreign_keys=[jcmt.COMMON.project],
                                order_by=jcmt.COMMON.date_obs)
    projusers = relationship(ProjUser,
                         primaryjoin=omp.proj.projectid==ProjUser.projectid,
                         foreign_keys=[ProjUser.projectid],
                             order_by=[ProjUser.capacity.desc(),ProjUser.capacity_order.asc()],
                             lazy='joined')
    queueinfo = relationship(ProjQueue,
                          primaryjoin=omp.proj.projectid==omp.projqueue.projectid,
                          foreign_keys=[omp.projqueue.projectid],
                          lazy='joined')

    completion = column_property(100*(omp.proj.allocated-(omp.proj.remaining - omp.proj.pending))/omp.proj.allocated)
    used = column_property(omp.proj.allocated - (omp.proj.remaining - omp.proj.pending))

    timecharged = relationship(TimeAcct,
                               primaryjoin=omp.proj.projectid==omp.timeacct.projectid,
                               foreign_keys=[omp.timeacct.projectid],
                               order_by=omp.timeacct.date, backref=backref("project", uselist=False))

    faults = relationship(omp.fault,
                          secondary=omp.faultassoc.__table__,
                          primaryjoin=omp.proj.projectid==omp.faultassoc.projectid,
                          secondaryjoin=omp.fault.faultid==omp.faultassoc.faultid,
                          foreign_keys=[omp.faultassoc.projectid, omp.fault.faultid])
    
    msbs_done = relationship(MSBDone,
                            primaryjoin=omp.proj.projectid==omp.msbdone.projectid,
                             foreign_keys = omp.msbdone.projectid,
                             order_by=omp.msbdone.date)

    msbs_scheduled = relationship(MSBScheduled,
                                  primaryjoin=omp.proj.projectid==omp.msb.projectid,
                                  foreign_keys=[omp.msb.projectid])

    feedback = relationship(Feedback,
                            primaryjoin=omp.proj.projectid==omp.feedback.projectid,
                            foreign_keys=[omp.feedback.projectid],
                            order_by=omp.feedback.date)

    def get_msb_done_summary(self):
        """ Return a summary of the msbs done, with observation counts."""

        # Handle large number of results by breaking it down into separate queries with no join.
        msbids, obsids = zip(*object_session(self).query(Obs.msbid, func.count(Obs.obsid).label('obscount')).filter(Obs.project==self.projectid).filter(Obs.msbid!='CAL').filter(Obs.obs_type=='science').group_by(Obs.msbid).all())
        obscount_dict = dict(zip(msbids, obsids))
        msbquery = object_session(self).query(MSBDone).group_by(MSBDone.checksum, MSBDone.status)
        msbquery = msbquery.add_column(func.count('*').label('msb_count'))
        msbquery = msbquery.filter(MSBDone.projectid==self.projectid)
        msbquery = msbquery.filter(MSBDone.checksum != 'CAL')
        msbquery = msbquery.order_by(MSBDone.title, MSBDone.status)
        msbs = msbquery.all()
        #subquery = select([func.count(jcmt.COMMON.obsid).label('obscount')]).where(jcmt.COMMON.msbid==MSBDone.checksum).where(jcmt.COMMON.project==MSBDone.projectid).where(jcmt.COMMON.obs_type=='science').where(jcmt.COMMON.msbid!='CAL').as_scalar()
        #query = object_session(self).query(MSBDone, subquery).filter(MSBDone.checksum!='CAL')
        #query = query.add_column(subquery.c.obscount)
        #query = query.group_by(MSBDone.checksum, MSBDone.status)
        #query = query.add_column(func.count('*').label('msb_count'))
        #query = query.filter(MSBDone.projectid==self.projectid)
        #query = query.order_by(MSBDone.title, MSBDone.status)
        #results = query.limit(500).all()
        if len(msbs) > 0:
            results  = [msbdone_summary(*(i[0].checksum, i[0].status, i[0].title, i[0].instrument, i[0].waveband, i[0].target, i[0].projectid, i[1], obscount_dict.get(i[0].checksum, 0))) for i in msbs]
            #results = [msbdone_summary(*(i[0].checksum, i[0].status, i[0].title, i[0].instrument, i[0].waveband, i[0].target, i[0].projectid), i[-1], i[-2]) for i in results]
        return results
    
    def __repr__(self):
        return "<{}({})>".format(self.__class__.__name__, self.projectid)

    @property
    def queues(self):
        return [i.country for i in self.queueinfo]

    @property
    def obs_without_msb(self):
        checksums = [i.checksum for i in self.msbs_done]
        return [i for i in self.observations if i.msbid not in checksums]

    @property
    def pis(self):
        return [ i for i in self.projusers if i.capacity=='PI']

    @property
    def fops(self):
        return [i for i in self.projusers if i.capacity=='SUPPORT']

    @property
    def cois(self):
        return [i for i in self.projusers if i.capacity=='COI']

    def get_processing_jobs(self, tasks=['jcmt-nightly'], obsinfo=None, instinfo=None):
        observations = self.observations

        if obsinfo:
            observations = [o for o in observations
                            if has_all_attr(o, obsinfo)]


        if instinfo:
            subsystems = [s for o in observations
                          for s in o._inst_info
                          if has_all_attr(s, instinfo) ]
        else:
            subsystems = [s for o in observations for s in o._inst_info]

        return [i for s in subsystems for i in s.processing_jobs if (i.task in tasks or not tasks)]


    def msbs_repeats(self):
        """
         Get msbs as dictionary with all observations done by msb checksum?.
        """
        msb_checksums = set([i.checksum for i in proj.msbs_done])
        #for i in msb_checksums
        raise NotImplementedError

    def get_dates_obsactivity(self, byshift=False, observations=None):
        """Get the dates where observations happened/time was charged.

        
        Return an ordered dictionary with the keys as days that either observations
        were taken or time was charged (or both).

        The items contain a tuple, first item is lists of times charged
        that day, second item is list of observations.
        """
        print(observations)
        if not observations:

            observations = self.observations
        if not self.timecharged and not observations:
            return None

        timeresults = dict()

        for t in self.timecharged:
            date = t.date.date()
            r = timeresults.get(date, {'all-confirmed': 0.0, 'all-pending': 0.0})
            if t.confirmed:
                r['all-confirmed'] = r['all-confirmed'] + t.timespent/(60.0*60)
            else:
                r['all-pending'] = r['all-pending'] + t.timespent/(60.0*60)

            # Ensure it works if multiple shifts in one night: shouldn't happen, but could.
            if byshift:
                shifttop = r.get('shifts', {})
                shiftr = shifttop.get(t.shifttype, {'pending': 0.0, 'confirmed':0.0})
                if t.confirmed:
                    shiftr['confirmed'] += t.timespent/(60.0*60)
                else:
                    shiftr['pending'] += t.timespent/(60.0*60.)
                if t.comment:
                    shiftr['comment'] = t.comment
                shifttop[t.shifttype] = shiftr
                r['shifts'] = shifttop
            timeresults[date] = r

        # Now for observations: want time spent on sky by ompstatus (and shift? and band?)
        obsresults = dict()
        for o in self.observations:
            date = o.date_obs.date()
            r = obsresults.get(date, {})
            key = (date, o.instrument, o.band, o.ompstatus)
            r[key] = r.get(key, 0.0) + o.duration/(60*60.0)
            obsresults[date] = r

        dates = timeresults.keys() | obsresults.keys()
        results = OrderedDict()
        for d in sorted(list(dates)):
            results[d] = (timeresults.get(d, None), obsresults.get(d, None))
            
        return results


    def get_secondary_jcmt_papers(self, direct_papers):
        """
        Get all secondary JCMT papers that list a direct paper of

        this projecty as the source.
        """
        bibcodes = [i.bibcode for i in direct_papers]
        from eaodb import pigwidgeon as pig
        from sqlalchemy import select, func, alias
        session = self._sa_instance_state.session
        searchid = 1
        JCMT_PAPERTYPES = [i.id for i in session.query(pig.paper_types).filter(
            pig.paper_types.name_.in_(['JCMT Science Paper','JCMT Theory Paper'])).all()]
        BIBCODE_INFOSECTION = [i.id for i in session.query(pig.info_sections).filter(
            pig.info_sections.name_=='Data Source').all()]
        query = session.query(pig.papers)

        query = query.join(pig.comments, pig.papers.id==pig.comments.paper_id)
        query = query.join(pig.info_section_values, pig.info_section_values.comment_id==pig.comments.id)
        query = query.filter(pig.comments.id.in_(select([func.max(pig.comments.id)]).group_by(pig.comments.paper_id)))
        query = query.filter(func.upper(pig.info_section_values.entered_text).in_(bibcodes))
        query = query.filter(pig.comments.search_id==searchid)
        query = query.join(pig.papertype_value, pig.comments.id==pig.papertype_value.comment_id)
        query = query.filter(pig.papertype_value.papertype_id.in_(JCMT_PAPERTYPES))
        query = query.filter(pig.info_section_values.info_section_id.in_(BIBCODE_INFOSECTION))
        query = query.order_by(pig.papers.refereed, pig.papers.pubdate)
        query = query.options(joinedload(pig.papers.authors))
        papers = query.all()
        return papers
    def get_direct_jcmt_papers(self):
        """
        Get JCMT Science/Theory papers where this project is listed as the source of data.
        """
        from eaodb import pigwidgeon as pig
        from sqlalchemy import select, func, alias
        session = self._sa_instance_state.session
        searchid = 1
        JCMT_PAPERTYPES = [i.id for i in session.query(pig.paper_types).filter(
            pig.paper_types.name_.in_(['JCMT Science Paper','JCMT Theory Paper'])).all()]

        PROJECT_INFOSECTIONS = [i.id for i in session.query(pig.info_sections).filter(
            pig.info_sections.name_.in_(["Project Codes (PI/JLS/LAP)",
                                         "Project Codes (archival/other)"])).all()]
        all_projectid = [self.projectid]
        extra_project_names = lap_project_aliases.get(self.projectid, None)
        if extra_project_names:
            all_projectid.append(extra_project_names)
        # Get the values for 
        #c2 = alias(pig.comments)
        #intjoin = select([func.max(pig.comments.id)]).where(
        #    pig.comments.paper_id==pig.papers.id).correlate(pig.papers)
        query = session.query(pig.papers)

        query = query.join(pig.comments, pig.papers.id==pig.comments.paper_id)
        query = query.join(pig.info_section_values, pig.info_section_values.comment_id==pig.comments.id)
        query = query.filter(pig.comments.id.in_(select([func.max(pig.comments.id)]).group_by(pig.comments.paper_id)))
        query = query.filter(func.upper(pig.info_section_values.entered_text).in_(all_projectid))
        query = query.filter(pig.comments.search_id==searchid)
        query = query.join(pig.papertype_value, pig.comments.id==pig.papertype_value.comment_id)
        query = query.filter(pig.papertype_value.papertype_id.in_(JCMT_PAPERTYPES))
        query = query.filter(pig.info_section_values.info_section_id.in_(PROJECT_INFOSECTIONS))
        query = query.order_by(pig.papers.refereed, pig.papers.pubdate)
        query = query.options(joinedload(pig.papers.authors))
        papers = query.all()
        return papers


# Helper function for finding observations matching everything in a dictionary.
def has_all_attr(observation, obsinfo,):
    return all([getattr(observation, o)==obsinfo[o]  for o in obsinfo])





lap_project_aliases = {'M16AL001': ['TRANSIENT',]
                           }

#Group of observations: functions for total time, time in good/questionable/bad/junk,
# time by instrument, time by weather band, (and any combination of those), time by time of night
# Info on requests_band by actual band?

#Groups of time accounting objects: total time by night, total time by shift type, total time by project

# Groups of msbs: availability, plotting tools, also by weather band/queue/project etc.

# Groups of projects: msb avaialbility. Time spent by weatherband/instrument etc (same combos as observations), time charged by shift type, total time charged by queue etc

#( combo of observations and projects -- want time spent only by actual date range, but want info on what queues time was spent on., )

# Faults!!!

#Stats for time range or queue/semester combo, including, faults, 


# Obss: link to jsa_proc processing and links to calibration objects.




# NightLog: obslog, shiftlog and: created, with html output.



# Groups: used to instantiate relationships.

class msbGroup(list):
    
    def totaltime(self):
        pass
    def totalcount(self):
        pass
    def totaltaurange(self):
        pass


class observationGroup(list):
    @property
    def numobs(self):
        return len(self)
    @property
    def timespent(self):
        return sum([i.duration for i in self])

    @property
    def shifttypes(self):
        return set(i.shifttype for i in self)




