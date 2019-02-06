import cfgs, json
from pyfakefs.fake_filesystem_unittest import TestCase as FakeTestCase


class TestCase(FakeTestCase):
    ENV = {}
    VARS = {'$HOME': '/usr/fake'}

    def setUp(self):
        self.setUpPyfakefs()
        cfgs.expandvars, self._expandvars = self.expandvars, cfgs.expandvars
        cfgs.getenv, self._getenv = self.ENV.get, cfgs.getenv

    def tearDown(self):
        cfgs.expandvars, cfgs.getenv = self._expandvars, self._getenv

    def expandvars(self, s):
        for k, v in self.VARS.items():
            s = s.replace(k, v)
        return s


class TestTestCase(TestCase):
    def test_test_case(self):
        self.assertIs(self._getenv('NOT_DEFINED_NOT_DEFINED'), None)
        nd = '/var/$NOT_DEFINED_NOT_DEFINED/baz'
        self.assertEqual(self._expandvars(nd), nd)


class XDGTest(TestCase):
    def test_simple(self):
        x = cfgs.XDG

        self.assertEqual(x.XDG_CACHE_HOME, '/usr/fake/.cache')
        self.assertEqual(x.XDG_CONFIG_DIRS, '/etc/xdg')
        self.assertEqual(x.XDG_CONFIG_HOME, '/usr/fake/.config')
        self.assertEqual(x.XDG_DATA_DIRS, '/usr/local/share/:/usr/share/')
        self.assertEqual(x.XDG_DATA_HOME, '/usr/fake/.local/share')
        self.assertEqual(x.XDG_RUNTIME_DIR, '')

        self.assertEqual(x.cache_home, '/usr/fake/.cache')
        self.assertEqual(x.config_dirs, '/etc/xdg')
        self.assertEqual(x.config_home, '/usr/fake/.config')
        self.assertEqual(x.data_dirs, '/usr/local/share/:/usr/share/')
        self.assertEqual(x.data_home, '/usr/fake/.local/share')
        self.assertEqual(x.runtime_dir, '')

    def test_dir(self):
        self.assertEqual(
            sorted(dir(cfgs.XDG)),
            ['XDG_CACHE_HOME', 'XDG_CONFIG_DIRS', 'XDG_CONFIG_HOME',
             'XDG_DATA_DIRS', 'XDG_DATA_HOME', 'XDG_RUNTIME_DIR'])


class ConfigTest(TestCase):
    def test_simple(self):
        _write_file()
        expected = {'baz': [2, 3, 4], 'zip': 'zap'}
        actual = json.load(open('/usr/fake/.config/test/test.json'))
        self.assertEqual(actual, expected)

    def test_read_write(self):
        _write_file()

        with cfgs.Cfgs('test').config.file() as f:
            self.assertEqual(f['zip'], 'zap')
            self.assertEqual(f.data, {'baz': [2, 3, 4], 'zip': 'zap'})

    def test_configfile(self):
        with cfgs.Cfgs('test', format='ini').config.file() as f:
            f['foo'] = {'a' : 1, 'b': 2}
            f['bar'] = {}

        with cfgs.Cfgs('test', format='ini').config.file() as f:
            actual = {k: dict(v) for k, v in f.data.items()}
            expected = {'DEFAULT': {}, 'foo': {'a' : '1', 'b': '2'}, 'bar': {}}
            self.assertEqual(expected, actual)


class ConfigEnvTest(TestCase):
    ENV = {'CFGS_FORMATS': 'json:yaml'}

    def test_simple(self):
        cfgs.Cfgs('test', format='yaml')
        with self.assertRaises(ValueError):
            cfgs.Cfgs('test', format='ini')


class AllFilesTest(TestCase):
    def test_data(self):
        files = ('/usr/share/wombat.json', '/etc/xdg/test/wombat.json',
                 '/wombat.json')
        for f in files:
            self.fs.create_file(f)
        cfg = cfgs.Cfgs('test')
        actual = list(cfg.config.all_files('wombat.json'))
        expected = ['/etc/xdg/test/wombat.json']
        self.assertEqual(actual, expected)


def _write_file():
    with cfgs.Cfgs('test').config.file() as f:
        f['foo'] = 'bar'
        f['baz'] = [2, 3, 4]
        del f['foo']
        f.update(zip='zap')
