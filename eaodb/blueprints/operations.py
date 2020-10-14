"""
Miscellaneous operations related pages.

1) single night report
1a) opsmeeting -- multi night nightreport -- opsmeeting mode
1b) boardreport -- semester.

2) LAP/queue/semester monitoring pages. -- with FOP mode?

3) TAC completion pages (uses Hedwig JSON files)

"""

from flask import Blueprint
from flask_wtf import FlaskForm
from wtforms import  validators
from wtforms.fields.html5 import DateField

import datetime
import pytz

from sqlalchemy import or_, and_
from sqlalchemy.orm import joinedload, selectinload, subqueryload
from collections import namedtuple

from ..timeacct import TimeAcctGroup
from ..tools import observations as obs_tools

from flask import render_template, url_for, flash, redirect, request

from eaodb.webapp import db
from eaodb import omp, calibration
from eaodb.relationships import Obs, Scuba2, Acsis, Project, MSBDone, TimeAcct
from eaodb import timeacct




from eaodb.blueprints.operation_charts import plot_observed_time_by, plot_night_standards, plot_night_fcfs, create_performance_stats

TimeGap = namedtuple('TimeGap', 'date date_end duration status text author obslogid runnr instrument telescope')
WVMFILE="https://omp.eao.hawaii.edu/cgi-bin/get_resource.pl?type=dq-nightly&utdate={}&filename=tau_{}.png"
WVMFILE="https://www.eao.hawaii.edu/weather/opacity/mk/archive/{}.png"
# Define the Blueprint, its static folder and its templates.
ops = Blueprint('ops', 'ops',
                template_folder='templates',
                static_folder='static')

@ops.app_template_filter('timespent')
def timespent(timespent, blank=True):
    if blank:
        if timespent == 0:
            return ''
    return '{:.2f} hrs'.format(timespent)

@ops.app_template_filter('percentspent')
def percentspent(timespent):
    if not timespent:
        timespent = 0
    return '{:.1f}%'.format(timespent)

@ops.app_template_filter('project')
def formatproject(proj, projectinfo=None):

    url = url_for('project.projectpage', projectid=proj)
    title = ""
    if projectinfo:
        try:
            projectobj = next((p for p in projectinfo if p.projectid==proj),None)
        except:
            projectobj = projectinfo
        if projectobj:
            title = '{} ({:.1f}% of {:.1f} hrs)'.format(projectobj.title, projectobj.completion, float(projectobj.allocated)/(60.0*60.0))
    return '<a href={url} title="{title}">{projectid}</a>'.format(url=url,
                                                                  title=title,
                                                                  projectid=proj)

@ops.app_template_filter('comments')
def comments(comments, shifts, days):
    if not comments or len(comments)==0 or len(shifts) > 1 or len(days)>1:
        return ''
    else:
        return '<br>'.join(i for i in comments)


@ops.app_template_filter('timespent_unconfirmed')
def timespent_unconfirmed(timespent):
    if timespent > 0:
        return '({:.2f} unc.)'.format(timespent)
    else:
        return ''
@ops.app_template_filter('obslog_dateformat')
def _temp(x): return obs_tools.obslog_dateformat(x)

@ops.app_template_filter('TIMEGAPSTATUS')
def timegap_status(value):
    return obs_tools.TIMEGAPSTATUS[value]


@ops.route('/project-group')
def project_group():
    # The old LAP pages.
    pass

class NightRepForm(FlaskForm):
   utdate = DateField('UT Date', validators=[validators.required(),])
   end = DateField('End', validators=[validators.optional(),])

class BoardRepForm(FlaskForm):
   start = DateField('Start', validators=[validators.required(),])
   end = DateField('End', validators=[validators.required(),])


@ops.route('/')
def ops_home():
    return render_template('ops_home.html')
@ops.route('/night-search', methods=('POST',))

def nightreport_search():
    form = NightRepForm()
    if not form.validate_on_submit():
        flash(form.errors)
    return redirect(url_for('ops.night_report', utdate=form.utdate.data.strftime('%Y%m%d')))

@ops.route('/boardreport-search', methods=('POST',))
def boardreport_search():
    form = BoardRepForm()
    if not form.validate_on_submit():
        flash(form.errors)
    return redirect(url_for('ops.boardreport', start=form.start.data.strftime('%Y%m%d'), end=form.end.data.strftime('%Y%m%d')))

@ops.route('/report-search', methods=('POST',))
def nightreport_multi_search():
    form = NightRepForm()
    if not form.validate_on_submit():
        flash(form.errors)
    kwargs = {'utdate': form.utdate.data.strftime('%Y%m%d')}
    if form.end.data:
        kwargs['end'] = form.end.data.strftime('%Y%m%d')
    return redirect(url_for('ops.report', **kwargs))


@ops.route('/board-report/')
def boardreport():
    end = request.args.get('end', None, type=str)
    start = request.args.get('start', None, type=str)
    if start and end:
        start = datetime.datetime.strptime(str(start), '%Y%m%d')
        end = datetime.datetime.strptime(str(end), '%Y%m%d')
        # Get board info?
    form = BoardRepForm()
    form.process(start=start, end=end)
    onsky_plots, faultplots, timeacct_plots, weather_plots = create_performance_stats(start, end, db.session)
    return render_template('ops_boardreport.html', form=form, onsky_plots=onsky_plots,
                               faultplots = faultplots,
                               timeacct_plots = timeacct_plots, weather_plots=weather_plots)

@ops.route('/report/')
def report():
    default_end = datetime.datetime.now(pytz.utc).date()
    default_start = default_end  - datetime.timedelta(days=6)
    end = request.args.get('end', default_end.strftime('%Y%m%d'), type=str)
    start = request.args.get('utdate', default_start.strftime('%Y%m%d'), type=str)
    start = datetime.datetime.strptime(str(start), '%Y%m%d')
    end = datetime.datetime.strptime(str(end), '%Y%m%d')
    end += datetime.timedelta(hours=23, minutes=59, seconds=59.9)
    form = NightRepForm()
    form.process(utdate=start, end=end)

    return prepare_night_report(start, end, db.session, showobslog=False, showshift=False, showmsbs=False, form=form)

@ops.route('/timeacct/')
def timeacct_info():
    utdate_default = datetime.datetime.now(pytz.utc).date().strftime('%Y%m%d')
    startdate_ut = request.args.get('startdate', utdate_default, type=str)
    enddate_ut = request.args.get('enddate', None, type=str)
    shift = request.args.get('shift', None, type=str)

    startdate_ut = datetime.datetime.strptime(str(startdate_ut), '%Y%m%d')
    if not enddate_ut:
        enddate_ut = startdate_ut
    else:
        enddate_ut = datetime.datetime.strptime(str(enddate_ut), '%Y%m%d')
    enddate_ut += datetime.timedelta(hours=23, minutes=59, seconds=59.9)

    timeaccts = db.session.query(TimeAcct).outerjoin(omp.proj, TimeAcct.projectid==omp.proj.projectid)
    timeaccts = timeaccts.filter(TimeAcct.date >= startdate_ut).filter(TimeAcct.date <= enddate_ut)
    timeaccts = timeaccts.filter(or_(omp.proj.telescope=='JCMT',
                                     and_(omp.proj.telescope==None, TimeAcct.projectid.startswith('JCMT'))
                                         )
                                     )


    if shift:
        timeaccts = timeaccts.filter(TimeAcct.shifttype==shift)
    timeaccts = timeaccts.all()


    timeaccts_group = TimeAcctGroup(None, timeaccts)
    print(timeaccts)
    return render_template('timeacct_template.html', grp=timeaccts_group,
       start_ut=startdate_ut.date(), end_ut=enddate_ut.date(), shifttype=shift)

@ops.route('/night/')
def default_night():
    utdate = datetime.datetime.now(pytz.utc).date().strftime('%Y%m%d')
    return redirect(url_for('ops.night_report', utdate=utdate))

@ops.route('/<utdate>')
def night_report(utdate):

    # Single night
    form = NightRepForm()
    utdate = datetime.datetime.strptime(utdate, '%Y%m%d')
    form.process(utdate=utdate)
    start = utdate
    end = start +datetime.timedelta(hours=23, minutes=59, seconds=59.9)

    return prepare_night_report(start, end, db.session, showobslog=True, showshift=True, form=form)

def prepare_night_report(start, end, session, showobslog=True, showshift=True, showmsbs=True, form=None):
    faults, timeaccts, obsloginfo, shiftloginfo, observations, standards, fcfs, msbs, projectinfo, events = \
      get_nightreport_info(session, 'JCMT', start, end, shifts=showshift, msbs=showmsbs, obslog=showobslog)

    # Check if its multi day.
    wvmplot = None
    print('wvmplot!!!')
    multi = True
    if start.date() == end.date():
        multi = False
        date = start.date().strftime('%Y-%m-%d')
        wvmplot = WVMFILE.format(date)
        print(wvmplot)

    inst_time_plots = []
    # Get the summary plots

    if observations:
        statuses = set(i.ompstatus for i in observations)
        if  'Good' in statuses or 'Quest.' in statuses:
            inst_time_plots =  plot_observed_time_by(observations)
    # Create a summary object for those msbs with observations, and put it in a project dictionary.
    projdict = {}
    if msbs and (showmsbs or showobslog):
        msbs = [ i for i in msbs if i.observations ]
        projects = sorted(list(set(i.projectid for i in msbs)))
        msbsummary = namedtuple('msbsummary', 'title target instrument waveband status repeats')
        projdict = {}
        for p in projects:
            pmsbs = [i for i in msbs if i.projectid==p]
            checksum_status = set((i.checksum, i.status) for i in pmsbs)
            csdict = {cs: [i for i in pmsbs if i.checksum==cs[0] and i.status==cs[1]] for cs in checksum_status}
            output = []
            for cs in csdict:
                ms = csdict[cs]
                instrument = '/'.join(sorted(set(o.instrument for m in ms for o in m.observations)))
                output.append(msbsummary(ms[0].title, ms[0].target, instrument, ms[0].waveband, ms[0].status, len(ms)))
            projdict[p] = output

    # Check if we are dealing with one night or more?
    daterange = (start.date(), end.date())
    if daterange[1]==daterange[0]:
        daterange = (daterange[0],)
    daterange = ' to '.join(i.strftime('%Y-%m-%d') for i in daterange)
    if start.date() != end.date():
        obs_tools.INITIAL_HEADERS['UT']  = obs_tools.format_dateobs_multi

    # Create observation log.
    if showobslog:
        results, msbs = get_obs_log(msbs, shiftloginfo, obsloginfo, observations,
                                        inline_shift=True, telescope='JCMT')

        # Find the first observation for each MSB
        first_msbs_observations = { m.observations[0] : m for m in msbs if m.observations}
        msbtids = [i.msbtid for i in msbs if i.observations and i.msbtid is not None]

        # Now create the instrument tables.
        outputtables = []
        if len(results) > 0 and observations and len(observations) > 0:
            outputtables = get_instrumenttables(results)
    else:
        outputtables = []
        first_msbs_observations = {}
        msbtids = []
        
    #Now the time accounting information.

    print('\n\n\n CREATING TIME ACCT GROUP\n\n\n')
    timeacct_info = timeacct.TimeAcctGroup(faults, timeaccts, telescope='JCMT')
    print('\n\n\n CREATED TIME ACCT GROUP\n\n\n')

    # Get the summary of observations.
    obssuminfo = namedtuple('obssuminfo', 'duration band instrument ompstatus')
    summary =[]
    for b in set(o.band for o in observations):
        for i in set(o.instrument for o in observations):
            for s in set(o.ompstatus for o in observations):
                times = sum(o.duration for o in observations if o.band==b and o.instrument==i and o.ompstatus==s)
                if times > 0:
                    summary.append(obssuminfo(times/(60.0*60.0), b, i, s))
    output=summary
    obs_summarydict = {}
    obs_summarydict['Band'] = {b: sum(i.duration for i in output if i.band==b) for b in [1,2,3,4,5,None]}
    obs_summarydict['Instrument'] = {inst: sum(i.duration for i in output if i.instrument==inst) for inst in sorted(set(i.instrument for i in summary))}
    obs_summarydict['Status'] = {status: sum(i.duration for i in output if i.ompstatus==status) for status in ['Good', 'Quest.', 'Bad', 'Junk', 'Rejected']}


    standardplots = None
    if standards and len(standards) > 0:
        standardplots = [plot_night_standards(standards)]
        standardplots += [plot_night_standards(standards, y='peak_percent')]
    fcfplots = None
    if fcfs and len(fcfs) > 0:
        fcfplots = plot_night_fcfs(fcfs)
    return render_template('nightrep_template.html', timeacct=timeacct_info, daterange=daterange,
                               summarydict=obs_summarydict, events=events,
                               faults=faults, msb_projdict=projdict,
                               shiftcomments=shiftloginfo, obstables=outputtables,
                               first_msbs_observations=first_msbs_observations,
                               msbtids=msbtids, inst_time_plots=inst_time_plots,
                               showshift=showshift, showobslog=showobslog,
                               start=start.date(), end=end.date(),
                               fcfs=fcfs, standards=standards,
                               wvmplot=wvmplot, standardplots=standardplots, fcfplots=fcfplots, form=form, multi=multi)


@ops.route('/week')
def ops_meeting():
    # small number of days -- ops meeting.
    pass

@ops.route('/semester')
def semester_report():
    pass

@ops.route('/tag-summary/<semester>')
def tag_summary(semester):
    pass


@ops.route('/fop/<fopuname>/')
def fop_summary():
    # include semester?
    pass


def get_nightreport_info(session, telescope, start, end, shifts=True, msbs=True, obslog=True):

    # Get telescope
    telescope = telescope.upper()
    # Get HST time, and convert start and end times to utc.
    hst = pytz.timezone('HST')

    start_hst=start.replace(tzinfo=datetime.timezone.utc).astimezone(tz=hst)
    end_hst=end.replace(tzinfo=datetime.timezone.utc).astimezone(tz=hst)

    # Get the faults for that telescope that occured in that HST time.
    faults=session.query(omp.fault).filter(
        omp.fault.category==telescope).filter(or_(
            omp.fault.faultdate.between(start, end),
            and_(omp.fault.faultdate==None, omp.fault.faultid.like(start.date().strftime('%Y%m%d')+'%'))
            )
                                                  ).all()

    # If its JCMT, also get the JCMT events.
    if telescope == "JCMT":
        events = session.query(omp.fault).filter(
            omp.fault.category=="JCMT_EVENTS").filter(
            omp.fault.faultdate.between(start, end)).all()
    else:
        events = None

    # Get the time accounting information for all projects that either are on this telescope or start with <TELESCOPE-NAME>.
    timeaccts=session.query(TimeAcct).filter(
        omp.timeacct.date.between(start, end)
    ).outerjoin(omp.proj, omp.timeacct.projectid==omp.proj.projectid
    ).filter(or_(
        omp.proj.telescope==telescope,
        omp.timeacct.projectid.like('{}%'.format(telescope))
    )).all()

    # Get all the Obslog comments that occured in this time range.
    if obslog:
        obsloginfo = session.query(omp.obslog).filter(
            omp.obslog.date.between(start, end)).filter(omp.obslog.obsid==None).filter(omp.obslog.telescope==telescope).order_by(omp.obslog.obslogid).all()
    else:
        obsloginfo = None

    # Get the shift log comments for this time range.
    if shifts:
        shiftloginfo  = session.query(omp.shiftlog).filter(
            omp.shiftlog.date.between(start, end)).filter(
                omp.shiftlog.telescope==telescope).all()
    else:
        shiftloginfo=None
    # Get all the observations.
    observations = session.query(Obs).filter(
        Obs.date_obs.between(start, end)
        ).order_by(Obs.date_obs).options(joinedload(Obs.obslog_comments)).order_by(Obs.date_obs)
    observations = observations.options(joinedload(Obs.scuba2).subqueryload(Scuba2.processing_jobs))
    observations = observations.options(joinedload(Obs.acsis).subqueryload(Acsis.processing_jobs))
    observations = observations.all()

    # Get all projects with time charged OR observations %}

    projects = session.query(Project).join(Obs, Obs.project==Project.projectid).filter( Obs.date_obs.between(start, end)).filter(Project.telescope==telescope).all()
    print('\n\n\n GETTING PROJEcTS INCVLUDING TIMEACCT\n\n\n')
    projects += session.query(Project).join(omp.timeacct, omp.timeacct.projectid==Project.projectid).filter(omp.timeacct.date.between(start, end)).filter(Project.telescope==telescope).all()
    print('\n\n\n GOT PROJEcTS INCVLUDING TIMEACCT\n\n\n')
    projects = set(projects)


    # Get the SCUBA-2 and ACSIS standard values from the calibration database
    standards = session.query(calibration.standard).filter(calibration.standard.ut.between(start, end)).join(calibration.loginfo).filter(calibration.loginfo.logsource.like('%nightly%')).filter(calibration.standard.grouptype=='OBS').all()
    fcfs = session.query(calibration.calstats).filter(calibration.calstats.ut.between(start, end)).join(calibration.loginfo).filter(calibration.loginfo.logsource.like('%nightly%')).filter(calibration.calstats.grouptype=='OBS').all()

    # Join the ompstatus form obsrvations with standards.
    standard_status = [next((j.ompstatus for j  in observations if j.obsid==i.obsid), None)  for i in standards]
    fcf_status = [next((j.ompstatus for j in observations if j.obsid==i.obsid), None) for i in fcfs]

    fcfs = list(zip(fcfs, fcf_status))
    standards = list(zip(standards, standard_status))
    # Get the MSBS execute during this time.
    if msbs:
        msbs = session.query(omp.msbdone).filter(
            MSBDone.date.between(start, end)).join(
                omp.proj, omp.msbdone.projectid==omp.proj.projectid
            ).filter(omp.proj.telescope==telescope
            ).all()

        # Match up the MSBS and projects for this time.
        for m in msbs:
            m.observations = [o for o in observations if o.msbtid==m.msbtid and m.msbtid is not None]
            project = [p for p in projects if p.projectid==m.projectid]
            if len(project)==0:
                project = None
            m.project = project
    else:
        msbs = None

    # Return the various bits of info.
    return faults, timeaccts, obsloginfo, shiftloginfo, observations, standards, fcfs, msbs, projects, events

def get_obs_log(msbs, shiftloginfo, obsloginfo, observations, inline_shift=True, telescope='JCMT'):

    # Need to get only the most recent obslog info comment per timegap.
    # Check if all msbs have an observation?
    for i in msbs:
        if i.observations is None:
            print('MSB {} has no observations!'.format(i))

    combinedlist = []
    # Find time gaps, where gap between observations. Replace obslog
    # timegap object with custom one that includes all needed
    # information.
    for first, second in zip(observations[:-1], observations[1:]):
        timegap = (second.date_obs - first.date_end).total_seconds()
        if timegap > 5*60.0:
            matching_obslog_comments = [i for i in obsloginfo
                                        if abs(i.date - second.date_obs) < datetime.timedelta(seconds=3)]
            if len(matching_obslog_comments) > 0:
                comment = matching_obslog_comments[-1]
                combinedlist.append(TimeGap(first.date_end, second.date_obs, timegap, comment.commentstatus,
                                            comment.commenttext, comment.commentauthor, comment.obslogid,
                                            comment.runnr, comment.instrument, comment.telescope))
            else:
                status=13
                commenttext=None
                commentauthor=None
                obslogid=None
                runnr=None
                instrument=None
                telescope=telescope
                combinedlist.append(TimeGap(first.date_end, second.date_obs, timegap, status,
                                            commenttext, commentauthor, obslogid, runnr, instrument, telescope))
    combinedlist += observations

    if inline_shift:
        combinedlist += shiftloginfo

    sortedlist = sorted(combinedlist,
                        key=lambda x: x.date if hasattr(x, 'date') else x.date_obs)
    return sortedlist, msbs



def get_instrumenttables(results):
    """ Convert into table objects """

    # Find the changes of instrume
    instruments = [i.instrume
                   if hasattr(i, 'instrume') else None
                   for i in results]
    firstinstrument = next((item for item in instruments if item is not None),
                           None)
    if firstinstrument is not None:

        if instruments[0] is None:
            instruments[0] = firstinstrument

        # Replace Nones with the previous instrument
        for i in range(1,len(instruments)):
            if instruments[i] == None:
                instruments[i] = instruments[i - 1 ]
        # Find locations where instrument changes
        combo = list(zip(instruments[0:-1], instruments[1:]))
        indices = [i+1 for i in range(len(combo))
                   if combo[i][1] is not None
                   and combo[i][1] != combo[i][0]]

        start = 0
        outputtables = []
        for i in indices + [None]:
            instrument = instruments[start]
            rows = results[start:i]
            columns = obs_tools.get_columns(next(i for i in rows if hasattr(i, 'instrume') and i.instrume is not None))
            outputtables.append((instrument,rows, columns))
            start = i
    else:
        columns = obs_tools.get_columns(results[0])
        outputtables = outputtables.append(('No',results, columns))

    return outputtables
