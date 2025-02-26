from distutils.core import setup, Extension
from distutils.command.build_ext import *
from distutils.dist import Distribution
import os

# from http://stackoverflow.com/questions/12491328/python-distutils-not-include-the-swig-generated-module
from distutils.command.build import build
class CustomBuild(build):
    sub_commands = [
        ('build_ext', build.has_ext_modules),
        ('build_py', build.has_pure_modules),
        ('build_clib', build.has_c_libraries),
        ('build_scripts', build.has_scripts),
    ]

import numpy as np
numpy_inc = [np.get_include()]

import sys
from subprocess import check_output

eigen_inc = os.environ.get('EIGEN_INC', None)
if eigen_inc is None:
    try:
        eigen_inc = check_output(['pkg-config', '--cflags', 'eigen3']).strip()
        # py3
        eigen_inc = eigen_inc.decode()
    except:
        eigen_inc = ''
inc = eigen_inc.split()
    
ceres_inc = os.environ.get('CERES_INC', None)
ceres_lib = os.environ.get('CERES_LIB', None)
if ceres_inc is not None:
    inc.append(ceres_inc)

link = []
if ceres_lib is not None:
    link.append(ceres_lib)

module_ceres = Extension('tractor._ceres',
                         sources=['tractor/ceres-tractor.cc', 'tractor/ceres.i'],
                         include_dirs = numpy_inc,
                         extra_compile_args = inc,
                         extra_link_args = link,
                         language = 'c++',
                         swig_opts=['-c++'],
                         )

module_mix = Extension('tractor._mix',
                       sources = ['tractor/mix.i'],
                       include_dirs = numpy_inc,
                       extra_objects = [],
                       undef_macros=['NDEBUG'],
    )
#extra_compile_args=['-O0','-g'],
#extra_link_args=['-O0', '-g'],

module_em = Extension('tractor._emfit',
                      sources = ['tractor/emfit.i' ],
                      include_dirs = numpy_inc,
                      extra_objects = [],
                      undef_macros=['NDEBUG'],
                      )

kwargs = {}
if os.environ.get('CC') == 'icc':
    kwargs.update(extra_compile_args=['-g', '-xhost', '-axMIC-AVX512'],
                  extra_link_args=['-g', '-lsvml'])
else:
    kwargs.update(extra_compile_args=['-g', '-std=c99'],
                  extra_link_args=['-g'])

module_fourier = Extension('tractor._mp_fourier',
                           sources = ['tractor/mp_fourier.i'],
                           include_dirs = numpy_inc,
                           undef_macros=['NDEBUG'],
                           **kwargs)

class MyDistribution(Distribution):
    display_options = Distribution.display_options + [
        ('with-ceres', None, 'build Ceres module?'),
        ]


## Distutils is so awkward to work with that THIS is the easiest way to add
# an extra command-line arg!

mods = [module_mix, module_em, module_fourier]
pymods = ['tractor.mix', 'tractor.emfit', 'tractor.mp_fourier']
key = '--with-ceres'
if key in sys.argv:
    sys.argv.remove(key)
    mods.append(module_ceres)
    pymods.append('tractor.ceres')

# Record current version number....
cmd = 'echo "version = \'$(git describe)\'" > tractor/version.py'
print(cmd)
os.system(cmd)

setup(
    distclass=MyDistribution,
    cmdclass={'build': CustomBuild},
    name="tractor",
    version="git",
    author="Dustin Lang (UToronto) and David W. Hogg (NYU)",
    author_email="dstndstn@gmail.com",
    packages=['tractor', 'wise'],
    ext_modules = mods,
    package_data={'wise':['wise-psf-avg.fits', 'allsky-atlas.fits']},
    package_dir={'wise':'wise', 'tractor':'tractor'},
    url="http://theTractor.org/",
    license="GPLv2",
    description="probabilistic astronomical image analysis",
    long_description="Attempt at replacing heuristic astronomical catalogs with models built with specified likelihoods, priors, and utilities.",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
    ],
)
