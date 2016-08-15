#!/usr/bin/env python3

import subprocess as sp
from SMM import scheduler
import os
import json
from multiprocessing import Pool

def cleanup(v):
    if isinstance(v, float):
        return "{:.2f}".format(v)
    else:
        return str(v)

def print_chart(name, data):
    max_val = max(map(lambda x : len(x), data.values()))
    min_val = min(map(lambda x : len(x), data.values()))

    assert(max_val == min_val)

    keys = list(data.keys())

    with open('charts/' + name + ".txt", 'w') as f:
        f.write(" ".join(keys) + "\n")

        for i in range(max_val):
            f.write(" ".join(map(lambda k : str(data[k][i]), keys)) + "\n")

def print_table(name, rows, data):
    max_val = max(map(lambda x : len(x), data.values()))
    min_val = min(map(lambda x : len(x), data.values()))

    assert(max_val == min_val)

    keys = list(data.keys())

    with open('tables/' + name + ".txt", 'w') as f:
        f.write("\\begin{tabular}{|" + "|".join(map(lambda x : " r ", [""] + keys)) + "| }\n")
        f.write("\\hline \n")
        f.write(" & " + " & ".join(keys) + '\\\\ \\hline' + "\n")

        for i in range(max_val):
            f.write(" & ".join([rows[i]] + list(map(lambda k :cleanup(data[k][i]), keys))) + "\\\\ \\hline \n")

        f.write("\\end{tabular}\n")

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
    throughput = {}
    costs = {}
    for k,v in benchmarks.items():
        priorities['bins'] = v['responsebin']['priority_bins'][1:]
        priorities[k] = v['responsebin']['priority']

        costs['bins'] = v['responsebin']['cost_bins'][1:]
        costs[k] = v['responsebin']['cost']


        throughput[k] = [v['throughput_tasks_per_bin'], v['throughput_tasks_per_second']]

    print(priorities)

    print_chart('priorities', priorities)
    print_chart('costs', costs)
    print_table('throughput', ['Throughput (tasks/bin)', 'Throughput (tasks/second)'], throughput)

if __name__ == '__main__':
    main()
