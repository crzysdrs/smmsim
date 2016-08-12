#!/usr/bin/env python3

import sqlite3
import numpy as np
import argparse
import json
import os
import sys

def taskid(name):
    return "(select id from event_type where name = '{}')".format(name)

def responsetime(conn):
    c = conn.cursor()
    runtimes = c.execute("""
    select event.time, finished.time
    from event
    left join (select time, task_id from event where type_id=""" + taskid("run_task") + """) as finished
          on event.task_id = finished.task_id
    where event.type_id=""" + taskid("add_task")).fetchall()

    runtimes = np.array(runtimes)
    nones = runtimes == np.array(None)
    (finished, nofinish) = (runtimes[(~nones).all(axis=1)], runtimes[nones.any(axis=1)])

    runtimes = np.transpose(finished)
    (start, finish) = np.split(runtimes, 2)

    actual = np.subtract(finish, start)
    return {
        "completion":{
            "finished":len(finished),
            "dnf":len(nofinish),
        },
        "response_times":{
            "min":float(np.min(actual)),
            "mean":float(np.mean(actual)),
            "max":float(np.max(actual))
        }
    }

def maxtime(conn):
    c = conn.cursor()
    r = c.execute("SELECT max(time) as max_time FROM event WHERE bin_id not null").fetchall()
    last_time = r[0]['max_time']
    return last_time

def cputime(conn):
    c = conn.cursor()
    r = c.execute("SELECT SUM(length) as total_bin_time FROM event WHERE bin_id not null").fetchall()
    total_bin_time = r[0]['total_bin_time'];
    last_time = maxtime(conn)

    cputime = 0
    if total_bin_time and last_time:
        cpu_time = total_bin_time / last_time

    return {
        "cpu_time":cpu_time
    }


def totaltasks(conn):
    c = conn.cursor()
    r = c.execute("SELECT count(id) as total_tasks FROM event WHERE type_id = " + taskid("run_task")).fetchall()
    return r[0]['total_tasks']

def throughput(conn):
    c = conn.cursor()
    last_time = maxtime(conn)
    total_tasks = totaltasks(conn)

    return {
        "throughput_tasks_per_second": (total_tasks / (last_time / (10**6)))
    }

def throughputbin(conn):
    c = conn.cursor()
    bc = bincount(conn)
    total_tasks = totaltasks(conn)
    return  {
        "throughput_tasks_per_bin": total_tasks / bc['bins']['count']
    }

def bincount(conn):
    c = conn.cursor()
    r = c.execute("""
    select sum(length) as bin_length
    from event
    where bin_id not null
    group by bin_id""").fetchall()
    bindata = np.array(r)

    if len(bindata):
        binfo = (len(bindata), np.min(bindata), np.max(bindata), np.mean(bindata) )
    else:
        binfo = (0, 0, 0, 0)

    return {
        "bins":{
            "count":float(binfo[0]),
            "length":{
                "min":float(binfo[1]),
                "max":float(binfo[2]),
                "mean":float(binfo[3])
            }
        }
    }

def miscdata(conn):
    c = conn.cursor()
    r = c.execute("select * from misc").fetchall()
    return {
        "meta":{k:str(v) for k,v in r}
    }

def main():
    parser = argparse.ArgumentParser(description='Benchmark Enforcement Tool')
    parser.add_argument('db', type=str,
                        help='Sqlite Database File')

    args = parser.parse_args()

    if not os.path.exists(args.db):
        print("DB does not exist");
        sys.exit(1)

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    data = {}
    data.update(miscdata(conn))
    data.update(bincount(conn))
    data.update(responsetime(conn))
    data.update(cputime(conn))
    data.update(throughput(conn))
    data.update(throughputbin(conn))

    print(json.dumps(data, indent=4, sort_keys=True))

if __name__ == "__main__":
    main()
