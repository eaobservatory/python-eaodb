python-eaodb: tools to access and use EAO's databases via SQLAlchemy's ORM


This contains automatically generated classes for the omp, jcmt,
calibration, jsa_proc and pigwidgeon database tables. It also contains
utilities for connecting to the database in either read-write or
read-only mode. In addition, there are some additional helper files contained here:

  1. ompstate.py contains a class taken from jsa_proc allowing easy
     look up and manipulation of the ompstate names-integers.

To connect to the databases, there are helper function ins eaodb.util
which will read a config file and then return appropriate sqlalchemy
engines for either readonly connections or read-write connections
(enforced by the correct username/password being in the config file.)

An example config file (without hostnames or passwords) is included in
this repo.

Examples of use:

    from eaodb import omp, jcmt
    from eaodb import calibration as cal
    from eaodb import pigwidgeon as pig


    from eaodb.util import create_readonly_engine


    engine = create_readonly_engine()

    from sqlalchemy.orm import sessionmaker

    session = sessionmaker(bind=engine)()

    # Count the number of  SCUBA-2 observations from the database
    query = session.query(jcmt.COMMON).filter(jcmt.instrume=='SCUBA-2')

    print(query.count())

    # Limit to only questionable obsrvations.

    from eaodb.ompstate import OMPState
    ompstatus = OMPState.lookup_name('QUESTIONABLE')

    from sqlalchemy import select, func
    def generate_obslog_join(table):
       interior = select([func.max(omp.obslog.obslogid)])
       interior = interior.where(omp.obslog.obsid==table.obsid).correlate(table)
       return interior

    interior = generate_obslog_join(jcmt.COMMON)
    query = query.outerjoin(omp.obslog, omp.obslog.obslogid==interior)

    query.filter(omp.obslog.commentstatus.in_(ompstatus))
    print(query.count())


