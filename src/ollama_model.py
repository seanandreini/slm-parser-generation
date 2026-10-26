import requests
import re

from src.evaluators import evaluate_json_parser
from src.prompts import PROMPTS

OLLAMA_URL = "http://host.docker.internal:11434/api/generate"


def clean_code(code):
    regex = r"```python\n(.*?)\n```"
    match = re.search(regex, code, re.DOTALL)
    return match.group(1).strip() if match else code.strip()


def generate_solution_pass1(prompt, args):
    payload = {
        "model": args.model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 2048,
            "temperature": args.temperature,
            "seed": args.seed
        }
    }

    print("generating...")
    response = requests.post(OLLAMA_URL, json=payload).json()
    print("response generated.")
    code = clean_code(response.get("response", ""))

    requests.post(OLLAMA_URL, json={"model": args.model, "keep_alive": 0})
    return {
        "code": code,
        "prompt_tokens": response.get("prompt_eval_count", 0),
        "output_tokens": response.get("eval_count", 0),
        "time": response.get("eval_duration", 0) / 1e9
    }


def generate_self_debug(prompt, args):
    i = 0
    prompt_tokens = 0
    output_tokens = 0
    total_time = 0.0
    while (True):
        payload = {
            "model": args.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 2048,
                "temperature": args.temperature,
                "seed": args.seed
            }
        }

        print("generating...")
        response = requests.post(OLLAMA_URL, json=payload).json()
        print("response generated.")
        code = clean_code(response.get("response", ""))

        prompt_tokens += response.get("prompt_eval_count", 0)
        output_tokens += response.get("eval_count", 0)
        total_time += response.get("eval_duration", 0) / 1e9

        result = evaluate_json_parser(solution_code=code, stop_on_error=True)
        if (result['is_correct']):
            break
        
        i += 1
        if i > args.self_debug_max_tries:
            break
        print(f"the code failed. try n.{i}.")
        prompt = PROMPTS['self_debug'].format(
            previous_code=code, 
            error_message=result.get('first_error'))

    requests.post(OLLAMA_URL, json={"model": args.model, "keep_alive": 0})
    
    return {
        "code": code,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "time": total_time
    }


STRATEGIES = {
    "direct": generate_solution_pass1,
    "self_debug": generate_self_debug
}
