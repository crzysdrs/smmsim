#!/usr/bin/env
import random
from scheduler import Bin

class DefaultBin:
    def __init__(self, tasks, binsize):
        self._tasks = tasks
        self._queue = []
        self._binsize = binsize

    def getBinKey(self, time, f):
        b = Bin()
        while b.getCost() < self._binsize:
            if len(self._queue) == 0:
                self._queue = (self._tasks)
                self._queue = sorted(self._queue, key=f)

            front = self._queue[0]
            if front.getCost() + b.getCost() <= self._binsize:
                b.addTask(front)
            else:
                return b
            self._queue = self._queue[1:]

        return b

    def requestBin(self, time, cpu_id):
        return self.getBinKey(time, lambda x: -x.getPriority())

class RandomBin(DefaultBin):
    def requestBin(self, time, cpu_id):
        return self.getBinKey(time, lambda *args : random.random())

class FillBin(DefaultBin):
    def requestFillBin(self, criteria, time):
        def fillBin(criteria, best, space, i, choices):
            if space <= 0 or i < 0:
                return (0, None)
            elif best[space][i] is not None:
                pass
            else:
                best[space][i] = fillBin(criteria, best, space, i - 1, choices)
                if space >= choices[i].getCost():
                    sub = fillBin(criteria, best, space - choices[i].getCost(), i - 1, choices)
                    b = (sub[0] + criteria(choices[i]), i)
                    if best[space][i][0] < b[0]:
                        best[space][i] = b

            return best[space][i]

        b = Bin()

        while sum(map(lambda x : x.getCost(), self._queue)) < self._binsize:
            self._queue += self._tasks

        best = [[None for y in range(len(self._queue))] for x in range(self._binsize + 1)]

        fillBin(criteria, best, self._binsize, len(self._queue) - 1, self._queue)

        space = self._binsize

        i = len(self._queue) - 1
        while space >= 0 and i >= 0:
            if not best[space][i]:
                break

            i = best[space][i][1]
            if i:
                c = self._queue[i]
                b.addTask(c)
                self._queue[i] = None
                space -= c.getCost()
                i -= 1
            else:
                break

        self._queue = list(filter(lambda x : x is not None, self._queue))
        return b

class MaxFillBin(FillBin):
    def requestBin(self, time, cpu_id):
        return self.requestFillBin(lambda x : x.getCost(), time)

class MaxPriorityBin(FillBin):
    def requestBin(self, time, cpu_id):
        return self.requestFillBin(lambda x : x.getPriority(), time)
