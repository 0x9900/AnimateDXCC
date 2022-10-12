#!/usr/bin/env python3
#
import sys

from setuptools import setup, find_packages

__author__ = "Fred C. (W6BSD)"
__version__ = '1.0.1'
__license__ = 'BSD'

long_description = open('./README.md').read()

URLS = {
  'Source': 'https://github.com/0x9900/AnimateDXCC/',
  'Tracker': 'https://github.com/0x9900/AnimateDXCC/issues',
}

py_version = sys.version_info[:2]
if py_version < (3, 9):
  raise RuntimeError('AnimMUF requires Python 3.9 or later')

setup(
  name='AnimateDXCC',
  version=__version__,
  description='DXCC Animation',
  long_description=long_description,
  long_description_content_type='text/markdown',
  url='https://0x9900.com/',
  project_urls = URLS,
  license=__license__,
  author=__author__,
  author_email='w6bsd@bsdworld.org',
  py_modules=[
    'animatedxcc',
    'purge_images'
  ],
  python_requires=">=3.9.0",
  entry_points = {
    'console_scripts': [
      'animatedxcc = animatedxcc:main',
      'purge_images = purge_images:main',
    ],
  },
  classifiers=[
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.9',
    'Topic :: Communications :: Ham Radio',
  ],
)
