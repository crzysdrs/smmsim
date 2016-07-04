#!/usr/bin/env python

from scheduler import CheckGroup, Check, Task, Bin, getChecks
import binpackers
import checksplitters
import argparse
import sys, inspect

def classmembers(module):
    return inspect.getmembers(sys.modules[module], inspect.isclass)

def main():
    binpackers = classmembers("SMM.binpackers")
    binpackers = filter(lambda x : 'requestBin' in x[1].__dict__, binpackers)
    binpackers = dict(binpackers)

    checksplitters = classmembers("SMM.checksplitters")
    checksplitters = filter(lambda x : 'splitChecks' in x[1].__dict__, checksplitters)
    checksplitters = dict(checksplitters)


    parser = argparse.ArgumentParser(description='Simulator an SMM Scheduler')
    parser.add_argument('--task_granularity', dest='granularity', type=int,
                        default=50,  help='Max size of tasks (microseconds).')
    parser.add_argument('--smm_per_second', dest='smm_per_sec',
                        default=10,  type=int, help='SMM Actions to Run Per Second.')
    parser.add_argument('--bin_size', dest='bin_size',
                        default=100, type=int, help='SMM Bin Size (microseconds).')
    parser.add_argument('--smm_overhead', dest='smm_cost',
                        default=70,  help='Overhead of invoking SMM (microseconds).')
    parser.add_argument('sim_length', type=int,
                        help='Length of Simulation (seconds).')
    parser.add_argument('--binpacker', choices=binpackers.keys(),
                        default="DefaultBin",
                        help='The BinPacker class that wille be used to fill bins.')
    parser.add_argument('--checksplitter', choices=checksplitters.keys(),
                        default="DefaultTasks",
                        help='The class that will convert checks into tasks.')

    args = parser.parse_args()

    checks = getChecks()
    splitter = checksplitters[args.checksplitter]()
    tasks = splitter.splitChecks(checks, args.granularity)

    #all times are in microseconds
    one_second = 10**6
    time = 0
    packer = binpackers[args.binpacker](tasks, args.bin_size)
    next_time = 0
    target_time = one_second * args.sim_length
    while time < target_time:
        b = packer.requestBin(time)
        print time, b.getCost()
        next_time = time + one_second/args.smm_per_sec
        time += b.getCost() + args.smm_cost

        #Assumes that overlapping bins will wait until previous bin finishes
        if next_time > time:
            time = next_time

if __name__ == "__main__":
    main()
