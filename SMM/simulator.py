#!/usr/bin/env python

from scheduler import CheckGroup, Check, Task, Bin, getChecks
from binpackers import *
from checksplitters import *

def main():
    checks = getChecks()
    granularity = 50
    splitter = DefaultTasks()
    tasks = splitter.split(checks, granularity)

    for t in tasks:
        print t

    #all times are in microseconds
    one_second = 10**6
    time = 0
    target_time = 50 * one_second
    binsize = 100
    #packer = DefaultBin(tasks, binsize)
    packer = MaxFillBin(tasks, binsize)
    smm_cost = 70
    smm_per_second = 10

    next_time = 0
    while time < target_time:
        b = packer.requestBin(time)
        print time, b.getCost()
        next_time = time + one_second/smm_per_second
        time += b.getCost() + smm_cost

        #Assumes that overlapping bins will wait until previous bin finishes
        if next_time > time:
            time = next_time

if __name__ == "__main__":
    main()
