#!/usr/bin/python
#	vim:fileencoding=utf-8
# (C) 2010 Michał Górny, distributed under the terms of 3-clause BSD license

import codecs, os.path
from diffmask.util import DiffmaskList

class MaskMerge(DiffmaskList):
	""" A class representing the contents of a set of merged
		package.mask files as a string list (with newlines preserved).
		"""
	def ProcessMaskFile(self, file, header):
		""" Read a single package.mask file (being given as an open file
			instance) and append it with the name `header'. """
		mf = file.readlines()

		# try to drop copyright, examples etc.
		ccb = None # current comment block
		gotwhite = True # whitespace status

		for i in range(len(mf)):
			if mf[i].startswith('#'):
				if gotwhite:
					ccb = i
					gotwhite = False
			elif not mf[i].strip():
				gotwhite = True
			else: # package atom
				if ccb is not None:
					del mf[:ccb]
				break

		# Ensure the trailing newline.
		try:
			if mf[-1].strip():
				mf.append('\n')
		except IndexError: # An empty repo? Just omit it.
			return

		self.extend(['## *%s*\n' % header, '\n'])
		self.extend(mf)

	def ProcessRepos(self):
		for o in self.portdb.getRepositories():
			path = self.portdb.getRepositoryPath(o)
			try:
				maskf = codecs.open(os.path.join(path, 'profiles', 'package.mask'), 'r', 'utf8')
			except IOError:
				pass
			else:
				self.ProcessMaskFile(maskf, o)

	def ProcessProfiles(self):
		for p in self.portdb.settings.profiles:
			try:
				maskf = codecs.open(os.path.join(p, 'package.mask'), 'r', 'utf8')
			except IOError:
				pass
			else:
				profname = 'profile: %s' % os.path.relpath(p, os.path.join(self.portdb.porttree_root, 'profiles'))
				self.ProcessMaskFile(maskf, profname)

	def __init__(self, dbapi):
		""" Instantiate the MaskMerge class. Grab the list of active
			package.mask files from Portage and read them. """
		self.portdb = dbapi
		self.ProcessRepos()
		self.ProcessProfiles()
		# Drop the trailing blank line.
		if not self[-1].strip():
			del self[-1]
