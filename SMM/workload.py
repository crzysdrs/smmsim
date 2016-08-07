#!/usr/bin/env python3

import scheduler
import json
import argparse
import schema

class Workload:
    def __init__(self):
        self.__events = []
        self.__time = 0

    def timeForward(self, n):
        assert(n >= 0)
        self.__time += n

    def getTime(self):
        return self.__time

    def createCheck(self, c):
        self.__events.append(
            {
                'time':self.__time,
                'action':'newcheck',
                'checks':c.getData()
            }
        )

    def removeCheck(self, c):
        self.__events.append(
            {
                'time':self.__time,
                'action':'removecheck',
                'checks':list(map(lambda c : {'name':c['name'], 'group':c['group']}, c.getData()))
            }
        )

    def endSim(self):
        self.__events.append(
            {
                'time':self.__time,
                'action':'endsim',
            }
        )

    def changeVars(self, vars):
        self.__events.append(
            {
                'time':self.__time,
                'action':'changevars',
                'vars':vars
            }
        )

    def writeWorkload(self, file_path):
        with open(file_path, 'w') as f:
            for e in self.__events:
                schema.validate(e)
                f.write(json.dumps(e, indent=4) + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create a workload for an SMM Scheduler Simulator')
    scheduler.schedulerOptions(parser)
    parser.add_argument('file', type=str,
                        help='Specify the workload output file.')

    args = parser.parse_args()

    w = Workload()

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

    endtime = args.sim_length * 10**6
    if endtime < w.getTime():
        w.moveTimeForward(endtime - w.getTime())

    w.endSim()

    w.writeWorkload(args.file)
