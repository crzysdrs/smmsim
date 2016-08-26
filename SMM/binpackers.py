#!/usr/bin/env
import random
from SMM.scheduler import Bin
import functools

"""
This is a collection of Bin Packing algorithms to be used with
the SMM simulator. Any class in module that implements
requestBin will be automatically added to the list of avialable
bin packers.
"""

def bisect(l, v, cmp=None):
    """ Find the rightmost insertion point for an element in a list

    Using list l, find the insertion index for value v, using an
    an optional comparison function.
    """
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
    """ The Default Bin Packing Algorithm (uses priority queue).

    A simplistic algorithm that reads tasks sequentially
    from a priority queue. If the next highest priority task
    does not fit in the bin, the bin is complete.
    DefaultBin only considers priority and leads to the possibility
    that low priority tasks will starve. Bins will be filled in
    O(n) time where n is the number of available tasks.
    """
    def __init__(self):
        self._queue = []
        self._cmp = lambda x: -x.getPriority()

    def getBinKey(self, state, f):
        """ Determine the next bin based on a ordering function

        The preferred approach is usually to store the ordered
        tasks in the queue field.
        """
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
        """ Return a filled bin based on the current state"""
        return self.getBinKey(state, self._cmp)

    def addTask(self, task):
        """ Adds a task to the current bin packer """
        ix = bisect(self._queue, task, cmp=lambda x, y : self._cmp(x) - self._cmp(y))
        self._queue.insert(ix, task)

    def unusedTasks(self):
        """ Return the set of tasks that haven't been placed into a bin

        This is important for bin packers that may have tasks pre-emptively
        placed in bins. If they are swapped out, they need to relinquish their
        tasks.
        """
        return self._queue

    def removeSubCheck(self, subcheck):
        """ Removes a subcheck from the existing queue of tasks """
        self._queue = list(filter(lambda t:  t.getCheck() == subcheck, self._queue))

    def ageQueue(self):
        """ Ages (i.e. reprioritizes) tasks in the queue """
        [t.setPriority(t.getPriority() + 1) for t in self._queue]

class AgingBin(DefaultBin):
    """ Packs based on a priority queue while aging unused tasks

    Algorithm that reads tasks from a priority queue with an added
    aging mechanism. This causes any unused tasks still remaining
    in the queue to increase priority every time they are unselected
    preventing starvation. If the next highest priority task does
    not fit the bin is complete. Bins will be filled in O(n)
    time where n is the number of available tasks.
    """
    def requestBin(self, state, cpu_id):
        """ Returns a bin based on the current state """
        b = super().requestBin(state, cpu_id)
        self.ageQueue()
        return b

class RandomBin(DefaultBin):
    """ Randomly chooses tasks to fill in a bin.

    Uses a randomly permuted queue to determine the next task selection. The algorithm reads from that queue in sequential order until it is unable to fit the next task in the bin. Bins will be filled in O(n) time where n is the number of available tasks.
    """
    def __init__(self):
        """ Initialize with random number generator for ordering """
        super().__init__()
        self._cmp = lambda *args : random.random()

    def requestBin(self, state, cpu_id):
        """ Request a bin based on the current state """
        return super().requestBin(state, cpu_id)

class LeastRecentBin(DefaultBin):
    """ Choose the least recently run task to prioritize.

    When a task is created or executed a time stamp is updated
    on the task. The time stamps are used as priorities which
    allows no tasks to be starved as all tasks will be served
    depending on their age. If the next oldest task does not
    fit the bin is complete. There is no risk of starvation
    as old tasks are always effectively highest priority.
    Bins will be filled in O(n) time  where n is the
    number of available tasks.

    """
    def __init__(self):
        """The ordering function should be based on the last time run """
        super().__init__()
        self._cmp = lambda x : x.lastTimeRun()

    def requestBin(self, state, cpu_id):
        """ Request a bin based on the current state """
        return super().requestBin(state, cpu_id)

class KnapsackBin(DefaultBin):
    """ A generic knapsack bin filler

    This class will be inherited to build a Knapsack filler based
    on different criteria
    """
    def requestFillBin(self, criteria, state):
        """ Return a bin based on a criterion function for knapsack value """
        b = Bin()

        best = [[None for y in range(len(self._queue))] for x in range(state.getVar('binsize') + 1)]

        # Bottom Up Knapsack Value Determination
        for i in range(len(self._queue)):
            for j in range(state.getVar('binsize') + 1):
                if i > 0:
                    best[j][i] = best[j][i-1]
                else:
                    best[j][i] = (0, None)

                cost = self._queue[i].getCost()
                if cost <= j:
                    if i > 0:
                        sub = best[j - cost][i - 1]
                    else:
                        sub = (0, None)
                    new = (sub[0] + criteria(self._queue[i]), i)
                    if best[j][i][0] < new[0]:
                        best[j][i] = new

        space = state.getVar('binsize')

        i = len(self._queue) - 1

        # Determine the correct "Best" value based on
        # bottom uup results.
        while space >= 0 and i >= 0:
            if not best[space][i]:
                break

            i = best[space][i][1]
            if i is not None:
                c = self._queue[i]
                b.addTask(c)
                self._queue[i] = None
                space -= c.getCost()
                i -= 1
            else:
                break

        #Remove selected tasks from queue
        self._queue = list(filter(lambda x : x is not None, self._queue))
        return b

class CostKnapsackBin(KnapsackBin):
    """ CostKnapsack uses the Knapsack algorithm with the task cost as criteria"""
    def requestBin(self, state, cpu_id):
        return self.requestFillBin(lambda x : x.getCost(), state)

class PriorityKnapsackBin(KnapsackBin):
    """ PriorityKnapsack uses the Knapsack algorithm with the task priority as criteria"""
    def requestBin(self, state, cpu_id):
        b = self.requestFillBin(lambda x : x.getPriority(), state)
        self.ageQueue()
        return b

class BinQueue(DefaultBin):
    """ A generic class that maintains queues of bins to be run in the future."""
    def __init__(self):
        """ Initializes an empty bin queue for storing future bins """
        super().__init__()
        self._binqueue = []

    def _requestBin(self, state, cpu_id):
        """ Handle the construction of new bins with empty queues """
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
        """ Add a new task with no priority consideration """
        self._queue.append(task)

    def unusedTasks(self):
        """ Return the set of tasks that may be in bins but not yet run
        """
        return functools.reduce(lambda x, y : x + y, [b.getTasks() for b in self._binqueue], []) + self._queue

    def removeSubCheck(self, subcheck):
        """ Removes a subcheck from the set of unused tasks """
        self._queue = list(filter(lambda t:  t.getCheck() == subcheck, self.unusedTasks()))
        self._binqueue = []

class LPBinPack(BinQueue):
    """ Linear Programming Bin Packer

    A linear programming implementation of the canonical
    Bin Packing algorithm. It provides a minimal number
    of bins filled with tasks that are as full as possible.
    One minor modification that is made to this implementation
    that only the next several bins are kept while the remaining
    tasks are placed back on the queue. This allows bins to be
    refilled later in more optimal matter as other tasks become
    available otherwise the later bins would simply be under filled.
    LPBinPack is currently limited to finding the best
    solution with maximum 10 bins to constrain the overall
    runtime which can be substantial.
    """
    def computeBins(self, state, cpu_id):
        """ Compute the next several bins using LP Bin pack algo """
        import pulp
        import time

        #https://www.linkedin.com/pulse/bin-packing-python-pulp-michael-basilyan
        #This code modified from https://github.com/mbasilyan/binpacking/blob/master/binpacker.py
        items = [(i, i.getCost()) for i in self._queue]
        itemCount = len(items)
        if itemCount == 0:
            return

        # Max number of bins allowed.
        maxBins = 10

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
        try:
            prob.solve()
        except:
            #Sometimes the solver crashes?! Better luck next time.
            return
        #print("Solved in %s seconds." % (time.time() - start_time))

        # Bins used
        bin_count = int(sum([y[i].value() for i in range(maxBins)]))
        #print("Bins used: {}".format(bin_count))

        # The rest of this is some unpleasent massaging to get pretty results.
        bins = {}

        for itemBinPair in x.keys():
            if(x[itemBinPair].value() == 1):
                itemNum = itemBinPair[0]
                binNum = itemBinPair[1]
                if binNum not in bins:
                    bins[binNum] = Bin()

                bins[binNum].addTask(itemNum)

        self._binqueue = sorted(bins.values(), key=lambda b:b.getCost(), reverse=True)
        split = int(len(self._binqueue) * 0.75)
        if split > 1:
            (self._binqueue, dropped) = (self._binqueue[:split], self._binqueue[split:])
            self._queue = sum(map(lambda d: d.getTasks(), dropped), [])
        else:
            self._queue = []

        #Apparently, if the maxBins is exceeded it just throws all remaining tasks into one big task
        # which is probably cheating.
        large = filter(lambda b : b.getCost() > binCapacity, self._binqueue)
        self._binqueue = list(filter(lambda b : b.getCost() <= binCapacity, self._binqueue))

        self._queue.extend(sum([l.getTasks() for l in large], []))

        #print (list(map(lambda b : b.getCost(), self._binqueue)))


    def requestBin(self, state, cpu_id):
        """ Request the next available bin """
        return super()._requestBin(state, cpu_id)
