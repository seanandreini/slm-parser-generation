import argparse
import time
import json
import os
import re, yaml
from types import SimpleNamespace

from src.prompts import MAIN_PROMPTS
from src.ollama_model import STRATEGIES
from src.evaluators import evaluate_json_parser
from src.monitor import GPUMonitor

def positive_int(value):
    ivalue = int(value)
    if(ivalue <= 0):
        raise argparse.ArgumentTypeError(f"{value} is not a positive integer (>0)")
    return ivalue


def main():
    parser = argparse.ArgumentParser(description="SLM parser generation benchmark")
    parser.add_argument("--model", type=str, default="qwen2.5-coder:3b")
    parser.add_argument("--task", type=str, default="json",
                        choices=MAIN_PROMPTS.keys())
    parser.add_argument("--output_file_path", type=str,
                        default="data/processed")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--initial_temperature", type=float, default=None)
    parser.add_argument("--strategy", type=str,
                        default="direct", choices=STRATEGIES.keys())
    parser.add_argument("--max_tokens", type=positive_int, default=8192)
    parser.add_argument("--max_tries", type=positive_int, default=None)
    parser.add_argument("--n_agents", type=positive_int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--runs", type=positive_int, default=1)
    parser.add_argument("--config", type=str, default="configs/config.yaml")

    args = parser.parse_args()

    with open(args.config) as f:
        cfg = yaml.safe_load(f)

    for key, value in vars(args).items():
        if key != "config":
          cfg[key] = value

    config = SimpleNamespace(**cfg)

    if config.strategy in ("self_debug", "solver_verifier_judge", "society_of_minds"):
        config.max_tries = config.max_tries if config.max_tries else 3

    if config.strategy == "society_of_minds":
        config.inital_temperature = config.initial_temperature if config.initial_temperature else 0.7
        config.n_agents = config.n_agents if config.n_agents else 3

    output_file = os.path.join(
        config.output_file_path, f"{config.task}_{re.sub(r'[-:./]', '_', config.model)}_{config.strategy}.jsonl")

    prompt = MAIN_PROMPTS[config.task]

    for run_id in range(1, config.runs+1):
      monitor = GPUMonitor()
      monitor.start()
      print(f"run n.{run_id}")
      generation_result, trace = STRATEGIES[config.strategy](prompt, config)
      gpu_info = monitor.stop()

      start_time = time.time()
      eval_result = evaluate_json_parser(solution_code=generation_result['code'])
      evaluation_time = time.time()-start_time

      record = {
          "timestamp": time.strftime("%Y-%m-%d %H-%M-%S"),
          "model": config.model,
          "strategy": config.strategy,
          "run": run_id,
          "initial_temperature": config.initial_temperature if config.initial_temperature else config.temperature,
          "temperature": config.temperature,
          "accuracy": eval_result['passed']/eval_result['total'] if eval_result['total'] > 0 else 0,
          "passed": eval_result['passed'],
          "total": eval_result['total'],
          "passed_y": eval_result['passed_y'],
          "passed_n": eval_result['passed_n'],
          "is_correct": eval_result['is_correct'],
          "prompt_tokens": generation_result['prompt_tokens'],
          "eval_tokens": generation_result['output_tokens'],
          "max_tokens_per_generation": config.max_tokens,
          "inference_time": generation_result['inference_time'],
          "total_generation_time": generation_result['total_time'],
          "evaluation_time": evaluation_time,
          "peak_vram_mb": gpu_info['peak_vram_mb'] if "openai" not in config.model else None,
          "max_tries": config.max_tries if config.max_tries else 1,
          "seed": config.seed,
          "prompt": prompt,
          "solution": generation_result['code'],
          "first_error": eval_result['first_error'],
          "trace": trace if trace else None
      }

      output_path = os.path.dirname(output_file)
      if not os.path.exists(output_path):
          os.makedirs(output_path)

      with open(output_file, 'a') as f:
          f.write(json.dumps(record)+'\n')

      print(f"accuracy: {eval_result['passed']/eval_result['total'] if eval_result['total']>0 else 0}\n")
      print(f"passed: {eval_result['passed']}\n")
      print(f"total: {eval_result['total']}\n")
      print(f"inference time: {generation_result['inference_time']}\n")
      print(f"total time: {generation_result['total_time']}\n")
      print(f"peak vram (MB): {gpu_info['peak_vram_mb']}\n")

      config.seed += 1


if __name__ == "__main__":
    main()
