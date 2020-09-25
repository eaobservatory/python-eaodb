


from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from eaodb.util import get_config
from eaodb import relationships


db = SQLAlchemy(model_class=relationships.jcmt.Base)

from eaodb.blueprints.auth import auth
from eaodb.blueprints.project import project
from eaodb.blueprints.observations import obs
from eaodb.blueprints.operations import ops
from flask_bootstrap import Bootstrap

from flask_login import LoginManager, current_user
from flask_ldap3_login import LDAP3LoginManager
from flask_login import login_required
from .util import get_ldap_config


def create_app(port):
    app = Flask(__name__, static_folder='../static/', template_folder='../templates/')
    config = get_config()
    app.config['SQLALCHEMY_DATABASE_URI'] = config.get('DATABASE_READONLY', 'remoteurl').format(port)
    app.config['SQLALCHEMY_ECHO'] = bool(int(config.get('DATABASE_READONLY', 'echo')))
    app.config['SECRET_KEY']='testsecretkeyalsdkjf'
    db.init_app(app)
    Bootstrap(app)
    # Add the ldap config information from the .ini file.
    ldapconf = get_ldap_config()
    app.config.update(ldapconf)
    
    # Login Manager: set up ldap as well.
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    ldap_manager = LDAP3LoginManager(app)

    from eaodb.blueprints.user_model import create_user
    @login_manager.user_loader
    def load_user(user_id):
        return create_user(user_id)

    app.register_blueprint(auth)
    app.register_blueprint(project, url_prefix='/project')
    app.register_blueprint(obs, url_prefix='/obs')
    app.register_blueprint(ops, url_prefix='/ops')
    
    return app



    
