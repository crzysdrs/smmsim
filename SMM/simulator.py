#!/usr/bin/env python3

from SMM.scheduler import CheckGroup, Check, Task, Bin, getChecks, getBinPackers, getCheckSplitters, get_git_revision_hash
from SMM import binpackers, checksplitters, log, schema
import argparse
import sys
import json
from functools import partial
import time as timelib
import jsonschema
import numpy as np


class SchedulerState:
    """ Maintains the current state of the scheduler

    Anything that can be modified by workload instructions should
    be included here. This allows a clear seperation line of
    where the data should be stored/modified so that the state is
    not stored in local variables throughout the application.
    """
    def __init__(self, logger):
        self.__state =  {
            'taskgran':50, #Task Granularity
            'smmpersecond':10, #SMMs per second
            'smmoverhead':70, #SMI Overhead
            'binsize':100, # Bin Size
            'binpacker':'DefaultBin', #Bin Packer
            'cpus':1, #Number of CPUs
            'checksplitter':'DefaultTasks', #Chosen CheckSplitter
            'rantask':'reschedule', #What to do when task is complete
        }
        self.__checksplitter = None
        self.__binpacker = None
        self.__logger = logger
        self.__checks = {}
        self.__tasks = []
        self.__time = 0
        self.__done = False

        # Update all the var states with defaults so they
        # are logged
        for k, v in self.__state.items():
            self.__updateVarState(k, v)

    def ranTask(self, time, task):
        """ Runs the neccesary clean up after task ran """
        self.__logger.removeTask(time, task)
        if self.getVar('rantask') == 'reschedule':
            task.reset()
            self.__logger.addTask(time, task)
            self.__binpacker.addTask(task)
        elif self.getVar('rantask') == 'discard':
            pass
        else:
            self.logger.error("Unknwon rantask setting")

    def simRunning(self):
        """ Is the simulation running? """
        return not self.__done

    def getTime(self):
        """ What is the current time? """
        return self.__time

    def moveTime(self, t):
        """ Move the time forward

        By only moving the time forward, we prevent all sorts
        of issues where the time state is inconsistent or
        logged in a strange order.
        """
        assert(t >= 0)
        self.__time += t

    def findCheck(self, parent_name, name):
        """ Finds a given check name within the class """
        parent = self.__checks.get(parent_name)
        if parent is None:
            return None

        return parent.getCheck(name)

    def addCheck(self, group, new_check):
        """ Adds a check of the given name """
        if group in self.__checks:
            parent = self.__checks[group]
        else:
            parent = CheckGroup(group, [])
            self.__checks[group] = parent

        parent.addSubCheck(new_check)
        new_tasks = self.__checksplitter.splitChecks(new_check, self.__state['taskgran'], self.getTime())

        self.__logger.timeEvent(self.__time, 0, "add_check", msg="Added {}".format(new_check))

        for t in new_tasks:
            self.__logger.addTask(self.getTime(), t)
            self.__binpacker.addTask(t)

    def __updateVarState(self, k, v):
        """ Handle special cases for var changes like BinPacker, Checksplitter

        This is for variable changes which have other impacts on the simulator
        like instantiating objects or other side effects.
        """
        if k == 'binpacker':
            binpackers = getBinPackers()
            old = self.__binpacker
            self.__binpacker = binpackers[v]()
            if old is not None:
                [self.__binpacker.addTask(x) for x in old.unusedTasks()]
        elif k == 'checksplitter':
            checksplitters = getCheckSplitters()
            self.__checksplitter = checksplitters[v]()

    def removeCheck(self, check):
        """ Removes a specified check """
        self.__logger.timeEvent(self.__time, 0, "rm_check", msg="Removed {}".format(check))

        subcheck = check.getGroup().removeSubCheck(check.getName())
        if subcheck:
            self.__binpacker.removeSubCheck(subcheck)

    def updateVar(self, k, v):
        """ Updates an internal variable state """
        self.__logger.timeEvent(self.__time, 0, "varchange", msg="Changed Var {} to {}".format(k, v))
        self.__state[k] = v
        self.__updateVarState(k, v)

    def endSim(self):
        """ Force the simulation to end """
        self.__done = True

    def getVar(self, k):
        """ Gets the current value of a state var """
        return self.__state[k]

    def getPacker(self):
        """ Get the current bin packer """
        return self.__binpacker

    def getSplitter(self):
        """ Get the current task splitter """
        return self.__splitter

    def getLogger(self):
        """ Get the current logger """
        return self.__logger

    def getCheckGroups(self):
        """ Get the list of check groups """
        return self.__checks

class RunWorkload:
    """ Runs a given workload by interacting with the SimulatorState """
    def __init__(self, state, stream, interactive, validate):
        def parse_json_stream(stream_name):
            """ Parses an incoming json stream workload """
            if stream_name == '-':
                stream = sys.stdin
            else:
                stream = open(stream_name)

            if stream_name == '-' and interactive:
                read = partial(stream.readline)
            else:
                chunksize = 1024
                read = partial(stream.read, chunksize)
            buffer = ""
            decoder = json.JSONDecoder()
            for chunk in iter(read, ''):
                if interactive:
                    buffer = chunk
                else:
                    buffer += chunk
                while buffer:
                    try:
                        buffer = buffer.lstrip()
                        obj, idx = decoder.raw_decode(buffer)
                        if validate:
                            schema.validate(obj)
                        yield obj
                        buffer = buffer[idx:]
                    except ValueError as e:
                        if interactive:
                            print(e)
                        #Needs more input
                        break
                    except jsonschema.ValidationError as e:
                        if interactive:
                            print(e)
                            break
                        else:
                            raise

        self.__state = state
        #Set of possible commands from workload
        self.__cmds = {
            'newcheck':lambda msg : self.createCheck(msg['checks']),
            'removecheck':lambda msg : self.removeCheck(msg['checks']),
            'changevars':lambda msg : self.changeVars(msg['vars']),
            'endsim':lambda msg : self.__state.endSim(),
        }
        self.__events = parse_json_stream(stream)
        self.__nextEvent = None

    def createCheck(self, checks):
        """ Creates a set of checks in the simulator state """
        for c in checks:
            new = Check(c['name'], c['priority'], c['cost'])
            self.__state.addCheck(c['group'], new)

    def removeCheck(self, checks):
        """ Removes a set of checks from the simulator state """
        for c in checks:
            found = self.__state.findCheck(c['group'], c['name'])
            if found:
                self.__state.removeCheck(found)
            else:
                self.__state.getLogger().error(self.__state.getTime(), "Can't find check {}.{}".format(c['group'], c['name']))

    def changeVars(self, vars):
        """ Changes the specified vars in the simulator state """
        for k,v in vars.items():
            self.__state.updateVar(k, v)

    def updateWorkload(self):
        """ Updates the workload to the current time index """
        def getNextEvent():
            """ Only get a new event if there is no deferred event """
            valid = False
            e = None
            while e is None:
                e = next(self.__events)
            return e

        if not self.__state.simRunning():
            return

        try:
            time = self.__state.getTime()
            if self.__nextEvent is None:
                self.__nextEvent = getNextEvent()

            while time >= self.__nextEvent['time']:
                e = self.__nextEvent
                if e['action'] in self.__cmds:
                    self.__cmds[e['action']](e)

                self.__nextEvent = getNextEvent()
        except StopIteration:
            self.__state.endSim()

def main():
    parser = argparse.ArgumentParser(description='Simulate an SMM Scheduler')

    parser.add_argument('workload', type=str,
                        help='Specify the workload to run.')
    parser.add_argument('--sqllog', type=str,
                        default="",
                        help='Desired Location of sqlite log (WILL OVERWRITE).')
    parser.add_argument('--interactive',
                        default=False,
                        action='store_true',
                        help='Want to run interactively.')
    parser.add_argument('--validate',
                        default=False,
                        action='store_true',
                        help='Enable schema validator.')
    parser.add_argument('--verbose',
                        default=False,
                        action='store_true',
                        help='Enable logging output.')


    args = parser.parse_args()

    #Choose desired logger
    if args.sqllog != "":
        logger = log.SqliteLog(args.verbose, args.sqllog)
    else:
        logger = log.SimLog(args.verbose)

    # Collect system stats
    misc = {
        'start_gmt':timelib.strftime("%a, %d %b %Y %X +0000", timelib.gmtime()),
        'start_local':timelib.strftime("%a, %d %b %Y %X +0000"),
        'start_cpu_clock':timelib.clock(),
        'start_wall_clock':timelib.time(),
        'ver':get_git_revision_hash(),
        'args': " ".join(map(lambda x : '"{}"'.format(x), sys.argv))
    }
    #all times are in microseconds
    one_second = int(10**6)
    next_time = 0

    for k,v in misc.items():
        logger.addMisc(k, v)

    #initiliaze system state and workload
    state = SchedulerState(logger)
    workload = RunWorkload(state, args.workload, args.interactive, args.validate)

    #Run the actual simulation
    workload.updateWorkload() #Updates all the time zero events
    while state.simRunning():
        workload.updateWorkload()
        next_time = state.getTime() + one_second//state.getVar('smmpersecond')
        bins = []
        cpu_count = state.getVar('cpus')
        # Collect bins to be run
        for cpu_id in range(cpu_count):
            bins.append(state.getPacker().requestBin(state, cpu_id))
            logger.timeEvent(state.getTime(), state.getVar('smmoverhead'), "SMI", cpu=cpu_id)

        state.moveTime(state.getVar('smmoverhead'))

        #Determine ordering in tasks across bins
        planned_tasks = []
        for b, cpu_id in zip(bins, range(cpu_count)):
            start_times = map(int, np.cumsum([0] + [t.getCost() for t in b.getTasks()]))
            tasks = b.getTasks() + [None]
            all_tasks = [(t, s, b, cpu_id) for (t,s) in zip(tasks, start_times)]
            planned_tasks += all_tasks

        planned_tasks = sorted(planned_tasks, key=lambda t : t[1])

        #Start bins
        for b, cpu_id in zip(bins, range(cpu_count)):
            logger.timeEvent(state.getTime(), 0, "bin_start", cpu=cpu_id, bin=b)

        #Run tasks within bins
        time = state.getTime()
        for (t, start_time, b, cpu_id) in planned_tasks:
            state.moveTime(time + start_time - state.getTime())
            if t is None:
                logger.timeEvent(state.getTime(), 0, "bin_end", cpu=cpu_id, bin=b)
            else:
                logger.timeEvent(state.getTime(), t.getCost(), "run_task", task=t, cpu=cpu_id, bin=b)
                t.run(state.getTime())
                state.ranTask(state.getTime(), t)

        #Assumes that overlapping bins will wait until previous bin finishes
        if next_time > state.getTime():
            state.moveTime(next_time - state.getTime())
        else:
            logger.warning(state.getTime(), "Current Bin Will not terminate before next Bin is scheduled")

    workload.updateWorkload() #Finish up any lingering events

    logger.timeEvent(state.getTime(), 0, "end_sim")

    #Capture system state at the end of simulation
    misc = {
        'end_gmt':timelib.strftime("%a, %d %b %Y %X +0000", timelib.gmtime()),
        'end_local':timelib.strftime("%a, %d %b %Y %X +0000"),
        'end_cpu_clock':timelib.clock(),
        'end_wall_clock':timelib.time()
    }

    for k,v in misc.items():
        logger.addMisc(k, v)

    logger.endLog()

if __name__ == "__main__":
    main()
