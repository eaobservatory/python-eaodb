"""
Constants and classes for easily handling constants in the OMP/JCMT etc databases
"""
from collections import namedtuple, OrderedDict
# A variety of OMP constants
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
OMPStateInfo = namedtuple('OMPStateInfo', ('name', 'caom_fail', 'caom_junk'))


MSBDONESTATUS = {
    0: 'Fetched',
    1: 'Done',
    2: 'Removed',
    3: 'Comment',
    4: 'Undone',
    5: 'Rejected',
    6: 'Suspended',
    7: 'Aborted',
    8: 'Unremoved',
}

FEEDBACKSTATUS = {
    1: 'INFO',
    2: 'IMPORTANT',
    0: 'HIDDEN',
    3: 'SUPPORT',
    }


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

    # Taken from jsa_proc. This should be factored 
class OMPState:
    """Class for handling OMP observation states.
    """

    GOOD = 0
    QUESTIONABLE = 1
    BAD = 2
    REJECTED = 3
    JUNK = 4

    _info = OrderedDict((
        (GOOD,         OMPStateInfo('Good',        False, False)),
        (QUESTIONABLE, OMPStateInfo('Quest.',True,  False)),
        (BAD,          OMPStateInfo('Bad',         True,  False)),
        (REJECTED,     OMPStateInfo('Reject',    False, False)),
        (JUNK,         OMPStateInfo('Junk',        True,  True)),
    ))

    STATE_ALL = tuple(_info.keys())
    STATE_NO_COADD = set((JUNK, BAD))

    @classmethod
    def get_name(cls, state):
        """
        Return the human-readable name of the state.

        Raises OMPError if the state does not exist.
        """

        try:
            return cls._info[state].name
        except KeyError:
            raise OMPError('Unknown OMP state code {0}'.format(state))

    @classmethod
    def is_valid(cls, state):
        """
        Check whether a state is valid.

        Returns True if the state exists.
        """

        return state in cls._info

    @classmethod
    def is_caom_fail(cls, state):
        """
        Return whether the state should be marked as a failure in CAOM-2.
        """

        try:
            return cls._info[state].caom_fail
        except KeyError:
            raise OMPError('Unknown OMP state code {0}'.format(state))

    @classmethod
    def is_caom_junk(cls, state):
        """
        Return whether or not the state should be marked junk in CAOM-2.
        """

        try:
            return cls._info[state].caom_junk
        except KeyError:
            raise OMPError('Unknown OMP state code {0}'.format(state))

    @classmethod
    def lookup_name(cls, name):
        """Return the state code corresponding to the given name.

        Raises OMPError if the state name is not recognised.

        Names are compared in a case-insensitive manner.
        """

        lowername = name.lower()

        for (state, info) in cls._info.items():
            if lowername == info.name.lower():
                return state

        raise OMPError('Unknown OMP state name {0}'.format(name))


class Bands:
    """ class for weather info"""
    BAND1 = [0,0.05]
    BAND2 = [0.05, 0.08]
    BAND3 = [0.08, 0.12]
    BAND4 = [0.12, 0.2]
    BAND5 = [0.2, 100]

    @classmethod
    def get_band(self, tau):
        """ Return the band a given tau is in."""
        if tau < self.BAND1[1]:
            return 1
        elif tau < self.BAND2[1]:
            return 2
        elif tau < self.BAND3[1]:
            return 3
        elif tau < self.BAND4[1]:
            return 4
        elif tau >= self.BAND5[0]:
            return 5
        else:
            return np.nan
    @classmethod
    def get_fromname(self, name):
        if int(name) == 1:
            return self.BAND1
        elif int(name) == 2:
            return self.BAND2
        elif int(name) == 3:
            return self.BAND3
        elif int(name) == 4:
            return self.BAND4
        elif int(name) == 5:
            return self.BAND5
        else:
            return 'unknown'

    def get_bands(tau):
        """
        Turn lists of 225 GHz taus into JCMT bands.
        """

        tau = np.asarray(tau)
        bands = np.zeros(tau.shape)

        band1 = tau < BAND1[1]
        band2 = (tau >= BAND2[0]) & (tau < BAND2[1])
        band3 = (tau >= BAND3[0]) & (tau < BAND3[1])
        band4 = (tau >= BAND4[0]) & (tau < BAND4[1])
        band5 = (tau >= BAND5[0])

        bands[band1] = 1
        bands[band2] = 2
        bands[band3] = 3
        bands[band4] = 4
        bands[band5] = 5

        return bands
