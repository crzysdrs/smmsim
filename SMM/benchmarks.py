#!/usr/bin/env python3

import sqlite3
import numpy as np
import argparse

def timediff(conn):
    #Computes the minimum, maximum and mean of each tasks runtime seperation.
    #Effectively means that an ephemeral attack that is shorter than the min
    # that occurs outside of the detection period will never be detected.
    results = []

    for task in conn.cursor().execute("SELECT * FROM task order by id;"):
        events = conn.cursor().execute("SELECT time as end from event WHERE task_id = ? order by time", (task['id'],) ).fetchall()
        if events:
            e = np.array(events)
            next_e = np.append([[0]], e, axis=0)
            next_e = np.delete(next_e, len(next_e) - 1, 0)
            diff = np.subtract(e, next_e)
            diff = np.delete(diff, 0, 0)

            results.append( (task['name'], len(e), np.min(diff), np.max(diff), np.mean(diff)) )
        else:
            results.append( (task['name'], 0, 0, 0, 0) )

    return results

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
    r = c.execute("SELECT count(id) as total_tasks FROM event WHERE task_id not null").fetchall()
    return r[0]['total_tasks']

def throughput(conn):
    c = conn.cursor()
    last_time = maxtime(conn)
    total_tasks = totaltasks(conn)
    r = c.execute("SELECT count(id) as total_tasks FROM event WHERE task_id not null").fetchall()
    return total_tasks / (last_time / (10**6))

def throughputbin(conn):
    c = conn.cursor()
    bc = bincount(conn)
    total_tasks = totaltasks(conn)
    return total_tasks / bc[0]

def bincount(conn):
    c = conn.cursor()
    r = c.execute("select sum(length) as bin_length from event where bin_id not null group by bin_id").fetchall()
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
    #if we had any firm failure cases, we could easily check that the
    # min/max/average met certain criteria.
    print ("Time Betweeen Subsequent Repeated Task: count/min/max/avg (microseconds)")
    times = timediff(conn)
    for t in times:
        print(("{:>50} {:>10}" + "{:>15}" * 2 + "{:>15.2f}").format(*t))

    print ("SMM CPU Time Percentage: {}%".format(cputime(conn) * 100))
    print ("Throughput {} tasks/second".format(throughput(conn)))
    print ("Throughput {} tasks/bin".format(throughputbin(conn)))

if __name__ == "__main__":
    main()
