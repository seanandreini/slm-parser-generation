import argparse, time, json, os, re

from src.prompts import PROMPTS
from src.ollama_model import STRATEGIES
from src.ollama_model import generate_solution_pass1
from src.evaluators import evaluate_json_parser

def main():
  parser = argparse.ArgumentParser(description="SLM parser generation benchmark")
  parser.add_argument("--model", type=str, default="qwen2.5-coder:3b")
  parser.add_argument("--task", type=str, default="json", choices=PROMPTS.keys())
  parser.add_argument("--output_file_path", type=str, default="data/processed")
  parser.add_argument("--strategy", type=str, default="direct", choices=STRATEGIES.keys())

  args = parser.parse_args()

  output_file = os.path.join(args.output_file_path, f"{args.task}_{re.sub(r'[-:]', '_', args.model)}_{args.strategy}.jsonl")

  prompt = PROMPTS[args.task]
  generation_result = STRATEGIES[args.strategy](model_name=args.model, prompt=prompt)
  eval_result = evaluate_json_parser(solution_code=generation_result['code'])

  record = {
    "timestamp": time.strftime("%Y-%m-%d %H-%M-%S"),
    "model": args.model,
    "strategy": args.strategy,
    "prompt": prompt,
    "solution": generation_result['code'],
    "accuracy": eval_result['passed']/eval_result['total'] if eval_result['total']>0 else 0,
    "passed": eval_result['passed'],
    "total": eval_result['total'],
    "is_correct": eval_result['is_correct'],
    "first_error": eval_result['first_error'],
    "prompt_tokens": generation_result['prompt_tokens'],
    "output_tokens": generation_result['output_tokens'],
    "inference_time": generation_result['time']
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
  print(f"first error: {eval_result['first_error']}\n")
  print(f"inference time: {generation_result['time']}\n")

if __name__ == "__main__":
  main()