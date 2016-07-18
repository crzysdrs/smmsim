#!/usr/bin/env python3

from scheduler import CheckGroup, Check, Task, Bin, getChecks, getBinPackers, getCheckSplitters, get_git_revision_hash
import binpackers
import checksplitters
import argparse
import log
import sys
import json

from time import gmtime, strftime

class SchedulerState:
    def __init__(self, logger):
        self.__state =  {
            'taskgran':0,
            'smmpersecond':0,
            'smmoverhead':0,
            'binsize':0,
            'binpacker':'',
            'cpus':0,
            'checksplitter':'',
            'endsim':0
        }
        self.__checksplitter = None
        self.__binpacker = None
        self.__logger = logger
        self.__checks = {}
        self.__tasks = []
        self.__time = 0

    def getTime(self):
        return self.__time

    def moveTime(self, t):
        self.__time += t

    def getTasks(self):
        return self.__tasks

    def findCheck(self, parent_name, name):
        parent = self.__checks.get(parent_name)
        if parent is None:
            return None

        return parent.getCheck(name)

    def addCheck(self, group, new_check):
        if group in self.__checks:
            parent = self.__checks[group]
        else:
            parent = CheckGroup(group, [])
            self.__checks[group] = parent

        parent.addSubCheck(new_check)
        new_tasks = self.__checksplitter.splitChecks(new_check, self.__state['taskgran'])

        for t in new_tasks:
            self.__logger.addTask(self.getTime(), t)

        self.__tasks += new_tasks

    def removeCheck(self, check):
        self.__logger.genericEvent(self.__time, None, "Removed Check {}".format(check), 0)
        self.__tasks = filter(lambda t: t.getCheck() != check, self.__tasks)
        check.getGroup().removeSubCheck(check.getName())

    def updateVar(self, k, v):
        self.__logger.genericEvent(self.__time, None, "Changed Var {} to {}".format(k, v), 0)
        self.__state[k] = v
        if k == 'binpacker':
            binpackers = getBinPackers()
            self.__binpacker = binpackers[v]()
        elif k == 'checksplitter':
            checksplitters = getCheckSplitters()
            self.__checksplitter = checksplitters[v]()

    def getVar(self, k):
        return self.__state[k]

    def getPacker(self):
        return self.__binpacker

    def getSplitter(self):
        return self.__splitter

    def getLogger(self):
        return self.__logger

    def getCheckGroups(self):
        return self.__checks

class RunWorkload:
    def __init__(self, state, w):
        self.__state = state
        self.__w = w
        self.__cmds = {
            'newcheck':lambda msg : self.createCheck(msg['data']),
            'removecheck':lambda msg : self.removeCheck(msg['data']),
            'changevars':lambda msg : self.changeVars(msg['data']),
        }
        self.__eventid = 0
        self.__state.updateVar('endsim', w['endsim'])

    def createCheck(self, checks):
        for c in checks:
            new = Check(c['name'], c['priority'], c['cost'])
            self.__state.addCheck(c['group'], new)

    def removeCheck(self, checks):
        for c in checks:
            found = self.__state.findCheck(c['group'], c['name'])
            if found:
                self.__state.removeCheck(found)
            else:
                self.__state.getLogger().error(self.__state.getTime(), "Can't find check {}.{}".format(c['group'], c['name']))

    def changeVars(self, vars):
        for k,v in vars.items():
            self.__state.updateVar(k, v)

    def updateWorkload(self):
        time = self.__state.getTime()
        eol = lambda : not (self.__eventid < len(self.__w['events']))

        if eol():
            return

        e = self.__w['events'][self.__eventid]
        while not eol() and time >= e['time']:
            if e['action'] in self.__cmds:
                self.__cmds[e['action']](e)
            else:
                print("Unknown command {}".format(e['action']))
            self.__eventid += 1
            if eol():
                e = None
            else:
                e = self.__w['events'][self.__eventid]


def main():
    parser = argparse.ArgumentParser(description='Simulate an SMM Scheduler')

    parser.add_argument('workload', type=str,
                        help='Specify the workload to run.')
    parser.add_argument('--sqllog', type=str,
                        default="",
                        help='Desired Location of sqlite log (WILL OVERWRITE).')

    args = parser.parse_args()

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
    #all times are in microseconds
    one_second = int(10**6)
    next_time = 0

    for k,v in misc.items():
        logger.addMisc(k, v)

    w = json.load(open(args.workload))
    state = SchedulerState(logger)
    workload = RunWorkload(state, w)

    workload.updateWorkload() #Updates all the time zero events
    while state.getTime() < state.getVar('endsim'):
        workload.updateWorkload()
        next_time = state.getTime() + one_second//state.getVar('smmpersecond')
        bins = []
        cpu_count = state.getVar('cpus')
        for cpu_id in range(cpu_count):
            bins.append(state.getPacker().requestBin(state, cpu_id))
            logger.genericEvent(state.getTime(), cpu_id, "SMI", state.getVar('smmoverhead'))

        state.moveTime(state.getVar('smmoverhead'))

        for b, cpu_id in zip(bins, range(cpu_count)):
            logger.genericEvent(state.getTime(), cpu_id, "Bin Begin", 0, bin=b)
            for t in b.getTasks():
                logger.taskEvent(state.getTime(), t, cpu_id, b)
                t.run(state.getTime())
                state.moveTime(t.getCost())

        logger.genericEvent(state.getTime(), cpu_id, "Bin End", 0, bin=b)

        #Assumes that overlapping bins will wait until previous bin finishes
        if next_time > state.getTime():
            state.moveTime(next_time - state.getTime())
        else:
            logger.warning(state.getTime(), "Current Bin Will not terminate before next Bin is scheduled")

    workload.updateWorkload() #Finish up any lingering events

    misc = {
        'end_gmt':strftime("%a, %d %b %Y %X +0000", gmtime()),
        'end_local':strftime("%a, %d %b %Y %X +0000"),
    }

    for k,v in misc.items():
        logger.addMisc(k, v)

    logger.endLog()

if __name__ == "__main__":
    main()
