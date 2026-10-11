import re, json

regex = r"```python\n(.*?)\n```"

outputsamples = []
with open("data/processed/test_output.jsonl", "r") as f:
  for line in f:
    sample = json.loads(line)
    solution = sample['solution']
    match = re.search(regex, solution, re.DOTALL)
    solution = match.group(1) if match else solution
    sample['solution'] = solution
    outputsamples.append(sample)


with open("data/processed/test_output.jsonl", "w") as f:
  for sample in outputsamples:
    f.write(json.dumps(sample)+"\n")