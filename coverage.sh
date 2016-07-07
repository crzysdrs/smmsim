#/bin/bash

coverage run smm_sim 10 || exit 1

coverage run smm_sim 10 --task_granularity 20 --bin_size 60 --smm_overhead 30 || exit 1

coverage run smm_sim 10 --sqllog test.db || exit 1

coverage run smm_sim 10 --binpacker MaxFillBin || exit 1

coverage run smm_sim 10 --binpacker MaxPriorityBin || exit 1

coverage run smm_sim 10 --binpacker RandomBin || exit 1
