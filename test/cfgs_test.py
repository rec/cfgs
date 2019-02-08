import cfgs, json
from pyfakefs.fake_filesystem_unittest import TestCase as FakeTestCase


class TestCase(FakeTestCase):
    ENV = {'XDG_RUNTIME_DIR': '/var/rt'}
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
        self.assertEqual(x.XDG_RUNTIME_DIR, '/var/rt')

        with self.assertRaises(AttributeError):
            x.XDG_CACHE_DIRS

    def test_dir(self):
        self.assertEqual(
            sorted(dir(cfgs.XDG)),
            ['XDG_CACHE_HOME', 'XDG_CONFIG_DIRS', 'XDG_CONFIG_HOME',
             'XDG_DATA_DIRS', 'XDG_DATA_HOME', 'XDG_RUNTIME_DIR'])


class ConfigTest(TestCase):
    def test_simple(self):
        with cfgs.Cfgs('test').config.open() as f:
            print('XXXX', f.filename)
            f['foo'] = 'bar'
            f['baz'] = [2, 3, 4]
            del f['foo']
            f.update(zip='zap')

        expected = {'baz': [2, 3, 4], 'zip': 'zap'}
        actual = json.load(open('/usr/fake/.config/test/test.json'))
        self.assertEqual(actual, expected)

    def test_read_write(self):
        with cfgs.Cfgs('test').config.open() as f:
            f['foo'] = 'bar'
            f['baz'] = [2, 3, 4]
            del f['foo']
            f.update(zip='zap')

        with cfgs.Cfgs('test').config.open() as f:
            self.assertEqual(f['zip'], 'zap')
            self.assertEqual(f.data, {'baz': [2, 3, 4], 'zip': 'zap'})

    def test_bad_format(self):
        c = cfgs.Cfgs('test', format='wombat')
        with self.assertRaises(ValueError):
            c.config.open()

    def test_guess_format(self):
        with cfgs.Cfgs('test').data.open('special.yml') as f:
            f['foo'] = 'bar'
            f['baz'] = [2, 3, 4]
            del f['foo']
            f.update(zip='zap')

        with cfgs.Cfgs('test').data.open('special.yml') as f:
            self.assertEqual(f.data, {'baz': [2, 3, 4], 'zip': 'zap'})
            self.assertNotIn('"', open(f.filename).read())
            self.assertIn('zip', open(f.filename).read())

    def test_configfile(self):
        with cfgs.Cfgs('test', format='configparser').config.open() as f:

            f['foo'] = {'a' : 1, 'b': 2}
            f['bar'] = {}
            print('XXX', f.filename)

        with cfgs.Cfgs('test').config.open(format='configparser') as f:
            print('XXX', f.filename)
            actual = {k: dict(v) for k, v in f.data.items()}
            expected = {'DEFAULT': {}, 'foo': {'a' : '1', 'b': '2'}, 'bar': {}}
            self.assertEqual(expected, actual)


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
