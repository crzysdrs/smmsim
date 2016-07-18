#!/usr/bin/env python3

import scheduler
import json
import argparse

class Workload:
    def __init__(self, endsim):
        self.__endsim = endsim
        self.__events = []
        self.__time = 0

    def timeForward(self, n):
        assert(n >= 0)
        self.__time += n

    def createCheck(self, c):
        self.__events.append(
            {
                'time':self.__time,
                'action':'newcheck',
                'data':c.getData()
            }
        )

    def removeCheck(self, c):
        self.__events.append(
            {
                'time':self.__time,
                'action':'removecheck',
                'data':c.getData()
            }
        )

    def changeVars(self, vars):
        self.__events.append(
            {
                'time':self.__time,
                'action':'changevars',
                'data':vars
            }
        )

    def getWorkload(self):
        return {
            'endsim':self.__endsim,
            'events':self.__events
        }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create a workload for an SMM Scheduler Simulator')
    scheduler.schedulerOptions(parser)
    parser.add_argument('file', type=str,
                        help='Specify the workload output file.')

    args = parser.parse_args()

    w = Workload(args.sim_length * 10**6)

    w.changeVars(
        {
            'taskgran':args.granularity,
            'smmpersecond':args.smm_per_sec,
            'smmoverhead':args.smm_cost,
            'binsize':args.bin_size,
            'binpacker':args.binpacker,
            'cpus':args.cpus,
            'checksplitter':args.checksplitter,
        }
    )

    for c in scheduler.getChecks():
        w.createCheck(c)

    w.timeForward(args.sim_length * 10**6 - 1)

    for c in scheduler.getChecks():
        w.removeCheck(c)

    with open(args.file, 'w') as f:
        f.write(json.dumps(w.getWorkload()))
