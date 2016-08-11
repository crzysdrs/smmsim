#!/usr/bin/env python3
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
    entry_points={
        'console_scripts': [
            'smmsim = SMM.simulator:main',
            'smmbench = SMM.benchmarks:main',
            'smmgenwork = SMM.workload:genericWorkload',
            'smmrandwork = SMM.workload:randWorkload',
            'smmvalidate = SMM.schema:validatestream',
        ],
    },
    install_requires=[
        'argparse',
        'pulp',
        'jsonschema',
    ]
)
