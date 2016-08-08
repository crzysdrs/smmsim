[![Build Status](https://travis-ci.org/crzysdrs/smmsim.svg?branch=master)](https://travis-ci.org/crzysdrs/smmsim)
[![codecov](https://codecov.io/gh/crzysdrs/smmsim/branch/master/graph/badge.svg)](https://codecov.io/gh/crzysdrs/smmsim)

# SMM Simulator

## Description

Intended to run simulations of various scheduling algorithms for SMM (System Management Mode) tasks. These tasks have been subdivided to be able to be run across multiple sessions of an SMI (System Management Interrupt). Given a simulation run result, a set of benchmarks will exist that will help judge a given scheduling algorithm.

## Dependencies

A few dependencies may be required depending on your setup.

Ubuntu Installation:

```
apt-get install pip3 python3-numpy
pip3 install coverage
./setup.py develop --user
```

## General Usage

### Simulator

```
$ smmsim 
usage: smmsim [-h] [--task_granularity GRANULARITY]
              [--smm_per_second SMM_PER_SEC] [--bin_size BIN_SIZE]
              [--smm_overhead SMM_COST]
              [--binpacker {DefaultBin,MaxPriorityBin,RandomBin,MaxFillBin}]
              [--cpus CPUS] [--checksplitter {DefaultTasks}]
              [--sqllog SQLLOG]
              sim_length
```

This gives a general means of running various simulations by adjusting the parameters associated with a given scheduler approach. It is easily extended to incorporate additional scheduling algorithms and tasks divisions. If the output is logged to a sqlite database file, it can be benchmarked to determine the efficacy of the scheduler.

### Benchmark Tool

```
$ smmbench
usage: smmbench [-h] db
```

Given a sqlite database file, run the set of predetermined benchmarks to determine the efficacy of the scheduler.
