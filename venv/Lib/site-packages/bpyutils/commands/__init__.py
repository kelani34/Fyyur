# imports - compatibility imports
from __future__ import absolute_import
import collections

# imports - standard imports
import traceback

from bpyutils.commands.util 	import cli_format
from bpyutils.util._dict        import merge_dict
from bpyutils.util.types        import lmap, auto_typecast
from bpyutils.util.string       import strip
from bpyutils.util.imports      import import_handler
from bpyutils.util.system       import touch
from bpyutils 		      	    import (cli, log)
from bpyutils._compat		    import iteritems
from bpyutils.config            import environment
from bpyutils.__attr__      	import __name__
from bpyutils.exception         import DependencyNotFoundError

logger    = log.get_logger(level = log.DEBUG)

ARGUMENTS = dict(
    run_job                     = None,
    params                      = None,
    jobs						= 1,
    check		 				= False,
    interactive  				= False,
    yes			 				= False,
    no_cache		            = False,
    no_color 	 				= True,
    output						= None,
    ignore_error				= False,
    force						= False,
    verbose		 				= False
)

@cli.command
def command(**ARGUMENTS):
    try:
        return _command(**ARGUMENTS)
    except Exception as e:
        if not isinstance(e, DependencyNotFoundError):
            cli.echo()

            traceback_str = traceback.format_exc()
            cli.echo(traceback_str)

            cli.echo(cli_format("""\
An error occured while performing the above command. This could be an issue with
"bpyutils". Kindly post an issue at https://github.com/achillesrasquinha/bpyutils/issues
""", cli.RED))
        else:
            raise e

def to_params(kwargs):
    class O(object):
        pass

    params = O()

    kwargs = merge_dict(ARGUMENTS, kwargs)

    for k, v in iteritems(kwargs):
        setattr(params, k, v)

    return params

def format_params(params):
    params = params or []
    params = lmap(lambda x: lmap(strip, x.split(";")), params)
    
    args   = {}
    
    for param in params:
        for p in param:
            key, value = p.split("=")
            args[key]  = auto_typecast(value)

    return args
            
def _command(*args, **kwargs):
    a = to_params(kwargs)

    if not a.verbose:
        logger.setLevel(log.NOTSET)

    logger.info("Environment: %s" % environment())
    logger.info("Arguments Passed: %s" % locals())

    file_ = a.output

    if file_:
        logger.info("Writing to output file %s..." % file_)
        touch(file_)
    
    logger.info("Using %s jobs..." % a.jobs)

    if a.run_jobs:
        logger.info("Running module %s" % a.run_jobs)

        for module in a.run_jobs:
            jobs = import_handler("%s.jobs" % module)
            args = format_params(a.param)

            for job in jobs:
                name = job

                if isinstance(job, collections.Mapping):
                    name = job["name"]
                
                job_module_runner = import_handler("%s.%s.run" % (module, name))
                job_module_runner(**args)

    if a.run_job:
        logger.info("Running a specific job %s" % a.run_job)

    if a.method:
        for method in a.method:
            args = format_params(a.param)

            callable = import_handler(method)
            callable(**args)

    if a.run_ml:
        args = format_params(a.param)
        pipelines = [
            "data.get_data",
            "data.preprocess_data",
            "pipelines.train"
        ]

        for pipeline in pipelines:
            args = format_params(a.param)

            callable = import_handler("%s.%s" % (a.run_ml, pipeline))
            callable(**args)
