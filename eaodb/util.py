from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine
try:
    from configparser import ConfigParser
    from configparser import NoOptionError
except ImportError:
    from ConfigParser import SafeConfigParser as ConfigParser
    from ConfigParser import NoOptionError
import os

config = None
home_directory = None
config_file = ('etc', 'eaodb.ini')

def get_config():
    """
    Read the configuration file.

    Return a ConfigParser object.

    Raise error if the config file doesn't exist.
    """

    global config

    if config is None:
        file_ = os.path.join(get_home(), *config_file)

        if not os.path.exists(file_):
            raise Exception("Config file {} doesn't exist", file_)

        config = ConfigParser()
        config.read(file_)### for python3?, encoding='utf8')

    return config

# Taken from Hedwig
def get_home():
    """
    Determine the application's home directory.
    """

    global home_directory

    if home_directory is not None:
        return home_directory

    return os.environ.get('EAODB_DIR', os.getcwd())



def create_readwrite_db_engine(dbname):
    config = get_config()

    dburl = config.get(dbname.upper(), 'url')
    try:
        echo = config.getint(dbname.upper(), 'echo')
    except:
        echo = 0
    engine = create_engine(dburl, echo=bool(echo))
    return engine


def create_readonly_all_engine():
    config = get_config()
    dburl = config.get('DATABASE_READONLY', 'url')
    try:
        echo = config.getint('DATABASE_READONLY', 'echo')
    except:
        echo = 0
    engine = create_engine(dburl, echo=bool(echo))
    return engine


def create_readonly_scoped_session():
    readonly_engine = create_readonly_all_engine()
    return scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=readonly_engine))
