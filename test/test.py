#!/usr/bin/env python3

import subprocess as sp
from SMM import scheduler
import os
import json
from multiprocessing import Pool
from tabulate import tabulate
import numpy

def print_table(location, table, table_opts):
    with open(location, 'w') as f:
        f.write(tabulate(table, **table_opts))

def transpose_data_fmt(data, first_col=None):
    max_val = max(map(lambda x : len(x), data.values()))
    min_val = min(map(lambda x : len(x), data.values()))

    assert(max_val == min_val)

    headers = sorted(list(data.keys()))
    if first_col is not None:
        if first_col in headers:
            headers.remove(first_col)
            headers.insert(0, first_col)

    rows = [headers]
    for i in range(max_val):
        rows.append([data[h][i] for h in headers])

    return rows


def transpose_data(table):
    return numpy.asarray(table).T.tolist()

def run_sim(b):
    os.system("cat results/{bp}.prelude results/sim.workload | smmsim /dev/stdin --sqllog results/{bp}.log".format(bp=b))

def collect_result(b):
    json_result= sp.check_output(
        "smmbench results/{bp}.log".format(bp=b),
        shell=True
    )
    return (b, json_result)

def main():
    binpackers = scheduler.getBinPackers()
    sim_time = 1000
    load_factor = 0.90
    if not os.path.exists("results"):
        os.mkdir("results")

    if not os.path.exists("charts"):
        os.mkdir("charts")

    if not os.path.exists("tables"):
        os.mkdir("tables")

    sp.call(
        [
            "smmrandwork",
            str(sim_time),
            str(load_factor),
            "results/sim.workload",
            "--cost-mu", "25",
            "--cost-sigma", "50",
            "--priority-mu", "10",
            "--priority-sigma", "10",
            "--skip-prelude"
        ]
    )

    for b in binpackers.keys():
        sp.call(
            [
                "smmrandwork",
                "--prelude-only",
                "--binpacker={bp}".format(bp=b),
                str(sim_time),
                str(load_factor),
                "results/{bp}.prelude".format(bp=b)
            ]
        )


    benchmarks = {}

    p = Pool(5)
    #p.map(run_sim, binpackers.keys())
    results = p.map(collect_result, binpackers.keys())

    for b,v in results:
        benchmarks[b] = json.loads(v.decode())

    priorities = {}
    costs = {}

    throughput = {
        '': ['Tasks/Bin', 'Tasks/Second']
    }

    for k,v in benchmarks.items():
        priorities['bins'] = v['responsebin']['priority_bins'][1:]
        priorities[k] = v['responsebin']['priority']

        costs['bins'] = v['responsebin']['cost_bins'][1:]
        costs[k] = v['responsebin']['cost']


        throughput[k] = [v['throughput_tasks_per_bin'], v['throughput_tasks_per_second']]

    print(priorities)

    chart_opts = {
        'tablefmt':"plain",
        'floatfmt':".8f",
        'numalign':"right",
        'headers':"firstrow",
    }
    print_table('charts/priorities.txt', transpose_data_fmt(priorities, first_col="bins"), chart_opts)
    print_table('charts/costs.txt', transpose_data_fmt(costs, first_col="bins"), chart_opts)

    table_opts = {
        'tablefmt':"latex",
        'floatfmt':".2f",
        'numalign':"right",
        'headers':"firstrow"
    }
    print_table('tables/throughput.tex', transpose_data(transpose_data_fmt(throughput, first_col='')), table_opts )

if __name__ == '__main__':
    main()
