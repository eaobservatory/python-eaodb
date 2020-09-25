"""
Tools for handling observations information.
"""

from collections import OrderedDict

from flask import Markup

# Constants

OMP_OBSCOMMENT_LINK = "http://omp.eao.hawaii.edu/cgi-bin/staffobscomment.pl?oid={obsid}&inst={instrument}&runnr={obsnum}&ut={date_obs}"

PROCSTRING = '<a href="https://www.eao.hawaii.edu/processing/job/{jobid}">Job {jobid}<br/><img class="tableprevimg" src="https://www.eao.hawaii.edu/processing/job/{jobid}/preview/{filename}"></a>'

OBSCOMMENT_TIMEFORMAT = '%Y-%m-%d-%H-%M-%S'


# Bandwidths
het_bandwidth = [('1000MHzx1024','1000MHz 1024'),
                     ('1000MHzx2048', '1000MHz 2048'),
                     ('250MHzx4096', '250MHz 4096'),
                     ('250MHzx8192', '250MHz 8192'),
                     ('other', 'Other')
                     ]

het_swmode = [('chop', 'Chop'), ('pssw', 'PSSW'), ('freqsq', 'Freq. SW')]

obs_type = [('science', 'Science'),
                ('pointing', 'Pointing'),
                ('focus', 'Focus'),
                ('setup', 'Setup'),
                ('noise', 'Noise'),
                ('skydip', 'Skydip'),
                ('flatfield', 'Flatfield')]

# Scan patterns
jcmt_scanpatterns = [('raster', 'Raster'),
                     ('grid', 'Grid'),
                     ('jiggle', 'Jiggle'),
                     ('CURVY_PONG', 'Pong'),
                     ('CV_DAISY', 'Daisy'),
                     ('stare', 'S2-Stare'),]
    
scanpattern_lookup = {'raster': ['DISCRETE_BOUSTROPHEDON','raster','RASTER',], 'CV_DAISY': ['CV_DAISY', 'DAISY']}

OMPSTATUS = {
    0: 'Good',
    1: 'Quest.',
    2: 'Bad',
    3: 'Reject',
    4: 'Junk',
}
    
FORMATS = {
    'AvWVM': '{:.2f}',
    'Seeing': '{:.2f}',
    'Completion': '{:.1f}',
    }

jcmt_instruments = [('SCUBA2','SCUBA-2'),
                    ('POL2', 'POL-2'),
                    ('HARP', 'HARP'),
                    ('RxA3M','RxA3m'),
                    ('UU', 'ʻŪʻū'),
   
                    ]
ompstatus = [
    ('0', 'Good'),
    ('1', 'Quest.'),
    ('2', 'Bad'),
    ('4', 'Junk'),
    ('3', 'Reject'),
    ]
         
TIMEGAPSTATUS = {
    10: 'INST.',
    11: 'WEATHER',
    12: 'FAULT',
    14: 'NEXT PRJ',
    15: 'PREV PRJ',
    16: 'NON DRIVER',
    17: 'SCHEDULED',
    18: 'OVERHEAD',
    19: 'LOGISTICS',
    13: 'UNKNOWN',
}

FAULTSTATUS = {
    0: 'Open',
    1: 'Closed',
    2: 'WorksForMe',
    3: 'NotAFault',
    4: 'WontBeFixed',
    5: 'Duplicate',
    6: 'OpenWillBeFixed',
    7: 'Suspended',
}

OMPSTATUS = {
    0: 'Good',
    1: 'Quest.',
    2: 'Bad',
    3: 'Reject',
    4: 'Junk',
}

FEEDBACKSTATUS = {
    1: 'INFO',
    2: 'IMPORTANT',
    0: 'HIDDEN',
    3: 'SUPPORT',
    }



# Ways to format things for obslog display
def format_obslog_mode(obs):
    return '<br>'.join(obs.log_mode.split('_'))

def obslog_dateformat(dateobj):
    return dateobj.strftime('%H:%M:%S')
def obslog_dateformat_multi(dateobj):
    return dateobj.strftime('%Y-%m-%d<br>%H:%M:%S')

def format_dateobs_multi(obs):
    return format_dateobs(obs, timeonly=False)

def format_dateobs(obs, timeonly=True):
    if timeonly:
        time = obs.date_obs.strftime('%H:%M:%S')
    else:
        time = obs.date_obs.strftime('%Y-%m-%d<br>%H:%M:%S')
    return '{}<br>{:.1f} min'.format(time, obs.duration/60.0)

def format_waveband(obs):
    output = []
    for i in obs.acsis:
        if i.molecule and i.molecule != 'No Line':
            output += ['{} {}'.format(i.molecule, i.transiti.replace(' ', ''))]
        else:
            output += ['{:.1F} GHz'.format(float(i.restfreq))]
    return '<br>'.join(output)
                           
def format_restfreq(obs):
    return '<br>'.join(['{:.1f} GHz'.format(i.restfreq) for i in obs.acsis]).lstrip()
def format_molecule(obs):
    return '<br>'.join(['{} {}'.format(
        i.molecule if i.molecule != 'No Line' else 'No',
        i.transiti.replace(' ','') if i.transiti != 'No Line' else 'Line')
                      for i in obs.acsis])

def format_velocity(obs):
    return '<br>'.join(
        ['{:.1f} {}'.format(i.zsource, i.doppler).strip()
         for i in obs.acsis]
    )

def format_bwmode(obs):
    return '<br>'.join([str(i.bwmode) for i in obs.acsis])




def get_comment_link(obs):
    return OMP_OBSCOMMENT_LINK.format(obsid=obs.obsid,
                                      instrument=obs.instrume,
                                      obsnum=obs.obsnum,
                                      date_obs=obs.date_obs.strftime(OBSCOMMENT_TIMEFORMAT)
                                  )
def format_ompcomments(obs):
    """
    Print the list of comments, show full list as a tooltip.
    Hyperlink to the link to change the comment.
    """
    comment_link = '<a href="{}">update comment</a>'.format(get_comment_link(obs))

    if obs.obslog_comments:
        if len(obs.obslog_comments) > 1:
            allobscomments = '<br>'.join(format_obscomment(i) for i in obs.obslog_comments)
        else:
            allobscomments = ""
        comment_text = '<div class="obscomment" title="{}"><pre>{}</pre></div>'.format(
            allobscomments,
            format_obscomment(obs.latest_ompcomment))
    else:
        comment_text = ''
    return comment_link + '<br>' + comment_text


def formatprocjobs(job, filename):
    if job:
        return PROCSTRING.format(jobid=job, filename=filename)

def format_previews(obs):
    results = obs.get_processing_links()
    previewstr = '<div class="preview-{backend}">{procjobs_info}</div>'
    output = ''
    if results:
        for info in results:
            if info:
                output += previewstr.format(backend=obs.backend,
                                            procjobs_info=formatprocjobs(info[0], info[1]))
    return output

def format_obscomment(comment, join='<br>'):
    OBSCOMMENT = """{status}{join}{author}:{date}{join}{text}"""
    return Markup(OBSCOMMENT.format(status=OMPSTATUS.get(comment.commentstatus, 'UNKNOWN'),
                             join=join,
                             author = comment.commentauthor,
                             date=comment.commentdate.strftime('%Y-%m-%d %H:%M:%S'),
                             text=comment.commenttext))            



# Default headers sets.
INITIAL_HEADERS = OrderedDict(
    UT=format_dateobs_multi,
    Scan='obsnum',
    Mode=format_obslog_mode,
    Project='project',
    Source='object',
)
END_HEADERS = OrderedDict(
    Grade='band',
    Shift='oper_sft',
    Status='ompstatus',
    Comments=format_ompcomments,
    Previews=format_previews,
)
SCUBA2_HEADERS = OrderedDict(
    Inbeam='inbeam',
    Seeing='avseeing',
    AvWVM='avwvm',
)
ACSIS_HEADERS = OrderedDict(
    Waveband=format_waveband,
    Velocity=format_velocity,
    Bandwidth=format_bwmode,
)

OTHER_ACSIS_HEADERS = dict(
    Molecule=format_molecule,
    Velocity=format_velocity,
    RestFreq=format_restfreq,
)


# Define the default values
DEFAULT_ACSIS_COLUMNS = INITIAL_HEADERS.copy()
DEFAULT_ACSIS_COLUMNS.update(ACSIS_HEADERS)
DEFAULT_ACSIS_COLUMNS.update(END_HEADERS)


DEFAULT_SCUBA2_COLUMNS = INITIAL_HEADERS.copy()
DEFAULT_SCUBA2_COLUMNS.update(SCUBA2_HEADERS)
DEFAULT_SCUBA2_COLUMNS.update(END_HEADERS)


def get_commentdict():

    S2_HEADERCOMMENTS={}
    with open('scuba2_fitsheaders.txt','r') as comfile:
        for line in comfile:
            name, var = line.partition('=')[::2]
            S2_HEADERCOMMENTS[name.strip().replace('-','_').lower()] = var.strip()

    ACSIS_HEADERCOMMENTS={}
    with open('acsis_fitsheaders.txt','r') as comfile:
        for line in comfile:
            name, var = line.partition('=')[::2]
            ACSIS_HEADERCOMMENTS[name.strip().replace('-','_').lower()] = var.strip()
    COMMENTDICT={}
    COMMENTDICT['ACSIS']=ACSIS_HEADERCOMMENTS
    COMMENTDICT['SCUBA-2']=S2_HEADERCOMMENTS
    return COMMENTDICT


def get_columns(r):
    columns = OrderedDict()
    columns.update(INITIAL_HEADERS)
    if r.backend == 'ACSIS':
        columns.update(ACSIS_HEADERS)
    elif r.backend == 'SCUBA-2':
        columns.update(SCUBA2_HEADERS)
    columns.update(END_HEADERS)
    return columns

# Obs values to include at all -- display name, attribute name, default text format, default html format


# # custom values to create
# UT
# waveband
# velocity
# bandwidth
# Comments
# previews
# # All having 
