#!/usr/bin/env python3
import sqlite3
import os

class SimLog(object):
    def __init__(self):
        self._verbose = True

    def addMisc(self, key, val):
        print("Misc: {}:{}".format(key, val))

    def addTask(self, time, task):
        print("{:020d}: Added Task {}".format(time, task))

    def genericEvent(self, time, cpu, event, length, bin=None):
        if bin is not None:
            bin_id = bin.getId()
        else:
            bin_id = 0

        print("{:020d}: Proc {:04d}: Bin {:08d} Event:{} Length:{}".format(time, cpu, bin_id, event, length))

    def taskEvent(self, time, task, cpu, bin):
        print("{:020d}: Proc {:04d}: Bin {:08d} Task {}".format(time, cpu, bin.getId(), task))

    def warning(self, time, msg):
        print("{:020d}: Warning {}".format(time, msg))

    def error(self, time, msg):
        print("{:020d}: Error {}".format(time, msg))

    def endLog(self):
        pass;

class SqliteLog(SimLog):
    def __init__(self, location):
        super().__init__()
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
        (id auto increment, time int, cpu_id int, bin_id int, task_id int default null, generic_id default null, length int null);
        """)
        c.execute("""
        CREATE TABLE task
        (id int, name text);
        """
        )
        c.execute("""
        CREATE TABLE generic_event
        (id int, name text);
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

    def genericEvent(self, time, cpu, event, length, bin=None):
        if self._verbose:
            super().genericEvent(time, cpu, event, length, bin)

        if bin:
            bin_id = bin.getId()
        else:
            bin_id = None

        if event not in self.__events:
            self.__events[event] = self.__eventid
            self.__cursor.execute(
                "INSERT INTO generic_event (id, name) VALUES (?, ?);",
                (self.__eventid, event)
            )
            self.__eventid += 1

        event_id = self.__events[event]

        self.__cursor.execute(
            "INSERT INTO event (time, cpu_id, bin_id, generic_id, length) VALUES (?, ?, ?, ?, ?);",
            (time, cpu, bin_id, event_id, length)
        )

    def taskEvent(self, time, task, cpu, bin):
        if self._verbose:
            super().taskEvent(time, task, cpu, bin)

        self.__cursor.execute(
            "INSERT INTO event (time, cpu_id, bin_id, task_id, length) VALUES (?, ?, ?, ?, ?);",
            (time, cpu, bin.getId(), self.__tasks[task], task.getCost())
        )

    def endLog(self):
        self.__conn.commit()
        self.__conn.close()
