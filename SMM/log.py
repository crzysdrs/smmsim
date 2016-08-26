#!/usr/bin/env python3
import sqlite3
import os

""" A set of Logging Classes for use with the simulator """

class SimLog(object):
    """ Logs to stdout the plain text form of the log """
    def __init__(self, verbose):
        self._verbose = verbose

    def addMisc(self, key, val):
        """ Miscellaneous informatino notification """
        if self._verbose:
            print("Misc: {}:{}".format(key, val))

    def addTask(self, time, task):
        """ A task was added """
        if self._verbose:
            self.printTimeEvent(time, 0, "add_task", task=task)

    def removeTask(self, time, task):
        """ A task was removed """
        if self._verbose:
            self.printTimeEvent(time, 0, "rm_task", task=task)

    def printTimeEvent(self, time, length, event, task=None, cpu=None, bin=None, msg=None):
        """ Print the info about an an event """
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
        """ An event occurred """
        self.printTimeEvent(time, length, event, task, cpu, bin, msg)

    def warning(self, time, msg):
        """ The simulator warned about something """
        print("{:020d}: Warning {}".format(time, msg))

    def error(self, time, msg):
        """ The simulator errored """
        print("{:020d}: Error {}".format(time, msg))

    def endLog(self):
        """ Terminate Log """
        pass

class SqliteLog(SimLog):
    """ A Sqlite Log that is stored in a specified file """
    def __init__(self, verbose, location):
        super().__init__(verbose)
        self.__tasks = {}
        self.__events = {}
        self.__eventid = 0
        self.__taskid = 0

        #Attempt to remove existing log
        try:
            os.remove(location)
        except OSError as e:
            if e.errno != 2:
                raise e

        self.__conn = sqlite3.connect(location)
        self.__cursor = self.__conn.cursor()
        c = self.__cursor

        #Create various tables
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
        (id integer primary key, name text, cost integer, priority integer);
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
        """ Log Miscellaneous information """
        if self._verbose:
            super().addMisc(key, val)

        self.__cursor.execute(
            "INSERT INTO misc (key, val) VALUES (?, ?);",
            (key, val)
        )


    def addTask(self, time, task):
        """ Log task addition """
        i = self.__taskid
        self.__taskid += 1

        self.__cursor.execute(
            "INSERT INTO task (id, name, priority, cost) VALUES (?, ?, ?, ?);",
            (i, str(task), task.getPriority(), task.getCost())
        )
        self.__tasks[task] = i

        self.timeEvent(time, 0, "add_task", task=task)

    def removeTask(self, time, task):
        """ Log task removal """
        self.timeEvent(time, 0, "rm_task", task=task)
        del self.__tasks[task]

    def timeEvent(self, time, length, event, task=None, cpu=None, bin=None, msg=None):
        """ Log event occured """
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
        """End the log by cleaning up the database connection """
        self.__conn.commit()
        self.__conn.close()
