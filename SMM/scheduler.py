#!/usr/bin/env python3
import inspect
import sys
import subprocess

def get_git_revision_hash():
    return subprocess.check_output(['git', 'rev-parse', 'HEAD']).rstrip()

def classmembers(module):
    return inspect.getmembers(sys.modules[module], inspect.isclass)

def getBinPackers():
    import binpackers
    binpackers = classmembers("binpackers")
    binpackers = filter(lambda x : 'requestBin' in x[1].__dict__, binpackers)
    binpackers = dict(binpackers)
    return binpackers

def getCheckSplitters():
    import checksplitters
    checksplitters = classmembers("checksplitters")
    checksplitters = filter(lambda x : 'splitChecks' in x[1].__dict__, checksplitters)
    checksplitters = dict(checksplitters)
    return checksplitters

class CheckGroup:
    def __init__(self, name, subchecks=None):
        self.__name = name
        if not subchecks:
            subchecks = {}

        self.__subchecks = {}

        for sc in subchecks:
            self.addSubCheck(sc)

    def addSubCheck(self, sc):
        sc.setGroup(self)
        self.__subchecks[sc.getName()] = sc

    def getCheck(self, name):
        if name in self.__subchecks:
            return self.__subchecks[name]
        else:
            return None

    def getGroupCost(self):
        return sum([sc.getCost() for sc in self.__subchecks.values()])

    def getName(self):
        return self.__name

    def removeSubCheck(self, name):
        if name in self.__subchecks:
            del self.__subchecks[name]

    def getData(self):
        j = []
        for s in self.__subchecks.values():
            j.append(s.getData())
        return j

class Check:
    def __init__(self, name, priority, cost):
        self.__name = name
        self.__cost = cost
        self.__group = None
        self.__priority = priority

    def setGroup(self, group):
        self.__group = group

    def getGroup(self):
        return self.__group

    def makeTask(self, index, cost):
        return Task(self, index, cost)

    def getCost(self):
        return self.__cost

    def getPriority(self):
        return self.__priority

    def setPriority(self, p):
        self.__priority = p

    def getParentName(self):
        if self.__group:
            parent = self.__group.getName()
        else:
            parent = 'Orphan'
        return parent

    def getName(self):
        return self.__name

    def __str__(self):
        parent = self.getParentName()
        return "Check {}.{}".format(parent, self.__name)

    def __repr__(self):
        return self.__str__()

    def getData(self):
        parent = self.getParentName()
        return {
            'group': self.getParentName(),
            'name': self.__name,
            'cost': self.__cost,
            'priority' : self.__priority,
            'attribs': {
            },
        }

class Task:
    def __init__(self, subcheck, index, cost):
        self.__subcheck = subcheck
        self.__index = index
        self.__cost = cost

    def getCost(self):
        return self.__cost

    def getPriority(self):
        return self.__subcheck.getPriority()

    def getCheck(self):
        return self.__subcheck

    def __str__(self):
        return "Task {}.{}".format(self.__subcheck, self.__index)

    def __repr__(self):
        return self.__str__()

class Bin:
    bin_count = 0
    def __init__(self):
        self.__tasks = []
        self.__id = Bin.bin_count
        Bin.bin_count += 1

    def getId(self):
        return self.__id

    def addTask(self, t):
        self.__tasks.append(t)

    def getTasks(self):
        return self.__tasks

    def getCost(self):
        return sum([t.getCost() for t in self.__tasks])


def getChecks():
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
