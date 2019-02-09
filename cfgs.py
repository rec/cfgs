import copy, os

getenv = os.environ.get
expandvars = os.path.expandvars
__all__ = ['Project', 'XDG']


class Project:
    DEFAULT_FORMAT = 'json'

    def __init__(self, name, format=DEFAULT_FORMAT):
        self.name = name
        self.xdg = XDG()

        def path(attrname):
            path = getattr(self.xdg, attrname)
            if attrname.endswith('DIRS'):
                return [os.path.join(i, self.name) for i in path.split(':')]
            return os.path.join(path, self.name)

        self.cache = Cache(path('XDG_CACHE_HOME'))

        h, d = path('XDG_CONFIG_HOME'), path('XDG_CONFIG_DIRS')
        self.config = Directory(h, d, format)

        h, d = path('XDG_DATA_HOME'), path('XDG_DATA_DIRS')
        self.data = Directory(h, d, format)


class XDG:
    DEFAULTS = {
        'XDG_CACHE_HOME': '$HOME/.cache',
        'XDG_CONFIG_DIRS': '/etc/xdg',
        'XDG_CONFIG_HOME': '$HOME/.config',
        'XDG_DATA_DIRS': '/usr/local/share/:/usr/share/',
        'XDG_DATA_HOME': '$HOME/.local/share',
        'XDG_RUNTIME_DIR': ''}

    PREFIX = 'XDG_'

    def __init__(self):
        for k, v in self.DEFAULTS.items():
            setattr(self, k, getenv(k) or expandvars(v))


class Directory:
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
            except IOError:
                pass

    def open(self, filename=None, format=None):
        if not filename:
            basename = os.path.basename(self.home)
            filename = '%s.%s' % (basename, format or self.format)
        fullname = os.path.join(self.home, filename)
        return File(fullname, format, self.format)


class File:
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
        if not format:
            ext = os.path.splitext(self.filename)[1]
            format = self.FROM_SUFFIX.get(ext) or default_format

        if format not in self.FORMATS:
            raise ValueError('Do not understand format ' + format)

        if format == 'configparser':
            self._parser = _ConfigParser()
        else:
            self._parser = _Parser(format)

        self.read()

    def update(self, a=(), **kwds):
        return self.data.update(a, **kwds)

    def read(self):
        try:
            with open(self.filename) as fp:
                self.data = self._parser.read(fp)
        except IOError:
            self.data = self._parser.create()
        return self.data

    def write(self):
        with open(self.filename, 'w') as fp:
            self._parser.write(self.data, fp)

    def as_dict(self):
        return self._parser.as_dict(self.data)

    def clear(self):
        self.data.clear()

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


class _Parser:
    def __init__(self, format):
        parser = __import__(format)
        self.read, self.write = parser.load, parser.dump

    def create(self):
        return {}

    def as_dict(self, data):
        return copy.deepcopy(data)


class _ConfigParser:
    def __init__(self):
        try:
            configparser = __import__('configparser')
        except ImportError:
            configparser = __import__('ConfigParser')
        self.create = configparser.SafeConfigParser

    def read(self, fp):
        data = self.create()
        data.readfp(fp)
        return data

    def write(self, data, fp):
        data.write(fp)

    def as_dict(self, data):
        return {k: dict(v) for k, v in data.items()}


class Cache:
    def __init__(self, dirname):
        self.dirname = dirname

    def directory(self, name='cache', cache_size=0):
        name = os.path.join(self.dirname, name)
        return CacheDirectory(name, cache_size)


class CacheDirectory:
    def __init__(self, dirname, cache_size):
        self.dirname = dirname
        self.cache_size = cache_size
        _makedirs(self.dirname)
        self._prune(0)

    def open(self, filename, size_guess=0, binary=False):
        if '/' in filename:
            raise ValueError('Subdirectories are not allowed in caches')

        bin = 'b' if binary else ''

        full = os.path.join(self.dirname, filename)
        if os.path.exists(full):
            return open(full, 'r' + bin)

        self._prune(size_guess)
        return open(full, 'w' + bin)

    def _prune(self, size_guess):
        if not self.cache_size:
            return

        files = os.listdir(self.dirname)
        info = {f: os.stat(os.path.join(self.dirname, f)) for f in files}
        required_size = sum(s.st_size for f, s in info.items()) + size_guess
        if required_size <= self.cache_size:
            return

        # Delete oldest items first
        for f, s in sorted(info.items(), key=lambda x: x[1].st_mtime):
            os.remove(os.path.join(self.dirname, f))
            required_size -= s.st_size
            if required_size <= self.cache_size:
                return


def _makedirs(f):  # For Python 2 compatibility
    try:
        os.makedirs(f)
    except:
        pass
