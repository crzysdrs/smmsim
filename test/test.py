#!/usr/bin/env python3

import subprocess as sp
from SMM import scheduler
import os

def main():
    binpackers = scheduler.getBinPackers()
    sim_time = 10
    check_count = 100
    if not os.path.exists("results"):
        os.mkdir("results")

    sp.call(
        [
            "smmrandwork",
            str(sim_time),
            str(check_count),
            "results/sim.workload",
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
                str(check_count),
                "results/{bp}.prelude".format(bp=b)
            ]
        )


    for b in binpackers.keys():
        os.system("cat results/{bp}.prelude results/sim.workload | smmsim /dev/stdin --sqllog results/{bp}.log".format(bp=b))
        sp.call(
            [
                "smmbench",
                "results/{bp}.log".format(bp=b)
            ]
        )

if __name__ == '__main__':
    main()
