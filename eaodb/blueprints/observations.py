"""
Blueprint defining JCMT/OMP observation related pages.

There is a top level search page that shows all observations matching
a search. There is also a page to let you look at an individual observation.


"""

from flask_wtf import FlaskForm
from wtforms import StringField, SelectMultipleField, DecimalField,\
     BooleanField, TimeField, validators, RadioField, IntegerField, SelectField, ValidationError

from wtforms.ext.dateutil.fields import DateTimeField
from wtforms.widgets import CheckboxInput, ListWidget, RadioInput

from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy import Time, cast, func, and_, or_
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.orm.exc import NoResultFound
import datetime

from eaodb.webapp import db
from ..tools.observations import ompstatus, jcmt_instruments, \
     jcmt_scanpatterns, obs_type, het_bandwidth, het_swmode, scanpattern_lookup
from ..tools.observations import DEFAULT_ACSIS_COLUMNS, \
     DEFAULT_SCUBA2_COLUMNS, END_HEADERS, INITIAL_HEADERS, PROCSTRING, \
     get_commentdict, OMPSTATUS
COMMENTDICT=get_commentdict()

from eaodb.relationships import Project, Obs, Scuba2, Acsis, \
     ProjUser, ProjQueue
from eaodb import omp


# Define the Blueprint, its static folder and its templates.
obs = Blueprint('obs', 'obs',
                template_folder='templates',
                static_folder='static')


# Get the default heading sets.
acsis_columns = DEFAULT_ACSIS_COLUMNS.copy()
scuba2_columns = DEFAULT_SCUBA2_COLUMNS.copy()


CALCOLUMNS = {
    'calstats': ('filter', 'trans', 'noise', 'peak_obs', 'peak_fit', 'fcfasec', 'fcfasec_err','fcfbeam', 'fcfbeam_err', 'fcfmatch', 'fcfmatch_err', 'fwhmmain', 'error_beam'),
    'nefd': ('filter', 'nefd', 'zenith_nefd', 'effective_nefd', 'nbol'),
    'noise': ('filter', 'sigma'),
    'receptor': ('obsid_subsysnr', 'hybrid', 'receptor', 'tsys', 'rms', 'restfreq'),
    'noisestats': ('file', 'median_tsys', 'rms_baseline', 'rms_mean'),
    'efficiency': ('file', 'filter', 'flux_in_beam', 'brightness_temp', 'semidiameter', 'beamwidth', 'mean_tstara', 'sigma_tstara','eta_mb', 'eta_ap'),
    'standard':('subsys', 'sideband', 'integint', 'peak', 'l_bound', 'h_bound', 'integ_percent', 'peak_percent'),
    }


class ObsIDSearchForm(FlaskForm):
    obsid=StringField('ObservationID', description='e.g. scuba2_00026_20200724T063132', validators=[validators.optional()])
    utdate=IntegerField('UT Date', description='YYYYMMDD format', validators=[validators.optional()])
    obsnum=IntegerField('Observation Number', validators=[validators.optional()])
    backend = RadioField('Backend', description='Backend', choices=(('ACSIS', 'ACSIS'), ('SCUBA-2', 'SCUBA-2')),
                             validators=[validators.optional(),],
                             widget=ListWidget(prefix_label=True),
                             option_widget=RadioInput())

class ObservationSearchForm(FlaskForm):
    """Form to search for a JCMT observation"""
    obsid = StringField('Observation ID')
    project = StringField("Project ID")
    object = StringField("Source Name")
    ompstatus = SelectMultipleField('OMP Status', choices=ompstatus,
                                    widget=ListWidget(prefix_label=False),
                                    option_widget=CheckboxInput())
    instrument = SelectMultipleField('Instrument', choices=jcmt_instruments,
                                     widget=ListWidget(prefix_label=False),
                                     option_widget=CheckboxInput())
    scanmode = SelectMultipleField('Scan Pattern', choices=jcmt_scanpatterns,
                                   widget=ListWidget(prefix_label=False),
                                   option_widget=CheckboxInput())
    obs_type = SelectMultipleField('Obs Type', choices=obs_type,
                                   widget=ListWidget(prefix_label=False),
                                   option_widget=CheckboxInput())

    date_obs = DateTimeField('Start Date', validators=[validators.optional()],
                             display_format='%Y-%m-%d %H:%M:%S')
    date_end = DateTimeField('End Date', validators=[validators.optional()],
                             display_format='%Y-%m-%d %H:%M:%S',)
    singledaydesc = "Find only observations occuring on the " +\
                    "date part of the Start Date field"
    singleday = BooleanField('Single Day?', description=singledaydesc)
    frequency_start = DecimalField('Min Frequency (GHz)',
                                   validators=[validators.optional()],
                                   places=4)
    frequency_end = DecimalField('Max Frequency (GHz)',
                                 validators=[validators.optional()],
                                 places=4)

    bwmode = SelectMultipleField('Bandwidth Mode', choices=het_bandwidth,
                                 widget=ListWidget(prefix_label=False),
                                 option_widget=CheckboxInput())
    sw_mode = SelectMultipleField('Switching Mode', choices=het_swmode,
                                  widget=ListWidget(prefix_label=False),
                                  option_widget=CheckboxInput())
    molecule = SelectMultipleField(u'Molecule/Transition')

    starttime = TimeField('Start Time', validators=[validators.optional()],
                          format='%H:%M:%S')
    endtime = TimeField('End Time', validators=[validators.optional()],
                        format='%H:%M:%S')
    utc = RadioField('TZ', choices=[('hst', 'HST'), ('utc', 'UTC')],
                     default='hst')

    fop = StringField('Friend of Project')
    semester = StringField('Semester')
    country = StringField('Queue')
    state = BooleanField('Enabled projects only?', default=False)


def get_molecule_choices(session):
    molecule_transition = session.query(Acsis.molecule + ';' +
            func.replace(Acsis.transiti, "  - ", " - ")
                                        )
    molecule_transition = molecule_transition.distinct()
    molecule_transition = molecule_transition.filter(Acsis.molecule != None
            ).filter(Acsis.transiti != None).all()

    molecule_transition.sort()
    choices = []
    for i in molecule_transition:
        molecule, transition = i[0].split(';')
        label = molecule + ' ' + transition.replace(' - ', '-')
        choices += [(i[0], label)]
    return choices


def create_obsquery_from_form(form):
    print('\n\nCREATING OBSQUERY FROM FORM\n\n')
    query = db.session.query(Obs)
    joinlist = {}
    warnings = []
    print(dir(form))
    # Handle date stuff:
    if form.singleday.data and form.date_obs.data:
        day = form.date_obs.data.date()
        day_end = day + datetime.timedelta(days=1)
        query = query.filter(Obs.date_obs >= day).filter(Obs.date_obs < day_end)
        if form.date_end.data:
            warnings += ['Cannot specify both end date and singleday; end date has been ignored.']

    elif form.date_obs.data:
        query = query.filter(Obs.date_obs >= form.date_obs.data)
    elif form.date_end.data:
        query = query.filter(Obs.date_end <= form.date_end.data)
        if form.data.singleday:
            warnings += ['Cannot specify both end date and singleday; end date has been ignored.']

    # Handle time of day.
    if form.starttime.data:
        starttime = form.starttime.data
        if not form.utc.data == 'utc':
            starttime = datetime.datetime.combine(datetime.date.today(), starttime) +\
                datetime.timedelta(hours=-10)
            starttime = starttime.time()
        query = query.filter(cast(Obs.date_obs, Time) >= starttime)
    if form.endtime.data:
        endtime = form.endtime.data
        if not form.utc.data:
            endtime = datetime.datetime.combine(datetime.date.today(), endtime) +\
                datetime.timedelta(hours=-10)
            endtime = endtime.time()
        query = query.filter(cast(Obs.date_obs, Time) >= endtime)

    # Handle start/end frequency
    if form.frequency_start.data:
        query = query.filter(Acsis.restfreq >= form.frequency_start.data)
        joinlist += [(Acsis, Obs.obsid == Acsis.obsid)]
    if form.frequency_end.data:
        query = query.filter(Acsis.restfreq <= form.frequency_end.data)
        if 'Acsis' not in joinlist:
            joinlist['Acsis'] = (Acsis, Obs.obsid == Acsis.obsid)

    for key in ('obsid', 'project', 'object'):
        values = form.data[key]
        the_attr = getattr(Obs, key)
        if values is not None and values != '':
            query = query.filter(the_attr == values)

    # Handl instrument: complex, need to handl pol-2?
    print('instrument data!', form.instrument.data)
    if form.instrument.data and form.instrument.data != []:
        print('In instrument handling!')
        values = form.data['instrument'].copy()
        theattr = Obs.instrume
        if values and len(values) > 0:
            print('Values were selected!')
            conditions = []
            if 'SCUBA2' in values:
                values.remove('SCUBA2')
                conditions += [and_(Obs.instrume=='SCUBA-2', or_(Obs.inbeam==None, Obs.inbeam.notlike('%pol%')))]
            if 'POL2' in values:
                values.remove('POL2')
                conditions += [and_(Obs.instrume=='SCUBA-2', Obs.inbeam.like('%pol%'))]
            conditions += [Obs.instrume.in_(values)]
            query = query.filter(or_(*conditions))
            print(conditions)

    if form.ompstatus.data and form.ompstatus.data != []:
        values = [int(i) for i in form.ompstatus.data]
        query = query.join(Obs.latest_ompcomment).filter(omp.obslog.commentstatus.in_(values))
    for key in ('sw_mode', 'obs_type'):
        values = form.data[key]
        the_attr = getattr(Obs, key)
        if key == 'ompstatus' and values:
            values = [int(i) for i in values]
        if values and len(values) > 0:
            query = query.filter(the_attr.in_(values))

    if form.scanmode.data:
        values = form.scanmode.data
        if values is not None and values != []:
            value_lists = [scanpattern_lookup.get(v, [v]) for v in values]
            value_lists_flat = [i for v in value_lists for i in v]
            query = query.filter(Obs.scanmode.in_(value_lists_flat))
    if form.molecule.data:
        values = form.molecule.data
        if values is not None and values != []:
            or_list = []
            for v in values:
                mole, transit = v.split(';')
                transit = transit.replace('-', '%-%')
                or_list.append(and_(Acsis.molecule == mole,
                                    Acsis.transiti.like(transit)))
            query = query.filter(or_(*or_list))
            if 'Acsis' not in joinlist:
                joinlist['Acsis'] = (Acsis, Obs.obsid == Acsis.obsid)

    if form.bwmode.data and form.bwmode.data != []:
        or_list = None
        values = form.bwmode.data
        values_notother = [i for i in values if i != 'other']
        if 'other' in values:
            or_list = Acsis.bwmode.notin_([
                i[0] for i in het_bandwidth if i[0] != 'other'])
        if 'Acsis' not in joinlist:
            joinlist['Acsis'] = (Acsis, Obs.obsid == Acsis.obsid)
        if or_list is not None and values_notother != []:
            query = query.filter(or_(Acsis.bwmode.in_(values_notother), or_list))
        elif or_list is not None:
            query = query.filter(or_(or_list))
        else:
            query = query.filter(Acsis.bwmode.in_(values_notother))
    if form.semester.data and form.semester.data != '':
        query = query.filter(Project.semester == form.semester.data.upper())
        if 'Project' not in joinlist:
            joinlist['Project'] = (Project, Obs.project == Project.projectid)

    if form.state.data:
        query = query.filter(Project.state == True)
        if 'Project' not in joinlist:
            joinlist['Project'] = (Project, Obs.project == Project.projectid)
    if form.fop.data and form.fop.data != '':
        query = query.filter(ProjUser.userid == form.fop.data.upper())
        query = query.filter(ProjUser.capacity == 'Support')
        if 'ProjUser' not in joinlist:
            joinlist['ProjUser'] = (ProjUser, Obs.project == ProjUser.projectid)

    if form.country.data and form.country.data != '':
        query = query.filter(ProjQueue.country == form.country.data.upper())
        if 'ProjQueue' not in joinlist:
            joinlist['ProjQueu'] = (ProjQueue, Obs.project == ProjQueue.projectid)

    print('joinlist!', joinlist)
    for j in joinlist:
        query = query.join(joinlist[j])
    return query

@obs.route('/obsid_search', methods=('POST',))
def obsid_search():
    form = ObsIDSearchForm()
    if not form.obsid.data and not (form.obsnum.data and form.utdate.data and form.backend.data and form.backend.data != 'None'):
        flash('You must provide either an observation ID, or all of UT date, Observation Number and backend')
    if not form.validate_on_submit():
        flash(form.errors)
    return redirect(url_for('obs.obsinfo', obsid=form.obsid.data, obsnum=form.obsnum.data, backend=form.backend.data,
                                utdate=form.utdate.data))


@obs.route('/observation_search', methods=('POST',))
def observation_search():
    choices = get_molecule_choices(db.session)
    form = ObservationSearchForm()
    form.molecule.choices = choices

    if form.validate_on_submit():
        print('form data!', type(form.data), form.data, dir(form.data))

        kwargs_withvalues = {k: v for k, v in form.data.items()
                                if v and v != [] and k != 'csrf_token'}
        print(kwargs_withvalues)
        return redirect(url_for('obs.observations', **kwargs_withvalues))
    else:
        print(form.errors)
        return ("Invalid form!" + str(form.errors))


@obs.route('/', methods=('GET',))
def observations():
    print('args is', request.args)

    # arguments that require custom query:
    choices = get_molecule_choices(db.session)
    form = ObservationSearchForm()
    form.molecule.choices = choices
    print('request args', request.args)
    form.process(formdata=request.args)
    print(form.data)

    # Now do search, if args was set.
    if len(request.args) > 0:
        query = create_obsquery_from_form(form)
        query = query.order_by(Obs.date_obs)
        query = query.options(joinedload(Obs.acsis))
        query = query.options(joinedload(Obs.scuba2))
        query = query.options(joinedload(Obs.acsis).selectinload(Acsis.processing_jobs))
        query = query.options(joinedload(Obs.scuba2).selectinload(Scuba2.processing_jobs))
        query = query.options(selectinload(Obs.obslog_comments))
        count = query.count()
        print('COUNT IS', count, '\n\n')

        if count < 300:
            results = query.all()
        else:
            results = query.limit(300).all()
        print(results)
        acsis_columns = INITIAL_HEADERS.copy()
        acsis_columns.update(DEFAULT_ACSIS_COLUMNS)
        acsis_columns.update(END_HEADERS)
        scuba2_columns = INITIAL_HEADERS.copy()
        scuba2_columns.update(DEFAULT_SCUBA2_COLUMNS)
        scuba2_columns.update(END_HEADERS)
    else:
        results = None
        acsis_columns = None
        scuba2_columns = None
        count = None
    print(form.instrument, dir(form.instrument), form.instrument.data)
    return render_template('observations.html', form=form, count=count,
                           observations=results, acsis_columns=acsis_columns,
                           scuba2_columns=scuba2_columns)


@obs.route('/obsinfo', methods=('GET',))
def obsinfo():
    obsid = request.args.get('obsid', None, type=str)
    if not obsid:
        obsnum = request.args.get('obsnum', None, type=int)
        utdate = request.args.get('utdate', None, type=int)
        backend = request.args.get('backend', None, type=str)
    form = ObsIDSearchForm()
    form.process(request.args)
    headercomments=None
    warningstring=None
    result=None
    if obsid or (obsnum and utdate and backend):
        if obsid:
            query = db.session.query(Obs).filter(Obs.obsid==obsid)
            try:
                result = query.one()
                headercomments=COMMENTDICT[result.backend]
            except NoResultFound:
                warningstring='WARNING: No observation found with obsid=%s.' % obsid
        else:
            query = db.session.query(Obs).filter(Obs.obsnum==obsnum, Obs.utdate==utdate, Obs.backend==backend)
            count = query.count()
            if count == 0:
                warningstring = 'WARNING: No observations found for your request. Are you sure the observation exists?'
            elif count > 1:
                warningstring = 'WARNING: Multiple observations were found. There are a small number of observations that have repeated obsnums on the same day in the system due to bugs. Please specify an Observation ID, or use the Observation Search instead.'
            else:
                result = query.one()
                headercomments=COMMENTDICT[result.backend]
    if result:
        # Check for information about that observation in the calibration database.
        calinfo = result.results
    else:
        calinfo = None
    if warningstring:
        flash(warningstring)
    return render_template("obsinfo.html", obs=result, form=form,
                               headercomments=headercomments, warningstring=warningstring, calinfo=calinfo, calinfo_columns=CALCOLUMNS)



@obs.app_template_filter('formatprocjobs')
def format_procjobs(job, filename):
    if job:
        return PROCSTRING.format(jobid=job, filename=filename)

@obs.app_template_filter('ompstatus')
def ompstatus(status):
    return OMPSTATUS.get(int(status), None)

@obs.app_template_filter('project')
def project_link(projectid, text=None):
    url = url_for('project.projectpage', projectid=projectid)
    if not text or text == '':
        text = projectid
    return "<a href={url}>{text}</a>".format(url=url, text=text)

@obs.app_template_filter('obs')
def observation_link(obsid, text=None):
    url = url_for('obs.obsinfo', obsid=obsid)
    if not text:
        text = text
    return "<a href={url}>{text}</a>".format(url=url, text=text)
