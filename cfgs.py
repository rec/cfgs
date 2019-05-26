"""
`cfgs`

Simple, correct handling of config, data and cache files.
Fully compliant with the XDG Base Directory Specification.
"""

import copy
import os

_getenv = os.environ.get
_expandvars = os.path.expandvars


class App:
    """
    `cfg.App` is the main class, but it has no methods - it just holds the
    `config`, `data`, `cache` and `xdg` objects.
    """

    DEFAULT_FORMAT = 'json'
    """The default, default file format for all Apps"""

    def __init__(
        self, name, format=DEFAULT_FORMAT, read_kwds=None, write_kwds=None
    ):
        """
        Arguments:

          name: the name of the App.  `name` is used as a directory
                name so it should not contain any characters illegal in
                pathnames

          format: the format for config and data files from this App
        """

        def path(attrname):
            path = getattr(self.xdg, attrname)
            if attrname.endswith('DIRS'):
                return [os.path.join(i, self.name) for i in path.split(':')]
            return os.path.join(path, self.name)

        _check_filename(name)

        self.name = name
        """The text name of the App"""

        self.xdg = XDG()
        """A `cfg.XFG` as of when the App was constructed."""

        self.cache = Cache(path('XDG_CACHE_HOME'))
        """A `cfg.Cache` that manages cache directories"""

        if format not in FORMATS:
            raise ValueError('Unknown format', format)

        if format == 'configparser':
            self.format = ConfigparserFormat()
            """A `cfgs.Format` representing the data format."""
        else:
            self.format = Format(format, read_kwds, write_kwds)

        h, d = path('XDG_CONFIG_HOME'), path('XDG_CONFIG_DIRS')
        self.config = Directory(h, d, self.format)
        """A `cfgs.Directory` for config files"""

        h, d = path('XDG_DATA_HOME'), path('XDG_DATA_DIRS')
        self.data = Directory(h, d, self.format)
        """A `cfgs.Directory` for data files"""


class XDG:
    """
    The XDG Base Directory Spec mandates six directories for config and data
    files, caches and runtime files, with default values that can be overridden
    through environment variables.  This class takes a snapshot of these six
    directories using the current environment.
    """

    def __init__(self):
        """
        Construct the class with a snapshot of the six XDG base directories
        """

        def get(k, v):
            return _getenv(k) or _expandvars(v)

        self.XDG_CACHE_HOME = get('XDG_CACHE_HOME', '$HOME/.cache')
        """Base directory relative to which
           user-specific non-essential (cached) data should be written
        """

        self.XDG_CONFIG_DIRS = get('XDG_CONFIG_DIRS', '/etc/xdg')
        """A set of preference ordered base directories relative to which
           configuration files should be searched
        """

        self.XDG_CONFIG_HOME = get('XDG_CONFIG_HOME', '$HOME/.config')
        """Base directory relative to which user-specific
           configuration files should be written
        """

        self.XDG_DATA_DIRS = get(
            'XDG_DATA_DIRS', '/usr/local/share/:/usr/share/'
        )
        """A set of preference ordered base directories relative to which
           data files should be searched
        """

        self.XDG_DATA_HOME = get('XDG_DATA_HOME', '$HOME/.local/share')
        """Base directory relative to which user-specific
           data files should be written
        """

        self.XDG_RUNTIME_DIR = get('XDG_RUNTIME_DIR', '')
        """Base directory relative to which
           user-specific runtime files and other file objects should be placed
        """


class Directory:
    """
    An XDG directory of persistent, formatted files
    """

    def __init__(self, home, dirs, format):
        """
        Don't call this constructor directly - use either
        `cfgs.App.config` or `cfgs.App.data` instead.
        """
        self.home = home
        self.dirs = dirs
        assert not isinstance(format, str)
        self.format = format
        self.dirs.insert(0, self.home)

    def open(self, filename=None):
        """
        Open a persistent `cfg.File`.

        Arguments:
          filename: The name of the persistent file. If None,
            `filename` defaults to `cfg.App.name` plus the format suffix

          format: A string representing the file format.  If None,
             first try to guess the filename from the filename, then use
             `self.format`
        """
        if not filename:
            basename = os.path.basename(self.home)
            suffix = FORMAT_TO_SUFFIX[self.format.name]
            filename = '%s%s' % (basename, suffix)
        elif filename.startswith('/'):
            filename = filename[1:]

        return File(self.full_name(filename), self.format)

    def all_files(self, filename):
        """
        Yield all filenames matching the argument in either the home
        directory or any of the search directories
        """
        for p in self.dirs:
            full_path = os.path.join(p, filename)
            try:
                yield open(full_path) and full_path
            except IOError:
                pass

    def full_name(self, filename):
        """
        Return the full name of a file with respect to this XDG directory
        """
        return os.path.join(self.home, filename)


class File:
    """
    A formatted data or config file where you can set and get items,
    and read or write.
    """

    def __init__(self, filename, format):
        """Do not call this constructor directly but use
        `cfg.Directory.open` instead"""

        self.filename = filename
        """The full pathname to the data file"""

        self.contents = {}
        """The contents of the formatted file, read and parsed.

        This will be a `dict` for all formats except `configparser`,
        where it will be a `configparser.SafeConfigParser`.
        """

        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        self.format = format
        self.read()

    def read(self):
        """Re-read the contents from the file"""
        try:
            with open(self.filename) as fp:
                self.contents = self.format.read(fp)
        except IOError:
            self.contents = self.format.create()
        return self.contents

    def write(self):
        """Write the contents to the file"""
        with open(self.filename, 'w') as fp:
            self.format.write(self.contents, fp)

    def as_dict(self):
        """Return a deep copy of the contents as a dict"""
        return self.format.as_dict(self.contents)

    def clear(self):
        """Clear the contents without writing"""
        self.contents.clear()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.write()


class Cache:
    """
    A class that creates caches
    """

    def __init__(self, dirname):
        """Do not call this constructor - instead use `cfgs.App.cache` """

        self.dirname = dirname
        """The full path of the root directory for all cache directories"""

    def directory(self, name='cache', cache_size=0):
        """
        Return a `cfgs.CacheDirectory`

        Arguments:
          name: The relative pathname of the cache directory

          cache_size: The number of bytes allowed in the cache.
              The default of 0 means "unlimited cache size"
        """
        name = os.path.join(self.dirname, name)
        return CacheDirectory(name, cache_size)


class CacheDirectory:
    def __init__(self, dirname, cache_size):
        """Do not call this constructor - use `cfgs.Cache.directory`"""

        self.dirname = dirname
        """The full path to this cache directory"""

        self.cache_size = cache_size
        """
        The number of bytes allowed in the cache.
        0 means "unlimited cache size"
        """

        _makedirs(self.dirname)
        self.prune()

    def open(self, filename, size_guess=0, binary=False):
        """
        Open a cached file in this directory.

        If the file already exists, it is opened for read.

        Otherwise the cache is pruned and the file is opened for write.

        Arguments:
          filename: the name of the file, relative to the cache directory
          size_guess: A guess as to how large the file will be, in bytes
          binary: if True, the file is opened in binary mode

        """
        if '/' in filename:
            raise ValueError('Subdirectories are not allowed in caches')

        bin = 'b' if binary else ''

        full = os.path.join(self.dirname, filename)
        if os.path.exists(full):
            return open(full, 'r' + bin)

        self.prune(size_guess)
        return open(full, 'w' + bin)

    def prune(self, bytes_needed=0):
        """
        Prune the cache to generate at least `bytes_needed` of free space,
        if this is possible.
        """
        if not self.cache_size:
            return

        files = os.listdir(self.dirname)
        info = {f: os.stat(os.path.join(self.dirname, f)) for f in files}
        required_size = sum(s.st_size for f, s in info.items()) + bytes_needed
        if required_size <= self.cache_size:
            return

        # Delete oldest items first
        for f, s in sorted(info.items(), key=lambda x: x[1].st_mtime):
            os.remove(os.path.join(self.dirname, f))
            required_size -= s.st_size
            if required_size <= self.cache_size:
                return


def _check_filename(filename):
    # Just a heuristic - names might pass this test and still not
    # be valid i.e. CON on Windows.
    bad_chars = _BAD_CHARS.intersection(set(filename))
    if bad_chars:
        bad_chars = ''.join(sorted(bad_chars))
        raise ValueError('Invalid characters in filename: "%s"' % bad_chars)


SUFFIX_TO_FORMAT = {
    '.cfg': 'configparser',
    '.ini': 'configparser',
    '.json': 'json',
    '.toml': 'toml',
    '.yaml': 'yaml',
    '.yml': 'yaml',
}
"""
Map file suffixes to the file format - the partial inverse
to `cfgs.FORMAT_TO_SUFFIX`
"""

FORMAT_TO_SUFFIX = {
    'configparser': '.ini',
    'json': '.json',
    'toml': '.toml',
    'yaml': '.yml',
}
"""
Map file formats to file suffix - the partial inverse
to `cfgs.SUFFIX_TO_FORMAT`
"""

FORMATS = set(SUFFIX_TO_FORMAT.values())
"""A list of all formats that `cfgs` understands."""


class Format:
    def __init__(self, format, read_kwds, write_kwds):
        self.name = format
        """The name of this format"""

        self._read_kwds = read_kwds or {}
        self._write_kwds = write_kwds or {}
        self._parser = __import__(format)

    def read(self, fp):
        """Read contents from an open file in this format"""
        load = getattr(self._parser, 'safe_load', self._parser.load)
        return load(fp, **self._read_kwds)

    def write(self, contents, fp):
        """Write contents in this format to an open file"""
        dump = getattr(self._parser, 'safe_dump', self._parser.dump)
        return dump(contents, fp, **self._write_kwds)

    def create(self):
        """Return new, empty contents"""
        return {}

    def as_dict(self, contents):
        """Convert the contents to a dict"""
        return copy.deepcopy(contents)


class ConfigparserFormat(Format):
    name = 'configparser'
    """The name of the configparser format"""

    def __init__(self):
        self._parser = __import__(self.name)

    def read(self, fp):
        """Read contents from an open file in this format"""
        contents = self.create()
        contents.readfp(fp)
        return contents

    def write(self, contents, fp):
        """Write contents in this format to an open file"""
        contents.write(fp)

    def create(self):
        """Return new, empty contents"""
        return self._parser.SafeConfigParser()

    def as_dict(self, contents):
        """Convert the contents to a dict"""
        return {k: dict(v) for k, v in contents.items()}


def _makedirs(f):  # For Python 2 compatibility
    try:
        os.makedirs(f)
    except Exception:
        pass


_BAD_CHARS = set('/\\?%*:|"<>\';')
