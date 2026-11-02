import requests, re, time, os
from openai import OpenAI

from src.evaluators import evaluate_json_parser
from src.prompts import PROMPTS

OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
_groq_client = None
def get_groq_client():
    global _groq_client
    if _groq_client is None:
        _groq_client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ["GROQ_API_KEY"],
            max_retries=5
        )
    return _groq_client

def call_model(prompt, config, temperature=None, seed=None):
    temperature = temperature if temperature else config.temperature
    seed = seed if seed else config.seed
    
    if "openai" in config.model:
        start_time = time.time()
        response = get_groq_client().chat.completions.create(
            model=config.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_completion_tokens=2048,
            seed=seed
        )
        inference_time = time.time()-start_time
        return {
            "response": response.choices[0].message.content or "",
            "prompt_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "inference_time": inference_time
        }

    payload = {
        "model": config.model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": config.max_tokens,
            "temperature": config.temperature,
            "seed": config.seed
        }
    }
    response = requests.post(OLLAMA_URL, json=payload).json()
    return {
        "response": response.get("response", ""),
        "prompt_tokens": response.get("prompt_eval_count", 0),
        "output_tokens": response.get("eval_count", 0),
        "inference_time": response.get("eval_duration", 0) / 1e9
    }

def clean_code(code):
    regex = r"```python\n(.*?)\n```"
    match = re.search(regex, code, re.DOTALL)
    return match.group(1).strip() if match else code.strip()


def generate_solution_pass1(prompt, config):
    start_time = time.time()
    

    print("generating...")
    response = call_model(prompt, config)
    print("response generated.")
    code = clean_code(response["response"])

    total_time = time.time()-start_time
    if "openai" not in config.model:
        requests.post(OLLAMA_URL, json={"model": config.model, "keep_alive": 0})
    return {
        "code": code,
        "prompt_tokens": response["prompt_tokens"],
        "output_tokens": response["output_tokens"],
        "inference_time": response["inference_time"],
        "total_time": total_time
    }, []

def generate_self_debug(original_prompt, config):
    start_time = time.time()
    i = 0
    trace = []
    prompt_tokens = 0
    output_tokens = 0
    inference_time = 0.0
    prompt = original_prompt
    while (True):
        print("generating...")
        response = call_model(prompt, config)
        print("response generated.")
        code = clean_code(response["response"])

        prompt_tokens += response["prompt_tokens"]
        output_tokens += response["output_tokens"]
        inference_time += response["inference_time"]

        i += 1
        result = evaluate_json_parser(solution_code=code, stop_on_error=True)

        trace.append({
            "iteration": i,
            "code": code,
            "passed": result['passed'],
            "total": result['total']
        })
        if i >= config.max_tries:
            break
        if (result['is_correct']):
            break
        print(f"the code failed. try n.{i}.")
        prompt = PROMPTS['self_debug'].format(
            original_prompt=original_prompt,
            code=code, 
            error_message=result.get('first_error'))

    total_time = time.time()-start_time
    if "openai" not in config.model:
        requests.post(OLLAMA_URL, json={"model": config.model, "keep_alive": 0})
    return {
        "code": code,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "inference_time": inference_time,
        "total_time": total_time
    }, trace

def generate_solver_verifier_judge(original_prompt, config):
    start_time = time.time()
    prompt_tokens = 0
    output_tokens = 0
    inference_time = 0.0
    i = 0
    solver_prompt = original_prompt
    trace = []

    while(True):
      print(f"iteration {i+1}")
      print("solver is generating...")
      solver_response = call_model(solver_prompt, config)
      print("solver generated a solution.")
      code = clean_code(solver_response["response"])

      prompt_tokens += solver_response["prompt_tokens"]
      output_tokens += solver_response["output_tokens"]
      inference_time += solver_response["inference_time"]

      verifier_prompt = PROMPTS['verifier'].format(
          original_prompt = original_prompt,
          code = code
      )
      print("verifier is generating...")
      verifier_response = call_model(verifier_prompt, config)
      print("verifier generated a response.")

      prompt_tokens += verifier_response["prompt_tokens"]
      output_tokens += verifier_response["output_tokens"]
      inference_time += verifier_response["inference_time"]

      verifier_output = verifier_response["response"]

      judge_prompt = PROMPTS['judge'].format(
          original_prompt = original_prompt,
          code = code,
          review = verifier_output
      )
      print("judge is generating...")
      judge_response = call_model(judge_prompt, config)
      print("judge generated a response.")

      prompt_tokens += judge_response["prompt_tokens"]
      output_tokens += judge_response["output_tokens"]
      inference_time += judge_response["inference_time"]

      judge_output = judge_response["response"]

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
          original_prompt = original_prompt,
          code = code,
          feedback = judge_output
      )

    total_time = time.time()-start_time
    if "openai" not in config.model:
        requests.post(OLLAMA_URL, json={"model": config.model, "keep_alive": 0})
    return {
        "code": code,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "inference_time": inference_time,
        "total_time": total_time
    }, trace

def generate_society_of_minds(original_prompt, config):
    start_time = time.time()
    i = 0
    prompt_tokens = 0
    output_tokens = 0
    inference_time = 0.0
    trace = []
    agent_prompts = [original_prompt] * config.n_agents

    while(True):
      solutions = []
      for agent, agent_prompt in enumerate(agent_prompts):
          print(f"agent {agent+1} is generating...")
          response = call_model(agent_prompt, config, config.initial_temperature if i == 0 else config.temperature, config.seed * 1000 + agent)
          print(f"agent {agent+1} generated.")
          solutions.append(clean_code(response["response"]))

          prompt_tokens += response["prompt_tokens"]
          output_tokens += response["output_tokens"]
          inference_time += response["inference_time"]

      signs = []
      for solution in solutions:
          result = evaluate_json_parser(solution_code=solution, subset=True)
          signs.append(result['sign'])

      consensus = len(set(tuple(s) for s in signs)) == 1
      trace.append({
          "round": i,
          "prompts": agent_prompts,
          "solutions": solutions,
          "signs": signs,
          "consensus": consensus
      })

      if consensus:
          print("consensus")
          break

      i += 1
      if i >= config.max_tries:
          print("max tries")
          break

      print("regenerating")

      agent_prompts = [
          PROMPTS['som_agent'].format(
              original_prompt=original_prompt,
              code=solutions[agent],
              others="\n\n".join(
                  f"### Solution from agent {j + 1}\n{code}"
                  for j, code in enumerate(solutions) if j != agent
              ),
          )
          for agent in range(config.n_agents)
      ]


    chosen_agent = max(range(len(signs)), key=lambda i: signs.count(signs[i]))
    trace.append({
        "stop_reason": "max_tries" if i==config.max_tries else "consensus",
        "chosen_agent": chosen_agent+1
    })
    total_time = time.time()-start_time

    if "openai" not in config.model:
        requests.post(OLLAMA_URL, json={"model": config.model, "keep_alive": 0})
    return {
        "code": solutions[chosen_agent],
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "inference_time": inference_time,
        "total_time": total_time
    }, trace
      



    
    



STRATEGIES = {
    "direct": generate_solution_pass1,
    "self_debug": generate_self_debug,
    "solver_verifier_judge": generate_solver_verifier_judge,
    "society_of_minds": generate_society_of_minds
}
