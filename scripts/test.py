from evalplus.data import get_human_eval_plus
import requests, json

problems = get_human_eval_plus()

print(f"Number of problems: {len(problems)}")

ollama_url = "http://host.docker.internal:11434/api/generate"

samples = []

for task_id in problems.keys():
  problem = problems[task_id]
  prompt = problem["prompt"]

  payload = {
    "model": "qwen2.5-coder:3b",
    "prompt": prompt,
    "stream": False
  }
  response = requests.post(ollama_url, json=payload).json()
  generated_code = response.get("response", "")

  samples.append({
    "task_id": task_id,
    "solution": generated_code
  })

import os
path = "data/processed/"
if not os.path.exists(path):
  os.makedirs(path)
output_file = f"{path}test_output.jsonl"
with open(output_file, "w") as f:
  for sample in samples:
    f.write(json.dumps(sample) + "\n")
