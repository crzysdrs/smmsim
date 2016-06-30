#!/usr/bin/env python

from scheduler import CheckGroup, Check, Task

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

if __name__ == "__main__":
    main()
