from __future__ import absolute_import

# imports - standard imports
import sys
import os.path as osp
import sqlite3

# imports - module imports
from bpyutils.config        import PATH
from bpyutils.util.string   import strip
from bpyutils.util.system   import makedirs, read, popen, which
from bpyutils.util.imports  import import_handler
from bpyutils               import config, log, cli

logger = log.get_logger()

IntegrityError      = sqlite3.IntegrityError
OperationalError    = sqlite3.OperationalError

def _get_queries(buffer):
    queries = [ ]
    lines   = buffer.split(";")

    for line in lines:
        line = strip(line)
        queries.append(line)

    return queries

class DB(object):
    def __init__(self, path, timeout = 10):
        self.path        = path
        self._connection = None
        self.timeout     = timeout

    @property
    def connected(self):
        _connected = bool(self._connection)
        return _connected

    def connect(self, bootstrap = True, **kwargs):
        """
        Connect to database.
        """
        if not self.connected:
            self._connection = sqlite3.connect(self.path,
                timeout = self.timeout, **kwargs)
            self._connection.row_factory = sqlite3.Row

    def query(self, *args, **kwargs):
        if not self.connected:
            self.connect()

        script      = kwargs.pop("script", False)
        generate    = kwargs.pop("generate", False)

        cursor      = self._connection.cursor()
        getattr(cursor,
            "execute%s" % ("script" if script else "")
        )(*args, **kwargs)

        self._connection.commit()

        results = cursor.fetchall()
        results = [dict(result) for result in results]

        if len(results) == 1:
            results = results[0]

        cursor.close()

        return results

    def from_file(self, path):
        buffer  = read(path)
        queries = _get_queries(buffer)

        for query in queries:
            _CONNECTION.query(query)

_CONNECTION = None

def get_connection(location = PATH["CACHE"], bootstrap = True, log = False):
    global _CONNECTION

    if not _CONNECTION:
        if log:
            logger.info("Establishing a DataBase connection...")

        makedirs(location, exist_ok = True)

        abspath  = osp.join(location, "db.db")

        _CONNECTION = DB(abspath)
        _CONNECTION.connect(
            detect_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )

        if bootstrap:
            if log:
                logger.info("Bootstrapping DataBase...")

            abspath = osp.join(config.PATH["DATA"], "bootstrap.sql")
            _CONNECTION.from_file(abspath)

    return _CONNECTION

def run_db_shell(path):
    exec_sqlite = which("litecli")

    if not exec_sqlite:
        cli.echo(cli.format("For a more interactive shell, install litecli (https://github.com/dbcli/litecli) using the command: pip install litecli", cli.YELLOW))
        exec_sqlite = which("sqlite3", raise_err = True)
    
    code = popen("%s %s" % (exec_sqlite, path))

    sys.exit(code)