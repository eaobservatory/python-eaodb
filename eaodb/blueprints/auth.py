from flask import Blueprint, render_template, flash, request, redirect, url_for, current_app, abort, session
from flask_login import current_user, login_user, \
    logout_user, login_required
from flask_wtf import FlaskForm
import wtforms
from wtforms import validators
from flask_ldap3_login import AuthenticationResponseStatus
from sqlalchemy import func
from eaodb.webapp import db

# Supporting python2 and python3
try:
    from urllib.parse import urlparse, urljoin
except ImportError:
    from urlparse import urlparse, urljoin

# Required for support version 2 and 3; to remove replace unicode with str
import sys
if sys.version_info[0]>=3:
    unicode = str

import logging
logger = logging.getLogger(__name__)

#from .flask_app import login_manager
import crypt

from .user_model import LDAPUser, HedwigUser
#from ..util import create_readonly_scoped_session
from .. import omp, hedwig2omp

#ReadOnlySession = create_readonly_scoped_session()

# Set up authorization blueprint.
auth = Blueprint('auth', __name__)



@auth.before_request
def get_current_user():
    logger.debug('Getting current user %s', current_user)
    if hasattr(current_user, 'username'):
        print(current_user.username)
    else:
        print('no user name')
    user = current_user

#from hedwig.config import get_database as hedwig_get_database



# For this to work
#hedwigdb = hedwig_get_database()


# Login Form and View
class MultiTypeLoginForm(FlaskForm):
    username = wtforms.StringField('Username', validators=[validators.Required()])
    password = wtforms.PasswordField('Password', validators=[validators.Required()])
    submit = wtforms.SubmitField('Submit')
    remember_me = wtforms.BooleanField('Remember Me', default=True)
    logintype = wtforms.RadioField('Login Type',
                                   choices=[('username', 'Username & Password'),
                                            #('omp', 'Project ID & Project Password'),
                                            ('ldap','Staff Login via ldap')],
                                   validators=[validators.Required()])


    # def validate_omp_project_password(self):
    #     logger.debug('Validing LoginForm with project id and project password')
    #     # These are stored in the database as plain text.
    #     rsession = ReadOnlySession()
    #     encrypted_db = rsession.query(omp.proj.encrypted).filter(
    #         omp.proj.projectid==self.username.data).one_or_none()[0]
    #     salted_password = crypt.crypt(self.password.data, salt=encrypted_db)
    #     if encrypted_db == salted_password:
    #         self.user = ProjectUser(self.username.data)
    #         login_user(self.user)
    #         return True
    #     else:
    #         self.user = None
    #         return False

    # def validate_username_password(self):
    #     """
    #     Currently looking this up in a file with test (fake) hash
    #     passwords for a couple of user names; should eventually access
    #     hediwg login, via Oauth.
    #     """



    #     # For this to work you must have a connection to the hedwig database.
    #     hedwigdb = hedwig_get_database()
    #     hedwig_id = hedwigdb.authenticate_user(self.username.data, self.password.data)
    #     if hedwig_id is not None:
    #         rsession =  ReadOnlySession()
    #         OMP_username = rsession.query(hedwig2omp.user.omp_id).\
    #                    filter(hedwig2omp.user.hedwig_id==hedwig_id).one_or_none()[0]
    #         rsession.close()
    #         print(self.username.data, OMP_username)
    #         self.user = HedwigUser(hedwig_id, OMP_username)
    #         login_user(self.user)
    #         return True
    #     else:
    #         self.user = None
    #         return False

    def validate_ldap(self):
        """
        Taken from the flask_ldap3_login form, but with different user saving.
        """
        logging.debug('Validating LoginForm against LDAP')
        ldap_mgr = current_app.ldap3_login_manager
        username = self.username.data
        password = self.password.data

        result = ldap_mgr.authenticate(username, password)

        if result.status == AuthenticationResponseStatus.success:
            self.user = LDAPUser(result.user_id, result.user_info)
            login_user(self.user)
            return True

        else:
            self.user = None
            self.username.errors.append('Invalid Username/Password.')
            self.password.errors.append('Invalid Username/Password.')
            return False

    def validate(self, *args, **kwargs):
        """
        Validates the form by calling `validate` on each field, passing any
        extra `Form.validate_<fieldname>` validators to the field validator.

        also calls `validate_ldap`

        If it is successful at loggin in, it will create a form.user
        User object in the output.
        """

        logging.debug(' Form validation in progress')
        valid = FlaskForm.validate(self, *args, **kwargs)
        if not valid:
            logging.debug("Form validation failed before we had a chance to "
                          "check ldap. Reasons: '{0}'".format(self.errors))
            return valid

        print(self.logintype.data, type(self.logintype.data))
        if self.logintype.data == 'ldap':

            logging.debug('IN LDAP VALIDARTION')
            return self.validate_ldap()



@auth.route("/login", methods=['GET', 'POST'])
def login():
    try:
        if current_user.is_authenticated:
            flash('You are already logged in.')
            return redirect(request.path)
    except:
        pass
    form = MultiTypeLoginForm()
    if form.validate_on_submit():

        print(form.user)
        login_user(form.user)
        logging.debug('Logged in succesfully?')
        flash('Logged in successfully')
        next = request.args.get('next')

        if not is_safe_url(next):
            return abort(400)

        return redirect(next or url_for('project.project_search'))

    return render_template('login.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    print(session)
    logout_user()
    print(session)
    return redirect(url_for('project.project_search'))


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc
