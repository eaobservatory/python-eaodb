from flask_login import UserMixin

from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import func

#from eaodb.util import create_readonly_all_engine
from eaodb import omp, hedwig2omp

from eaodb.webapp import db

#ReadOnlySession = scoped_session(sessionmaker(create_readonly_all_engine(), autoflush=False, autocommit=False))


# We need to support:
#
#  - ldap login: for staff
#  - username/password login (with hedwig usernames and passwords) for everyone in Hedwig.
#  - historical projectcode and password logins (omp-style)




# user needs a property:
#  - is staff
#  - is project (for project passwords)
#  - is hedwig (for hedwig names)

# Support these as booleans in case we want to allow e.g. staff access
# for some other type of user.


# Define User data-model Role aspects are modelled after the
# Flask-User aspects, but without the database requirements.
class User(UserMixin):

    def get_projects(self, capacity='PI'):
        query = db.session.query(omp.proj)
        query = query.join(omp.projuser, omp.projuser.projectid==omp.proj.projectid)
        query = query.filter(omp.projuser.userid == self.OMP_username)
        query = query.filter(omp.projuser.capacity == capacity)
        projects = [i for i in query.all()]
        return projects
    

    def roles(self):
        """ Returns list of user's role names.

        roles are normally e.g. 'staff' or
        a project name; others might be added in the future.
        """

        roles = []
        # if logged in via ldap, then if in 'staff' group have property staff.
        if self.staff:
            roles += ['staff']

        if self.project:
            roles += ['project-{}'.format(self.projectid)]

        if self.OMP_username:
            roles += ['project-{}'.format(i[0])
                      for i in get_omp_projects(self.OMP_username)]
        return roles


    def has_roles(self, *required_roles):
        """Return True iff user has all required_roles.

        Takes a list of required roles, e.g.
        has_roles(required_role1, required_role2, required_role3)

        Each required_role is the name of a role, or a tuple of roles.

        A tuple indicates the user needs *one* of the roles in the tuple.
        A single role name indicates the user must have that exact role.
        """

        user_roles = self.roles

        for role in required_roles:
            if isinstance(role, (list, tuple)):
                tuple_of_role_names = role
                authorized = False
                for role_name in tuple_of_role_names:
                    if role_name in user_roles:
                        authorized = True
                        break
                if not authorized:
                    return False
            else:
                role_name = role
                if not role_name in user_roles:
                    return False
        return True



class HedwigUser(User):
    def __init__(self, userid, OMP_username):
        self.username = userid
        self.id = 'hedwig-{}'.format(userid)
        self.OMP_username = OMP_username

        self.staff = False
        self.hedwig = True



class LDAPUser(User):
    def __init__(self, user_id, user_info):
        self.username = user_id
        self.id = 'ldap-{}'.format(self.username)
        self.hedwig = False

        # Check if they are staff (I'm assuming 'eaoperson' is the
        # appropriate objectClass?)
        if 'eaoperson' in user_info['objectClass']:
            self.staff = True

        # Get their OMP username as well. If they are in the session,
        # get it from there. Otherwise log it from the database (or if
        # logging in force it from the database).
        
        #rsession =  ReadOnlySession()
        self.OMP_username = db.session.query(omp.user.userid).\
                            filter(omp.user.alias==func.upper(self.username)).one_or_none()
        #rsession.close()


# Loading user -- need to know which it is.  This requires a function
# that takes the ID, and returns the user. To be simple, we will first
# of all do this by requerying the relevant databases. Ultimately this
# may need to be stored in a server-side session for performance
# reasons?

from flask import current_app

def create_user(user_id):
    # Get type first: this is first part of username.
    user_type = user_id.split('-')[0]

    # Now get the name.
    user_name = '-'.join(user_id.split('-')[1:])
    print(user_type, user_name, type(user_name))
    if user_type == 'project':
        user = ProjectUser(user_name)

    elif user_type == 'hedwig':
        hedwig_id = int(user_name)
        rsession = ReadOnlySession()
        omp_username = rsession.query(hedwig2omp.user.omp_id).\
                       filter(hedwig2omp.user.hedwig_id==hedwig_id).one_or_none()

        user = HedwigUser(user_name, omp_username)

    if user_type == 'ldap':
        # Need to look this up in system.
        ldap_mgr = current_app.ldap3_login_manager
        user_info = ldap_mgr.get_user_info_for_username('sgraves')
        user_id = user_info['uid'][0]
        user = LDAPUser(user_id, user_info)

    else:
        user = None
    return user





def get_omp_projects(OMPusername):
    """
    Returns a list of OMP projectids for a given user. Include
    everything they are a CO or a PI on.
    """
    #rsession =  ReadOnlySession()
    query = db.session.query(omp.projuser.projectid)
    query = query.filter(omp.projuser.userid==OMPusername)
    query = query.filter(omp.projuser.capacity.in_(['COI', 'PI']))
    projects = [i for i in query.all()]
    return projects



