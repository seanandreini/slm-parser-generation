import requests, re

OLLAMA_URL = "http://host.docker.internal:11434/api/generate"

def clean_code(code):
    regex = r"```python\n(.*?)\n```"
    match = re.search(regex, code, re.DOTALL)
    return match.group(1).strip() if match else code.strip()

def generate_solution_pass1(model_name, prompt):
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 2048
        }
    }

    print("generating...")
    response = requests.post(OLLAMA_URL, json=payload).json()
    print("response generated.")
    code = clean_code(response.get("response", ""))
    
    return {
      "code": code,
      "prompt_tokens": response.get("prompt_eval_count", 0), 
      "output_tokens": response.get("eval_count", 0), 
      "time": response.get("eval_duration", 0) / 1e9
    }

STRATEGIES = {
    "direct": generate_solution_pass1
}