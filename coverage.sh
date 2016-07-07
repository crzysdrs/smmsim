#/bin/bash

SMM_SIM=./SMM/simulator.py
COV_RUN="coverage run --source=SMM"

coverage erase

$COV_RUN $SMM_SIM 10 || exit 1

$COV_RUN $SMM_SIM 10 --task_granularity 20 --bin_size 60 --smm_overhead 30 || exit 1

$COV_RUN $SMM_SIM 10 --sqllog test.db || exit 1

$COV_RUN $SMM_SIM 10 --binpacker MaxFillBin || exit 1

$COV_RUN $SMM_SIM 10 --binpacker MaxPriorityBin || exit 1

$COV_RUN $SMM_SIM 10 --binpacker RandomBin || exit 1

coverage combine
coverage report
