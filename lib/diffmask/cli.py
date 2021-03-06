#!/usr/bin/python
#	vim:fileencoding=utf-8
# (C) 2010 Michał Górny, distributed under the terms of 3-clause BSD license

import optparse, os, os.path, tempfile

from portage import create_trees
from portage.const import USER_CONFIG_PATH
from portage.package.ebuild.getmaskingstatus import getmaskingstatus
from portage.package.ebuild.getmaskingreason import getmaskingreason
from portage.versions import best

from diffmask import PV as MY_PV
from diffmask.maskfile import MaskFile
from diffmask.maskmerge import MaskMerge
from diffmask.unmaskfile import UnmaskFile
from diffmask.syncedunmaskfile import SyncedUnmaskFile

def update(unmask, mask, dbapi):
	if mask is None:
		mask = MaskFile(MaskMerge(dbapi))
	elif isinstance(mask, MaskMerge):
		mask = MaskFile(mask)
	if not isinstance(unmask, UnmaskFile):
		unmask = UnmaskFile(unmask)

	return (SyncedUnmaskFile(mask, unmask), mask)

def vimdiff(vimdiffcmd, unmaskpath, m, dbapi):
	if isinstance(unmaskpath, UnmaskFile):
		unmaskpath = unmaskpath.write()
	if m is None:
		m = MaskMerge(dbapi)

	t = tempfile.NamedTemporaryFile()
	t.write(m.toString().encode('utf8'))
	t.flush()

	os.system('%s "%s" "%s"' % (vimdiffcmd, t.name, unmaskpath))
	return (unmaskpath, m)

def find_cpv_match(mask, cpv, comment = None, dbapi = None):
	""" Try to get first good match for cpv and the comment in the mask
		file. """
	def repo_iter(f):
		for r in mask:
			for b in r:
				yield (r, b)

	if dbapi is not None:
		slot = dbapi.aux_get(cpv, ['SLOT'])[0]
		if slot:
			cpv = '%s:%s' % (cpv, slot)

	match = None
	for r, b in repo_iter(mask):
		if cpv in b:
			match = (r, b)
			# getmaskingreason() can sometime provide a broken comment,
			# so don't require a match (but prefer one)
			if comment is None or b.comment == comment:
				break

	if match is None:
		raise ValueError('CPV not matched anything in the file')

	return match

def add(pkgs, unmask, mask, dbapi):
	if mask is None:
		mask = MaskFile(MaskMerge(dbapi))
	elif isinstance(mask, MaskMerge):
		mask = MaskFile(mask)
	if not isinstance(unmask, UnmaskFile):
		unmask = UnmaskFile(unmask)

	for pkg in pkgs:
		matches = dbapi.xmatch('match-all', pkg)
		if not matches:
			print('No packages match %s.' % pkg)
			continue

		skipping = False
		while len(matches) > 0:
			bm = best(matches)
			ms = getmaskingstatus(bm)

			if skipping:
				if ms:
					print("(if you'd like to unmask the older version,\n pass <=%s instead)" % bm)
					break
			elif not ms:
				print('%s is visible, skipping the atom.' % bm)
				skipping = True
			elif ms != ['package.mask']:
				print('%s is masked by: %s; skipping.' % (bm, ', '.join(ms)))
			else:
				mr = getmaskingreason(bm).splitlines(True)
				if not mr[0].startswith('#'):
					raise AssertionError("getmaskingreason() didn't return a comment")

				try:
					(r, b) = find_cpv_match(mask, bm, mr, dbapi)
				except ValueError:
					print('Unable to find a matching mask for %s.' % bm)
				else:
					print('Unmasking %s.' % bm)

					try:
						ur = unmask[r.name]
					except KeyError:
						ur = unmask.MaskRepo(r.name)
						unmask.append(ur)

					ur.append(b)
				break

			matches.remove(bm)
		else:
			print("No '%s' suitable for unmasking found." % pkg)

	return (unmask, mask)

def delete(pkgs, unmask, mask, dbapi):
	if not isinstance(unmask, UnmaskFile):
		unmask = UnmaskFile(unmask)

	for pkg in pkgs:
		matches = dbapi.xmatch('match-visible', pkg)
		if not matches:
			print('No packages match %s.' % pkg)
			continue

		while len(matches) > 0:
			bm = best(matches)

			try:
				(r, b) = find_cpv_match(unmask, bm, dbapi = dbapi)
			except ValueError:
				print('No mask for %s found.' % bm)
			else:
				print('Removing unmask for %s.' % bm)
				r.remove(b)

				# Feel free to remove an empty repository.
				if not r:
					unmask.remove(r)
				break

			matches.remove(bm)
		else:
			print("No '%s' suitable for un-unmasking found." % pkg)

	return (unmask, mask)

def main(argv):
	parser = optparse.OptionParser(version=MY_PV, usage='%prog <actions> [options] [packages]')
	parser.add_option('-U', '--unmask-file', action='store',
			dest='unmask', help='package.unmask file location')

	gr = optparse.OptionGroup(parser, 'Actions')
	gr.add_option('-a', '--add', action='append_const',
			dest='mode', const='add',
			help='Unmask specified packages.')
	gr.add_option('-d', '--delete', action='append_const',
			dest='mode', const='delete',
			help='Remove the unmask entries for specified packages.')
	gr.add_option('-u', '--update', action='append_const',
			dest='mode', const='update',
			help='Update unmasks according to the package.mask files and remove the old ones.')
	gr.add_option('-v', '--vimdiff', action='append_const',
			dest='mode', const='vimdiff',
			help='vimdiff the merged package.mask file with package.unmask.')
	parser.add_option_group(gr)

	gr = optparse.OptionGroup(parser, 'Options related to vimdiff')
	gr.add_option('--vimdiffcmd', action='store',
			dest='vimdiff', default='vimdiff', help='vimdiff command')
	parser.add_option_group(gr)

	(opts, args) = parser.parse_args(args=argv[1:])

	if not opts.mode:
		if os.path.basename(argv[0]).startswith('vimdiff'):
			opts.mode = ('vimdiff')
		else:
			parser.print_help()
			return 2

	opts.mode = frozenset(opts.mode)
	if 'add' in opts.mode and 'delete' in opts.mode:
		parser.error('--add and --delete arguments are exclusive.')
		return 2
	if not args and ('add' in opts.mode or 'delete' in opts.mode):
		parser.error('--and and --delete actions require at least a single package')
		return 2

	trees = create_trees(
			config_root = os.environ.get('PORTAGE_CONFIGROOT'),
			target_root = os.environ.get('ROOT'))
	porttree = trees[max(trees)]['porttree']
	portdb = porttree.dbapi

	unmask = opts.unmask
	if not unmask:
		unmask = os.path.join(porttree.settings['PORTAGE_CONFIGROOT'],
			USER_CONFIG_PATH, 'package.unmask')
		if os.path.isdir(unmask):
			unmask = os.path.join(unmask, 'diffmask')
	mask = None

	if 'add' in opts.mode:
		(unmask, mask) = add(args, unmask, mask, dbapi = portdb)
	elif 'delete' in opts.mode:
		(unmask, mask) = delete(args, unmask, mask, dbapi = portdb)
	if 'update' in opts.mode:
		(unmask, mask) = update(unmask, mask, dbapi = portdb)
	if 'vimdiff' in opts.mode:
		(unmask, mask) = vimdiff(opts.vimdiff, unmask, mask, dbapi = portdb)

	if isinstance(unmask, UnmaskFile):
		unmask.write()

	return 0
