#!/bin/bash
# usage: run_everything.sh "models" "strategies"
MODELS=${1:-"qwen2.5-coder:1.5b qwen2.5-coder:3b qwen2.5-coder:7b qwen2.5:3b qwen2.5:7b granite-code:3b granite-code:8b"}
STRATEGIES=${2:-"direct self_debug solver_verifier_judge society_of_minds"}
for model in $MODELS; do
  for strategy in $STRATEGIES; do
    echo "$(date +%H:%M:%S) $model $strategy" >> progress.log
    python main.py --model "$model" --runs 10 --strategy "$strategy"
  done
  ollama stop "$model"
done
