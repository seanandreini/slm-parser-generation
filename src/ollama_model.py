import requests
import re

from src.evaluators import evaluate_json_parser
from src.prompts import PROMPTS

OLLAMA_URL = "http://host.docker.internal:11434/api/generate"


def clean_code(code):
    regex = r"```python\n(.*?)\n```"
    match = re.search(regex, code, re.DOTALL)
    return match.group(1).strip() if match else code.strip()


def generate_solution_pass1(prompt, config):
    payload = {
        "model": config.model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 2048,
            "temperature": config.temperature,
            "seed": config.seed
        }
    }

    print("generating...")
    response = requests.post(OLLAMA_URL, json=payload).json()
    print("response generated.")
    code = clean_code(response.get("response", ""))

    requests.post(OLLAMA_URL, json={"model": config.model, "keep_alive": 0})
    return {
        "code": code,
        "prompt_tokens": response.get("prompt_eval_count", 0),
        "output_tokens": response.get("eval_count", 0),
        "time": response.get("eval_duration", 0) / 1e9
    }, {}


def generate_self_debug(prompt, config):
    i = 0
    trace = []
    prompt_tokens = 0
    output_tokens = 0
    total_time = 0.0
    while (True):
        payload = {
            "model": config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 2048,
                "temperature": config.temperature,
                "seed": config.seed
            }
        }

        print("generating...")
        response = requests.post(OLLAMA_URL, json=payload).json()
        print("response generated.")
        code = clean_code(response.get("response", ""))

        prompt_tokens += response.get("prompt_eval_count", 0)
        output_tokens += response.get("eval_count", 0)
        total_time += response.get("eval_duration", 0) / 1e9


        i += 1
        result = evaluate_json_parser(solution_code=code, stop_on_error=True)

        trace.append({
            "iteration": i,
            "code": code,
            "passed": result['passed'],
            "total": result['total']
        })
        if i > config.max_tries:
            break
        if (result['is_correct']):
            break
        print(f"the code failed. try n.{i}.")
        prompt = PROMPTS['self_debug'].format(
            previous_code=code, 
            error_message=result.get('first_error'))

    requests.post(OLLAMA_URL, json={"model": config.model, "keep_alive": 0})
    
    return {
        "code": code,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "time": total_time
    }, trace

def solver_verifier_judge(prompt, config):
    prompt_tokens = 0
    output_tokens = 0
    total_time = 0.0
    i = 0
    solver_prompt = prompt

    trace = []

    payload = {
        "model": config.model,
        "prompt": solver_prompt,
        "stream": False,
        "options": {
            "num_predict": 2048,
            "temperature": config.temperature,
            "seed": config.seed
        }
    }

    while(True):
      print(f"iteration {i+1}")
      print("solver is generating...")
      solver_response = requests.post(OLLAMA_URL, json=payload).json()
      print("solver generated a solution.")
      code = clean_code(solver_response.get("response", ""))

      prompt_tokens += solver_response.get("prompt_eval_count", 0)
      output_tokens += solver_response.get("eval_count", 0)
      total_time += solver_response.get("eval_duration", 0) / 1e9

      verifier_prompt = PROMPTS['verifier'].format(
          original_prompt = prompt,
          code = code
      )
      payload['prompt'] = verifier_prompt
      print("verifier is generating...")
      verifier_response = requests.post(OLLAMA_URL, json=payload).json()
      print("verifier generated a response.")

      prompt_tokens += verifier_response.get("prompt_eval_count", 0)
      output_tokens += verifier_response.get("eval_count", 0)
      total_time += verifier_response.get("eval_duration", 0) / 1e9

      verifier_output = verifier_response.get("response", "")

      judge_prompt = PROMPTS['judge'].format(
          original_prompt = prompt,
          code = code,
          review = verifier_output
      )
      payload['prompt'] = judge_prompt
      print("judge is generating...")
      judge_response = requests.post(OLLAMA_URL, json=payload).json()
      print("judge generated a response.")

      prompt_tokens += judge_response.get("prompt_eval_count", 0)
      output_tokens += judge_response.get("eval_count", 0)
      total_time += judge_response.get("eval_duration", 0) / 1e9

      judge_output = judge_response.get("response", "")

      i += 1
      trace.append({
          "iteration": i,
          "code": code,
          "verifier_output": verifier_output,
          "judge_output": judge_output
      })

      if i >= config.max_tries or "DECISION: accept" in judge_output:
          break

      solver_prompt = PROMPTS['solver'].format(
          original_prompt = prompt,
          previous_code = code,
          feedback = judge_output
      )
      payload['prompt'] = solver_prompt
          

    return {
        "code": code,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "time": total_time
    }, trace



STRATEGIES = {
    "direct": generate_solution_pass1,
    "self_debug": generate_self_debug,
    "solver_verifier_judge": solver_verifier_judge
}
