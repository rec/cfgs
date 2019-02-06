from pyfakefs.fake_filesystem_unittest import TestCase as FakeTestCase
import cfgs


class TestCase(FakeTestCase):
    ENV = {}
    VARS = {'$HOME': '/usr/fake'}
    CACHE_SIZE = 0

    def setUp(self):
        self.setUpPyfakefs()
        cfgs.expandvars, self._expandvars = self.expandvars, cfgs.expandvars
        cfgs.getenv, self._getenv = self.ENV.get, cfgs.getenv
        self.cfgs = cfgs.Cfgs('test', self.CACHE_SIZE)

    def tearDown(self):
        cfgs.expandvars, cfgs.getenv = self._expandvars, self._getenv

    def expandvars(self, s):
        for k, v in self.VARS.items():
            s = s.replace(k, v)
        return s


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
