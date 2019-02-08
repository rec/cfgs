# See https://0x46.net/thoughts/2019/02/01/dotfile-madness/

__all__ = ['Cfgs']

import os

getenv = os.environ.get
expandvars = os.path.expandvars


class Cfgs:
    DEFAULT_FORMAT = 'json'

    def __init__(self, name, cache_size=0, format=DEFAULT_FORMAT):
        self.name = name
        self.cache_size = cache_size

        def path(attrname):
            path = getattr(XDG, attrname)
            if attrname.endswith('DIRS'):
                return [os.path.join(i, self.name) for i in path.split(':')]
            return os.path.join(path, self.name)

        self.cache = _Cache(
            path('XDG_CACHE_HOME'), cache_size)
        self.config = _Directory(
            path('XDG_CONFIG_HOME'), path('XDG_CONFIG_DIRS'), format)
        self.data = _Directory(
            path('XDG_DATA_HOME'), path('XDG_DATA_DIRS'), format)


class _XDG:
    DEFAULTS = {
        'XDG_CACHE_HOME': '$HOME/.cache',
        'XDG_CONFIG_DIRS': '/etc/xdg',
        'XDG_CONFIG_HOME': '$HOME/.config',
        'XDG_DATA_DIRS': '/usr/local/share/:/usr/share/',
        'XDG_DATA_HOME': '$HOME/.local/share',
        'XDG_RUNTIME_DIR': ''}

    def __getattr__(self, k):
        default = self.DEFAULTS.get(k)
        if default is None:
            raise AttributeError('XDG has no such attribute "%s"' %  k)
        return getenv(k) or expandvars(default)

    def __dir__(self):
        return list(self.DEFAULTS)


XDG = _XDG()


class _Directory:
    def __init__(self, home, dirs, format):
        self.home = home
        self.dirs = dirs
        self.format = format
        self.dirs.insert(0, self.home)

    def all_files(self, filename=None):
        """
        Yield all filenames matching the argument in either the home
        directory or the search directories
        """
        for p in self.dirs:
            full_path = os.path.join(p, filename)
            try:
                yield open(full_path) and full_path
            except FileNotFoundError:
                pass

    def open(self, filename=None, format=None):
        if not filename:
            basename = os.path.basename(self.home)
            filename = '%s.%s' % (basename, format or self.format)
        fullname = os.path.join(self.home, filename)
        return _File(fullname, format, self.format)


class _File:
    FROM_SUFFIX = {
        '.cfg': 'configparser',
        '.ini': 'configparser',
        '.json': 'json',
        '.toml': 'toml',
        '.yaml': 'yaml',
        '.yml': 'yaml',
    }
    TO_SUFFIX = {
        'configparser': '.ini',
        'json': '.json',
        'toml': '.toml',
        'yaml': '.yml',
    }
    FORMATS = set(FROM_SUFFIX.values())

    def __init__(self, filename, format, default_format):
        self.filename = filename
        _makedirs(os.path.dirname(self.filename))
        self._read, self._write, self._create = self._reader_writer(
            format, default_format)
        self.read()

    def update(self, a=(), **kwds):
        return self.data.update(a, **kwds)

    def read(self):
        try:
            with open(self.filename) as fp:
                self.data = self._read(fp)
        except FileNotFoundError:
            self.data = self._create()
        return self.data

    def write(self):
        with open(self.filename, 'w') as fp:
            self._write(self.data, fp)

    def __setitem__(self, k, v):
        self.data[k] = v

    def __getitem__(self, k):
        return self.data[k]

    def __delitem__(self, k):
        del self.data[k]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.write()

    def _reader_writer(self, format, default_format):
        print('XXX 3', format, default_format)
        if not format:
            ext = os.path.splitext(self.filename)[1]
            format = self.FROM_SUFFIX.get(ext) or default_format

        if format not in self.FORMATS:
            raise ValueError('Do not understand format ' + format)

        if format != 'configparser':
            parser = __import__(format)
            return parser.load, parser.dump, dict

        try:
            configparser = __import__('configparser')
        except ModuleNotFoundError:
            configparser = __import__('ConfigParser')

        def read(fp):
            data = configparser.SafeConfigParser()
            data.readfp(fp)
            return data

        def write(data, fp):
            data.write(fp)

        return read, write, configparser.SafeConfigParser


class _Cache:
    def __init__(self, dirname, cache_size):
        self.dirname = dirname
        self.cache_size = cache_size
        self._prune(0)

    def open(self, filename, size_guess, binary):
        if '/' in filename:
            raise ValueError('Subdirectories are not allowed in caches')

        bin = 'b' if binary else ''
        _makedirs(self.dirname)

        full = os.path.join(self.dirname, filename)
        if os.path.exists(full):
            return open(full, 'r' + bin)

        self._prune(size_guess)
        return open(full, 'w' + bin)

    def _prune(self, size_guess):
        if not self.cache_size:
            return

        info = {f: os.stat(f) for f in os.listdir(self.dirname)}
        required_size = sum(s.st_size for f, s in info.items()) + size_guess
        if required_size <= self.cache_size:
            return

        # Delete oldest items first
        for f, s in sorted(info.items(), key=lambda x: x[0].st_mtime):
            os.remove(f)
            required_size -= s.st_size
            if required_size <= self.cache_size:
                return


def _makedirs(f):  # For Python 2 compatibility
    try:
        os.makedirs(f)
    except:
        pass
