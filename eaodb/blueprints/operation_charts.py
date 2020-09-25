"""
Operation tracking charts

"""
import pandas as pd
from sqlalchemy.orm import object_session

from io import StringIO
import plotly.express as px
import plotly.graph_objects as go

from eaodb.relationships import Project
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
        
        

#df=df.groupby(['instrument', 'queue', 'band'], as_index=False).sum()

# plot the observed values
#agged = df.groupby(['instrument', 'band', 'queue'], as_index=False).sum()

