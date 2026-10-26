import argparse
import time
import json
import os
import re

from src.prompts import PROMPTS
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
                        choices=PROMPTS.keys())
    parser.add_argument("--output_file_path", type=str,
                        default="data/processed")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--strategy", type=str,
                        default="direct", choices=STRATEGIES.keys())
    parser.add_argument("--self_debug_max_tries", type=positive_int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--runs", type=positive_int, default=1)

    args = parser.parse_args()

    output_file = os.path.join(
        args.output_file_path, f"{args.task}_{re.sub(r'[-:]', '_', args.model)}_{args.strategy}.jsonl")

    prompt = PROMPTS[args.task]

    for run_id in range(1, args.runs+1):
      monitor = GPUMonitor()
      monitor.start()
      print(f"run n.{run_id}")
      generation_result = STRATEGIES[args.strategy](prompt=prompt, args=args)
      gpu_info = monitor.stop()

      eval_result = evaluate_json_parser(solution_code=generation_result['code'])

      record = {
          "timestamp": time.strftime("%Y-%m-%d %H-%M-%S"),
          "model": args.model,
          "strategy": args.strategy,
          "run": run_id,
          "temperature": args.temperature,
          "accuracy": eval_result['passed']/eval_result['total'] if eval_result['total'] > 0 else 0,
          "passed": eval_result['passed'],
          "total": eval_result['total'],
          "passed_y": eval_result['passed_y'],
          "passed_n": eval_result['passed_n'],
          "is_correct": eval_result['is_correct'],
          "prompt_tokens": generation_result['prompt_tokens'],
          "output_tokens": generation_result['output_tokens'],
          "inference_time": generation_result['time'],
          "peak_vram_mb": gpu_info['peak_vram_mb'],
          **({"max_tries": args.self_debug_max_tries} if args.strategy == "self_debug" else {}),
          "seed": args.seed,
          "prompt": prompt,
          "solution": generation_result['code'],
          "first_error": eval_result['first_error']
      }

      output_path = os.path.dirname(output_file)
      if not os.path.exists(output_path):
          os.makedirs(output_path)

      with open(output_file, 'a') as f:
          f.write(json.dumps(record)+'\n')

      print(f"accuracy: {eval_result['passed']/eval_result['total'] if eval_result['total']>0 else 0}\n")
      print(f"passed: {eval_result['passed']}\n")
      print(f"total: {eval_result['total']}\n")
      print(f"output tokens: {generation_result['output_tokens']}\n")
      print(f"inference time: {generation_result['time']}\n")
      print(f"peak vram (MB): {gpu_info['peak_vram_mb']}\n")
      print(f"first error: {eval_result['first_error']}\n")

      args.seed += 1


if __name__ == "__main__":
    main()
