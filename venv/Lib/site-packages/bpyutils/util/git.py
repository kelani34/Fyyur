import os.path as osp

from bpyutils.util.string import check_url

def resolve_git_url(repo, raise_err = True):
    if not check_url(repo, raise_err = False):
        repo = osp.abspath(repo)

        if not osp.exists(repo) and raise_err:
            raise ValueError("Repository %s not found." % repo)

    return repo