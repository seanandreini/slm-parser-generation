import requests, re, time

from src.evaluators import evaluate_json_parser
from src.prompts import PROMPTS

OLLAMA_URL = "http://host.docker.internal:11434/api/generate"

def clean_code(code):
    regex = r"```python\n(.*?)\n```"
    match = re.search(regex, code, re.DOTALL)
    return match.group(1).strip() if match else code.strip()

def generate_solution_pass1(prompt, config):
    start_time = time.time()
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

    total_time = time.time()-start_time
    requests.post(OLLAMA_URL, json={"model": config.model, "keep_alive": 0})
    return {
        "code": code,
        "prompt_tokens": response.get("prompt_eval_count", 0),
        "output_tokens": response.get("eval_count", 0),
        "inference_time": response.get("eval_duration", 0) / 1e9,
        "total_time": total_time
    }, []

def generate_self_debug(prompt, config):
    start_time = time.time()
    i = 0
    trace = []
    prompt_tokens = 0
    output_tokens = 0
    inference_time = 0.0
    payload = {
        "model": config.model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 2048,
            "temperature": config.temperature,
            "seed": config.seed,
            "repeat_penalty": 1.1
        }
    }
    while (True):

        print("generating...")
        response = requests.post(OLLAMA_URL, json=payload).json()
        print("response generated.")
        code = clean_code(response.get("response", ""))

        prompt_tokens += response.get("prompt_eval_count", 0)
        output_tokens += response.get("eval_count", 0)
        inference_time += response.get("eval_duration", 0) / 1e9


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
        payload['prompt'] = PROMPTS['self_debug'].format(
            original_prompt=prompt,
            code=code, 
            error_message=result.get('first_error'))

    total_time = time.time()-start_time
    requests.post(OLLAMA_URL, json={"model": config.model, "keep_alive": 0})
    return {
        "code": code,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "inference_time": inference_time,
        "total_time": total_time
    }, trace

def generate_solver_verifier_judge(prompt, config):
    start_time = time.time()
    prompt_tokens = 0
    output_tokens = 0
    inference_time = 0.0
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
      inference_time += solver_response.get("eval_duration", 0) / 1e9

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
      inference_time += verifier_response.get("eval_duration", 0) / 1e9

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
      inference_time += judge_response.get("eval_duration", 0) / 1e9

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
          code = code,
          feedback = judge_output
      )
      payload['prompt'] = solver_prompt


    total_time = time.time()-start_time
    requests.post(OLLAMA_URL, json={"model": config.model, "keep_alive": 0})
    return {
        "code": code,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "inference_time": inference_time,
        "total_time": total_time
    }, trace

def generate_society_of_minds(prompt, config):
    start_time = time.time()
    i = 0
    prompt_tokens = 0
    output_tokens = 0
    inference_time = 0.0
    trace = []
    agent_prompts = [prompt] * config.n_agents
    payload = {
        "model": config.model,
        "stream": False,
        "options": {
            "num_predict": 2048,
            "temperature": config.initial_temperature
        }
    }

    while(True):
      solutions = []
      for agent, agent_prompt in enumerate(agent_prompts):
          payload['options']['seed'] = config.seed * 1000 + agent
          payload['options']['temperature'] = config.initial_temperature if i == 0 else config.temperature
          payload['prompt'] = agent_prompt
          print(f"agent {agent+1} is generating...")
          response = requests.post(OLLAMA_URL, json=payload).json()
          print(f"agent {agent+1} generated.")
          solutions.append(clean_code(response.get("response", "")))

          prompt_tokens += response.get("prompt_eval_count", 0)
          output_tokens += response.get("eval_count", 0)
          inference_time += response.get("eval_duration", 0) / 1e9

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
              original_prompt=prompt,
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
