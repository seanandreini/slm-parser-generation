import glob, os, subprocess, random

def evaluate_json_parser(
    solution_code, test_dir="data/benchmarks/JSONTestSuite/test_parsing", entry_point="parse_json", timeout=2.0, stop_on_error=False, subset=False):
  y_files = sorted(glob.glob(os.path.join(test_dir, "y_*.json")))
  n_files = sorted(glob.glob(os.path.join(test_dir, "n_*.json")))

  passed_y = 0
  passed_n = 0
  total = len(y_files) + len(n_files)
  first_error = None
  sign = []

  if subset:
    rng = random.Random(0)
    y_files = rng.sample(y_files, max(1, len(y_files) // 10))
    n_files = rng.sample(n_files, max(1, len(n_files) // 10))

  print("evaluating y files...")
  for file in y_files:
    filename = os.path.basename(file)
    with open(file, "rb") as f:
      raw = f.read()
      script = f"{solution_code}\n\n{entry_point}({repr(raw.decode('utf-8', errors='ignore'))})"

    try:
      result = subprocess.run(['python3', '-'], input=script, text=True, capture_output=True, timeout=timeout)
      if result.returncode == 0:
        passed_y += 1
        sign.append("pass")
      else:
        sign.append("fail")
        if not first_error:
          first_error = f"Failed on valid JSON '{filename}': {result.stderr.strip()}"
          if stop_on_error:
            break

    except subprocess.TimeoutExpired:
      sign.append("timeout")
      if not first_error:
        first_error = f"Timeout on '{filename}'"
        if stop_on_error:
          break

  if not stop_on_error or not first_error:
    print("evaluating n files...")
    for file in n_files:
      filename = os.path.basename(file)
      with open(file, "rb") as f:
        raw = f.read()
        text = raw.decode('utf-8', errors='replace')
        script = (
            f"{solution_code}\n\n"
            f"try:\n"
            f"    {entry_point}({repr(text)})\n"
            f"except Exception:\n"
            f"    raise SystemExit(0)\n"
            f"raise SystemExit(3)\n"
        )

      try:
        result = subprocess.run(['python3', '-'], input=script, text=True, capture_output=True, timeout=timeout)
        if result.returncode == 0:
          sign.append("pass")
          passed_n += 1
        else:
          sign.append("fail")
          if not first_error:
            if result.returncode == 3:
              first_error = f"Accepted on invalid JSON '{filename}': {result.stderr.strip()}"
            else:
              first_error = f"Code crashed on '{filename}': {result.stderr.strip()}"
            if stop_on_error: 
              break

      except subprocess.TimeoutExpired:
        sign.append("timeout")
        pass

  return {
    "passed": passed_y + passed_n,
    "total": total,
    "passed_y": passed_y,
    "passed_n": passed_n,
    "is_correct": total == passed_y + passed_n,
    "sign": sign,
    "first_error": first_error
  }