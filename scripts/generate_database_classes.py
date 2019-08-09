import io
from sqlalchemy.engine import create_engine
from sqlalchemy.schema import MetaData
from sqlacodegen.codegen import CodeGenerator
from sqlacodegen.codegen import ModelClass

from eaodb.util import get_config


# No camelcase.
class myModelClass(ModelClass):
    def __init__(self, *args):
        ModelClass.__init__(self, *args)

    @classmethod
    def _tablename_to_classname(cls, tablename, inflect_engine):
        tablename = cls._convert_to_valid_identifier(tablename)
        return inflect_engine.singular_noun(tablename) or tablename



config = get_config()

for db in ('omp', 'jcmt', 'jsa_proc', 'pigwidgeon', 'calibration'):
    dburl = config.get('DATABASE_READONLY', 'url')
    dburl = dburl.replace('/omp?', '/{}?'.format(db))
    readonly_engine = create_engine(dburl, echo=0)


    metadata = MetaData(readonly_engine)
    metadata.reflect(readonly_engine, db)


    # Don't de pluralise.
    generator = CodeGenerator(metadata, False, False, False, True, False, class_model=myModelClass)


    output = io.StringIO()

    generator.render(output)

    output.seek(0)
    lines = output.readlines()
    output.close()

    # Remove dbname from start of name.
    newlines = [i.replace('class {}'.format(db), 'class ') for i in lines]
    # Write out
    outfile = io.open('{}.py'.format(db), 'w', encoding='utf-8')
    outfile.writelines(newlines)
    outfile.close()
