"""
Operation tracking charts

"""
import pandas as pd
from sqlalchemy.orm import object_session

from io import StringIO
import plotly.express as px
import plotly.graph_objects as go

from eaodb.relationships import Project
from collections import OrderedDict

INCLUDE_PLOTLYJS='cdn'

# Plots for a single time.
def plot_charged_time_by_type(timeacct):
    pass

layout = go.Layout(
  margin=go.layout.Margin(
        l=20, #left margin
        r=20, #right margin
        b=20, #bottom margin
        t=30, #top margin
    )
)

from matplotlib.figure import Figure

def plot_night_fcfs(fcfs):
    fcfs, statuses = zip(*fcfs)
    df = pd.DataFrame.from_dict([i.__dict__ for i in fcfs])
    df['status'] = pd.Series(statuses, name='status')
    figs = []
    for y in ('fcfasec', 'fcfbeam', 'fcfmatch', 'fwhmmain', 'error_beam'):
        error_y = y+'_err'
        if y in ['fwhmmain', 'error_beam']:
            error_y=None
        fig = px.scatter(df, x='ut', y=y, error_y=error_y, facet_col='filter', color='status', symbol='targetname', hover_data=['obsid'])
        fig['layout'].update(layout)
        #fig.layout.yaxis2.update(matches=None)
        fig.update_yaxes(showticklabels=True, col=2, matches=None)
        fig.update_layout(height=200, width=850)
        str_form = StringIO()
        fig.write_html(str_form, include_plotlyjs=INCLUDE_PLOTLYJS, config={'static': True, 'responsive':True},
                       full_html=False)
        str_form.seek(0)
        figs.append(str_form.read())

    return figs

# Standards charts. Plot integ %diff and peak %diff vs time, group by status and source

def plot_night_standards(standards, y='integ_percent'):
    standards, statuses = zip(*standards)
    df = pd.DataFrame.from_dict([i.__dict__ for i in standards])
    df['status'] = pd.Series(statuses, name='status')
    number_plots = len(set(df['instrument'].values))
    fig = px.scatter(df, x='ut', y=y, facet_col='instrument', color='status', symbol='targetname', hover_data=['obsid'])#, color=['instrument','instrument'], symbol=[['status', 'targetname']*2])
    fig['layout'].update(layout)
    fig.update_layout(height=200, width=400*number_plots + 50)
    str_form = StringIO()
    fig.write_html(str_form, include_plotlyjs=INCLUDE_PLOTLYJS, config={'static': True, 'responsive':True},
                           full_html=False)
    str_form.seek(0)

    return str_form.read()

Bands = pd.Categorical([1,2,3,4,5,'?'], ordered=True)
#Instruments = pd.Categorical(['SCUBA-2', 'POL-2', 'UU', 'HARP'], ordered=True)

def plot_observed_time_by(observations, breakdown_by=['instrument', 'queue', 'band'], status=['Good', 'Quest.']):
    """
    breakdown_by can be combinations of  instrument, weatherband, queue.
    """
    obsgroup = ObsGroup(observations)
    summtable = obsgroup.time_spent(by=breakdown_by, status=status)

    number_plots = len(set(summtable.instrument))
    x = breakdown_by[-1]
    y = 'duration'
    facet_col = breakdown_by[0]
    if len(breakdown_by)>2:
        color=breakdown_by[1]
    else:
        color=None
    fig = px.bar(summtable, x=x, y=y, color=color, facet_col=facet_col)
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    fig.update_layout(height=200, width=number_plots*200 + 50)
    #maxval = 0
    #for key, group in summtable.groupby(breakdown_by[0]):
    #    vals = group.pivot_table(index=breakdown_by[-1], columns='queue', aggfunc=sum)
    #    vals.columns = vals.columns.get_level_values(1)
    #    fig = px.bar(vals, height=200, width=300, labels={'value':'hrs'}, title=key)
    fig['layout'].update(layout)

    # Ensure it doesn't convert weather bands to strings.
    fig.update_layout(xaxis=dict(type='category'))
    for i in range(number_plots -1):
        label = 'xaxis{}'.format(i+2)
        fig['layout'].update({label: dict(type='category')})
    ##    if len(figs)!=0:
    #        fig.update_layout(showlegend=False, height=200, width=250)
    str_form = StringIO()
    fig.write_html(str_form, include_plotlyjs=INCLUDE_PLOTLYJS, config={'static': True, 'responsive':True},
                           full_html=False)
    str_form.seek(0)

    return str_form.read()







class ObsGroup:
    def __init__(self, observations):
        self.observations = observations

    def time_spent(self, by=['instrument','queue','band'], status=['Good', 'Quest.']):
        if 'queue' in by:
            projects = set(o.project for o in self.observations)
            projinfo = dict(object_session(self.observations[0]).query(Project.projectid, Project).filter(Project.projectid.in_(projects)).all())
        else:
            projinfo = {}
        results = []
        for o in self.observations:
            if o.ompstatus in status:
                obj = []
                for key in by:
                    if key == 'queue':
                        value = ','.join(getattr(projinfo.get(o.project, None),'queues', ['None']))
                    else:
                        value = getattr(o, key, 'None')
                    obj += [value]
                results += [[*obj, o.duration/(60.0*60.0)]]
        df = pd.DataFrame(results, columns= by + ['duration'])
        if 'unknown' in df.band:
            df.band[df.band=='unknown'] = '?'
        df.band = df.band.astype('category')
        df.band = pd.Series(df.band.values.astype(Bands), name=df.band.name)

        return df.groupby(by, as_index=False).sum()


import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from collections import OrderedDict
from matplotlib.colors import ListedColormap
from eaodb.relationships import TimeAcct, Obs, Project
import calendar
import dateutil
import datetime
from eaodb import omp
from sqlalchemy import func, or_, and_, select

colors = np.array([[0.67843137, 1.        , 0.18431373, 1.        ],
           [0.        , 0.3       , 0.        , 1.        ],
           [0.        , 0.50196078, 0.        , 1.        ],
                  [1.        , 0., 0., 1.        ],
           [1.        , 0.38823529, 0.27843137, 1. ],

           [0.54509804, 0.        , 0.        , 1.        ],
           [0.5       , 0.5       , 0.5       , 1.        ],
           [0.        , 0.        , 0.        , 1.        ]])
faultscm = ListedColormap(colors)

weather_colors = ((0.993248, 0.906157, 0.143936, 1.0),
                      (0.360741, 0.785964, 0.387814, 1.0),
                      (0.39215686274509803, 0.5843137254901961, 0.9294117647058824, 1.0),
                      (0.5411764705882353, 0.16862745098039217, 0.8862745098039215, 1.0),
                      (0.7, 0.7, 0.7, 1.0),
                      (0.0, 0.0, 0.0, 0.0))


systemdict = OrderedDict([
    (0, 'Human'),
(1022, 'QueryTool'),
(1042, 'Visitor Inst.'),
(1043, 'Other Inst.'),
(1044, 'DAS'),
(1046, 'CBE'),
(1049, 'RxB'),
(1050, 'RxW'),
(1051, 'SCUBA'),
(1053,'IFS'),
(1055, 'Surface'),
(1065, 'SCUBA-2'),
(2001,'HARP'),
(1048, 'RxA'),
(2008, 'Namakanui'),
(1045, 'ACSIS'),
(1052, 'WVM'),
(1054, 'RxH3'),
(1011, 'Computer'),
(1012, 'Carousel'),
(1016, 'Telescope'),
(-1, 'Other'),
])



typedict = OrderedDict([
(1005, 'Hardware'),
(1006, 'Software'),
(1013, 'Mechanical'),
(1014, 'Electronic'),
(1015, 'Cryogenic'),
(1029, 'Bug'),
(0, 'Human'),
(-1, 'Other'),
])

def board_ops_observedtimeplots(start, end, session):
    resultsdict = OrderedDict()

    historical_comparison_start = datetime.datetime(2015,8,1)

    months = dateutil.rrule.rrule(dateutil.rrule.MONTHLY,
                                  dtstart=historical_comparison_start,
                                  until=end)
    countries = select([omp.projqueue.projectid,
                        func.group_concat(omp.projqueue.country).label('countries')
                            ]).group_by(omp.projqueue.projectid).alias('countrytable')

    query = session.query(func.year(Obs.date_obs), func.month(Obs.date_obs), Obs.band,
                        Project.semester, countries.c.countries, Obs.instrument,
                        func.count(Obs.obsid), func.sum(Obs.duration)/(60.0*60.0)
                        ).join(Project, Obs.project==Project.projectid).join(
                            countries, countries.c.projectid==Project.projectid)

    columns = ['year', 'month', 'band', 'semester', 'queue', 'instrument', 'count', 'time']

    results = query.filter(Obs.date_obs >= historical_comparison_start).filter(Obs.date_end < end).group_by(
        Obs.utdate, Project.semester, Obs.instrument, countries.c.countries, Obs.band).all()

    df = pd.DataFrame(results, columns=columns)

    # Get semester names based on normal semesters and set date as index
    df['semestercat'] = ['B'] * len(df)
    df['semestercat'][df.month.isin([2,3,4,5,6,7,8])] = 'A'
    years = [y if m > 1 else y-1 for y,m  in zip(df.year, df.month)]
    df['semesteryear'] = years
    df['semestername'] = df['semesteryear'].map(str) + '-' + df['semestercat']
    df['date'] = [datetime.datetime(y,m,1) for y, m in zip(df.year, df.month)]
    df = df.set_index(df.date)

    # Fix up 'INT' as 'PI' for EAO
    df['queue'][df['queue']=='INT'] = 'PI'
    # Set TEX as PI ads its very small
    df['queue'][df['queue']=='TEX'] = 'PI'



    # Observed science time by semester by weather band:
    semestertime_band = df.pivot_table(columns=['band', 'queue'],
                    index='semestername', values='time', aggfunc='sum', dropna=False)
    # Remove JAC and EC to see only science time.
    sciencesemestertime_band = semestertime_band.loc[:,~semestertime_band.columns.get_level_values('queue').isin(['JAC','EC'])]

    # Create plot of science time by weather band.
    fig = Figure()
    ax = fig.add_subplot(111)
    sciencesemestertime_summary = sciencesemestertime_band.sum(axis=1, level='band')
    ax = sciencesemestertime_summary.plot.bar(stacked=True,
                                color=weather_colors, ax=ax)
    ax.set_xlabel('')
    ax.set_ylabel('Hours')
    ax.figure.set_tight_layout(True)

    #[i.set_edgecolor('black') for i in ax.legend_.patches]
    [i.set_edgecolor('black') for i in ax.patches]
    #[i.set_hatch('//////') for i in ax.patches[4*6:(5)*6]]
    ax.legend()
    ax.legend_.set_title('Weather Grade')
    semester_hours_fig = ax.figure

    # Now get plot all time in queues.
    ax = None
    queues = sorted(list(set(df.queue)))
    width = 1.0/(len(queues) + 2)
    for count, i in enumerate(queues):
        table = semestertime_band.iloc[:,
                    semestertime_band.columns.get_level_values('queue')==i]

        position = width + count*width
        if ax is None:
            fig = Figure()
            ax = fig.add_subplot(111)

        ax = table.plot.bar(stacked=True, color=weather_colors,
                            width=width, use_index=True, ax=ax,
                            legend=False, align='edge')

        rectangles = ax.containers[count*6:(count*6)+6]
        for rects in rectangles:
            [r.set_x(c + position) for c,r in enumerate(rects)]

        heights = table.sum(axis=1)
        positions = np.arange(len(table)) + position
        for y,x in zip(heights, positions):
            ax.text(x + 0.5*width, y + 5, '{}'.format(i, y),
                    ha='center', va='bottom', rotation=90, size='x-small')

    xlabels = [i.get_text() for i in ax.get_xticklabels()]
    ax.set_xticks(ax.get_xticks() + 0.5)
    ax.set_xticklabels(xlabels)

    ax.set_xlim(0,len(semestertime_band))
    ax.set_xlabel('')
    ax.set_ylabel('Hours')

    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[0:6], [1,2,3,4,5,'?'],
              title='Weather Grade',  bbox_to_anchor=[1,1],
              loc='upper left')
    ax.figure.set_size_inches([15,4])
    ax.figure.set_tight_layout(True)


    semester_hours_queue = ax.figure

    # Plots of time spent observing by instrument and weather band.
    # Get plots of instrument by weather band.
    instruments = list(set(df['instrument']))
    if 'SCUBA-2' in instruments and 'POL-2' in instruments:
        instruments.remove('SCUBA-2')
        instruments.remove('POL-2')
    instcats = pd.api.types.CategoricalDtype(
        categories=['SCUBA-2', 'POL-2'] + sorted(instruments),
        ordered=True)
    df['instrument'] = df['instrument'].astype(instcats)

    curr = df[(df.index >= start) & (df.index < end)]
    insttable_full = curr.pivot_table(columns=['instrument', 'queue'],
                                      index='band', values='time',
                                      aggfunc='sum', dropna=False)
    curr = curr[~curr['queue'].isin(['EC', 'JAC'])]
    insttable = curr.pivot_table(columns=['instrument'], index='band',
                                 values='time', aggfunc='sum', dropna=True)


    instcolors=['blue', 'lightgreen', 'orange', 'purple', 'black']
    size = len(insttable)
    fig = Figure()
    ax = fig.add_subplot(111)
    ax = insttable.plot.bar(stacked=True, color=instcolors, ax=ax)
    for n, hatch in enumerate((['///', '\\\\\\',]*size)[0:size]):
         [i.set_hatch(hatch) for i in ax.patches[n*size:(n+1)*size]]
    [i.set_edgecolor('black') for i in ax.patches]

    #[i.set_linewidth(2.0) for i in ax.patches]
    ax.set_xlabel('Weather Grade')
    ax.set_ylabel('Hours on sky')
    ax.legend()
    ax.legend_.set_title('Instrument')
    ax.tick_params(axis='x', labelrotation=0.0)
    ax.figure.set_tight_layout(True)
    instrument_hours = ax.figure

    fig = Figure()
    ax = fig.add_subplot(111)
    ax = insttable[0:5].plot.bar(stacked=True, color=instcolors, ax=ax)
    ax.set_xlabel('Weather Grade')
    ax.set_ylabel('Hours on sky')
    size = len(insttable[0:5])
    for n, hatch in enumerate((['///', '\\\\\\',]*size)[0:size]):
         [i.set_hatch(hatch) for i in ax.patches[n*size:(n+1)*size]]
    [i.set_edgecolor('black') for i in ax.patches]
    ax.legend()
    ax.legend_.set_title('Instrument')
    ax.tick_params(axis='x', labelrotation=0.0)
    ax.figure.set_tight_layout(True)

    instrument_hours_nounknown = ax.figure
    resultsdict['instrument_hours'] = (create_b64_img(instrument_hours), 'From the observation database, this shows the cumulative time spent in each weather band broken down by instrument for the reporting period. This includes observations marked as BAD or JUNK. Unknown weather occurs when there are no WVM values in database, or there is an unphysical WVM value. Time not spent creating a standard observation cannot be shown in this method (e.g. VLBI observing, lost time, closed time, etc.)', (insttable,))
    resultsdict['instrument_hours_nounknown'] = (create_b64_img(instrument_hours_nounknown), 'From the observation database, this shows the cumulative time spent in each weather band broken down by instrument for the reporting period. This includes observations marked as BAD or JUNK. Observations without a valid WVM are not included. Time not spent creating a standard observation cannot be shown in this method (e.g. VLBI observing, lost time, closed time, etc.', (insttable[0:5],))
    resultsdict['semester_hours_fig'] = (create_b64_img(semester_hours_fig), 'From the observation database, this shows the cumulative time spent carrying out regular observations in each weatherband for the standard 6-month semester periods. The final semester may be incomplete, if the current reporting period ends before the end of the semester.', (sciencesemestertime_summary,))
    resultsdict['semester_hours_queue'] = (create_b64_img(semester_hours_queue), 'From the observation database, this shows the cumulative time spent carrying out regular observations in each weatherband for the standard 6-month semester periods, broken down by the queue. For ease of comparison the historical INT and TEX queue has been converted to PI. The final semester may be incomplete, if the current reporting period ends before the end of the semester.', (sciencesemestertime_band,))

    return resultsdict

def board_ops_performance(start, end, session):

    # FAULTS
    query = session.query(omp.fault).filter(
        or_(and_(omp.fault.faultdate >= start, omp.fault.faultdate < end),
            and_(omp.fault.faultdate == None, omp.fault.faultid >= int(start.strftime('%Y%m%d')), omp.fault.faultid < int(end.strftime('%Y%m%d')))
                ))
    query = query.filter(omp.fault.category=='JCMT').filter(omp.fault.timelost > 0)
    faults = query.all()
    faultsdf = pd.DataFrame.from_records([i.__dict__ for i in faults])

    # make it match
    faultsdf = faultsdf.rename(columns={'faultdate':'date', 'timelost': 'timespent'})
    faultsdf['projtype'] = ['FAULT'] * len(faultsdf['date'])

    # non-technical faults:

    faultsdf['projtype'][faultsdf.type==0] = 'NONTECH FAULT'
    faultsdf['projtype'][faultsdf.status==3] = 'NONTECH FAULT'
    faultsdf['timespent'] = faultsdf.timespent.astype(float)
    # Replace faults with no fault date with their file date, and use
    # on,.y the date part of the fault.
    faultsdf.date = [datetime.datetime(t.year, t.month, t.day) if not pd.isnull(t) else datetime.datetime.strptime(str(int(id_)), '%Y%m%d')  for t, id_ in zip(faultsdf.date, faultsdf.faultid)]
    faultsdf.shifttype[faultsdf.shifttype.isnull()] = 'UNKNOWN'
    faultsumm = faultsdf.groupby(['date', 'shifttype', 'projtype']).agg({'timespent': sum})
    faultsumm = faultsumm.reset_index()

    # TIME CHARGED
    countries = select([omp.projqueue.projectid,
                        func.group_concat(omp.projqueue.country).label('countries')
                            ]).group_by(omp.projqueue.projectid).alias('countrytable')

    timeaccts = session.query(TimeAcct, countries.c.countries).filter(TimeAcct.date >= start).filter(TimeAcct.date <= end).filter(or_(TimeAcct.projectid.startswith('JCMT'), Project.telescope=='JCMT')).outerjoin(Project, Project.projectid==TimeAcct.projectid).outerjoin(countries, Project.projectid==countries.c.projectid).all()
    timeaccts, queues = zip(*timeaccts)

    timeacctsdf = pd.DataFrame.from_records([i.__dict__ for i in timeaccts])
    timeacctsdf['queue'] = queues
    timeacctsdf.date = pd.to_datetime(timeacctsdf.date)

    timeacctsdf.timespent = timeacctsdf.timespent.astype(float)
    timeacctsdf.timespent = timeacctsdf.timespent/(60.0*60)



    # Create project types.
    timeacctsdf['projtype'] = [i if ('JCMT' in i or i in ['FAULT', 'NONTECH FAULT']) else ('EC' if 'EC' in i else 'SCI') for i in timeacctsdf.projectid]
    categories = ['SCI', 'JCMTCAL', 'EC', 'FAULT', 'NONTECH FAULT', 'JCMTOTHER', 'JCMTEXTENDED', 'JCMTWEATHER', 'JCMT_SHUTDOWN']
    projtypecat = pd.api.types.CategoricalDtype(categories=categories)

    timeacctsdf = timeacctsdf.groupby(['date', 'shifttype', 'projtype']).agg({'timespent': sum})
    timeacctsdf = timeacctsdf.reset_index()
    timeacctsdf = timeacctsdf.append(faultsumm)
    timeacctsdf.timespent = timeacctsdf.timespent.astype(float)
    timeacctsdf.date = pd.to_datetime(timeacctsdf.date)
    timeacctsdf = timeacctsdf.set_index('date')
    timeacctsdf['projtype'] = timeacctsdf['projtype'].astype(projtypecat)
    timeacctsdf.shifttype[timeacctsdf.shifttype==''] = 'UNKNOWN'


    return timeacctsdf, faultsdf


def create_performance_stats(start, end, session):
    historical_start = datetime.datetime(2003,2,1)
    shiftstart = datetime.datetime(2019,3,2)
    eao_start = datetime.datetime(2015,2,1)
    timeacctsdf, faultsdf = board_ops_performance(historical_start, end, session)


    perdict = OrderedDict()
    faultdict = OrderedDict()

    #

    historical_noshiftsummary = timeacctsdf[timeacctsdf.index < start].groupby([pd.Grouper(freq='M'), 'projtype']).sum().reset_index().pivot_table(index='date', columns=['projtype'], aggfunc='sum', margins=False, fill_value=0.0)
    historical_noshiftsummary = historical_noshiftsummary.groupby([historical_noshiftsummary.index.month]).mean()

    current = timeacctsdf[timeacctsdf.index >= start].groupby([pd.Grouper(freq='M'), 'projtype']).sum().reset_index().pivot_table(index='date', columns=['projtype'], aggfunc='sum', margins=False, fill_value=0.0)
    current.columns = current.columns.droplevel(0)

    comparison = historical_noshiftsummary[historical_noshiftsummary.index.isin(current.index.month)].reindex(current.index.month)

    # Get names of times correct.
    comparison.index = [calendar.month_name[i] for i in comparison.index.values]
    comparison.index = comparison.index.set_names('Month')
    comparison.columns = comparison.columns.droplevel(0)

    fig = Figure()
    ax1 = fig.add_subplot(121)
    ax2 = fig.add_subplot(122, sharey=ax1)
    ax1 = current.drop(['JCMTEXTENDED'], axis=1).plot.bar(stacked=True, cmap=faultscm, ax=ax1, legend=False, width=0.8)
    ax2 = comparison.drop(['JCMTEXTENDED'], axis=1).plot.bar(stacked=True, cmap=faultscm, ax=ax2, legend=True, width=0.8)
    #ax1.set_xticklabels([calendar.month_name[int(i.get_text().split('-')[1])] + '' + i.get_text().split('-')[0] for i in ax1.get_xticklabels()])
    #ax2.set_xticklabels([calendar.month_name[int(i.get_text())] for i in ax2.get_xticklabels()])
    ax1.set_xticklabels([i.strftime('%Y-%m') for i in current.index])
    ax1.set_title('Reporting Period')
    ax2.set_title('Mean historical\n{} to {}'.format(historical_start.strftime('%Y-%m'),  (start - datetime.timedelta(days=1)).strftime('%Y-%m')))
    ax1.set_ylabel('hrs')
    ax1.set_xlabel(None)
    ax2.set_xlabel(None)

    #fig.set_tight_layout(rect=[0,0,0.72,1])
    fig.set_tight_layout(True)
    handles, labels = ax2.get_legend_handles_labels()
    ax2.legend(handles[::-1], labels[::-1],bbox_to_anchor=(1, 1), title=False)
    performance_comparison = fig
    perdict['performance_comparison'] = (create_b64_img(fig), 'Comparison of charged time for reporting period compared with historical values. All shifts are included. Time labelled as JCMT Extended has been dropped.', (current, comparison))

    regularshifts = {}
    extrashifts = {}
    regularshiftplot, extrashiftplot, shiftdf = create_shiftgroups(timeacctsdf[timeacctsdf.index > start], extended=False)
    perdict['regularshift'] = (create_b64_img(regularshiftplot), 'Break down of time charged for each standard shift (DAY, EO and NIGHT) for the current reporting period.', shiftdf)
    perdict['extrashift'] = (create_b64_img(extrashiftplot), 'Break down of time charged for the extra shift types (OTHER and UNKNOWN) in the current reporting period. Normally no time should be charged to these shift types.', ())

    regularshiftplot_all, extrashiftplot_all, allshiftdf = create_shiftgroups(timeacctsdf[timeacctsdf.index > shiftstart], extended=False, width=1.0)
    perdict['regularshift_all'] = (create_b64_img(regularshiftplot_all), 'Break down of time charged by month and shift for all regular shifts since the start of recorded shifts at %s' % shiftstart.strftime('%Y-%m-%d'), allshiftdf)

    perdict['extrashift_all'] = (create_b64_img(extrashiftplot_all), 'Break down of time charged by month and shift for all extra shifts (OTHER and UNKNOWN) since the start of recorded shifts at %s' % shiftstart.strftime('%Y-%m-%d'),())

    faulttype_plot, faultdfs = faultbreakdown_plots(faultsdf[faultsdf.date >=start])
    faultdict['faultbreakdown'] = (create_b64_img(faulttype_plot), 'Break down of time charged to faults for the current reporting period, by system, by type and by shift', faultdfs)

    cleartime = timeacctsdf[timeacctsdf['projtype'].isin(['EC', 'FAULT', 'SCI', 'JCMTCAL', 'JCMTOTHER', 'NONTECH FAULT'])]
    cleartime = cleartime.groupby(cleartime.index).agg({'timespent': sum})

    faulttime =  timeacctsdf[timeacctsdf['projtype'].isin(['FAULT', 'NONTECH FAULT'])]
    faulttime = faulttime.groupby(faulttime.index).agg({'timespent': sum})

    combined = cleartime.join(faulttime.rename(columns={'timespent': 'faulttime'}))
    combined = combined.fillna(0.0)
    currentfaultrate_weekly, currentdf = plot_fault(combined, 'W', start, end, start)
    historicalfaultrate_weekly, historicaldf = plot_fault(combined, 'W', eao_start, end, start)
    faultdict['currentfault_weekly'] = (create_b64_img(currentfaultrate_weekly), 'Comparison of the weekly fault rate over the reporting period. The top plot shows the clear time (all time charged apart from weather or shutdown time) and fault time  per week, and the lower plot shows percentage of clear time lost to faults. A red line marks the target 5% fault rate.', currentdf)
    faultdict['historicalfault_weekly'] = (create_b64_img(historicalfaultrate_weekly), 'Comparison of the weekly fault rate since EAO took over operations in February 2015. The top plot shows the clear time (all time charged apart from weather or shutdown time) and fault time  per week, and the lower plot shows percentage of clear time lost to faults. A red line marks the target 5% fault rate, and a dashed black line shows the current reporting period.', historicaldf)

    onskydict = board_ops_observedtimeplots(start, end, session)

    weatherdict = weathercharts('WVMINFO', 7, 16, datetime.datetime(2015,2,1), start, end)
    return onskydict, faultdict, perdict, weatherdict

def make_shift_plots(shifts, extended=False, width=0.8):
    fig = Figure()
    sharey = None
    legend = False
    for i, shift in enumerate(shifts):
        if i > 0:
            sharey = sharedax
        ax = fig.add_subplot(1, len(shifts), i+1, sharey=sharey)
        if i == 0:
            sharedax = ax
        if i==len(shifts) - 1:
            legend = True
        df = shifts[shift]
        if not extended:
            df = df.drop(['JCMTEXTENDED'], axis=1)
        ax = df.plot.bar(stacked=True, cmap=faultscm, ax=ax, legend=legend, width=width)
        ax.set_xticklabels([j.strftime('%Y-%m') for j in shifts[shift].index])
        ax.set_title(shift)
        if i == len(shifts) - 1:
            handles, labels = ax.get_legend_handles_labels()
            ax.legend(handles[::-1], labels[::-1],bbox_to_anchor=(1, 1), title=False)
        if i == 0:
            ax.set_xlabel('hrs')
    fig.set_tight_layout(True)
    return fig


def faultbreakdown_plots(faultsdf):

    #faultsdf = faultsdf[faultsdf.date > start]
    faultsdf.timespent = faultsdf.timespent.astype(float)
    # Only faults with time lost
    faultsdf = faultsdf[faultsdf.timespent > 0]
    faultsdf = faultsdf.replace({'type': typedict, 'fsystem': systemdict})

    fsystemtime = faultsdf.groupby('fsystem').agg({'timespent': sum})
    typetime = faultsdf.groupby('type').agg({'timespent': sum})
    shifttime = faultsdf.groupby('shifttype').agg({'timespent': sum})
    faulttime_bytype =  Figure()
    ax1 = faulttime_bytype.add_subplot(131)
    ax2 = faulttime_bytype.add_subplot(132, sharey=ax1)
    ax3 = faulttime_bytype.add_subplot(133, sharey=ax1)
    fsystemtime.plot.bar(color='green', legend=False, ax=ax1)
    typetime.plot.bar(color='purple', legend=False, ax=ax2)
    shifttime.plot.bar(color='red', legend=False, ax=ax3)

    ax1.set_title('Fault time by System')
    ax2.set_title('Fault time by Type')
    ax3.set_title('Fault time by Shift')

    ax1.set_xlabel('')
    ax2.set_xlabel('')
    ax3.set_xlabel('')

    ax1.set_ylabel('Hours')

    faulttime_bytype.set_tight_layout(True)

    return faulttime_bytype, (fsystemtime, typetime, shifttime)


def create_shiftgroups(currtime, extended=False, width=0.8):
    regularshifts = {}
    extrashifts = {}
    for shift, group in currtime.groupby('shifttype'):
        summ = group.groupby([pd.Grouper(freq='M'), 'projtype']).sum().reset_index().pivot_table(index='date',
                                    columns=['projtype'], aggfunc='sum', margins=False, fill_value=0.0)
        summ.columns = summ.columns.droplevel(0)
        if (summ > 0).sum().sum() > 0:
            if shift in ['DAY', 'NIGHT', 'EO']:
                regularshifts[shift] = summ
            else:
                extrashifts[shift] = summ





    if len(regularshifts) > 0:
        regularshiftplot = make_shift_plots(regularshifts, extended=extended, width=width)
    if len(extrashifts) > 0 :
        extrashiftplot = make_shift_plots(extrashifts, extended=extended)
    summarydf = currtime.groupby([pd.Grouper(freq='M'), 'projtype', 'shifttype']).sum().reset_index().pivot_table(index='date', columns=['projtype', 'shifttype'], aggfunc='sum', margins=False, fill_value=0.0)
    summarydf.columns = summarydf.columns.droplevel(0)
    return regularshiftplot, extrashiftplot, (summarydf,)

def plot_fault(combined, freq, start, end, reportstart):
    resamp = combined.resample(freq).sum()
    resamp['fault_percent'] = 100 * resamp.faulttime/resamp.timespent
    resamp = resamp[resamp.index >= start]
    fig = fig = Figure()
    ax1 = fig.add_subplot(211)
    ax2 = fig.add_subplot(212, sharex=ax1)
    resamp[['timespent', 'faulttime']].plot(ax=ax1, drawstyle='steps-mid')
    resamp[['fault_percent']].plot(ax=ax2, drawstyle='steps-mid', legend=False)
    ax1.lines[0].set_label('Clear Time')
    ax1.lines[1].set_label('Fault Time')
    ax1.legend()
    ax2.set_ylabel('% fault')
    ax2.hlines(5.0, *ax2.get_xlim(), color='red')
    ax1.set_xlim(start, end)
    if start  < reportstart:
        ax1.vlines(reportstart, *ax1.get_ylim(), color='black', linestyle='dashed')
        ax2.vlines(reportstart, *ax2.get_ylim(), color='black', linestyle='dashed')
    ax1.set_ylabel('hrs')
    return fig, (resamp[['timespent', 'faulttime', 'fault_percent']],)

def create_b64_img(figure):
    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

    from io import BytesIO
    import base64

    canvas = FigureCanvas(figure)
    img = BytesIO()
    canvas.print_png(img)
    img.seek(0)
    png = base64.b64encode(img.getvalue())
    return png


def weathercharts(wvmfile, hourstart, hourend, weatherstart, startdate, enddate):

    weatherdict = OrderedDict()

    # Get WVM data from disk.
    wvmvalues = pd.read_csv(wvmfile, index_col='isoTime', parse_dates=['isoTime'])
    wvmvalues = wvmvalues.drop_duplicates()
    wvmvalues.replace(0, np.nan, inplace=True)

    hours = wvmvalues.index.hour + (wvmvalues.index.minute/60.0)

    nightlywvm = wvmvalues[(hours >=hourstart) & (hours <= hourend)]
    nightlywvm = nightlywvm.rename(columns={'mean':'wvmtau'})


    # plot of average WVM per night.
    dsampler = nightlywvm[['wvmtau']].resample('D')
    nightlywvm_daily = dsampler.mean()
    nightlywvm_daily['median'] = dsampler.median()
    nightlywvm_daily['count'] = dsampler.count()

    fig = Figure()
    ax = fig.add_subplot(111)
    bar1 = ax.bar(nightlywvm_daily.index, nightlywvm_daily['median'],
                      width=1, alpha=0.8, align='edge')
    ax.set_ylim(0,0.5)
    ax.set_xlim(weatherstart, enddate)

    missingdata = nightlywvm_daily['median'].isna().replace(True, 0.5)
    bar2 = ax.bar(nightlywvm_daily.index, missingdata, width=1, alpha=0.4,
                      align='edge', fc=bar1[0].get_facecolor(), zorder=0.8)
    bar3 = ax.bar(nightlywvm_daily.index, missingdata, width=1, alpha=0.2,
                      align='edge', fc='0.7', zorder=0.8)
    ax.fill_between(nightlywvm_daily.index, 0.0, 0.05, color='0.5', alpha=0.5,
                        zorder=0, edgecolor='none')
    ax.fill_between(nightlywvm_daily.index, 0.0, 0.08, color='0.5', alpha=0.5,
                        zorder=0, edgecolor='none')
    ax.fill_between(nightlywvm_daily.index, 0.0, 0.12, color='0.5', alpha=0.5,
                        zorder=0, edgecolor='none')
    ax.fill_between(nightlywvm_daily.index, 0.0, 0.2, color='0.5', alpha=0.5,
                        zorder=0, edgecolor='none')
    ax.set_ylabel('Opacity (225 GHz, WVM)')
    fig.autofmt_xdate()
    #plt.minorticks_on()
    fig.autofmt_xdate(which='minor')
    fig.set_tight_layout(True)

    weatherdict['nightlyopacity-time'] = (create_b64_img(fig), 'Median weather per night over time, based on the JCMT WVM values between %i and %i UT. Please note that the JCMT WVM does not produce any data when the telescope is not open.'.format(hourstart, hourend), ())

    # Make plot of monthly hours in each band (including unknown)
    bands = [0.0, 0.05, 0.08, 0.12, 0.2, 10.0]
    bandlabels = [1,2,3,4,5]
    wvmvalues['Grade'] = pd.cut(wvmvalues['mean'], bands, labels=bandlabels)#.values.add_categories('missing')
    #wvmvalues['Grade'] = wvmvalues['Grade'].fillna('missing')

    wvmbands_month_mean, month_mean_dfs = comparison_bandhours(wvmvalues, 0.5, startdate, enddate, frequency='month', hourstart=hourstart, hourend=hourend, avfunction='mean')
    weatherdict['wvmbands_monthcomparison_mean'] = (create_b64_img(wvmbands_month_mean), 'The time spent per night in a given weather band, summed over a whole month and compared with the mean historical values. All weather grade information come from the JCMT WVM, which is only active when the JCMT is open.', month_mean_dfs)
    wvmbands_month_median, month_median_dfs = comparison_bandhours(wvmvalues, 0.5, startdate, enddate,  frequency='month', hourstart=hourstart, hourend=hourend, avfunction='median')
    weatherdict['wvmbands_monthcomparison_media'] = (create_b64_img(wvmbands_month_median), 'The time spent per night in a given weather band, summed over each month of the reporting period and compared with the median historical values. All weather grade information come from the JCMT WVM, which is only active when the JCMT is open.', month_median_dfs)
    wvmbands_week_mean, week_mean_dfs = comparison_bandhours(wvmvalues, 0.5, startdate, enddate, frequency='week', hourstart=hourstart, hourend=hourend, avfunction='mean')
    weatherdict['wvmbands_weekcomparison_mean'] = (create_b64_img(wvmbands_week_mean), 'The time spent per night in a given weather band, summed over each week of the reporting period and compared with the mean historical values. All weather grade information come from the JCMT WVM, which is only active when the JCMT is open.', week_mean_dfs)
    wvmbands_week_median, week_median_dfs = comparison_bandhours(wvmvalues, 0.5, startdate, enddate, frequency='week', hourstart=hourstart, hourend=hourend, avfunction='median')
    weatherdict['wvmbands_weekcomparison_median'] = (create_b64_img(wvmbands_week_median), 'The time spent per night in a given weather band, summed over each week of the reporting period and compared with the mean historical values. All weather grade information come from the JCMT WVM, which is only active when the JCMT is open. Only time between %i and %i UT was considered.'%(hourstart, hourend), week_median_dfs)
    return weatherdict

def comparison_bandhours(wvm, hours_per_sample, startdate, enddate, frequency='month', hourstart=7, hourend=16, avfunction='mean'):

    """frequency can be month or week, avfunction is how historical data is combined (mean or median)"""

    # Do median
    bands = wvm[['Grade']]
    bands['count']  = [hours_per_sample] * len(bands)
    # Get the hours only at night
    hours = bands.index.hour + (bands.index.minute/60.0)
    bandsnight = bands[(hours >=hourstart) & (hours<=hourend)]
    bandsnight = bandsnight.asfreq('30min')
    bandsnight = bandsnight.set_index(bandsnight.index.set_names(['date']))

    #Split into data before and after the startdate.
    newdata = bandsnight[(bandsnight.index >= startdate)&(bandsnight.index < enddate)]
    olddata = bandsnight[(bandsnight.index < startdate) & (bandsnight.index < enddate)]
    if frequency == 'week':
        newsummary = newdata.pivot_table(columns=['Grade'], aggfunc='sum', index='date', dropna=False)
        newsummary = newsummary.groupby(newsummary.index.dayofyear//7, sort=False).sum()

        newsummary.index.name='week of year'
        # Need to rearrange so it goes from correct date to new
        a=olddata.pivot_table(columns=['Grade'], aggfunc='sum', index='date', dropna=False)
        oldaveragesummary = a.groupby([a.index.year, a.index.dayofyear//7]).sum()
        oldaveragesummary = oldaveragesummary.groupby(oldaveragesummary.index.get_level_values(1)).agg(avfunction)
        oldaveragesummary = oldaveragesummary[oldaveragesummary.index.isin(newsummary.index)].reindex(newsummary.index)
        oldaveragesummary.index.name='week of year'
    elif frequency == 'month':
        newsummary = newdata.pivot_table(columns='Grade', aggfunc='count', index='date', dropna=False).resample('M').sum()
        a=olddata.pivot_table(columns='Grade', aggfunc='count', index='date', dropna=False).resample('M').sum()
        oldaveragesummary = a.groupby(a.index.month).agg(avfunction)
        oldaveragesummary = oldaveragesummary[oldaveragesummary.index.isin(newsummary.index.month)].reindex(newsummary.index.month)


    # Create figures.
    fig = Figure()
    ax1, ax2 = fig.subplots(1,2, sharey=True, sharex=False)
    if frequency == 'month':
        width=0.8
    else:
        width=1.0
    newsummary.plot.bar(stacked=True, color=weather_colors, legend=False, ax=ax1, width=width)
    oldaveragesummary.plot.bar(stacked=True, color=weather_colors, legend=False, ax=ax2, width=width)
    if frequency == 'month':
        [i.set_edgecolor('black') for i in ax1.patches]
        [i.set_edgecolor('black') for i in ax2.patches]
        [i.set_hatch('//////') for i in ax1.patches[4*6:(5)*6]]
        [i.set_hatch('//////') for i in ax2.patches[4*6:(5)*6]]


    handles, _ = ax1.get_legend_handles_labels()
    labels = [1,2,3,4,5, 'unknown']
    ax2.legend(handles, labels, title='Weather Grade', bbox_to_anchor=(1,0.5), loc='center left')
    ax1.set_ylabel('Hours')
    if frequency == 'month':
        ax1.set_xticklabels([calendar.month_name[int(i.get_text().split('-')[1])] + ' ' + i.get_text().split('-')[0] for i in ax1.get_xticklabels()])
        ax2.set_xticklabels([calendar.month_name[int(i.get_text())] for i in ax2.get_xticklabels()])
    ax2.set_xlabel('')
    ax1.set_xlabel('')

    ax1.set_title('{}-{}'.format(startdate.strftime('%Y/%m'), enddate.strftime('%Y/%m')))
    ax2.set_title('{}-{} ({})'.format(olddata.index[0].strftime('%Y/%m'), olddata.index[-1].strftime('%Y/%m'), avfunction) )

    fig.set_tight_layout(True)
    return fig, (newsummary, oldaveragesummary)
