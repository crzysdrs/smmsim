#!/usr/bin/env python3

from scheduler import CheckGroup, Check, Task, Bin, getChecks
import binpackers
import checksplitters
import argparse
import log
import sys, inspect
import subprocess
from time import gmtime, strftime

def get_git_revision_hash():
    return subprocess.check_output(['git', 'rev-parse', 'HEAD']).rstrip()

def classmembers(module):
    return inspect.getmembers(sys.modules[module], inspect.isclass)

def main():
    binpackers = classmembers("binpackers")
    binpackers = filter(lambda x : 'requestBin' in x[1].__dict__, binpackers)
    binpackers = dict(binpackers)

    checksplitters = classmembers("checksplitters")
    checksplitters = filter(lambda x : 'splitChecks' in x[1].__dict__, checksplitters)
    checksplitters = dict(checksplitters)


    parser = argparse.ArgumentParser(description='Simulator an SMM Scheduler')
    parser.add_argument('--task_granularity', dest='granularity', type=int,
                        default=50,  help='Max size of tasks (microseconds).')
    parser.add_argument('--smm_per_second', dest='smm_per_sec',
                        default=10,  type=int, help='SMM Actions to Run Per Second.')
    parser.add_argument('--bin_size', dest='bin_size',
                        default=100, type=int, help='SMM Bin Size (microseconds).')
    parser.add_argument('--smm_overhead', dest='smm_cost', type=int,
                        default=70,  help='Overhead of invoking SMM (microseconds).')
    parser.add_argument('sim_length', type=int,
                        help='Length of Simulation (seconds).')
    parser.add_argument('--binpacker', choices=binpackers.keys(),
                        default="DefaultBin",
                        help='The BinPacker class that wille be used to fill bins.')
    parser.add_argument('--cpus', type=int,
                        default=1,
                        help='Number of CPUs')
    parser.add_argument('--checksplitter', choices=checksplitters.keys(),
                        default="DefaultTasks",
                        help='The class that will convert checks into tasks.')
    parser.add_argument('--sqllog', type=str,
                        default="",
                        help='Desired Location of sqlite log (WILL OVERWRITE).')

    args = parser.parse_args()

    checks = getChecks()
    splitter = checksplitters[args.checksplitter]()
    tasks = splitter.splitChecks(checks, args.granularity)

    if args.sqllog != "":
        logger = log.SqliteLog(args.sqllog)
    else:
        logger = log.SimLog()

    misc = {
        'start_gmt':strftime("%a, %d %b %Y %X +0000", gmtime()),
        'start_local':strftime("%a, %d %b %Y %X +0000"),
        'ver':get_git_revision_hash(),
        'args': " ".join(map(lambda x : '"{}"'.format(x), sys.argv))
    }

    for k,v in misc.items():
        logger.addMisc(k, v)

    for t in tasks:
        logger.addTask(0, t)

    #all times are in microseconds
    one_second = int(10**6)
    time = 0
    packer = binpackers[args.binpacker](tasks, args.bin_size)
    next_time = 0
    target_time = one_second * args.sim_length

    cpu_id = 0

    while time < target_time:
        next_time = time + one_second//args.smm_per_sec
        bins = []
        for cpu_id in range(args.cpus):
            bins.append(packer.requestBin(time, cpu_id))
            logger.genericEvent(time, cpu_id, "SMI", args.smm_cost)

        time += args.smm_cost

        for b, cpu_id in zip(bins, range(args.cpus)):
            logger.genericEvent(time, cpu_id, "Bin Begin", 0, bin=b)
            for t in b.getTasks():
                logger.taskEvent(time, t, cpu_id, b)
                time += t.getCost()

        logger.genericEvent(time, cpu_id, "Bin End", 0, bin=b)

        #Assumes that overlapping bins will wait until previous bin finishes
        if next_time > time:
            time = next_time
        else:
            logger.warning(time, "Current Bin Will not terminate before next Bin is scheduled")

    misc = {
        'end_gmt':strftime("%a, %d %b %Y %X +0000", gmtime()),
        'end_local':strftime("%a, %d %b %Y %X +0000"),
    }

    for k,v in misc.items():
        logger.addMisc(k, v)

    logger.endLog()

if __name__ == "__main__":
    main()
