from collections import namedtuple, OrderedDict
OMPError = Exception

# Information about each state:
#     name: Human-readable name
#     caom_fail: should be marked as fail status in CAOM-2
#     caom_junk: should be marked as junk quality in CAOM-2
OMPStateInfo = namedtuple('OMPStateInfo', ('name', 'caom_fail', 'caom_junk'))


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
        (QUESTIONABLE, OMPStateInfo('Questionable',True,  False)),
        (BAD,          OMPStateInfo('Bad',         True,  False)),
        (REJECTED,     OMPStateInfo('Rejected',    False, False)),
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
