from bpyutils.api.base import BaseAPI
from bpyutils import request as req

class GitHub(BaseAPI):
    url = "https://api.github.com"

    def __init__(self, token = None, *args, **kwargs):
        self._super = super(GitHub, self)
        self._super.__init__(*args, **kwargs)

        self._token = token

        self._repo_reponame = None
        self._repo_reponame = None

    def repo(self, username, reponame):
        self._repo_username = username
        self._repo_reponame = reponame
        return self

    def pr(self):
        if not self._repo_username or not self._repo_reponame:
            raise ValueError("Repo username or reponame not found.")

        url = "repos/%s/%s/pulls" % (self._repo_username, self._repo_reponame)
        response = self.get(url)
        return response