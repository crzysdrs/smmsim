#!/usr/bin/env python3

class CheckGroup:
    def __init__(self, name, subchecks=None):
        self.__name = name
        if not subchecks:
            subchecks = []

        self.__subchecks = []

        for sc in subchecks:
            self.addSubCheck(sc)

    def addSubCheck(self, sc):
        sc.setGroup(self)
        self.__subchecks.append(sc)

    def getChecks(self):
        return self.__subchecks

    def getGroupCost(self):
        return sum([sc.getCost() for sc in self.__subchecks])

    def getName(self):
        return self.__name

class Check:
    def __init__(self, name, priority, cost):
        self.__name = name
        self.__cost = cost
        self.__group = None
        self.__priority = priority

    def setGroup(self, group):
        self.__group = group

    def makeTask(self, index, cost):
        return Task(self, index, cost)

    def getCost(self):
        return self.__cost

    def getPriority(self):
        return self.__priority

    def setPriority(self, p):
        self.__priority = p

    def __str__(self):
        if self.__group:
            parent = self.__group.getName()
        else:
            parent = '<UNDEFINED>'

        return "Check {}.{}".format(parent, self.__name)

    def __repr__(self):
        return self.__str__()

class Task:
    def __init__(self, subcheck, index, cost):
        self.__subcheck = subcheck
        self.__index = index
        self.__cost = cost

    def getCost(self):
        return self.__cost

    def getPriority(self):
        return self.__subcheck.getPriority()

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
