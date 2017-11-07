import os
import numpy as np
from astrometry.util.fits import *

from wisecat import _read_wise_cats, _read_wise_cats_wcs


def allwise_catalog_wcs(wcs, pixelmargin=0, path='allwise-cats', cols=None):
    return _read_wise_cats_wcs(wcs,
                               os.path.join(
                                   path, 'wise-allwise-cat-part%02i.fits'),
                               os.path.join(
                                   path, 'wise-allwise-cat-part%02i-radec.fits'),
                               allwise_catalog_dec_range, cols=cols,
                               pixelmargin=pixelmargin)


def allwise_catalog_radecbox(r0, r1, d0, d1,
                             path='allwise-cats', cols=None):
    return _read_wise_cats(r0, r1, d0, d1,
                           os.path.join(
                               path, 'wise-allwise-cat-part%02i.fits'),
                           os.path.join(
                               path, 'wise-allwise-cat-part%02i-radec.fits'),
                           allwise_catalog_dec_range, cols=cols)


allwise_catalog_dec_range = [
    (-90., -74.240000),
    (-74.240000, -67.927300),
    (-67.927300, -62.944400),
    (-62.944400, -58.612800),
    (-58.612800, -54.775900),
    (-54.775900, -51.267600),
    (-51.267600, -47.958100),
    (-47.958100, -44.807200),
    (-44.807200, -41.784400),
    (-41.784400, -38.860700),
    (-38.860700, -36.029800),
    (-36.029800, -33.257200),
    (-33.257200, -30.551400),
    (-30.551400, -27.896500),
    (-27.896500, -25.250300),
    (-25.250300, -22.629900),
    (-22.629900, -20.043100),
    (-20.043100, -17.452900),
    (-17.452900, -14.862900),
    (-14.862900, -12.277900),
    (-12.277900, -9.684500),
    (-9.684500, -7.083500),
    (-7.083500, -4.476500),
    (-4.476500, -1.861900),
    (-1.861900, 0.746200),
    (0.746200, 3.357000),
    (3.357000, 5.987600),
    (5.987600, 8.619900),
    (8.619900, 11.275200),
    (11.275200, 13.943800),
    (13.943800, 16.641700),
    (16.641700, 19.362100),
    (19.362100, 22.111600),
    (22.111600, 24.906400),
    (24.906400, 27.733200),
    (27.733200, 30.605700),
    (30.605700, 33.546100),
    (33.546100, 36.548700),
    (36.548700, 39.645300),
    (39.645300, 42.841900),
    (42.841900, 46.153000),
    (46.153000, 49.606100),
    (49.606100, 53.260800),
    (53.260800, 57.180600),
    (57.180600, 61.619500),
    (61.619500, 66.823700),
    (66.823700, 73.620200),
    (73.620200, 90.),
]
