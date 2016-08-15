#!/usr/bin/env python

from SMM.scheduler import Task

class DefaultTasks:
    def __init__(self):
        pass

    def splitChecks(self, c, granularity, time):
        tasksize = granularity
        tasks = []
        cost = c.getCost()
        i = 0
        while cost > 0:
            task_cost = tasksize if cost > tasksize else cost
            tasks.append(c.makeTask(i, task_cost, time))
            cost -= tasksize
            i += 1

        return tasks
