import gc
import json
import time
from datetime import datetime
from subprocess import check_output
from typing import Dict, Iterator, List, Tuple

from axol.common import get_logger


Revision = str
Json = Dict

class RepoHandle:
    def __init__(self, repo: str):
        self.repo = repo
        self.logger = get_logger()

    def check_output(self, *args):
        import gc
        cmd = [
            'git', f'--git-dir={self.repo}/.git', *args
        ]
        last = None
        for _ in range(10):
            try:
                return check_output(cmd)
            except OSError as e:
                raise e
                last = e
                if 'Cannot allocate memory' in str(e):
                    self.logger.debug(' '.join(cmd))
                    self.logger.error('cannot allocate memory... trying GC and again')
                    gc.collect()
                    import time
                    time.sleep(2)
                else:
                    raise e
        else:
            assert last is not None
            raise last


    def get_revisions(self) -> List[Tuple[str, datetime]]:
        """
        returns in order of ascending timestamp
        """
        ss = list(reversed(self.check_output(
            'log',
            '--pretty=format:%h %ad',
            '--no-patch',
        ).decode('utf8').splitlines()))
        def pdate(l):
            ds = ' '.join(l.split()[1:])
            return datetime.strptime(ds, '%a %b %d %H:%M:%S %Y %z')
        return [(l.split()[0], pdate(l)) for l in ss]

    def get_content(self, rev: str) -> str:
        return self.check_output(
            'show',
            rev + ':content.json',
        ).decode('utf8')

    def iter_versions(self, last=None) -> Iterator[Tuple[Revision, datetime, Json]]:
        revs = self.get_revisions()
        if last is not None:
            revs = revs[-last: ]
        for rev, dd in revs:
            self.logger.info('processing %s %s', rev, dd)
            cc = self.get_content(rev)
            if len(cc.strip()) == 0:
                j: Json = {}
            else:
                j = json.loads(cc)
            yield (rev, dd, j)
