#!/usr/bin/env python
"""
Setup.py
"""
from setuptools import setup, find_packages

setup(
    name='SMM',
    version='0.1',
    description='SMM Scheduler Simulator',
    author='Mitch Souders',
    author_email='msouders@pdx.edu',
    scripts=[
    ],
    packages = find_packages(),
    #package_dir={'': 'SMM'},
    #py_modules=[
    #    'SMM'
    #],
    entry_points={
        'console_scripts': [
            'smm_sim = SMM.simulator:main'
        ],
    },
    install_requires=[
        'argparse',
    ]
)
