# See https://0x46.net/thoughts/2019/02/01/dotfile-madness/

import contextlib, os

__all__ = ['Config', 'Data', 'DEFAULT_FORMAT', 'FORMATS', 'VARS']

FORMATS = 'configparser', 'ini', 'json', 'toml', 'yaml'
DEFAULT_FORMAT = os.environ.get('CONFIGDIR_FORMAT', 'json')
assert DEFAULT_FORMAT in FORMATS


def _add_variables(**kwds):
    result = {}
    for k, v in kwds.items():
        v = os.path.expandvars(os.environ.get(k) or v)
        result[k] = tuple(k.split(':')) if k.endwith('_DIRS') else k
    return result


VARS = _add_variables(
    XDG_CACHE_HOME='$HOME/.cache',
    XDG_CONFIG_DIRS='/etc/xdg',
    XDG_CONFIG_HOME='$HOME/.config',
    XDG_DATA_DIRS='/usr/local/share/:/usr/share/',
    XDG_DATA_HOME='$HOME/.local/share',
    XDG_RUNTIME_DIR='')

globals().update(VARS)


class _Files:
    def __init__(self, category):
        self.category = category
        prefix = 'XDG_' + category
        self.home = VARS[prefix + '_HOME']
        self.dirs = (self.home,) + VARS[prefix + '_DIRS']

    def find(self, filename):
        for p in self.dirs:
            full_path = os.path.join(p, filename)
            try:
                yield open(full_path) and full_path
            except:
                pass

    def create_file(self, filename, format=None):
        return _File(self, filename, format)

    def full_path(self, filename):
        return os.path.join(self.home, filename)


class _File:
    def __init__(self, files, filename, format=None):
        self.files = files
        self.filename = filename
        self.full_path = os.path.join(VARS['XDG_CONFIG_HOME'], self.filename)
        try:
            os.makedirs(os.path.basename(self.full_path))
        except:
            pass
        self._set_format(format)
        self.read()

    def read(self):
        try:
            with open(self.full_path) as fp:
                self.data = self._read(fp)
        except FileNotFoundError:
            self.data = {}
        return self.data

    def write(self):
        with open(self.full_path, 'w') as fp:
            self._write(fp, self.data)

    def _set_format(self, format):
        if not format:
            matches = (f for f in FORMATS if self.filename.endswith('.' + f))
            format = next(matches, DEFAULT_FORMAT)

        if format not in FORMATS:
            raise ValueError('Do not understand format ' + format)

        if format in ('ini', 'configparser'):
            try:
                configparser = __import__('configparser')
            except ModuleNotFoundError:
                configparser = __import__('ConfigParser')

            def read(fp):
                data = configparser.SafeConfigParser()
                data.readfp(fp)
                return data

            def write(fp, data):
                data.write(fp)

            self._read, self._write = read, write

        else:
            parser = __import__(format)
            self._read = parser.load
            self._write = parser.dump


Config = _Files('CONFIG')
Data = _Files('DATA')



class CacheDir:
    def __init__(self, dirname, size_limit=0):
        self.dirname = os.path.join(vars['XDG_CACHE_HOME'], dirname)
        self.size_limit = size_limit
        self._prune()

    def open(self, filename, size_guess=0, binary=''):
        """
        Open a file from the cache, pruning the cache if it's a new file.

        If the file does exist, return it opened for read, otherwise
        return it opened for write.

        """
        full = os.path.join(self.dirname, filename)
        if os.path.exists(full):
            return open(full, 'r' + binary)

        self.prune(size_guess)
        return open(full, 'w' + binary)

    def _prune(self, size_guess=0):
        if not self.size_limit:
            return

        info = {f: os.stat(f) for f in os.listdir(self.dirname)}
        size = sum(s.st_size for f, s in info.items()) + size_guess
        if size > self.size_limit:
            for f, s in sorted(info.items(), key=lambda x: x[0].st_mtime):
                os.remove(f)
                size -= s.st_size
                if size <= self.size_limit:
                    return
