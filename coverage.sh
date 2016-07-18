#/bin/bash

SMM_SIM=./SMM/simulator.py
SMM_BENCH=./SMM/benchmarks.py
WORKLOAD=./SMM/workload.py

COV_RUN="coverage run --parallel-mode --source=SMM"

coverage erase

function run_sim {
    $COV_RUN $WORKLOAD $1 tmp.workload || exit 1
    $COV_RUN $SMM_SIM $2 tmp.workload || exit 1
}

run_sim "10 --task_granularity 20 --bin_size 60 --smm_overhead 30"  ""

run_sim "10 --cpus 4" ""

run_sim "10 --binpacker LeastRecentBin" ""

run_sim "10 --binpacker MaxFillBin" ""

run_sim "10 --binpacker MaxPriorityBin"  ""

run_sim "10 --binpacker RandomBin" "--sqllog random.db"

$COV_RUN $SMM_BENCH random.db || exit 1

coverage combine
coverage report
