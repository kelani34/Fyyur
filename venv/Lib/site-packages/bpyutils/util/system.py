# imports - compatibility imports
from bpyutils._compat import iteritems

# imports - standard imports
import sys, os, os.path as osp
import errno
import zipfile
import subprocess  as sp
import shutil
import tempfile
import contextlib
from   glob import glob
import traceback

# imports - module imports
from bpyutils.util._dict      import merge_dict
from bpyutils.exception       import PopenError
from bpyutils.util.string     import (
    strip,
    safe_decode,
    get_random_str
)
from bpyutils.util.environ    import SECRETS
from bpyutils._compat         import iteritems, PY2
from bpyutils.log             import get_logger
from bpyutils.cli import util as _cli

logger = get_logger()

__STDOUT__ = None

def read(fname, mode = "r"):
    """Read content from a given file.

    Args:
        fname (str, Path): The path to the file.
        mode (str): File mode while opening. Defaults to "r".

    Returns:
        [type]: The content within the file.

    Example

        >>> bpy.read("path/to/file")
        'Hello, World!'
    """
    with open(fname, mode = mode or "r") as f:
        data = f.read()
    return data

def write(fname, data = None, force = False, append = False, mode = None):
    if not osp.exists(fname) or append or force:
        with open(fname, mode = mode or ("a" if append else "w")) as f:
            if data:
                f.write(data)

def which(executable, raise_err = False):
    exec_ = None

    if not PY2:
        try:
            exec_ = shutil.which(executable)
        except shutil.Error: # pragma: no cover
            pass

    if not exec_:
        # worst to worst case.
        from distutils.spawn import find_executable
        exec_ = find_executable(executable)
        
    if not exec_ and raise_err:
        raise ValueError("Executable %s not found." % exec_)
    
    return exec_

def pardir(fname, level = 1):
    for _ in range(level):
        fname = osp.dirname(fname)
    return fname

def popen(*args, **kwargs):
    output      = kwargs.get("output", False)
    quiet       = kwargs.get("quiet" , False)
    directory   = kwargs.get("cwd")
    environment = kwargs.get("env")
    shell       = kwargs.get("shell", True)
    raise_err   = kwargs.get("raise_err", True)

    environ     = os.environ.copy()
    if environment:
        environ.update(environment)

    for k, v in iteritems(environ):
        environ[k] = str(v)

    command     = " ".join([str(arg) for arg in args])
    logger.info("Executing command: %s" % command)

    if quiet:
        output  = True
    
    proc        = sp.Popen(command,
        bufsize = -1,
        stdin   = sp.PIPE if output else kwargs.get("stdin"),
        stdout  = sp.PIPE if output else None,
        stderr  = sp.PIPE if output else None,
        env     = environ,
        cwd     = directory,
        shell   = shell
    )

    code       = proc.wait()

    if code and raise_err:
        raise PopenError(code, command)

    if output:
        output, error = proc.communicate()

        if output:
            output = safe_decode(output)
            output = strip(output)

        if error:
            error  = safe_decode(error)
            error  = strip(error)

            logger.error("Error executing command %s: %s" % (command, error))

        if quiet:
            return code
        else:
            return code, output, error
    else:
        return code

def makedirs(dirs, exist_ok = False):
    dirs = osp.abspath(dirs)

    try:
        os.makedirs(dirs)
    except OSError as e:
        if not exist_ok or e.errno != errno.EEXIST:
            raise

    return dirs

def makepath(path):
    dirs = osp.dirname(path)
    makedirs(dirs, exist_ok = True)

    write(path)

def touch(filename):
    if not osp.exists(filename):
        with open(filename, "w") as f:
            pass

def remove(*paths, **kwargs):
    recursive = kwargs.get("recursive", False)
    raise_err = kwargs.get("raise_err", True)

    for path in paths:
        path = osp.realpath(path)

        if osp.isdir(path):
            if recursive:
                shutil.rmtree(path)
            else:
                if raise_err:
                    raise OSError("{path} is a directory.".format(
                        path = path
                    ))
        else:
            try:
                os.remove(path)
            except (OSError, PermissionError):
                if raise_err:
                    raise

@contextlib.contextmanager
def make_temp_dir(root_dir = None):
    dir_path = tempfile.mkdtemp(dir = root_dir)
    try:
        yield dir_path
    finally:
        shutil.rmtree(dir_path)

@contextlib.contextmanager
def make_temp_file():
    with make_temp_dir() as tmp_dir:
        hash_    = get_random_str()
        tmp_file = osp.join(tmp_dir, hash_)

        touch(tmp_file)
        
        yield tmp_file

def check_gzip(f, raise_err = True):
    """
    Check if a given file is a gzipped file.
    """
    if osp.exists(f):
        with open(f, "rb") as f:
            content = f.read(2)
            
            if content == b"\x1f\x8b":
                return True
            else:
                if raise_err:
                    raise ValueError("File %s is not a gzip file." % f)

    return False

class BaseShell:
    def __init__(self, *args, **kwargs):
        self._kwargs = kwargs

    def __call__(self, *args, **kwargs):
        kwargs = merge_dict(self._kwargs, kwargs)
        return popen(*args, **kwargs)

if PY2:
    def ShellEnvironment(**kwargs):
        yield BaseShell(**kwargs)
else:
    class ShellEnvironment(BaseShell, contextlib.ContextDecorator):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

def get_os():
    platform = sys.platform
    
    if platform.startswith("linux"):
        return "linux"
    elif platform == "darwin":
        return "macos"
    elif platform == "win32":
        return "windows"

def unzip(path, target = None):
    target = target or osp.dirname(path)
    makedirs(target, exist_ok = True)

    with zipfile.ZipFile(path, "r") as zf:
        zf.extractall(target)

def get_files(dir_, type_ = "*.*"):
    dir_ = osp.abspath(dir_)
    return glob("%s/**/%s" % (dir_, type_), recursive = True)

def get_basename(path):
    return osp.basename(osp.normpath(path))

def make_archive(base_name, *args, **kwargs):
    with make_temp_dir() as tmp_dir:
        source_archive = osp.join(tmp_dir, "archive")
        target_archive = shutil.make_archive(source_archive, *args, **kwargs)

        makepath(base_name)
        shutil.move(target_archive, base_name)

def move(*files, **kwargs):
    """Move a file or a list of files to destination

    Args:
        files (str, `Path`): The source file to move. (Can be a file or a directory).
        dest (str, `Path`): The destination path to move files to (Can be a file or a directory).

    Example:

        >>> bpy.move("path/to/file1", "path/to/file2", dest = "path/to/dest")
    """
    dest = kwargs["dest"]

    for f in files:
        shutil.move(f, dest)

def copy(*files, **kwargs):
    """Copy a file or a list of files to destination

    Args:
        files (str, `Path`): The source file to copy. (Can be a file or a directory).
        dest (str, `Path`): The destination path to copy files to (Can be a file or a directory).
        raise_err (bool): Raise `FileNotFoundError` if a give file isn't found, else ignore.

    Raises:
        FileNotFoundError: If a given file isn't found and `raise_err` is not flagged.

    Example:

        >>> bpy.copy("path/to/file1", "path/to/file2", dest = "path/to/dest")
    """
    dest = kwargs["dest"]
    raise_err = kwargs.get("raise_err", False)
    
    for f in files:
        abspath = osp.abspath(f)

        if not osp.exists(abspath) and raise_err:
            raise FileNotFoundError("No file %s found." % abspath)
        else:
            shutil.copy2(abspath, dest)

def extract_all(source, dest):
    """Unpack an archive to a desired destination.

    Args:
        source (str, Path): The source path to the archive file.
        dest (str, Path): The destination path to extract the archive to.

    Example

        >>> bpy.extract_all("path/to/src", "path/to/dest")
    """
    shutil.unpack_archive(source, dest)

def pretty_print_error(e):
    summary    = traceback.extract_stack()
    
    error_type = type(e)
    error_name = error_type.__name__
    error_msg  = e.message
    newline    = "\n\n"

    _cli.echo(
        "  " + _cli.format(error_name, _cli.RED)  + newline +
        "  " + _cli.format(error_msg,  _cli.BOLD) + newline
    )

    error_str = traceback.format_exc()
    _cli.echo(error_str)