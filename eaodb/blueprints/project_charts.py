import plotly.graph_objects as go
import plotly.express as px
import plotly.colors as plc
from io import StringIO
INCLUDE_PLOTLYJS='cdn'
import datetime
import numpy as np
import pandas as pd

from astropy.time import Time as aTime
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy import units as u
#from itertools import cycle

layout = go.Layout(
  margin=go.layout.Margin(
        l=20, #left margin
        r=20, #right margin
        b=20, #bottom margin
        t=30, #top margin
    )
)


def completion_piechart(proj):
    completion = float(proj.completion)
    used = float(proj.used)/(60.0*60) if proj.used > 0 else 0
    allocated = float(proj.allocated)/(60.0*60.0) if proj.allocated > 0 else 0

    labels=['{:.1f}% Complete<br>({:.1f}/{:.1f} hrs)'.format(completion, used, allocated), ' ']
    values = [completion, 100 - completion]
    colors = ['gold', 'darkgray']
    colors = ['gold', 'darkgray']
    fig = go.Figure(data=[go.Pie(labels=labels, values=values,
                                     textinfo='label', textfont_size=10,
                insidetextorientation='auto', hoverinfo='none',
                direction='counterclockwise', showlegend=False, sort=False
                                )], layout=layout,)
    fig.update_traces(textinfo='label', marker=dict(colors=colors, line=dict(color='white', width=4)))
    fig.update_layout(width=200, height=250,  title='Completion', title_font_size=15)
    config = {'staticPlot': True}
    str_form = StringIO()
    fig.write_html(str_form, include_plotlyjs=INCLUDE_PLOTLYJS,
                       config={'staticPlot': True, 'responsive': True},
                       full_html=False)
    str_form.seek(0)
    return str_form.read()

def completion_cumulative(proj):
    timecharged = proj.timecharged
    dates = {}
    unconfirmed = 0
    for i in timecharged:
        if i.confirmed:
            dates[i.date] = dates.get(i.date, 0) + i.timespent/(60.0*60.0)
        else:
            unconfirmed += i.timespent/(60.0*60.0)


    
    dates_sorted = sorted(dates.keys())
    cumulative = [0]
    for i in dates_sorted:
        cumulative += [cumulative[-1] + dates[i]]
    fig = go.Figure(go.Scatter(x=dates_sorted, y=cumulative[1:]), layout=layout,)
    if len(dates_sorted) > 0:
        end_date = min(datetime.date.today(), dates_sorted[-1].date() + datetime.timedelta(days=6*30))
        start_date = dates_sorted[0]
    else:
        end_date = datetime.date.today()
        start_date = datetime.date.today()

    fig.update_xaxes(range=[start_date, end_date], title='Date')
    fig.update_yaxes(range=[0,max(float(proj.allocated)/(60.0*60.0), cumulative[-1])], title='Hrs')
    fig.update_layout(width=300, height=250, title='Cumulative Time Spent', title_font_size=15)
    str_form = StringIO()
    fig.write_html(str_form, include_plotlyjs=INCLUDE_PLOTLYJS,
                       config={'staticPlot': False, 'responsive': True},
                       full_html=False)
    str_form.seek(0)
    return str_form.read()




def observability(msbs, utdate=None, semesterdates=None, multiproject=False):
    """
    Create a plot of observability ala source plot, for all sources in msb list.

    msbs: list of msbinfo objects
    figure: matplotlib figure object.
    utdate: datetime.date object
    semesterdates: start and end tuples for semester.

    Returns a figure object.
    """
    msbs = [(obs.coordstype,
            float(obs.ra2000) if obs.ra2000 is not None else None,
            float(obs.dec2000) if obs.dec2000 is not None else None, obs.target)
                 for msb in msbs
                     for obs in msb.plannedobs if obs is not None]
    if not utdate:
        utdate = datetime.date.today()
    # Get telescope position.
    jcmt = EarthLocation(lat=19.82283890588*u.degree,
                         lon=-155.4770278387 *u.degree, height=4120.0*u.meter)

    #get time information.
    utcoffset = -10*u.hour 
    time = utdate.strftime('%Y-%m-%d 0:00:00') # Today

    midnight_hi = aTime(time) - utcoffset
    delta_midnight = np.linspace(-12,12,100)*u.hour
    frame_tonight = AltAz(obstime=midnight_hi + delta_midnight, location=jcmt)

    # semester stuff
    #start=aTime(semesterdates[0].strftime('%Y-%m-%d'))
    #end = aTime(semesterdates[1].strftime('%Y-%m-%d'))
    #delta = end - start
    #semtimes = start + np.linspace(0, delta.value-1, delta.value) * u.day

    # Get Coordinate type from msb
    coordstypes = set([i[0] for i in msbs])
    plotdict={}
    coorddict={}


    # Go through each type of coordinates.
    for coord in coordstypes:
        print('\n\nCOORDSTYPE is {}\n\n'.format(coord))
        if coord == 'RADEC':
            ra = [i[1] for i in msbs if i[0]==coord]
            dec = [i[2] for i in msbs if i[0]==coord]
            if not multiproject:
                labels = [i[3] for i in msbs if i[0]==coord]
            else:
                labels = ['{}: {}'.format(i[4], i[3]) for i in msbs if i[0]==coord]
                projects = [i[4] for i in msbs if i[0]==coord]
                projectcolors = {}
                for p in set(projects):
                    projectcolors[p] = next(cycler)
                colors = [projectcolors[i[4]] for i in msbs if i[0]==coord]

            coords = SkyCoord(ra=np.rad2deg(ra)*u.degree,
                              dec=np.rad2deg(dec)*u.degree,
                              frame='fk5')
            coorddict[coord] = coords
            sources_tonight = coords[:, np.newaxis].transform_to(frame_tonight)
            plotdict[coord] = sources_tonight, labels
        else:
            print('WARNING: CANNOT SHOW NON RADEC MSBS YET!')


    title='MSB Source observability at {}'.format(utdate.strftime('%Y-%m-%d'))
    coord, labels = plotdict.get('RADEC', (None, None))
    if coord:
        times = np.array([delta_midnight.value]*(len(coord.alt.value))).swapaxes(0,1) * u.hour
        pcoords = coord.alt.value.swapaxes(0,1)
        
        df = pd.DataFrame(pcoords, index=times[:,0], columns=labels)

        #data=[go.Scatter(x=times[:,0], y=pcoords, showlegend=False, mode='lines')]
        fig = go.Figure(layout=layout)
        for name, col in df.iteritems():
            fig.add_trace(go.Scatter(x=times[:,0], y=col, mode='lines', name=name))
        #fig = px.line(df, title=title)

        #if multiproject:
        #    for l, c in zip(lines, colors):
        #        l.set_color(c)
     
        fig.update_yaxes(range=[0,90], title='Altitude')
        tickvals = np.arange(-12, 12, 2)
        ticklabels = tickvals.copy()
        ticklabels[ticklabels<0] = tickvals[tickvals<0] + 24
        fig.update_xaxes(range=[-12,12], title='Time (HST)', tickvals=tickvals, ticktext=ticklabels)
        fig.update_layout( margin=go.layout.Margin(
        l=20, #left margin
        r=20, #right margin
        b=20, #bottom margin
        t=30, #top margin
    ))
        fig.update_layout(width=500, height=250, legend_title_text='Source', title_font_size=15,
                              title=title)
    
        str_form = StringIO()
        fig.write_html(str_form, include_plotlyjs=INCLUDE_PLOTLYJS,
                        config={'staticPlot': False, 'responsive': True},
                        full_html=False)
        str_form.seek(0)
        return str_form.read()
    else:
        return ''

