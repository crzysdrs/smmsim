[![Build Status](https://travis-ci.org/crzysdrs/smmsim.svg?branch=master)](https://travis-ci.org/crzysdrs/smmsim)
[![codecov](https://codecov.io/gh/crzysdrs/smmsim/branch/master/graph/badge.svg)](https://codecov.io/gh/crzysdrs/smmsim)

# SMM Simulator

## Description

Intended to run simulations of various scheduling algorithms for SMM (System Management Mode) tasks. These tasks have been subdivided to be able to be run across multiple sessions of an SMI (System Management Interrupt). Given a simulation run result, a set of benchmarks will exist that will help judge a given scheduling algorithm.

The tool was written with the intention of making it easy to add new bin packing algorithms, check splitting algorithms and other internal state modifications. The workload file format is straightfoward and easy to hand write (though I wouldn't recommend doing so). Creating a new workload generator itself should also be a relatively simple task.

## Dependencies

A few dependencies may be required depending on your setup.

Ubuntu Installation:

```
apt-get install python3-pip python3-numpy
pip3 install coverage setuptools
./setup.py develop --user
```

## General Usage

### Workload Generator
```
usage: smmrandwork [-h] [--task_granularity GRANULARITY]
                   [--smm_per_second SMM_PER_SEC] [--bin_size BIN_SIZE]
                   [--smm_overhead SMM_COST]
                   [--binpacker {AgingBin,CostKnapsackBin,PriorityKnapsackBin,LPBinPack,LeastRecentBin,DefaultBin,RandomBin}]
                   [--cpus CPUS] [--checksplitter {DefaultTasks}]
                   [--cost-mu COST_MU] [--cost-sigma COST_SIGMA]
                   [--priority-mu PRIORITY_MU]
                   [--priority-sigma PRIORITY_SIGMA] [--validate]
                   [--prelude-only] [--skip-prelude]
                   [--load] [--checks-per-sec]
                   sim_length file
```

Creates a JSON file format of workload instructions that will be executed by the simulator (i.e. smmsim). The simulation check creation is controlled by ```--load``` where you specify a workload factor or ```--checks-per-sec``` which specifies the number of checks to create per second. Try adjusting the various parameters to create a workload that matches the intended usage of the simulator.

### Simulator
```
usage: smmsim [-h] [--sqllog SQLLOG] [--interactive] [--validate] [--verbose]
              workload
```

The simulator takes a JSON workload file and runs it, while logging all the relevant actions to a sqlite database file (or stdout).

### Validator

```
smmvalidate
```

Takes stdin and validates the values and dumps it back on to stdout. Fails if there is a validation error.

### Benchmark Tool

```
$ smmbench
usage: smmbench [-h] db
```

Given a sqlite database file, run the set of predetermined benchmarks to determine the efficacy of the scheduler.

## Recommended Usage

Since most of the tools are intended to work with the input/output of the previous, the easiest approach is to use a pipeline of the tools. The ```smmvalidate``` usage is optional, you can turn on validation in either ```smmrandwork``` or ```ssmsim``` for the same effect.

```
smmrandwork 1 --load 0.95 /dev/stdout | smmvalidate | smmsim /dev/stdin --sqllog test.db
smmbench test.db
```

It's also entirely possible to run each individually:

```
smmrandwork 1 --load 0.95 my.workload --validate
smmsim my.workload --sqllog test.db
smmbench test.db
```

To really get the most benefit from the tool, you will need to learn the various adjustments that can be made to workload generator to create more interesting workloads. 
