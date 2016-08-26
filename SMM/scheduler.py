#!/usr/bin/env python3
import inspect
import sys
import subprocess

""" This module contains general sets of useful pieces that are
specific to scheduling (not neccesarily simulation) and other
general helpful functions.
"""
def get_git_revision_hash():
    """ Gets the current repo commit hash """
    return subprocess.check_output(['git', 'rev-parse', 'HEAD']).rstrip()

def classmembers(module):
    """ Gets the classmembers of a specific module """
    return inspect.getmembers(sys.modules[module], inspect.isclass)

def getBinPackers():
    """ Gets a list of all the bin packers """
    import SMM.binpackers
    binpackers = classmembers("SMM.binpackers")
    binpackers = filter(lambda x : 'requestBin' in x[1].__dict__, binpackers)
    binpackers = dict(binpackers)
    return binpackers

def getCheckSplitters():
    """ Gets a list of all the check splitters """
    import SMM.checksplitters
    checksplitters = classmembers("SMM.checksplitters")
    checksplitters = filter(lambda x : 'splitChecks' in x[1].__dict__, checksplitters)
    checksplitters = dict(checksplitters)
    return checksplitters

class CheckGroup:
    """ A check group is a named group of collected checks """
    def __init__(self, name, subchecks=None):
        self.__name = name
        if not subchecks:
            subchecks = {}

        self.__subchecks = {}

        for sc in subchecks:
            self.addSubCheck(sc)

    def addSubCheck(self, sc):
        """ Adds a subcheck """
        sc.setGroup(self)
        self.__subchecks[sc.getName()] = sc

    def getCheck(self, name):
        """ Gets a subcheck with the name specified """
        if name in self.__subchecks:
            return self.__subchecks[name]
        else:
            return None

    def getGroupCost(self):
        """ Gets the overall cost of the entire group """
        return sum([sc.getCost() for sc in self.__subchecks.values()])

    def getName(self):
        """ Get the name of the check group """
        return self.__name

    def removeSubCheck(self, name):
        """ Removes the subcheck from the group """
        c = None
        if name in self.__subchecks:
            c = self.__subchecks[name]
            del self.__subchecks[name]

        return c

    def getData(self):
        """ Get a JSON formatted version """
        j = []
        for s in self.__subchecks.values():
            j.append(s.getData())
        return j

class Check:
    """ A check has an associated priority, cost and will be split into tasks """
    def __init__(self, name, priority, cost):
        self.__name = name
        self.__cost = cost
        self.__group = None
        self.__priority = priority

    def setGroup(self, group):
        """ Sets the parent check group """
        self.__group = group

    def getGroup(self):
        """ Gets the parent check group """
        return self.__group

    def makeTask(self, index, cost, time):
        """ Makes a task based on a slice of the Check """
        return Task(self, index, cost, time)

    def getCost(self):
        """ Gets the cost of the Check """
        return self.__cost

    def getPriority(self):
        """ Get the current priority """
        return self.__priority

    def setPriority(self, p):
        """ Update the current priority """
        self.__priority = p

    def getParentName(self):
        """ Gets the parent name (if available) """
        if self.__group:
            parent = self.__group.getName()
        else:
            parent = 'Orphan'
        return parent

    def getName(self):
        """ Gets the checks name """
        return self.__name

    def __str__(self):
        """ Human readable check """
        parent = self.getParentName()
        return "Check {}.{}".format(parent, self.__name)

    def __repr__(self):
        return self.__str__()

    def getData(self):
        """ JSON Formatted version of the check """
        parent = self.getParentName()
        return {
            'group': self.getParentName(),
            'name': self.__name,
            'cost': self.__cost,
            'priority' : self.__priority,
            'misc': {
            },
        }

class Task:
    """ A subdivision of a check """
    def __init__(self, subcheck, index, cost, time):
        self.__subcheck = subcheck
        self.__index = index
        self.__cost = cost
        self.__lastTime = time
        self.__priority = self.__subcheck.getPriority()

    def reset(self):
        """ Reset the priority to it's initial value """
        self.__prioirity = self.__subcheck.getPriority()

    def getCost(self):
        """ Get the cost of the task """
        return self.__cost

    def getPriority(self):
        """ Gets the priority of the task """
        return self.__priority

    def setPriority(self, p):
        """ Set the priority of the task """
        self.__priority = p

    def getCheck(self):
        """ Get the parent check """
        return self.__subcheck

    def lastTimeRun(self):
        """ Get the last time the task was run """
        return self.__lastTime

    def run(self, time):
        """ Notify the task that it has been run """
        self.__lastTime = time + self.getCost()

    def __str__(self):
        return "Task {}.{}".format(self.__subcheck, self.__index)

    def __repr__(self):
        return self.__str__()

class Bin:
    """ A bin is a collection of tasks that are going to run collectively """
    bin_count = 0 # Unique identifier for a bin
    def __init__(self):
        self.__tasks = []
        self.__id = Bin.bin_count
        Bin.bin_count += 1

    def getId(self):
        """ Get current Bin ID """
        return self.__id

    def addTask(self, t):
        """ Add a task to the bin """
        self.__tasks.append(t)

    def getTasks(self):
        """ Get the tasks from the bin """
        return self.__tasks

    def getCost(self):
        """ Get the cost of the bin's subtasks """
        return sum([t.getCost() for t in self.__tasks])


def getChecks():
    """ Get the generic list of tasks that was defined in EPA-RIMM """
    return [
        CheckGroup(
            'IDTcheck', [
                Check('IDTR', 9, 1),
                Check('HashIdtTable', 20, 10),
                Check('IdtFunctionPtrWalker', 14, 15),
            ]
        ),
        CheckGroup(
            'HyperCall', [
                Check('HypercallTableAddr', 18, 5),
                Check('HypercallTableHash', 9, 50),
                Check('HypercallTableWalk', 11, 100),
            ]
        ),
        CheckGroup(
            'GDT', [
                Check('GDTR', 3, 1),
                Check('GdtHash', 19, 50),
            ]
        ),
        CheckGroup(
            'Kernel', [
                Check('KernelAddr', 15, 20),
                Check('KernelHash', 4, 500),
            ]
        ),
        CheckGroup(
            'VmExit', [
                Check('VmExitTableAddr', 5, 1),
                Check('VmExitTableHash', 2, 5),
                Check('VmExitTableWalk', 17, 10),
            ]
        ),
        CheckGroup(
            'CR0', [
                Check('CR0Val', 17, 1),
            ]
        ),
    ]

def schedulerOptions(parser):
    """ Add arguments to a parser that are the default settings for a scheduler """
    binpackers = getBinPackers()
    checksplitters = getCheckSplitters()

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
