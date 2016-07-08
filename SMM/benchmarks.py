#!/usr/bin/env python3

import sqlite3
import numpy as np
import argparse

def timediff(conn):
    #Computes the minimum, maximum and mean of each tasks runtime seperation.
    #Effectively means that an ephemeral attack that is shorter than the min
    # that occurs outside of the detection period will never be detected.

    results = np.array([[0, 0, 0]])
    for task in conn.cursor().execute("SELECT * FROM task order by id;"):
        events = conn.cursor().execute("SELECT time as end from event WHERE task_id = ? order by time", (task['id'],) ).fetchall()
        if events:
            e = np.array(events)
            next_e = np.append([[0]], e, axis=0)
            next_e = np.delete(next_e, len(next_e) - 1, 0)
            diff = np.subtract(e, next_e)
            diff = np.delete(diff, 0, 0)

            results = np.append(results, [[np.min(diff), np.max(diff), np.mean(diff)]], axis=0)
        else:
            results = np.append(results, [[0, 0, 0]], axis=0)

    results = np.delete(results, 0, 0)
    return results

def main():
    parser = argparse.ArgumentParser(description='Benchmark Enforcement Tool')
    parser.add_argument('db', type=str,
                        help='Sqlite Database File')

    args = parser.parse_args()

    print("Benchmarking...")
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    #if we had any firm failure cases, we could easily check that the
    # min/max/average met certain criteria.
    print (timediff(conn))

if __name__ == "__main__":
    main()
