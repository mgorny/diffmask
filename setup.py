#!/usr/bin/python
#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 3-clause BSD license.

from distutils.core import setup

import os.path, sys

sys.path.insert(0, os.path.join(os.path.dirname(sys.argv[0]), 'lib'))
try:
	from diffmask import PV
except ImportError:
	PV = 'unknown'

setup(
		name = 'diffmask',
		version = PV,
		author = 'Michał Górny',
		author_email = 'mgorny@gentoo.org',
		url = 'http://github.com/mgorny/diffmask',

		package_dir = {'': 'lib'},
		packages = ['diffmask'],
		scripts = ['diffmask'],

		classifiers = [
			'Development Status :: 3 - Alpha',
			'Environment :: Console',
			'Intended Audience :: System Administrators',
			'License :: OSI Approved :: BSD License',
			'Operating System :: POSIX',
			'Programming Language :: Python',
			'Topic :: System :: Installation/Setup'
		]
)
