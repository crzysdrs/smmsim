#!/usr/bin/env
import random
from scheduler import Bin

class DefaultBin:
    def __init__(self):
        self._queue = []

    def getBinKey(self, state, f):
        b = Bin()

        if len(state.getTasks()) == 0:
            return b

        while b.getCost() < state.getVar('binsize'):
            if len(self._queue) == 0:
                self._queue = list(state.getTasks())
                self._queue = sorted(self._queue, key=f)

            front = self._queue[0]
            if front.getCost() + b.getCost() <= state.getVar('binsize'):
                b.addTask(front)
            else:
                return b
            self._queue = self._queue[1:]

        return b

    def requestBin(self, state, cpu_id):
        return self.getBinKey(state, lambda x: -x.getPriority())

class RandomBin(DefaultBin):
    def requestBin(self, state, cpu_id):
        return self.getBinKey(state, lambda *args : random.random())

class LeastRecentBin(DefaultBin):
    def requestBin(self, state, cpu_id):
        return self.getBinKey(state, lambda x : x.lastTimeRun())

class FillBin(DefaultBin):
    def requestFillBin(self, criteria, state):
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

        while sum(map(lambda x : x.getCost(), self._queue)) < state.getVar('binsize') and len(state.getTasks()) > 0:
            self._queue += state.getTasks()

        best = [[None for y in range(len(self._queue))] for x in range(state.getVar('binsize') + 1)]

        fillBin(criteria, best, state.getVar('binsize'), len(self._queue) - 1, self._queue)

        space = state.getVar('binsize')

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
    def requestBin(self, state, cpu_id):
        return self.requestFillBin(lambda x : x.getCost(), state)

class MaxPriorityBin(FillBin):
    def requestBin(self, state, cpu_id):
        return self.requestFillBin(lambda x : x.getPriority(), state)
