#!/usr/bin/env python3

from SMM import scheduler, schema
import json
import argparse
import numpy as np

class Workload:
    def __init__(self, validate):
        self.__events = []
        self.__time = 0
        self.__validate = validate

    def timeForward(self, n):
        assert(n >= 0)
        self.__time += int(n)

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
                if self.__validate:
                    schema.validate(e)
                f.write(json.dumps(e, indent=4) + "\n")

def randWorkload():
    parser = argparse.ArgumentParser(description='Create a workload for an SMM Scheduler Simulator')
    scheduler.schedulerOptions(parser)

    parser.add_argument('--cost_mu', type=float, default=10,
                        help='Cost Mean')
    parser.add_argument('--cost_sigma', type=float, default=1,
                        help='Cost Sigma')

    parser.add_argument('--priority_mu', type=int, default=10,
                        help='Cost Mean')
    parser.add_argument('--priority_sigma', type=int, default=5,
                        help='Cost Sigma')

    parser.add_argument('checks', type=int,
                        help='Number of Checks')

    parser.add_argument('file', type=str,
                        help='Specify the workload output file.')


    args = parser.parse_args()

    w = Workload(False)

    w.changeVars(
        {
            'taskgran':args.granularity,
            'smmpersecond':args.smm_per_sec,
            'smmoverhead':args.smm_cost,
            'binsize':args.bin_size,
            'binpacker':args.binpacker,
            'cpus':args.cpus,
            'checksplitter':args.checksplitter,
            'rantask':'discard',
        }
    )

    cost = np.random.normal(args.cost_mu, args.cost_sigma, args.checks)
    cost = np.clip(cost, 1, 1000)
    priority = np.random.normal(args.priority_mu, args.priority_sigma, args.checks)
    priority = np.clip(priority, 1, 20)

    insertion = (args.sim_length * 10**6) / args.checks
    for i in range(args.checks):
        cg = scheduler.CheckGroup('random_' + str(i))
        c = scheduler.Check(str(i), int(priority[i]), int(cost[i]))
        cg.addSubCheck(c)
        w.createCheck(cg)
        w.timeForward(insertion)

    endtime = args.sim_length * 10**6
    if endtime < w.getTime():
        w.moveTimeForward(endtime - w.getTime())

    w.endSim()

    w.writeWorkload(args.file)

def genericWorkload():
    parser = argparse.ArgumentParser(description='Create a workload for an SMM Scheduler Simulator')
    scheduler.schedulerOptions(parser)
    parser.add_argument('file', type=str,
                        help='Specify the workload output file.')

    args = parser.parse_args()

    w = Workload(True)

    w.changeVars(
        {
            'taskgran':args.granularity,
            'smmpersecond':args.smm_per_sec,
            'smmoverhead':args.smm_cost,
            'binsize':args.bin_size,
            'binpacker':args.binpacker,
            'cpus':args.cpus,
            'checksplitter':args.checksplitter,
            'rantask':'reschedule',
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
