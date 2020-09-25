"""
Usage: runweb.py [-h]
       runweb.py [-d] [--port=port] [--host=host]

Start the web server on the internal flask server.

Options:
  -h --help       Show this help.
  -d --debug      Run using flasks debug mode. Allows reloading of code.
  -p --port=port  Port to run on [default: 5000]
  --host=host     Host to run on

"""


import logging

from docopt import docopt
from sshtunnel import SSHTunnelForwarder

from eaodb.webapp import create_app, db
from eaodb.util import get_config

# Parse arguments
arguments = docopt(__doc__, help=True)


if arguments['--debug'] is True:
    logging.basicConfig(level='DEBUG')
    logger = logging.getLogger('matplotlib').setLevel('INFO')
else:
    logging.basicConfig(level='INFO')
if arguments['--debug'] is True:
    host = '127.0.0.1'
    debug = True
else:
    host='0.0.0.0'
    debug = None

if arguments['--port']:
    port = int(arguments['--port'])
else:
    port = 5000

if arguments['--host']:
    host = arguments['--host']


    

config = get_config()['SSH_CONNECTION']
with SSHTunnelForwarder( (config['ssh_server'], int(config['ssh_port'])),
            ssh_username=config['ssh_username'], ssh_password=config['ssh_password'],
            remote_bind_address=(config['remote_bind_address'], int(config['remote_bind_port']))
                                 ) as tunnel:

    local_port = str(tunnel.local_bind_port)
    app = create_app(local_port)
    if debug:
        app.jinja_env.auto_reload=True
    app.run(host=host, debug=debug, port=port)
    
    
