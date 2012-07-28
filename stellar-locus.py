import matplotlib
matplotlib.use('Agg')
import pylab as plt
import numpy as np

from astrometry.util.pyfits_utils import *
from astrometry.util.plotutils import *
from astrometry.sdss import cas_flags

T = fits_table('MyTable_19_dstn.fit')

flag_names = dict((v,k) for k,v in cas_flags.items())

child = cas_flags['CHILD']

print 'now', len(T), 'total', sum((T.flags & child) > 0), 'CHILD'

badflags = 0
for flag in [ #'BLENDED',
	'NODEBLEND', 'MAYBE_CR', 'SATURATED',
	'EDGE', 'NOTCHECKED', 'SUBTRACTED', 'BINNED2',
	'BINNED4', 'DEBLENDED_AS_MOVING', 'BAD_MOVING_FIT',
	'PEAKS_TOO_CLOSE', 'INTERP_CENTER',
	#'DEBLEND_NOPEAK',
	#'DEBLENDED_AT_EDGE',
	'PSF_FLUX_INTERP',
	'DEBLEND_DEGENERATE', 'MAYBE_EGHOST' ]:
	val = cas_flags[flag]
	badflags |= val
	# n = sum((T.flags & val) > 0)
	# print 'flag', flag, ':', n
	# T.cut(T.flags & val == 0)
	# print 'now', len(T), 'total', sum((T.flags & child) > 0), 'CHILD'

T.cut((T.flags & badflags) == 0)
print 'now', len(T), 'total', sum((T.flags & child) > 0), 'CHILD'

# for i in range(64):
# 	n = sum((T.flags & (1<<i)) > 0)
# 	if n == 0:
# 		continue
# 	print i, '%0x'%(1<<i), flag_names[1<<i], n


#magerr = 0.25
if False:
	magerr = 0.1
	print len(T)
	T.cut(T.psfmagerr_r < magerr)
	print 'cut on r err:', len(T)
	T.cut(T.psfmagerr_g < magerr)
	print 'cut on g err:', len(T)
	T.cut(T.psfmagerr_i < magerr)
	print 'cut on i err:', len(T)

if True:
	maglo = 0.1
	maghi = 0.25
	print len(T)
	T.cut((T.psfmagerr_r > maglo) * (T.psfmagerr_r < maghi))
	print 'cut on r err:', len(T)
	T.cut((T.psfmagerr_g > maglo) * (T.psfmagerr_g < maghi))
	print 'cut on g err:', len(T)
	T.cut((T.psfmagerr_i > maglo) * (T.psfmagerr_i < maghi))
	print 'cut on i err:', len(T)



T.g = T.psfmag_g - T.extinction_g
T.r = T.psfmag_r - T.extinction_r
T.i = T.psfmag_i - T.extinction_i

kwa = dict(range=((-0.5, 2), (-0.5, 2)))
loghist(T.g-T.r, T.r-T.i, **kwa)
plt.xlabel('g-r')
plt.ylabel('r-i')
plt.savefig('gri.png')

I = ((T.flags & child) > 0)
print sum(I), 'child'
H,xe,ye = loghist((T.g-T.r)[I], (T.r-T.i)[I], **kwa)
plt.xlabel('g-r')
plt.ylabel('r-i')
plt.savefig('gri-child.png')

N = sum(I)

I = ((T.flags & child) == 0)
print sum(I), 'non-child'
# same number of samples as "child"...
I = np.flatnonzero(I)
I = I[np.random.permutation(len(I))[:N]]
print 'cut to', len(I), 'non-child'
loghist((T.g-T.r)[I], (T.r-T.i)[I], imshowargs=dict(vmax=np.log10(np.max(H))), **kwa)
plt.xlabel('g-r')
plt.ylabel('r-i')
plt.savefig('gri-notchild.png')
	
