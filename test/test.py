#!/usr/bin/env python3

import subprocess as sp
from SMM import scheduler
import os
import json
from multiprocessing import Pool
from tabulate import tabulate
import numpy
import time
import re

def print_table(location, table, table_opts, head=None):
    with open(location, 'w') as f:
        printed = tabulate(table, **table_opts)
        if 'tablefmt' in table_opts and table_opts['tablefmt'] == 'latex':
            if head:
                headers = r"\hline" + "\n" + "&".join(["\multicolumn{" + str(n) + "}{c}{" + t + "}" for (n,t) in head]) + r"\\\\"
                printed = re.sub(r"\\hline", headers, printed, 1)
            printed = re.sub(r"\bus\b", "$\\mu$s", printed)
        f.write(printed)


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

def run_sim(b, sim):
    cmd = "cat results_{sim}/{bp}.prelude results_{sim}/sim.workload | smmsim /dev/stdin --sqllog results_{sim}/{bp}.log".format(bp=b, sim=sim)
    os.system(cmd)

def collect_result(b, fname):
    json_result= sp.check_output(
        "smmbench {fname}".format(fname=fname),
        shell=True
    )
    return (b, json_result)

def main():
    runsim = True
    binpackers = scheduler.getBinPackers()
    sim_time = 1000

    if not os.path.exists("charts"):
        os.mkdir("charts")

    if not os.path.exists("tables"):
        os.mkdir("tables")

    sim = [70, 80, 90, 95]
    for s in sim:
        if not os.path.exists("results_{}".format(s)):
            os.mkdir("results_{}".format(s))
        if runsim:
            sp.call(
                [
                    "smmrandwork",
                    str(sim_time),
                    "results_{sim}/sim.workload".format(sim=s),
                    "--load={}".format(s / 100),
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
                        "--load={}".format(1),
                        str(sim_time),
                        "results_{sim}/{bp}.prelude".format(bp=b, sim=s)
                    ]
                )


    benchmarks = {}

    p = Pool(5)
    if runsim:
        p.starmap(run_sim, [(b, s) for b in binpackers.keys() for s in sim])

    results = {}
    for s in sim:
        results[s] = p.starmap(collect_result, [(b, "results_{s}/{bp}.log".format(bp=b, s=s)) for b in binpackers.keys()])

    for s in sim:
        benchmarks[s] = {}
        for b,v in results[s]:
            benchmarks[s][b] = json.loads(v.decode())

    priorities = {}
    costs = {}
    bin_head = [(1, ""), (2, "Bin Cost (us)")]
    bin_data = {
        '':['Avg', 'Std Dev', ],
    }
    throughput_head = [(1, ""), (2, "Tasks/Bin")]
    throughput = {
        '': ['70% Load', '95% Load']
    }
    response_stat_head = [(1, ""), (2, "Response Cost (us)")]
    response_stat = {
        '': ['Avg', 'Std Dev']
    }
    runtime_head = [(1, ""), (2, "70\\% Load (s)"), (2, "95\\% Load (s)")]
    runtime = {
        '': ['CPU', 'Wall', 'CPU', 'Wall']
    }

    sim_bin_data_head = [(1, "")] + [(2, "{}\\% Load".format(s)) for s in sim]
    sim_bin_data = {
        'workload': [s for s in sim]
    }

    sim_bin_resp_head = [(1, "")] + [(2, "{}\\% Load".format(s)) for s in sim]
    sim_bin_resp = {
        'workload': [s for s in sim]
    }

    for k,v in benchmarks[s].items():
        sim_bin_data[k] = []
        sim_bin_resp[k] = []

    for s in sim:
        for k,v in benchmarks[s].items():
            sim_bin_data[k] += [v['bins']['length']['mean']]
            sim_bin_resp[k] += [v['response_times']['mean']]

    for k,v in benchmarks[70].items():
        throughput[k] = [v['throughput_tasks_per_bin']]
        runtime[k] = [
            float(v['meta']['end_cpu_clock']) - float(v['meta']['start_cpu_clock']),
            float(v['meta']['end_wall_clock']) - float(v['meta']['start_wall_clock']),
        ]

    for k,v in benchmarks[95].items():
        priorities['bins'] = v['responsebin']['priority_bins'][1:]
        priorities[k] = v['responsebin']['priority']

        costs['bins'] = v['responsebin']['cost_bins'][1:]
        costs[k] = v['responsebin']['cost']


        throughput[k] += [v['throughput_tasks_per_bin']]
        bin_data[k] = [v['bins']['length']['mean'], v['bins']['length']['std']]

        response_stat[k] = [v['response_times']['mean'], v['response_times']['std']]

        runtime[k] += [
            float(v['meta']['end_cpu_clock']) - float(v['meta']['start_cpu_clock']),
            float(v['meta']['end_wall_clock']) - float(v['meta']['start_wall_clock']),
        ]


    chart_opts = {
        'tablefmt':"plain",
        'floatfmt':".8f",
        'numalign':"right",
        'headers':"firstrow",
    }
    print_table('charts/priorities.txt', transpose_data_fmt(priorities, first_col="bins"), chart_opts)
    print_table('charts/costs.txt', transpose_data_fmt(costs, first_col="bins"), chart_opts)

    print_table('charts/simbin.txt', transpose_data_fmt(sim_bin_data, first_col='workload'), chart_opts )
    print_table('charts/simbinresp.txt', transpose_data_fmt(sim_bin_resp, first_col='workload'), chart_opts )

    table_opts = {
        'tablefmt':"latex",
        'floatfmt':".2f",
        'numalign':"right",
        'headers':"firstrow"
    }

    print_table('tables/response_stat.tex', transpose_data(transpose_data_fmt(response_stat, first_col='')), table_opts, head=response_stat_head)
    print_table('tables/throughput.tex', transpose_data(transpose_data_fmt(throughput, first_col='')), table_opts , head=throughput_head)
    print_table('tables/bin_stat.tex', transpose_data(transpose_data_fmt(bin_data, first_col='')), table_opts ,head=bin_head)
    print_table('tables/simrun.tex', transpose_data(transpose_data_fmt(runtime, first_col='')), table_opts, head=runtime_head )


if __name__ == '__main__':
    main()
