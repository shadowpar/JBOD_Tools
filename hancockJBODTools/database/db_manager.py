from . import Base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from json import load


class db_manager(object):
    def __init__(self,dbname='daemontest',db_hostname='stmanager-db.sdcc.bnl.gov',db_port=5432,debug=False):
        self.Base = Base
        self.dbserver = db_hostname
        self.dbname = dbname
        self.dbport = str(db_port)
        self.engine = create_engine('postgresql://postgres:remotePSQL@' + self.dbserver + ':' + self.dbport + '/' + self.dbname)
        self.alchemy_session_config = sessionmaker(bind=self.engine)
        self.session = self.alchemy_session_config()