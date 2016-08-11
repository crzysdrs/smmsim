#!/usr/bin/env python3
import sqlite3
import os

class SimLog(object):
    def __init__(self, verbose):
        self._verbose = verbose

    def addMisc(self, key, val):
        if self._verbose:
            print("Misc: {}:{}".format(key, val))

    def addTask(self, time, task):
        if self._verbose:
            self.printTimeEvent(time, 0, "add_task", task=task)

    def removeTask(self, time, task):
        if self._verbose:
            self.printTimeEvent(time, 0, "rm_task", task=task)

    def printTimeEvent(self, time, length, event, task=None, cpu=None, bin=None, msg=None):
        bin_id = None
        if bin is not None:
            bin_id = bin.getId()

        if self._verbose:
            printable = {
                "Time":("{Time:020d}", time),
                "Event":("{Event:<10}", event),
                "Proc":("{Proc:04d}", cpu),
                "Bin":("{Bin:08d}", bin_id),
                "Task":("{Task}", task),
                "Length":("{Length}", length),
                "Msg":("{Msg}", msg),
            }
            order = ["Time", "Event", "Proc", "Bin", "Task", "Length", "Msg"]
            fmt = ""
            for o in order:
                if printable[o][1] is not None:
                    fmt += "{}: {} ".format(o, printable[o][0])

            items = ({k: v[1] for (k, v) in printable.items()})
            print(fmt.format(**items))

    def timeEvent(self, time, length, event, task=None, cpu=None, bin=None, msg=None):
        self.printTimeEvent(time, length, event, task, cpu, bin, msg)

    def warning(self, time, msg):
        print("{:020d}: Warning {}".format(time, msg))

    def error(self, time, msg):
        print("{:020d}: Error {}".format(time, msg))

    def endLog(self):
        pass

class SqliteLog(SimLog):
    def __init__(self, verbose, location):
        super().__init__(verbose)
        self.__tasks = {}
        self.__events = {}
        self.__eventid = 0
        self.__taskid = 0
        try:
            os.remove(location)
        except OSError as e:
            if e.errno != 2:
                raise e

        self.__conn = sqlite3.connect(location)
        self.__cursor = self.__conn.cursor()
        c = self.__cursor

        c.execute("""
        CREATE TABLE event
        (
            id integer primary key,
            time integer,
            type_id default null,
            cpu_id integer default null,
            bin_id integer default null,
            task_id integer default null,
            length integer default null,
            msg text default null
        );
        """)
        c.execute("""
        CREATE TABLE task
        (id integer primary key, name text);
        """
        )
        c.execute("""
        CREATE TABLE event_type
        (id int primary key, name text);
        """
        )

        c.execute("""
        CREATE TABLE misc
        (key text, val text);
        """
        )

    def addMisc(self, key, val):
        if self._verbose:
            super().addMisc(key, val)

        self.__cursor.execute(
            "INSERT INTO misc (key, val) VALUES (?, ?);",
            (key, val)
        )


    def addTask(self, time, task):
        if self._verbose:
            super().addTask(time, task)

        i = self.__taskid
        self.__taskid += 1

        self.__cursor.execute(
            "INSERT INTO task (id, name) VALUES (?, ?);",
            (i, str(task))
        )
        self.__tasks[task] = i

        self.timeEvent(time, 0, "add_task", task=task)

    def removeTask(self, time, task):
        self.timeEvent(time, 0, "rm_task", task=task)

        if self._verbose:
            super().removeTask(time, task)

        del self.__tasks[task]

    def timeEvent(self, time, length, event, task=None, cpu=None, bin=None, msg=None):
        if self._verbose:
            super().timeEvent(time, length, event, task, cpu, bin, msg)

        if bin:
            bin_id = bin.getId()
        else:
            bin_id = None

        if event not in self.__events:
            self.__events[event] = self.__eventid
            self.__cursor.execute(
                "INSERT INTO event_type (id, name) VALUES (?, ?);",
                (self.__eventid, event)
            )
            self.__eventid += 1

        event_id = self.__events[event]
        task_id = None
        if task is not None:
            task_id = self.__tasks[task]

        self.__cursor.execute(
            "INSERT INTO event (time, cpu_id, bin_id, type_id, task_id, length, msg) VALUES (?, ?, ?, ?, ?, ?, ?);",
            (time, cpu, bin_id, event_id, task_id, length, msg)
        )

    def endLog(self):
        self.__conn.commit()
        self.__conn.close()
