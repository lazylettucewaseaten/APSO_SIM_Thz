#!/bin/bash
echo "Evaluating Config A (Static)"
python3 run_single_config.py 0.4 0.6 0.15 0.3 1 > results_A_static.txt
echo "Evaluating Config A (Dynamic)"
python3 run_single_config.py 0.4 0.6 0.15 0.3 3 > results_A_dynamic.txt

echo "Evaluating Config B (Static)"
python3 run_single_config.py 0.3 0.7 0.15 0.3 1 > results_B_static.txt
echo "Evaluating Config B (Dynamic)"
python3 run_single_config.py 0.3 0.7 0.15 0.3 3 > results_B_dynamic.txt

echo "Evaluating Config C (Static)"
python3 run_single_config.py 0.4 0.6 0.15 0.1 1 > results_C_static.txt
echo "Evaluating Config C (Dynamic)"
python3 run_single_config.py 0.4 0.6 0.15 0.1 3 > results_C_dynamic.txt

echo "Evaluating Config D (Static)"
python3 run_single_config.py 0.4 0.6 0.25 0.3 1 > results_D_static.txt
echo "Evaluating Config D (Dynamic)"
python3 run_single_config.py 0.4 0.6 0.25 0.3 3 > results_D_dynamic.txt

echo "Done"
