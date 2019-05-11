from setuptools import setup
from setuptools.command.test import test as TestCommand
import os
import sys


# From here: http://pytest.org/2.2.4/goodpractises.html
class RunTests(TestCommand):
    DIRECTORY = 'test'

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = [self.DIRECTORY]
        self.test_suite = True

    def run_tests(self):
        # Import here, because outside the eggs aren't loaded.
        import pytest

        errno = pytest.main(self.test_args)
        if errno:
            raise SystemExit(errno)


class RunCoverage(RunTests):
    def run_tests(self):
        import coverage

        cov = coverage.Coverage(config_file=True)

        cov.start()
        super().run_tests()
        cov.stop()

        cov.report(file=sys.stdout)
        coverage = cov.html_report(directory='htmlcov')
        fail_under = cov.get_option('report:fail_under')
        if coverage < fail_under:
            print(
                'ERROR: coverage %.2f%% was less than fail_under=%s%%'
                % (coverage, fail_under)
            )
            raise SystemExit(1)


NAME = 'cfgs'
OWNER = 'rec'
FILENAME = os.path.join(os.path.dirname(__file__), 'VERSION')
VERSION = open(FILENAME).read().strip()

URL = 'http://github.com/{OWNER}/{NAME}'.format(**locals())
DOWNLOAD_URL = '{URL}/archive/{VERSION}.tar.gz'.format(**locals())

with open('test_requirements.txt') as f:
    TESTS_REQUIRE = f.read().splitlines()


setup(
    name=NAME,
    version=open('VERSION').read().strip(),
    description=(
        'cfgs is a pure Python library for data and config files which '
        'implements the XDG standard for persistent files'
    ),
    long_description=open('README.rst').read(),
    author='Tom Ritchford',
    author_email='tom@swirly.com',
    url=URL,
    download_url=DOWNLOAD_URL,
    license='MIT',
    py_modules=['cfgs'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    tests_require=TESTS_REQUIRE,
    cmdclass={'coverage': RunCoverage, 'test': RunTests},
    keywords=[
        'configuration',
        'cache',
        'configparser',
        'json',
        'toml',
        'yaml',
    ],
)
