import matplotlib
if __name__ == '__main__':
    matplotlib.use('Agg')
import numpy as np
import pylab as plt

import os
import datetime

import emcee
import triangle

import fitsio

from astrometry.util.file import *
from astrometry.util.fits import *
from astrometry.util.multiproc import *
from astrometry.util.plotutils import *
from astrometry.util.miscutils import *
from astrometry.util.util import *
from astrometry.util.resample import *
from astrometry.util.run_command import *
from astrometry.util.starutil_numpy import *
from astrometry.util.ttime import *
from astrometry.libkd.spherematch import *
from astrometry.blind.plotstuff import *

from unwise_coadd import get_wise_frames, get_l1b_file
from wise.wise import *

wisedir = 'wise-frames'

def sampleBall(p0, stdev, nw):
    '''
    Produce a ball of walkers around an initial parameter value 'p0'
    with axis-aligned standard deviation 'stdev', for 'nw' walkers.
    '''
    assert(len(p0) == len(stdev))
    return np.vstack([p0 + stdev * np.random.normal(size=len(p0))
                      for i in range(nw)])
                
def get_tim(w, roi):
    fn = get_l1b_file(wisedir, w.scan_id, w.frame_num, band)
    #print fn
    basefn = fn.replace('-int-1b.fits', '')
    fns = [fn, basefn + '-unc-1b.fits.gz', basefn + '-msk-1b.fits.gz']
    for fn in fns:
        if not os.path.exists(fn):
            #cmd = 'rsync -RLrvz carver:unwise/./%s .' % fn
            cmd = 'rsync -RLrvz carver:unwise/./%s* .' % basefn
            print cmd
            os.system(cmd)
    tim = read_wise_level1b(basefn, radecroi=roi, nanomaggies=True,
                            mask_gz=True, unc_gz=True, sipwcs=True,
                            constantInvvar=True)
    return tim

def all_plots(tractor, ps, S, ima):
    tims = tractor.getImages()

    for i,tim in enumerate(tims):
        mod = tractor.getModelImage(i)

        hh,ww = tim.shape
        wrap = TractorWCSWrapper(tim.wcs, ww, hh)
        #print 'Shape', tim.shape
        #print 'WCS', tim.wcs
        #print 'WCS', tim.wcs.wcs
        Yo,Xo,Yi,Xi,[rim,rmod] = resample_with_wcs(fakewcs, wrap, [tim.data, mod], 3)

        reim  = np.zeros((S,S))
        remod = np.zeros((S,S))
        reie  = np.zeros((S,S))
        reim [Yo,Xo] = rim
        remod[Yo,Xo] = rmod
        reie [Yo,Xo] = tim.getInvError()[Yi,Xi]

        plt.clf()
        plt.subplot(2,2,1)
        plt.imshow(tim.getImage(), **ima)
        ax = plt.axis()
        x,y = tim.getWcs().positionToPixel(RaDecPos(r, d))
        plt.plot([x], [y], 'o', mec='1', mfc='none', ms=12, mew=3)
        plt.axis(ax)

        plt.subplot(2,2,2)
        plt.imshow(reim, **ima)
        plt.suptitle('%.4f' % (tim.time.toYear()))

        plt.subplot(2,2,4)
        plt.imshow(remod, **ima)

        chi = (reim - remod) * reie

        plt.subplot(2,2,3)
        plt.imshow(chi, interpolation='nearest', origin='lower',
                   vmin=-5, vmax=5, cmap='RdBu')
        
        ps.savefig()
    

def epoch_coadd_plots(tractor, ps, S, ima, yearcut):

    bimg  = np.zeros((S,S))
    bmod  = np.zeros((S,S))
    bnum  = np.zeros((S,S))
    bchisq = np.zeros((S,S))
    bchi  = np.zeros((S,S))
    aimg  = np.zeros((S,S))
    amod  = np.zeros((S,S))
    anum  = np.zeros((S,S))
    achisq = np.zeros((S,S))
    achi  = np.zeros((S,S))

    tims = tractor.getImages()
    for i,tim in enumerate(tims):
        mod = tractor.getModelImage(i)

        hh,ww = tim.shape
        wrap = TractorWCSWrapper(tim.wcs, ww, hh)
        #print 'Shape', tim.shape
        #print 'WCS', tim.wcs
        #print 'WCS', tim.wcs.wcs
        Yo,Xo,Yi,Xi,[rim,rmod] = resample_with_wcs(fakewcs, wrap, [tim.data, mod], 3)

        if tim.time.toYear() > yearcut:
            im,mod,num,chisq,chi = (aimg, amod, anum, achisq, achi)
        else:
            im,mod,num,chisq,chi = (bimg, bmod, bnum, bchisq, bchi)
        im[Yo,Xo]  += rim
        mod[Yo,Xo] += rmod
        num[Yo,Xo] += 1.
        chi[Yo,Xo] += ((rim - rmod) * tim.getInvError()[Yi,Xi])
        chisq[Yo,Xo] += ((rim - rmod)**2 * tim.getInvvar()[Yi,Xi])

    bimg /= np.maximum(bnum, 1)
    aimg /= np.maximum(anum, 1)
    bmod /= np.maximum(bnum, 1)
    amod /= np.maximum(anum, 1)

    #print 'N', anum.max(), bnum.max()
    #print 'mean N', anum.mean(), bnum.mean()

    achi /= np.maximum(anum, 1)
    bchi /= np.maximum(bnum, 1)

    nn = np.mean([anum.mean(), bnum.mean()])

    #chimax = max(achisq.max(), bchisq.max())
    #ca = dict(interpolation='nearest', origin='lower', vmin=0, vmax=chimax)
    c2a = dict(interpolation='nearest', origin='lower', vmin=0, vmax=16*nn)
    ca = dict(interpolation='nearest', origin='lower', vmin=-3, vmax=3)

    plt.clf()

    plt.subplot(2,3,1)
    plt.imshow(bimg, **ima)

    plt.subplot(2,3,2)
    plt.imshow(bmod, **ima)
    plt.title('First epoch')

    plt.subplot(2,3,3)
    #plt.imshow(bchisq, **c2a)
    plt.imshow(bchi, **ca)

    plt.subplot(2,3,4)
    plt.imshow(aimg, **ima)

    plt.subplot(2,3,5)
    plt.imshow(amod, **ima)
    plt.title('Second epoch')

    plt.subplot(2,3,6)
    #plt.imshow(achisq, **c2a)
    plt.imshow(achi, **ca)

    ps.savefig()

if __name__ == '__main__':
    import logging
    lvl = logging.INFO
    lvl = logging.DEBUG
    logging.basicConfig(level=lvl, format='%(message)s', stream=sys.stdout)

    r,d = 133.795, -7.245
    #sz = 0.01
    sz = 0.006

    ps = PlotSequence('rogue')

    wfn = 'rogue-frames.fits'
    if os.path.exists(wfn):
        W = fits_table(wfn)
    else:
        W = get_wise_frames(r-sz, r+sz, d-sz, d+sz, margin=1.2)
        W.writeto(wfn)
    print len(W), 'WISE frames'

    band = 2
    W.cut(W.band == band)
    roi = [r-sz, r+sz, d-sz, d+sz]

    if not 'inroi' in W.get_columns():
        W.inroi = np.zeros(len(W), bool)
        for i,w in enumerate(W):
            tim = get_tim(w, roi)
            print 'Got', tim
            if tim is None:
                continue
            W.inroi[i] = True
        W.writeto(wfn)
    
    W.cut(W.inroi)
    W.cut(np.argsort(W.mjd))

    unw = fits_table('unwise-1342m076-w2-frames.fits')

    ima = dict(interpolation='nearest', origin='lower',
               vmin=-15, vmax=50)

    S = 30
    pixscale = 2.75 / 3600.
    fakewcs = Tan(r, d, S/2, S/2, -pixscale, 0., 0., pixscale, S, S)

    # Load the average PSF model (generated by wise_psf.py)
    P = fits_table('wise/wise-psf-avg.fits', hdu=band)
    psf = GaussianMixturePSF(P.amp, P.mean, P.var)

    tims = []
    keepi = []
    for i,w in enumerate(W):
        print
        tim = get_tim(w, roi)
        print 'Got', tim

        I = np.flatnonzero((unw.scan_id   == w.scan_id) *
                           (unw.frame_num == w.frame_num))
        assert(len(I) == 1)
        sky = unw.sky1[I[0]]
        #print 'unwise sky', sky
        #print 'vs', tim.sky
        if sky == 0.:
            sky = tim.sky.getValue()
        # Subtract sky estimate
        tim.data -= sky
        tim.sky.setValue(0)
        tim.zr = (tim.zr[0]-sky, tim.zr[1]-sky)
        #print 'zr', tim.zr

        maskfn = 'unwise-1342m076-w2-mask/unwise-mask-1342m076-%s%03i-w%i-1b.fits.gz' % (w.scan_id, w.frame_num, band)
        if not os.path.exists(maskfn):
            print 'no such file:', maskfn
            continue

        keepi.append(i)
        tims.append(tim)
        
        M = fitsio.read(maskfn)
        print 'read mask', M.shape, M.dtype
        x0,x1,y0,y1 = tim.extent
        M = M[y0:y1, x0:x1]
        masked = (M > 0)
        tim.data[masked] = 0.
        tim.invvar[masked] = 0.
        tim.psf = psf



    W.cut(np.array(keepi))
    assert(len(W) == len(tims))

    pm = PMRaDec(0., 0.)
    pm.setStepSizes(1e-4)
    parallax = 0.

    epochyr = 2010.5

    epoch = TAITime(None, mjd=datetomjd(datetime.datetime(2010, 9, 1)))
    print 'Epoch:', epoch.toYear()
    
    srcs = [
        PointSource(RaDecPos(133.7894517, -7.2508217),
                    NanoMaggies(w2=NanoMaggies.magToNanomaggies(13.731))),
        PointSource(RaDecPos(133.7974342, -7.2409883),
                    NanoMaggies(w2=NanoMaggies.magToNanomaggies(15.864))),
        MovingPointSource(RaDecPos(133.7947597, -7.2451456),
                          NanoMaggies(w2=NanoMaggies.magToNanomaggies(13.704)),
                          pm, parallax, epoch=epoch),
        ]

    tractor = Tractor(tims, srcs)
    tractor.freezeParams('images')
    tractor.printThawedParams()
    tractor.catalog.freezeParamsRecursive('*')
    tractor.catalog.thawPathsTo('w%i' % band)
    print 'Before fitting:', tractor.getParams()
    tractor.optimize_forced_photometry()
    print 'After  fitting:', tractor.getParams()

    epoch_coadd_plots(tractor, ps, S, ima, epochyr)
    #all_plots(tractor, ps, S, ima)

    print 'Fitting PM/Parallax...'
    tractor.catalog.thawPathsTo('pmra', 'pmdec', 'parallax')
    src = tractor.catalog[-1]
    src.thawPathsTo('ra', 'dec')
    tractor.printThawedParams()

    print 'Source', src

    dlnp,X,alpha,var = tractor.optimize(shared_params=False, variance=True, damp=1e-3)
    print 'Optimize:', dlnp
    print 'var:', var

    print 'Sampling:'
    tractor.catalog[0].freezeAllParams()
    tractor.catalog[1].freezeAllParams()

    dlnp,X,alpha,var = tractor.optimize(shared_params=False, variance=True, damp=1e-3)
    print 'Optimize:', dlnp
    print 'var:', var

    epoch_coadd_plots(tractor, ps, S, ima, epochyr)

    tractor.printThawedParams()

    nw = 30
    ndim = len(tractor.getParams())
    nthreads = 10

    p0 = tractor.getParams()

    print 'p0', p0
    
    # Create emcee sampler
    sampler = emcee.EnsembleSampler(nw, ndim, tractor, threads=nthreads)

    # Initial walker params
    pp = sampleBall(p0, 0.5 * np.sqrt(var), nw)

    nsteps = 50
                
    alllnp = np.zeros((nsteps,nw))
    allp = np.zeros((nsteps,nw,ndim))

    lnp = None
    rstate = None
    for step in range(nsteps):
        print 'Taking step', step
        pp,lnp,rstate = sampler.run_mcmc(pp, 1, lnprob0=lnp, rstate0=rstate)
        print 'Max lnprob:', np.max(lnp)
        imax = np.argmax(lnp)
        print pp[imax,:]
        alllnp[step,:] = lnp
        allp[step,:,:] = pp

    epoch_coadd_plots(tractor, ps, S, ima, epochyr)

    # Plot logprobs
    plt.clf()
    plt.plot(alllnp, 'k', alpha=0.5)
    mx = np.max([p.max() for p in alllnp])
    plt.ylim(mx-20, mx+5)
    plt.title('logprob')
    ps.savefig()

    # Plot parameter distributions
    burn = 20
    print 'All params:', allp.shape
    for i,nm in enumerate(tractor.getParamNames()):
        pp = allp[:,:,i].ravel()
        lo,hi = [np.percentile(pp,x) for x in [5,95]]
        mid = (lo + hi)/2.
        lo = mid + (lo-mid)*2
        hi = mid + (hi-mid)*2
        plt.clf()
        plt.subplot(2,1,1)
        plt.hist(allp[burn:,:,i].ravel(), 50, range=(lo,hi))
        plt.xlim(lo,hi)
        plt.subplot(2,1,2)
        plt.plot(allp[:,:,i], 'k-', alpha=0.5)
        plt.xlabel('emcee step')
        plt.ylim(lo,hi)
        plt.suptitle(nm)
        ps.savefig()

    nkeep = allp.shape[0] - burn
    X = allp[burn:, :,:].reshape((nkeep * nw, ndim))
    plt.clf()
    triangle.corner(X, labels=src.getParamNames(), plot_contours=False)
    ps.savefig()
                                                                                    
