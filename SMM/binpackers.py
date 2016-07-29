#!/usr/bin/env
import random
from scheduler import Bin
import functools

#returns the rightmost insertion location
def bisect(l, v, cmp=None):
    if not cmp:
        cmp = lambda x, y : 0 if x == y else (1 if x > y else -1)

    low = 0
    high = len(l)

    while low < high:
        mid = (high - low) // 2 + low
        c = cmp(l[mid], v)
        if c > 0:
            high = mid
        else:
            low = mid + 1

    return low

class DefaultBin:
    def __init__(self):
        self._queue = []
        self._cmp = lambda x: -x.getPriority()

    def getBinKey(self, state, f):
        b = Bin()

        if len(self._queue) == 0:
            return b

        while b.getCost() < state.getVar('binsize') and len(self._queue) > 0:
            front = self._queue[0]
            if front.getCost() + b.getCost() <= state.getVar('binsize'):
                b.addTask(front)
            else:
                return b
            self._queue = self._queue[1:]

        return b

    def requestBin(self, state, cpu_id):
        return self.getBinKey(state, self._cmp)

    def addTask(self, task):
        ix = bisect(self._queue, task, cmp=lambda x, y : self._cmp(x) - self._cmp(y))
        self._queue.insert(ix, task)

    def unusedTasks(self):
        return self._queue

    def removeSubCheck(self, subcheck):
        self._queue = list(filter(lambda t:  t.getCheck() == subcheck, self._queue))

class RandomBin(DefaultBin):
    def __init__(self):
        super().__init__()
        self._cmp = lambda *args : random.random()

    def requestBin(self, state, cpu_id):
        return super().requestBin(state, cpu_id)

class LeastRecentBin(DefaultBin):
    def __init__(self):
        super().__init__()
        self._cmp = lambda x : x.lastTimeRun()

    def requestBin(self, state, cpu_id):
        return super().requestBin(state, cpu_id)

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

class BinQueue(DefaultBin):
    def __init__(self):
        super().__init__()
        self._binqueue = []

    def _requestBin(self, state, cpu_id):
        if len(self._binqueue) == 0:
            self.computeBins(state, cpu_id)

        if len(self._binqueue) == 0:
            #must be no remaining tasks
            return Bin()
        else:
            front = self._binqueue[0]
            self._binqueue = self._binqueue[1:]
            return front

    def addTask(self, task):
        self._queue.append(task)

    def unusedTasks(self):
        return functools.reduce(lambda x, y : x + y, [b.getTasks() for b in self._binqueue], []) + self._queue

    def removeSubCheck(self, subcheck):
        self._queue = list(filter(lambda t:  t.getCheck() == subcheck, self.unusedTasks()))
        self._binqueue = []

class FirstFit(BinQueue):
    def requestBin(self, state, cpu_id):
        return super()._requestBin(state, cpu_id)

class LPBinPack(BinQueue):
    def computeBins(self, state, cpu_id):
        import pulp
        import time

        #https://www.linkedin.com/pulse/bin-packing-python-pulp-michael-basilyan
        #This code modified from https://github.com/mbasilyan/binpacking/blob/master/binpacker.py
        items = [(i, i.getCost()) for i in self._queue]
        print (items)
        itemCount = len(items)

        # Max number of bins allowed.
        maxBins = 32

        # Bin Size
        binCapacity = state.getVar("binsize")

        # Indicator variable assigned 1 when the bin is used.
        y = pulp.LpVariable.dicts('BinUsed', range(maxBins),
                                  lowBound = 0,
                                  upBound = 1,
                                  cat = pulp.LpInteger)

        # An indicator variable that is assigned 1 when item is placed into binNum
        possible_ItemInBin = [(itemTuple[0], binNum) for itemTuple in items
                              for binNum in range(maxBins)]
        x = pulp.LpVariable.dicts('itemInBin', possible_ItemInBin,
                                  lowBound = 0,
                                  upBound = 1,
                                  cat = pulp.LpInteger)

        # Initialize the problem
        prob = pulp.LpProblem("Bin Packing Problem", pulp.LpMinimize)

        # Add the objective function.
        prob += (
            pulp.lpSum([y[i] for i in range(maxBins)]),
            "Objective: Minimize Bins Used"
        )

        #
        # This is the constraints section.
        #

        # First constraint: For every item, the sum of bins in which it appears must be 1
        for j in items:
            prob += (
                pulp.lpSum([x[(j[0], i)] for i in range(maxBins)]) == 1,
                ("An item can be in only 1 bin -- " + str(j[0]))
            )

        # Second constraint: For every bin, the number of items in the bin cannot exceed the bin capacity
        for i in range(maxBins):
            prob += (
                pulp.lpSum([items[j][1] * x[(items[j][0], i)] for j in range(itemCount)]) <= binCapacity*y[i],
                ("The sum of item sizes must be smaller than the bin -- " + str(i))
            )

        # Write the model to disk
        #prob.writeLP("BinPack.lp")

        # Solve the optimization.
        start_time = time.time()
        prob.solve()
        print("Solved in %s seconds." % (time.time() - start_time))

        # Bins used
        bin_count = int(sum([y[i].value() for i in range(maxBins)]))
        print("Bins used: {}".format(bin_count))

        # The rest of this is some unpleasent massaging to get pretty results.
        bins = {}

        for itemBinPair in x.keys():
            if(x[itemBinPair].value() == 1):
                itemNum = itemBinPair[0]
                binNum = itemBinPair[1]
                if binNum not in bins:
                    bins[binNum] = Bin()

                bins[binNum].addTask(itemNum)

        self._binqueue = list(bins.values())
        self._queue = []

    def requestBin(self, state, cpu_id):
        return super()._requestBin(state, cpu_id)
