#!/usr/bin/env python3

import sqlite3
import numpy as np
import argparse
import json
import os
import sys

def taskid(name):
    return "(select id from event_type where name = '{}')".format(name)

def avghist(data, weights, bins=None):
    if bins is not None:
        sums = np.histogram(data, weights=weights, bins=bins)[0]
        (counts, buckets) = np.histogram(data, bins=bins)
        buckets=bins
    else:
        sums = np.histogram(data, weights=weights)[0]
        (counts, buckets) = np.histogram(data)

    #elements with zero count will by definition have zero sum, ignore div by zero
    counts[counts == 0] = 1

    bin_means = np.divide(sums, counts)
    return (bin_means, buckets)

def binresponsetime(conn):
    c = conn.cursor()
    sql = """
    select task.cost, task.priority, finished.time - event.time as responsetime, finished.time, event.time
    from event
    left join (select time, task_id from event where type_id=""" + taskid("run_task") + """) as finished
          on event.task_id = finished.task_id
    left join task on task.id = event.task_id
    where event.type_id=""" + taskid("add_task") + " order by event.time"

    results = c.execute(sql).fetchall()

    results = np.array(results, dtype=float)
    finished_results = results[~np.isnan(results[:,2])]

    cost = avghist(finished_results[:,0], weights=finished_results[:,2], bins=np.linspace(0, 50, num=20))
    priority = avghist(finished_results[:,1], weights=finished_results[:,2],  bins=list(range(1, 21)))

    r = {
        'responsebin':{
            'cost':list(cost[0]),
            'cost_bins':list(cost[1]),
            'priority':list(priority[0]),
            'priority_bins':list(map(float, priority[1]))
        }
    }
    return r

def responsetime(conn):
    c = conn.cursor()
    results = c.execute("""
    select finished.time, event.time, finished.time - event.time as responsetime
    from event
    left join (select time, task_id from event where type_id=""" + taskid("run_task") + """) as finished
          on event.task_id = finished.task_id
    where event.type_id=""" + taskid("add_task")).fetchall()

    results = np.matrix(results, dtype=float)
    runtimes = results[:,2]

    nones = runtimes == np.array(None)
    (finished, nofinish) = (runtimes[~np.isnan(runtimes).all(axis=1)], runtimes[np.isnan(runtimes).any(axis=1)])

    return {
        "completion":{
            "finished":finished.size,
            "dnf":nofinish.size,
        },
        "response_times":{
            "min":np.min(finished),
            "mean":np.mean(finished),
            "max":np.max(finished),
            "std":np.std(finished)
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
    bindata = np.array(r, dtype=float)

    if len(bindata):
        binfo = (len(bindata), np.min(bindata), np.max(bindata), np.mean(bindata), np.std(bindata) )
    else:
        binfo = (0, 0, 0, 0, 0)

    return {
        "bins":{
            "count":float(binfo[0]),
            "length":{
                "min":float(binfo[1]),
                "max":float(binfo[2]),
                "mean":float(binfo[3]),
                "std":float(binfo[4]),
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
    data.update(binresponsetime(conn))
    data.update(cputime(conn))
    data.update(throughput(conn))
    data.update(throughputbin(conn))

    print(json.dumps(data, indent=4, sort_keys=True))


if __name__ == "__main__":
    main()
