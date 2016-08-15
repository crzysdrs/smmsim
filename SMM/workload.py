#!/usr/bin/env python3

from SMM import scheduler, schema
import json
import argparse
import numpy as np
import random

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

    parser.add_argument('--cost-mu', type=float, default=10,
                        help='Cost Mean')
    parser.add_argument('--cost-sigma', type=float, default=1,
                        help='Priority Sigma')

    parser.add_argument('--priority-mu', type=int, default=10,
                        help='Cost Mean')
    parser.add_argument('--priority-sigma', type=int, default=5,
                        help='Priority Sigma')

    parser.add_argument('load', type=float,
                        help='Total Load')

    parser.add_argument('file', type=str,
                        help='Specify the workload output file.')

    parser.add_argument('--validate',
                        default=False,
                        action='store_true',
                        help='Enable schema validator.')

    parser.add_argument('--prelude-only',
                        default=False,
                        action='store_true',
                        help='Only emit prelude')

    parser.add_argument('--skip-prelude',
                        default=False,
                        action='store_true',
                        help='Skip prelude')


    args = parser.parse_args()

    w = Workload(args.validate)

    if not args.skip_prelude:
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

    one_second = 10**6
    if not args.prelude_only:
        check_count = 0
        smm_count = 1
        total = 0

        next_time = w.getTime() + one_second // args.smm_per_sec
        iteration_count = 10
        iteration = (next_time - w.getTime()) / iteration_count

        endtime = args.sim_length * 10**6
        while w.getTime() < endtime:
            for i in range(iteration_count):
                rand_size = 10000
                if check_count % rand_size == 0:
                    cost = np.random.normal(args.cost_mu, args.cost_sigma, rand_size)
                    cost = np.clip(cost, 1, 1000)
                    priority = np.random.normal(args.priority_mu, args.priority_sigma, rand_size)
                    priority = np.clip(priority, 1, 20)

                while total / (smm_count * args.bin_size) - args.load < - 0.1 * (iteration_count - 1 - i):
                    cg = scheduler.CheckGroup('random_' + str(check_count))
                    c = scheduler.Check(str(check_count), int(priority[check_count % rand_size]), int(cost[check_count % rand_size]))
                    check_count += 1
                    total += c.getCost()
                    cg.addSubCheck(c)
                    w.createCheck(cg)

                w.timeForward(iteration)

            smm_count += 1

        if endtime < w.getTime():
            w.moveTimeForward(endtime - w.getTime())

        w.endSim()

    w.writeWorkload(args.file)

    #print (check_count, smm_count, total)
    #print (total / (smm_count * args.bin_size) - args.load)

def genericWorkload():
    parser = argparse.ArgumentParser(description='Create a workload for an SMM Scheduler Simulator')
    scheduler.schedulerOptions(parser)
    parser.add_argument('file', type=str,
                        help='Specify the workload output file.')

    parser.add_argument('--validate',
                        default=False,
                        action='store_true',
                        help='Enable schema validator.')

    args = parser.parse_args()

    w = Workload(args.validate)

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
