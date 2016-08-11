#!/usr/bin/env python3

import sqlite3
import numpy as np
import argparse

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
    print ("Tasks Finished {} Tasks Remaining {}".format(len(finished), len(nofinish)))
    runtimes = np.transpose(finished)
    (start, finish) = np.split(runtimes, 2)
    actual = np.subtract(finish, start)
    print ("Response Times for Tasks (microseconds):\n Min {} Mean {} Max {}".format(np.min(actual), np.mean(actual), np.max(actual)))
    return actual

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

    if total_bin_time and last_time:
        return total_bin_time / last_time
    else:
        return 0

def totaltasks(conn):
    c = conn.cursor()
    r = c.execute("SELECT count(id) as total_tasks FROM event WHERE type_id = " + taskid("run_task")).fetchall()
    return r[0]['total_tasks']

def throughput(conn):
    c = conn.cursor()
    last_time = maxtime(conn)
    total_tasks = totaltasks(conn)

    return total_tasks / (last_time / (10**6))

def throughputbin(conn):
    c = conn.cursor()
    bc = bincount(conn)
    total_tasks = totaltasks(conn)
    return total_tasks / bc[0]

def bincount(conn):
    c = conn.cursor()
    r = c.execute("""
    select sum(length) as bin_length
    from event
    where bin_id not null
    group by bin_id""").fetchall()
    bindata = np.array(r)
    if len(bindata):
        return (len(bindata), np.min(bindata), np.max(bindata), np.mean(bindata) )
    else:
        return (0, 0, 0, 0)

def miscdata(conn):
    c = conn.cursor()
    r = c.execute("select * from misc").fetchall()
    return r

def main():
    parser = argparse.ArgumentParser(description='Benchmark Enforcement Tool')
    parser.add_argument('db', type=str,
                        help='Sqlite Database File')

    args = parser.parse_args()

    print("Benchmarking...")
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    print ("\n".join(map(lambda x : "Misc Data {:>15}:{}".format(x['key'], x['val']), miscdata(conn))))
    print ("Bins Total: {} \nBin Length min/max/avg (microseconds): {:>15} {:>15} {:>15.2f}".format(*bincount(conn)))
    responsetime(conn)

    print ("SMM CPU Time Percentage: {}%".format(cputime(conn) * 100))
    print ("Throughput {} tasks/second".format(throughput(conn)))
    print ("Throughput {} tasks/bin".format(throughputbin(conn)))

if __name__ == "__main__":
    main()
