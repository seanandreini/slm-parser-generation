# SLM Parser Generation

Benchmark for evaluating how well **Small Language Models (SLMs)** can write a parser from scratch, and whether different **inference strategies** improve the result compared with a single direct prompt.

The current task asks the model to write, in Python, a JSON parser compliant with **RFC 8259** (`parse_json(json_str)`) without using `json`, `eval` or other standard libraries or functions. Each generated parser is then run against the [JSONTestSuite](https://github.com/nst/JSONTestSuite) test suite.

## How it works

1. The model receives the task prompt (`src/prompts.py`) and returns Python code.
2. The code is extracted from the ```` ```python ```` block and executed in a separate `python` process against every test file:
   - `y_*.json` (valid JSON): the parser must **accept**;
   - `n_*.json` (invalid JSON): the parser **must** raise an exception.
   - `i_*.json` (implementation-defined) are ignored.
   Each test has a 1 s timeout.
3. One JSONL record per run is written to `data/processed/`, containing accuracy, tokens, timings, peak VRAM, the generated code and the full trace of intermediate steps.

### Prompting strategies

| Strategy | Description |
|---|---|
| `direct` | Generation with a single prompt. |
| `self_debug` | The code is tested. If it fails, the model receives the first error encountered and fixes the code (up to `--max_tries`, default 3). |
| `solver_verifier_judge` | Three roles played by the same model: the *solver* writes the code, the *verifier* reports bugs with concrete inputs, the *judge* confirms or rejects them and decides `accept` / `reject`. If the judge rejects the solver fixes the code. |
| `society_of_minds` | `--n_agents` agents (default 3) generate independent solutions. If their their results are different, each agent sees the others' solutions and revises its own. Stops on consensus or after `--max_tries` iterations. The majority solution is chosen. |

### Models tested

Local, via [Ollama](https://ollama.com): `qwen2.5-coder:1.5b`, `qwen2.5-coder:3b`, `qwen2.5-coder:7b`, `qwen2.5:3b`, `qwen2.5:7b`, `granite-code:3b`, `granite-code:8b`.
LLM reference, via the [Groq](https://groq.com) API: `openai/gpt-oss-120b`.

## Repository structure

```
├── main.py                 # entry point: generation + evaluation + saving results
├── run_everything.sh       # runs every model × strategy combination
├── configs/config.yaml     # Ollama URL and context window
├── src/
│   ├── prompts.py          # task and strategy prompts
│   ├── ollama_model.py     # model calls and strategy implementations
│   ├── evaluators.py       # parser evaluation on JSONTestSuite
│   └── monitor.py          # peak GPU VRAM sampling with PYNVML
├── scripts/code_metrics.py # code metrics for generated parsers with radon
├── data/processed/         # experiment results (.jsonl)
└── .devcontainer/          # Python 3.11 dev container with GPU access
```

## Requirements

- Python 3.11
- [Ollama](https://ollama.com) running, with the models to test already pulled (`ollama pull qwen2.5-coder:3b`, …)
- An NVIDIA GPU for VRAM usage tracking
- Optional: a `GROQ_API_KEY` environment variable to run `openai/gpt-oss-120b` for running the LLM

## Setup

```bash
git clone https://github.com/seanandreini/slm-parser-generation
cd slm-parser-generation
pip install -r requirements.txt

# test suite (not included in the repository)
git clone https://github.com/nst/JSONTestSuite data/benchmarks/JSONTestSuite
```



### Recommended for Windows: Dev Container on WSL2
 
The experiments were run inside the dev container in `.devcontainer/`.
 
1. Install WSL2, Docker (Docker Desktop with the WSL2 backend), VSCode with the **WSL** and **Dev Containers** extensions, and the NVIDIA driver on Windows.
2. Start Ollama on the host and pull the models.
3. If you want to use Groq, set `GROQ_API_KEY` in your WSL shell, e.g. in `~/.bashrc`. The container reads it from the environment VSCode is launched from.
4. Clone the repo inside the WSL filesystem, then run `code .` from WSL and choose **Reopen in Container**. The container runs `pip install -r requirements.txt` on creation.
5. Inside the container, clone JSONTestSuite as shown above.
By default `configs/config.yaml` points to `http://host.docker.internal:11434`. Without the container, change it to `http://localhost:11434/api/generate`.

## Usage

Single run:

```bash
python main.py --model qwen2.5-coder:7b --strategy self_debug --runs 10
```

Main options:

| Option | Default | Description |
|---|---|---|
| `--model` | `qwen2.5-coder:3b` | Ollama model name (or `openai/gpt-oss-120b` for Groq) |
| `--strategy` | `direct` | `direct`, `self_debug`, `solver_verifier_judge`, `society_of_minds` |
| `--runs` | `1` | number of runs (the seed is incremented on each run) |
| `--temperature` | `0.2` | sampling temperature |
| `--initial_temperature` | `0.7` | first-round temperature for `society_of_minds` |
| `--max_tries` | `3` | max iterations for the strategies with iterations |
| `--n_agents` | `3` | agents for `society_of_minds` |
| `--max_tokens` | `8192` | max tokens per generation |
| `--seed` | `42` | initial seed |
| `--output_file_path` | `data/processed` | output folder |

To run multiple experiments (every model × every strategy, 10 runs each):

```bash
# everything:
bash run_everything.sh

# one model, all strategies:
bash run_everything.sh "<model>"

# specific combinations:
bash run_everything.sh "<model1> <model2>" "<strategy1> <strategy2>"
```

Code metrics (cyclomatic complexity, LLOC/SLOC, maintainability index) for the generated parsers:

```bash
python scripts/code_metrics.py data/processed/<task>_<model>_<strategy>.jsonl
```

## Output format

Each file `data/processed/<task>_<model>_<strategy>.jsonl` has one line per run with:

- `accuracy`, `passed`, `total`, `passed_y`, `passed_n`, `is_correct`
- `prompt_tokens`, `eval_tokens`, `inference_time`, `total_generation_time`, `evaluation_time`
- `peak_vram_mb`
- `solution`: the final generated code
- `first_error`: the first failure encountered
- `trace`: intermediate steps of the strategy (empty for Direct)

## Results
 
Full results and discussion are in the thesis (see [Thesis](https://github.com/seanandreini/slm-parser-generation/releases/latest/download/thesis.pdf)).
 
### Metric
 
The main metric is the **honest balanced accuracy** (Honest BA):
 
- **balanced accuracy**: `BA = (passed_y / total_y + passed_n / total_n) / 2`, because JSONTestSuite has 95 valid and 188 invalid files, so a parser that rejects everything already gets 66.4% raw accuracy;
- **honest**: runs that don't follow the task constraints (importing `json` or `ast`, or calling `eval`, `exec` or `json.loads`, detected via the AST) are scored 0.
The `accuracy` field in the `.jsonl` files is the raw accuracy (`passed / total`).
 
### Mean honest balanced accuracy
 
| Model | Direct | Self-Debug | SVJ | SoM |
|---|---|---|---|---|
| qwen2.5-coder:1.5b | 0.269 ± 0.286 | 0.269 ± 0.286 | 0.269 ± 0.286 | 0.329 ± 0.289 |
| qwen2.5-coder:3b | 0.637 ± 0.143 | 0.621 ± 0.130 | 0.628 ± 0.154 | 0.522 ± 0.205 |
| qwen2.5-coder:7b | **0.746 ± 0.089** | 0.700 ± 0.094 | **0.746 ± 0.089** | 0.745 ± 0.089 |
| qwen2.5:3b | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.050 ± 0.158 | 0.000 ± 0.000 |
| qwen2.5:7b | 0.499 ± 0.193 | 0.527 ± 0.199 | 0.498 ± 0.188 | 0.516 ± 0.044 |
| granite-code:3b | 0.148 ± 0.238 | 0.147 ± 0.236 | 0.146 ± 0.236 | 0.270 ± 0.290 |
| granite-code:8b | 0.107 ± 0.226 | 0.107 ± 0.226 | 0.107 ± 0.226 | 0.158 ± 0.255 |
| *gpt-oss-120b (LLM)* | *0.994 ± 0.006* | *0.900 ± 0.316* | *0.630 ± 0.458* | *0.688 ± 0.475* |
 
SVJ = Solver-Verifier-Judge, SoM = Society of Minds.
 
### Cost relative to Direct (mean over the SLMs)
 
| Strategy | Generated tokens | Inference time | Peak VRAM |
|---|---|---|---|
| Self-Debug | 2.25× | 2.15× | 1.00× |
| SVJ | 3.20× | 2.91× | 1.00× |
| SoM | 4.34× | 4.28× | 1.00× |
 
### Key findings
 
- **SLMs vs. LLM:** the best SLM (`qwen2.5-coder:7b`, Direct) reaches 0.746 honest BA, against 0.994 for `gpt-oss-120b`.
- **Strategies:** they cost 2 to 4 times the Direct in tokens and time but do not improve accuracy. Society of Minds helps only the weakest models a little.
- **Constraint violations:** 80 of 320 runs use forbidden calls (`json`, `eval`, …), mostly from `qwen2.5:3b` and the `granite-code` models. Without penalising them, scores would be inflated: `qwen2.5:3b` gets 0.974 BA on violating runs and 0.500 on compliant ones. Self-Debug is the strategy that most often introduces new violations.
- **Code metrics:** cyclomatic complexity, LLOC and maintainability index do not reflect parser correctness.
## Thesis
> Sean Andreini, *Small Language Models for Code Generation: Evaluating Inference Strategies for Automated Parser Function Generation*, Bachelor's Thesis, Corso di Laurea in Informatica, Università degli Studi di Firenze, Academic Year 2025-2026.
> Supervisor: Prof. Fabio Pinelli. Co-supervisors: Prof. Simone Soderi, Prof. Letterio Galletta.
