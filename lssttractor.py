if __name__ == '__main__':
	import matplotlib
	matplotlib.use('Agg')

import os
import logging
import numpy as np
import pylab as plt

import pyfits

from astrometry.util.file import *
from astrometry.util.util import Sip
from astrometry.util.pyfits_utils import *

#from tractor import *
#from tractor import sdss as st
import tractor
from tractor import sdss_galaxy as gal

def main():
	from optparse import OptionParser
	import sys

	parser = OptionParser(usage=('%prog <img> <psf> <srcs>'))
	parser.add_option('-v', '--verbose', dest='verbose', action='count', default=0,
					  help='Make more verbose')
	opt,args = parser.parse_args()

	if len(args) != 3:
		parser.print_help()
		sys.exit(-1)

	if opt.verbose == 0:
		lvl = logging.INFO
	else:
		lvl = logging.DEBUG
	logging.basicConfig(level=lvl, format='%(message)s', stream=sys.stdout)

	imgfn, psffn, srcfn = args

	pimg = pyfits.open(imgfn)
	if len(pimg) != 4:
		print 'Image must have 3 extensions'
		sys.exit(-1)
	img = pimg[1].data
	mask = pimg[2].data
	var = pimg[3].data
	del pimg
	
	print 'var', var.shape
	#print var
	print 'mask', mask.shape
	#print mask
	print 'img', img.shape
	#print img

	print 'Variance range:', var.min(), var.max()

	print 'Image median:', np.median(img.ravel())

	invvar = 1./var
	invvar[var == 0] = 0.
	invvar[var < 0] = 0.

	assert(all(np.isfinite(img.ravel())))
	assert(all(np.isfinite(invvar.ravel())))

	psf = pyfits.open(psffn)[0].data
	print 'psf', psf.shape
	psf /= psf.sum()

	from tractor.emfit import em_fit_2d
	from tractor.fitpsf import em_init_params

	# Create Gaussian mixture model PSF approximation.
	S = psf.shape[0]
	# number of Gaussian components
	K = 3
	w,mu,sig = em_init_params(K, None, None, None)
	II = psf.copy()
	II /= II.sum()
	# HIDEOUS HACK
	II = np.maximum(II, 0)
	print 'Multi-Gaussian PSF fit...'
	xm,ym = -(S/2), -(S/2)
	em_fit_2d(II, xm, ym, w, mu, sig)
	print 'w,mu,sig', w,mu,sig
	mypsf = tractor.GaussianMixturePSF(w, mu, sig)


	P = mypsf.getPointSourcePatch(S/2, S/2)
	mn,mx = psf.min(), psf.max()
	ima = dict(interpolation='nearest', origin='lower',
			   vmin=mn, vmax=mx)
	plt.clf()
	plt.subplot(1,2,1)
	plt.imshow(psf, **ima)
	plt.subplot(1,2,2)
	pimg = np.zeros_like(psf)
	P.addTo(pimg)
	plt.imshow(pimg, **ima)
	plt.savefig('psf.png')

	sig = np.sqrt(np.median(var))

	plt.clf()
	plt.hist(img.ravel(), 100, range=(-3.*sig, 3.*sig))
	plt.savefig('imghist.png')

	srcs = fits_table(srcfn)
	print 'Initial:', len(srcs), 'sources'
	# Trim sources with x=0 or y=0
	srcs = srcs[(srcs.x != 0) * (srcs.y != 0)]
	print 'Trim on x,y:', len(srcs), 'sources left'
	# Zero out nans & infs
	for c in ['theta', 'a', 'b']:
		I = np.logical_not(np.isfinite(srcs.get(c)))
		srcs.get(c)[I] = 0.
	# Set sources with flux=NaN to something more sensible...
	I = np.logical_not(np.isfinite(srcs.flux))
	srcs.flux[I] = 1.
	# Sort sources by flux.
	srcs = srcs[np.argsort(-srcs.flux)]

	# Trim sources that are way outside the image.
	margin = 8. * np.maximum(srcs.a, srcs.b)
	H,W = img.shape
	srcs = srcs[(srcs.x > -margin) * (srcs.y > -margin) *
				(srcs.x < (W+margin) * (srcs.y < (H+margin)))]
	print 'Trim out-of-bounds:', len(srcs), 'sources left'


	wcs = tractor.FitsWcs(Sip(imgfn, 1))
	#wcs = tractor.NullWCS()

	timg = tractor.Image(data=img, invvar=invvar, psf=mypsf, wcs=wcs,
						 sky=tractor.ConstantSky(0.),
						 photocal=tractor.NullPhotoCal(),
						 name='image')

	inverr = timg.getInvError()
	assert(all(np.isfinite(inverr.ravel())))

	tsrcs = []
	for s in srcs:
		#pos = tractor.PixPos(s.x, s.y)
		pos = tractor.RaDecPos(s.ra, s.dec)
		if s.a > 0 and s.b > 0:
			eflux = tractor.Flux(s.flux / 2.)
			dflux = tractor.Flux(s.flux / 2.)
			re,ab,phi = s.a, s.b/s.a, 90.-s.theta
			eshape = gal.GalaxyShape(re,ab,phi)
			dshape = gal.GalaxyShape(re,ab,phi)
			print 'Fluxes', eflux, dflux
			tsrc = gal.CompositeGalaxy(pos, eflux, eshape, dflux, dshape)
		else:
			flux = tractor.Flux(s.flux)
			print 'Flux', flux
			tsrc = tractor.PointSource(pos, flux)
		tsrcs.append(tsrc)

	chug = tractor.Tractor([timg], catalog=tsrcs)

	ima = dict(interpolation='nearest', origin='lower',
			   vmin=-3.*sig, vmax=10.*sig)
	chia = dict(interpolation='nearest', origin='lower',
				vmin=-5., vmax=5.)

	plt.clf()
	plt.imshow(img, **ima)
	plt.colorbar()
	plt.savefig('img.png')

	mod = chug.getModelImages()[0]
	plt.clf()
	plt.imshow(mod, **ima)
	plt.colorbar()
	plt.savefig('mod.png')

	chi = chug.getChiImage(0)
	plt.clf()
	plt.imshow(chi, **chia)
	plt.colorbar()
	plt.savefig('chi.png')

	for step in range(5):
		#for i,src in enumerate(chug.getCatalog()):
		for i,src in enumerate([]):
			print 'Optimizing source', i, 'of', len(chug.getCatalog())

			pre = src.getModelPatch(timg)

			dlnp1,X,a = chug.optimizeCatalogFluxes(srcs=[src])
			dlnp2,X,a = chug.optimizeCatalogAtFixedComplexityStep(srcs=[src])

			post = src.getModelPatch(timg)

			print 'dlnp', dlnp1, dlnp2

			plt.clf()
			plt.subplot(2,2,1)
			img = timg.getImage()
			(x0,x1,y0,y1) = pre.getExtent()
			#print x0,x1,y0,y1
			#plt.imshow(img[y0:y1, x0:x1], **ima)
			plt.imshow(img, **ima)
			ax = plt.axis()
			plt.plot([x0,x0,x1,x1,x0], [y0,y1,y1,y0,y0], 'k-', lw=2)
			plt.axis(ax)
			plt.subplot(2,2,3)
			plt.imshow(pre.getImage(), **ima)
			plt.subplot(2,2,4)
			plt.imshow(post.getImage(), **ima)
			plt.savefig('prepost-s%i-s%03i.png' % (step, i))

			mod = chug.getModelImages()[0]
			plt.clf()
			plt.imshow(mod, **ima)
			plt.colorbar()
			plt.savefig('mod-s%i-s%03i.png' % (step, i))

			chi = chug.getChiImage(0)
			plt.clf()
			plt.imshow(chi, **chia)
			plt.colorbar()
			plt.savefig('chi-s%i-s%03i.png' % (step, i))


		dlnp,x,a = chug.optimizeCatalogFluxes()
		print 'fluxes: dlnp', dlnp
		dlnp,x,a = chug.optimizeCatalogAtFixedComplexityStep()
		print 'opt: dlnp', dlnp

		mod = chug.getModelImages()[0]
		plt.clf()
		plt.imshow(mod, **ima)
		plt.colorbar()
		plt.savefig('mod-s%i.png' % step)

		chi = chug.getChiImage(0)
		plt.clf()
		plt.imshow(chi, **chia)
		plt.colorbar()
		plt.savefig('chi-s%i.png' % step)


	return

	for step in range(5):
		chug.optimizeCatalogFluxes()
		mod = chug.getModelImages()[0]
		plt.clf()
		plt.imshow(mod, **ima)
		plt.colorbar()
		plt.savefig('mod-s%i.png' % step)

		chi = chug.getChiImage(0)
		plt.clf()
		plt.imshow(chi, **chia)
		plt.colorbar()
		plt.savefig('chi-s%i.png' % step)

	
if __name__ == '__main__':
	main()
	
