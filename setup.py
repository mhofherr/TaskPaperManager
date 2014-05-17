from __future__ import print_function
import os
import codecs
import os
import re
from distutils.core import setup, Command

from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))


class PyTest(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import sys
        import subprocess
        errno = subprocess.call([sys.executable, 'runtests.py'])
        raise SystemExit(errno)


def read(*paths):
    """Build a file path from *paths* and return the contents."""
    with open(os.path.join(*paths), 'r') as f:
        return f.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name='TaskPaperManager',
    version=find_version('tpm', '__init__.py'),
    description='Parse TaskPaper files and launch actions',
    long_description=(read('README.md')),
    #long_description=(read('README.rst') + '\n\n' +
    #                  read('HISTORY.rst') + '\n\n' +
    #                  read('AUTHORS.rst')),
    url='https://github.com/mhofherr/TaskPaperParser',
    license='GPLv3',
    author='Matthias Hofherr',
    author_email='matthias@mhofherr.de',
    include_package_data=False,
    packages=['tpm'],
    install_requires=[
        'pkginfo>=1.1',
        'py>=1.4.20',
        'pytest>=2.5.2',
        'python-dateutil>=2.2',
        'python-gnupg>=0.3.6',
        'requests>=2.3.0'
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: End Users/Desktop',
        'Natural Language :: English',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords='TaskPaper',
    cmdclass = {'test': PyTest},
)
