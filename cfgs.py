# See https://0x46.net/thoughts/2019/02/01/dotfile-madness/

import os

__all__ = ['Cache', 'Config', 'Data', 'DEFAULT_FORMAT', 'FORMATS', 'VARS']

FORMATS = 'configparser', 'ini', 'json', 'toml', 'yaml'
DEFAULT_FORMAT = os.environ.get('CFGS_FORMAT', 'json')
assert DEFAULT_FORMAT in FORMATS

_VARS = {
    'XDG_CACHE_HOME': '$HOME/.cache',
    'XDG_CONFIG_DIRS': '/etc/xdg',
    'XDG_CONFIG_HOME': '$HOME/.config',
    'XDG_DATA_DIRS': '/usr/local/share/:/usr/share/',
    'XDG_DATA_HOME': '$HOME/.local/share',
    'XDG_RUNTIME_DIR': ''}


def _split_path(k, v):
    v = os.path.expandvars(os.environ.get(k) or v)
    return tuple(v.split(':')) if k.endswith('_DIRS') else v


VARS = {k: _split_path(k, v) for k, v in _VARS.items()}
globals().update(VARS)
__all__.extend(VARS)


class _XDG:
    class Directory:
        def __init__(self, category):
            assert category in ('DATA', 'CONFIG')
            self.category = category
            prefix = 'XDG_' + category
            self.home = VARS[prefix + '_HOME']
            self.dirs = (self.home,) + VARS[prefix + '_DIRS']

        def find_all(self, filename):
            for p in self.dirs:
                full_path = os.path.join(p, filename)
                try:
                    yield open(full_path) and full_path
                except:
                    pass

        def File(self, filename, format=None):
            return _XDG.File(self.full_path(filename), format)

        def full_path(self, filename):
            return os.path.join(self.home, filename)

    class File:
        def __init__(self, filename, format=None):
            self.filename = filename
            _makedirs(os.path.basename(self.filename))
            self._set_format(format)
            self.read()

        def __del__(self):
            self.write()

        def read(self):
            try:
                with open(self.filename) as fp:
                    self.data = self._read(fp)
            except FileNotFoundError:
                self.data = {}
            return self.data

        def write(self):
            with open(self.filename, 'w') as fp:
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


Config = _XDG.Directory('CONFIG')
Data = _XDG.Directory('DATA')


class Cache:
    def __init__(self, dirname, size_limit=0):
        self.dirname = os.path.join(vars['XDG_CACHE_HOME'], dirname)
        _makedirs(self.dirname)
        self.size_limit = size_limit
        self._prune()

    def open(self, filename, size_guess=0, binary=False):
        """
        Open a file from the cache, pruning the cache if it's a new file.

        If the file does exist, return it opened for read, otherwise
        return it opened for write.

        Arguments:
           filename: pathname of the file relative to the cache directory
           size_guess: A guess as to the size of the file, in bytes
           binary: If true, the file is opened in binary mode

        """
        bin = 'b' if binary else ''
        full = os.path.join(self.dirname, filename)
        if os.path.exists(full):
            return open(full, 'r' + bin)

        self.prune(size_guess)
        return open(full, 'w' + bin)

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


def _makedirs(f):  # For Python 2 compatibility
    try:
        os.makedirs(f)
    except:
        pass
