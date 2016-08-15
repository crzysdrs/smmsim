#/bin/bash

SMM_SIM=`which smmsim`
SMM_BENCH=`which smmbench`
WORKLOAD=`which smmgenwork`
RANDWORKLOAD=`which smmrandwork`
SMM_VALID=`which smmvalidate`

COV_RUN="coverage run --parallel-mode --include=*/SMM/* --omit=*__init__*"

if [[ ( ! -e "$SMM_SIM" ) || ( ! -e "$SMM_BENCH" ) || ( ! -e "$WORKLOAD" ) || ( ! -e "$RANDWORKLOAD" ) || (! -e "$SMM_VALID") ]]; then
    echo "Missing one or more tools. Did you install the tool?"
    echo "./setup.py develop --user"
    exit 1
fi

if [[ ! -z "$1" ]]; then
    VERBOSE="--verbose"
fi

coverage erase

function run_sim {
    $COV_RUN $WORKLOAD $1 /dev/stdout | $COV_RUN $SMM_VALID | $COV_RUN $SMM_SIM $2 $VERBOSE /dev/stdin || exit 1
}

function run_sim2 {
    $COV_RUN $WORKLOAD $1 tmp.workload || exit 1
    cat tmp.workload | $COV_RUN $SMM_SIM  --validate $VERBOSE $2 /dev/stdin || exit 1
}

function run_sim3 {
    $COV_RUN $WORKLOAD $1 tmp.workload --validate || exit 1
    $COV_RUN $SMM_SIM $2 --validate $VERBOSE tmp.workload || exit 1
}

function run_rand {
    $COV_RUN $RANDWORKLOAD $1 tmp.workload --validate || exit 1
    $COV_RUN $SMM_SIM $2 --validate $VERBOSE tmp.workload || exit 1
}

run_sim "10 --task_granularity 20 --bin_size 60 --smm_overhead 30"  ""

run_sim "10 --cpus 4" ""

run_sim "10 --binpacker LeastRecentBin" ""

run_sim "10 --binpacker PriorityKnapsackBin" ""

run_sim "10 --binpacker CostKnapsackBin"  ""

run_sim "10 --binpacker LPBinPack"  ""

run_sim2 "10 --binpacker RandomBin" ""

run_rand "10 0.90" ""

run_sim "10 --binpacker RandomBin" "--sqllog random.db"

$COV_RUN $SMM_BENCH random.db || exit 1

run_sim "10 --binpacker AgingBin" "--sqllog aged.db"

$COV_RUN $SMM_BENCH aged.db || exit 1

coverage combine
coverage report
