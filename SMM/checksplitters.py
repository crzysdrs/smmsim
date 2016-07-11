#!/usr/bin/env python

from scheduler import Task

class DefaultTasks:
    def __init__(self):
        pass

    def splitChecks(self, checkgroups, granularity):
        tasksize = granularity
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
