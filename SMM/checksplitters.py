#!/usr/bin/env python
from SMM.scheduler import Task

"""
This is a collection of Check Splitting algorithms to be used with
the SMM simulator. Any class in module that implements
splitChecks will be automatically added to the list of avialable
bin packers.
"""

class DefaultTasks:
    """ Splits tasks in a greedy approach """
    def __init__(self):
        pass

    def splitChecks(self, c, granularity, time):
        """ Splits tasks by taking the largest possible chunk first"""
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
