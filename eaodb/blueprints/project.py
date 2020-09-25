"""
Blueprint defining JCMT/OMP project related pages.

This defines a top level project page that allows searching for a project.

There is a user specific page that shows the projects the currently
logged in user is defined as PI, COI or friend of project page.

There is a page of a project, and a page with the observations of a
project.

"""

from eaodb.webapp import db
from ..tools.observations import DEFAULT_ACSIS_COLUMNS, \
     DEFAULT_SCUBA2_COLUMNS, FORMATS
from .. import constants

from flask import Blueprint, render_template, Markup, redirect, url_for, flash
from eaodb.relationships import Project, MSBDone, Obs, Scuba2, Acsis, MSBScheduled

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField


from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import joinedload, subqueryload, selectinload

from sqlalchemy import func

from . import project_charts
from eaodb.blueprints.operation_charts import plot_observed_time_by

# Define the Blueprint, its static folder and its templates.
project = Blueprint('project', __name__,
                    template_folder='templates',
                    static_folder='static')

# define various app templates.
@project.app_template_filter('contactable')
def contactable(userinfo):
    if not userinfo.contactable:
        return u'<td title="Does not receive notifications.">✗</td>'
    else:
        return u'<td title="' + userinfo.user.email + u'">✉</td>'


@project.app_template_filter('cadc')
def cadc(userinfo):
    if not userinfo.user.cadcuser:
        return u'<td title="No CADC username">✗</td>'
    else:
        return u'<td title="CADC: ' + userinfo.user.cadcuser + u'">✓</td>'


@project.app_template_filter('enabled')
def enabled(value, symbol=False):
    if bool(value) is True:
        if symbol:
            return u'✓'
        return 'enabled'
    elif bool(value) is False:
        if symbol:
            return 'x'
        return 'disabled'
    else:
        return 'unknown'


@project.app_template_filter('msbstatus')
def msbstatus(value):
    return constants.MSBDONESTATUS.get(value, 'Unknown')


@project.app_template_filter('format_value')
def format_value(value, c):
    if value:
        try:
            return Markup(FORMATS.get(c, '{}').format(value))
        except ValueError:
            return value
    else:
        return 'NaN'


# Get the default heading sets; remove 'Project' as these are only
# created for one project.
acsis_columns = DEFAULT_ACSIS_COLUMNS.copy()
acsis_columns.pop('Project')
scuba2_columns = DEFAULT_SCUBA2_COLUMNS.copy()
scuba2_columns.pop('Project')


class ProjectSearchForm(FlaskForm):
    """ Form to search for a project"""
    projectid = StringField('Project ID')
    submit = SubmitField()


@project.route('/', methods=['GET', 'POST'])
def project_search():
    form = ProjectSearchForm()
    if form.validate_on_submit():
        print('VALIDATED!')
        return redirect(url_for('project.projectpage',
                                projectid=form.data['projectid']))
    return render_template('project_search.html', form=form)


@project.route('/<projectid>')
def projectpage(projectid):
    try:
        proj = db.session.query(Project).filter(
            Project.projectid == projectid)
        proj = proj.options(joinedload(Project.msbs_scheduled).subqueryload(MSBScheduled.plannedobs))
        proj = proj.one()

        completion_piechart = project_charts.completion_piechart(proj)
        cumulative = project_charts.completion_cumulative(proj)
        msbs = db.session.query(MSBScheduled).filter(MSBScheduled.projectid==projectid,
                                                         MSBScheduled.remaining > 0)
        msbs = msbs.all()
        observability = project_charts.observability(msbs)
        msbsummary = proj.get_msb_done_summary()
        direct_papers = proj.get_direct_jcmt_papers()
        secondary_papers = proj.get_secondary_jcmt_papers(direct_papers)
        return render_template('project.html', project=proj,
                               msbs_summary=msbsummary,
                               acsis_columns=acsis_columns,
                               scuba2_columns=scuba2_columns,
                                   direct_papers=direct_papers,
                                   secondary_papers = secondary_papers,
                                   piechart=completion_piechart,
                                   cumulative=cumulative,
                                   observability=observability)
    except NoResultFound:
        print('Project id  {} not found'.format(projectid))
        return 'Project id {} was not found'.format(projectid)


@project.route('/<projectid>/observations')
def obspage(projectid):
    proj = db.session.query(Project).filter(Project.projectid == projectid)
    #proj = proj.options(subqueryload(Project.observations).subqueryload(
    #    Obs.scuba2).subqueryload(Scuba2.processing_jobs))
    #proj = proj.options(subqueryload(Project.observations).subqueryload(
    #    Obs.acsis).subqueryload(Acsis.processing_jobs))
    #proj = proj.options(subqueryload(Project.observations).subqueryload(
    #    Obs.obslog_comments))
    proj = proj.one()
    query = db.session.query(Obs).filter(Obs.project==proj.projectid)
    obs_count = query.count()
    if obs_count > 1000:
        flash("Results limited to 1000 observations. For more control, use the <a href={}>observation search</a> and limit appropriately".format(url_for('obs.observation_search')))

    query = query.order_by(Obs.date_obs)
    query = query.options(joinedload(Obs.acsis))
    query = query.options(joinedload(Obs.scuba2))
    query = query.options(joinedload(Obs.acsis).subqueryload(Acsis.processing_jobs))
    query = query.options(joinedload(Obs.scuba2).subqueryload(Scuba2.processing_jobs))
    query = query.options(subqueryload(Obs.obslog_comments))
    query = query.limit(1000)
    observations = query.all()
    inst_time_plots = None
    if observations:
        inst_time_plots =  plot_observed_time_by(observations, breakdown_by=['instrument', 'ompstatus','band'])
    return render_template('project_obs.html', project=proj, observations=observations,
                           acsis_columns=acsis_columns,
                           scuba2_columns=scuba2_columns, inst_time_plots=inst_time_plots)
# @project.route('/<projectid>/msbs')
# def msbpage(projectid):
#     proj = db.session.query(Project).filter(Project.projectid == projectid)
#     proj = proj.options(joinedload(Project.observations).joinedload(
#         Obs.scuba2).selectinload(Scuba2.processing_jobs))
#     proj = proj.options(joinedload(Project.observations).joinedload(
#         Obs.acsis).selectinload(Acsis.processing_jobs))
#     proj = proj.options(joinedload(Project.observations).selectinload(
#         Obs.obslog_comments))
#     proj = proj.one()
#     msbsdone = proj.msbs_done()
#     return render_template('project_obs.html', project=proj,
#                            acsis_columns=acsis_columns,
#                            scuba2_columns=scuba2_columns)


# Value for formatting strings in a standard way

# projects; hyper link to proejct page
# obsid: hyper link to obsinfo page
# utdate: hyper link to obslog page (possibly specific for project?)
# latest_comment: link to  comment page and combination of info.
# UT_summary: full info in short form. Link to obslog?
# scan number: link to obsinfo


# waveband: complex
# velocity: complex


# Have multiple lines:
