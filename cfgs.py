# See https://0x46.net/thoughts/2019/02/01/dotfile-madness/

import os

__all__ = ['Cfgs']


class Cfgs:
    FORMATS = 'configparser', 'ini', 'json', 'toml', 'yaml'
    DEFAULT_FORMAT = 'json'

    def __init__(self, name, cache_size=0, default_format=None, formats=None):
        self.formats = formats or (
            os.environ.get('CFGS_FORMATS', '').split(':') or
            self.FORMATS)

        self.default_format = default_format or (
            os.environ.get('CFGS_DEFAULT_FORMAT', '').split(':') or
            self.DEFAULT_FORMAT)

        assert self.default_format in self.formats
        self.name = name
        self.cache_size = cache_size
        self.xdg = _XDG()

        self.cache = _Cache(self)
        self.config = _Directory(self, 'CONFIG')
        self.data = _Directory(self, 'DATA')


class _XDG:
    DEFAULTS = {
        'XDG_CACHE_HOME': '$HOME/.cache',
        'XDG_CONFIG_DIRS': '/etc/xdg',
        'XDG_CONFIG_HOME': '$HOME/.config',
        'XDG_DATA_DIRS': '/usr/local/share/:/usr/share/',
        'XDG_DATA_HOME': '$HOME/.local/share',
        'XDG_RUNTIME_DIR': ''}

    def __init__(self):
        for k, v in _XDG.DEFAULTS.items():
            v = os.path.expandvars(os.environ.get(k) or v)
            v = tuple(v.split(':')) if k.endswith('_DIRS') else v
            setattr(self, k, v)


class _Directory:
    def __init__(self, cfgs, category):
        def path(directory):
            home = getattr(cfgs.xdg, 'XDG_%s_%s' % (category, directory))
            return os.path.join(home, cfgs.name)

        self.cfgs = cfgs
        self.home = path('HOME')
        self.dirs = path('DIRS')

    def all_files(self, filename):
        """
        Yield all filenames matching the argument in either the home
        directory or the search directories
        """
        for p in (self.home,) + self.dirs:
            full_path = os.path.join(p, filename)
            try:
                yield open(full_path) and full_path
            except:
                pass

    def file(self, filename=None, format=None):
        filename = self.path_to(filename or self.cfgs.name)
        return _File(self.cfgs, filename, format)

    def path_to(self, filename):
        return os.path.join(self.home, filename)


class _File:
    def __init__(self, cfgs, filename, format):
        self.filename = filename
        _makedirs(os.path.basename(self.filename))
        self._read, self._write = _reader_writer(cfgs, self.filename, format)
        self.read()

    def __del__(self):
        try:
            self.write()
        except:
            pass

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


class _Cache:
    def __init__(self, dirname, cache_size):
        self.dirname = dirname
        self.cache_size = cache_size
        self._prune(0)

    def open(self, filename, size_guess, binary):
        if self.cache_size and '/' in filename:
            raise ValueError('Cache pruning does not work with subdirectories')

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


def _reader_writer(cfgs, filename, format):
    if not format:
        matches = (f for f in cfgs.formats if filename.endswith('.' + f))
        format = next(matches, cfgs.default_format)

    if format not in cfgs.formats:
        raise ValueError('Do not understand format ' + format)

    if format not in ('ini', 'configparser'):
        parser = __import__(format)
        return parser.load, parser.dump

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

    return read, write
