#!/usr/bin/env python

from scheduler import CheckGroup, Check, Task, Bin

def tasksplitter(checkgroups):
    tasksize = 50
    tasks = []
    for cg in checkgroups:
        for c in cg.getChecks():
            cost = c.getCost()
            i = 0
            while cost > 0:
                task_cost = tasksize if cost > tasksize else cost
                tasks.append(c.makeTask(i, task_cost))
                cost -= tasksize
                i += 1

    return tasks


class BinPacker:
    def __init__(self, tasks, binsize):
        self.__tasks = tasks
        self.__queue = []
        self.__binsize = binsize

    def requestBin(self, time):
        b = Bin()
        while b.getCost() < self.__binsize:
            if len(self.__queue) == 0:
                self.__queue = list(self.__tasks)
                self.__queue.sort(key=lambda t : t.getPriority())

            front = self.__queue[0]
            self.__queue = self.__queue[1:]
            if front.getCost() + b.getCost() <= self.__binsize:
                b.addTask(front)
            else:
                return b

        return b

def main():
    checks = [
        CheckGroup(
            'IDTcheck', [
                Check('IDTR', 1),
                Check('HashIdtTable', 10),
                Check('IdtFunctionPtrWalker', 15),
            ]
        ),
        CheckGroup(
            'HyperCall', [
                Check('HypercallTableAddr', 5),
                Check('HypercallTableHash', 50),
                Check('HypercallTableWalk', 100),
            ]
        ),
        CheckGroup(
            'GDT', [
                Check('GDTR', 1),
                Check('GdtHash', 50),
            ]
        ),
        CheckGroup(
            'Kernel', [
                Check('KernelAddr', 20),
                Check('KernelHash', 500),
            ]
        ),
        CheckGroup(
            'VmExit', [
                Check('VmExitTableAddr', 1),
                Check('VmExitTableHash', 5),
                Check('VmExitTableWalk', 10),
            ]
        ),
        CheckGroup(
            'CR0', [
                Check('CR0Val', 1),
            ]
        ),
    ]

    tasks = tasksplitter(checks)

    for t in tasks:
        print t

    #all times are in microseconds
    one_second = 10**6
    time = 0
    target_time = 50 * one_second
    binsize = 100
    packer = BinPacker(tasks, binsize)
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
