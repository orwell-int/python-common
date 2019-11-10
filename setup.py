#!/usr/bin/env python

import setuptools

setuptools.setup(name='orwell::common',
      version='1.0',
      description='Common code used in various Orwell projects.',
      author='Orwell',
      url='https://github.com/orwell-int/python-common',
      packages=['orwell_common'],
      install_requires=[
          'netifaces==0.10.9',
          'pyzmq>=17.1.2',
      ],
     )