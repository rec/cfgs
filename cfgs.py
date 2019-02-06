# See https://0x46.net/thoughts/2019/02/01/dotfile-madness/

import os
__all__ = ['Cfgs']


class Cfgs:
    FORMATS = 'configparser', 'ini', 'json', 'toml', 'yaml'
    FORMAT = 'json'

    def __init__(self, name, cache_size=0, format=None, formats=None):
        self.name = name
        self.cache_size = cache_size

        self.format = format or getenv('CFGS_FORMAT') or self.FORMAT
        self.formats = formats or getenv('CFGS_FORMATS') or self.FORMATS
        if isinstance(self.formats, str):
            self.formats = self.formats.split(':')
        if self.format not in self.formats:
            raise ValueError('Format %s not in %s' % (self.format, self.formats))

        self.cache = _Cache(self)
        self.config = _Directory(self, 'CONFIG')
        self.data = _Directory(self, 'DATA')

    def _path(self, category, directory):
        path = getattr(XDG, 'XDG_%s_%s' % (category, directory))
        if directory == 'DIRS':
            return [os.path.join(i, self.name) for i in path.split(':')]
        return os.path.join(path, self.name)


def getenv(x):
    return os.environ.get(x)


def expandvars(x):
    return os.path.expandvars(x)


class _XDG:
    PREFIX = 'XDG_'

    DEFAULTS = {
        'XDG_CACHE_HOME': '$HOME/.cache',
        'XDG_CONFIG_DIRS': '/etc/xdg',
        'XDG_CONFIG_HOME': '$HOME/.config',
        'XDG_DATA_DIRS': '/usr/local/share/:/usr/share/',
        'XDG_DATA_HOME': '$HOME/.local/share',
        'XDG_RUNTIME_DIR': ''}

    def __getattr__(self, k):
        k = k.upper()
        if not k.startswith(self.PREFIX):
            k = self.PREFIX + k
        return getenv(k) or expandvars(self.DEFAULTS[k])

    def __dir__(self):
        return list(self.DEFAULTS)


XDG = _XDG()


class _Directory:
    def __init__(self, cfgs, category):
        self.cfgs = cfgs
        self.home = cfgs._path(category, 'HOME')
        self.dirs = cfgs._path(category, 'DIRS')
        self.dirs.insert(0, self.home)

    def all_files(self, filename=None):
        """
        Yield all filenames matching the argument in either the home
        directory or the search directories
        """
        for p in self.dirs:
            full_path = self.path_to(filename, p)
            try:
                yield open(full_path) and full_path
            except FileNotFoundError:
                pass

    def file(self, filename=None, format=None):
        return _File(self.cfgs, self.path_to(filename), format)

    def path_to(self, filename=None, base=None):
        if not filename:
            filename = '%s.%s' % (self.cfgs.name, self.cfgs.format)
        return os.path.join(base or self.home, filename)


class _File:
    def __init__(self, cfgs, filename, format):
        self.filename = filename
        _makedirs(os.path.dirname(self.filename))
        rwc = _reader_writer(cfgs, self.filename, format)
        self._read, self._write, self._create = rwc
        self.read()

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


class _Cache:
    def __init__(self, cfgs):
        self.cfgs = cfgs
        self.dirname = cfgs._path('CACHE', 'HOME')
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
        if not self.cfgs.cache_size:
            return

        info = {f: os.stat(f) for f in os.listdir(self.dirname)}
        required_size = sum(s.st_size for f, s in info.items()) + size_guess
        if required_size <= self.cfgs.cache_size:
            return

        # Delete oldest items first
        for f, s in sorted(info.items(), key=lambda x: x[0].st_mtime):
            os.remove(f)
            required_size -= s.st_size
            if required_size <= self.cfgs.cache_size:
                return


def _makedirs(f):  # For Python 2 compatibility
    try:
        os.makedirs(f)
    except:
        pass


def _reader_writer(cfgs, filename, format):
    if not format:
        matches = (f for f in cfgs.formats if filename.endswith('.' + f))
        format = next(matches, cfgs.format)

    if format not in cfgs.formats:
        raise ValueError('Do not understand format ' + format)

    if format not in ('ini', 'configparser'):
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
