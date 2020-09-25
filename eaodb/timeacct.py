from collections import OrderedDict, namedtuple
import datetime

acc_summary = namedtuple('acc_summary', 'total total_unc project_time lost_tech lost_nontech lost weather other shutdown extended projects faultp faultptech')

def fault_nontechnical(fault):
    if fault.type==0 or fault.status==3:
        return True
    else:
        return False

FAKEPROJECTS=('JCMTEXTENDED', 'JCMTOTHER', 'JCMTWEATHER', 'JCMT_SHUTDOWN', 'UKIRTEXTENDED', 'UKIRTOTHER', 'UKIRT_SHUTDOWN')

    
class TimeAcctGroup(object):
    """Represent groups of time accounting objects"""
    def __init__(self, faults, timeaccts,
                 telescope='JCMT', projectinfo=None):

        # store the days, shifts, lists of timeacct objects and lists
        # of fault objects.
        self._faults = faults
        self._timeaccts = timeaccts
        self.telescope = telescope.upper()
            
        self.shifts = {}
        self.days = {}
        self.countries = {}
        self.projects = {}

        if timeaccts:
            for i in timeaccts:
                date = i.date.date()
                timelist, faultlist  = self.shifts.get(i.shifttype, [[],[]])
                self.shifts[i.shifttype] = [timelist + [i], faultlist]
                timelist, faultlist  = self.days.get(date, [[],[]])
                self.days[date] = [timelist + [i], faultlist]
                if i.projectid not in FAKEPROJECTS and i.project:
                    countries = set([j.country for j in i.project.queueinfo])
                else:
                    countries = []

                for c in countries:
                    clist = self.countries.get(c, [])
                    self.countries[c] = clist + [i]
                projectlist = self.projects.get(i.projectid, [])
                self.projects[i.projectid] = projectlist + [i]

        if faults:
            for i in faults:
                date = i.faultdate.date() if i.faultdate else datetime.datetime.strptime(str(i.faultid).split('.')[0], '%Y%m%d').date()
                timelist, faultlist  = self.shifts.get(i.shifttype, [[],[]])
                self.shifts[i.shifttype] = [timelist, faultlist + [i]]
                timelist, faultlist  = self.days.get(date, [[],[]])
                self.days[date] = [timelist, faultlist + [i]]


    def get_proj_timespent(self, projectid, shift=None, day=None):
        objs =   [i for i in self._timeaccts
                    if i.projectid==projectid
                    and (i.shifttype==shift or shift is None)
                    and (i.date.date()==day or day is None)]
        timespent = sum(i.timespent/(60.0*60.0) for i in objs)
        timespent_unconfirmed = sum(i.timespent/(60.0*60.0) for i in objs if i.confirmed==0)

        comments = [i.comment for i in objs if i.comment is not None]
        projinfo = next((i.project for i in self._timeaccts if i.projectid==projectid and i.projectid not in FAKEPROJECTS),None)

        return timespent, timespent_unconfirmed, comments, projinfo

    def get_faulttime(self, shift=None, day=None, technical=False):
        if not self._faults:
            return 0
        if technical is False:
            return float(sum(i.timelost for i in self._faults
                  if  fault_nontechnical(i)
                  and (i.shifttype==shift or shift is None)
                  and ( (i.faultdate and i.faultdate.date()==day) or day is None or i.faultid.startswith(day.strftime('%Y%m%d')) )))
        if technical is True:
            return float(sum(i.timelost for i in self._faults
                  if not fault_nontechnical(i)
                  and (i.shifttype==shift or shift is None)
                  and ( (i.faultdate and i.faultdate.date()==day) or day is None or i.faultid.startswith(day.strftime('%Y%m%d')))))


    def get_projecttime(self, shift=None, day=None):

        # For projects, need to get comments as above but also
        # confirmed/unconfirmed.
        projects = list(set(i.projectid for i in self._timeaccts
                       if (i.projectid=='{}CAL'.format(self.telescope) or not i.projectid.startswith(self.telescope))
                       and (i.shifttype==shift or shift is None)
                       and (i.date.date()==day or day is None)))
        print('projects in get-projecttime', projects)
        timespent = [self.get_proj_timespent(p, shift=shift, day=day) for p in projects]

        countries = set([t[-1].queueinfo[0].country for t in timespent])

        results = OrderedDict()
        for c in sorted(countries):
            ts = [t for t in timespent if t[-1].queueinfo[0].country==c]
            totaltime = sum(t[0] for t in ts)
            ts = sorted(ts, key=lambda x: x[-1].projectid)

            projects = [t[-1].projectid for t in ts]
            results[c] = (totaltime, OrderedDict(zip(projects, ts)))
        return results

    def get_total_time(self, shift=None, day=None):
      # Get total time in accountint system, including faults.
        total = sum(i.timespent for i in self._timeaccts
                    if (i.shifttype==shift or shift is None)
                    and (i.date.date()==day or day is None))/(60.0*60.0)
        timelost = self.get_faulttime(shift=shift, day=day, technical=True)
        timelost += self.get_faulttime(shift=shift, day=day, technical=False)
        total += float(timelost)
        total_unconfirmed = sum(i.timespent for i in self._timeaccts
                                if (i.shifttype==shift or shift is None)
                                and (i.date.date()==day or day is None)
                                and i.confirmed==0)/(60.0*60.0)
        return total, total_unconfirmed

    def get_total_projecttime(self, shift=None, day=None):
        projdict = self.get_projecttime(shift=shift, day=day)
        projecttime = sum(projdict[i][0] for i in projdict
                          if i!='JAC'
        )
        return projecttime

    def get_faultpercent(self, shift=None, day=None, technical=None):
        timelost_tech = self.get_faulttime(shift=shift, day=day, technical=True)
        timelost_nontech = self.get_faulttime(shift=shift, day=day, technical=False)
        timelost = timelost_tech + timelost_nontech
        total = self.get_total_time(shift=shift, day=day)[0]
        if not technical:
            return  100*float(timelost)/total if total > 0 else None
        else:
            return  100*timelost_tech/total if total > 0 else None

    def timeacct(self, shift=None, day=None):
        comments = True
        if day is None and len(self.days) > 1:
            comments=False
        if not self._faults:
            timelost_tech = 0.0
            timelost_nontech = 0.0
            timelost = 0.0
        else:
            timelost_tech = float(sum(i.timelost for i in self._faults
                                if not fault_nontechnical(i)
                                and (i.shifttype==shift or shift is None)
                                and ((i.faultdate and i.faultdate.date()==day) or day is None or i.faultdate.startswith(day.date().strftime('%Y%m%d')))))

            timelost_nontech = float(sum(i.timelost for i in self._faults
                                   if fault_nontechnical(i)
                                   and (i.shifttype==shift or shift is None)
                                   and ((i.faultdate and i.faultdate.date()==day) or day is None or i.faultdate.startswith(day.date().strftime('%Y%m%d')))))

            timelost = float(sum(i.timelost for i in self._faults
                           if (i.shifttype==shift or shift is None)
                           and ((i.faultdate and i.faultdate.date()==day) or day is None or i.faultdate.startswith(day.date().strftime('%Y%m%d')))))


        # For objects from the accounting system, need to get comments if comments==True
        weather = self.get_proj_timespent('{}WEATHER'.format(self.telescope), shift=shift, day=day)
        other = self.get_proj_timespent('{}OTHER'.format(self.telescope), shift=shift, day=day)
        shutdown = self.get_proj_timespent('{}_SHUTDOWN'.format(self.telescope), shift=shift, day=day)
        extended = self.get_proj_timespent('{}EXTENDED'.format(self.telescope), shift=shift, day=day)


        # For projects, need to get comments as above but also confirmed/unconfirmed.
        projdict = self.get_projecttime(shift=shift, day=day)

        


        # Get total time in accountint system, including faults.
        total = sum(i.timespent for i in self._timeaccts
                    if (i.shifttype==shift or shift is None)
                    and (i.date.date()==day or day is None))/(60.0*60.0)
        total += float(timelost)
        total_unconfirmed = sum(i.timespent for i in self._timeaccts
                                if (i.shifttype==shift or shift is None)
                                and (i.date.date()==day or day is None)
                                and i.confirmed==0)/(60.0*60.0)

        projecttime = self.get_total_projecttime(shift=shift, day=day)


        fault_percent = 100*float(timelost)/total if total > 0 else None
        fault_percenttechnical = 100*timelost_tech/total if total > 0 else None

        return acc_summary(total, total_unconfirmed, projecttime,
                           timelost_tech, timelost_nontech, timelost, weather,
                           other, shutdown, extended, projdict, fault_percent, fault_percenttechnical)
