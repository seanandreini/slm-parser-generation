import glob, os, subprocess

def evaluate_json_parser(
    solution_code, test_dir="data/benchmarks/JSONTestSuite/test_parsing", entry_point="parse_json", timeout=2.0, stop_on_error=False):
  y_files = sorted(glob.glob(os.path.join(test_dir, "y_*.json")))
  n_files = sorted(glob.glob(os.path.join(test_dir, "n_*.json")))

  passed = 0
  total = len(y_files) + len(n_files)
  first_error = None

  print("evaluating y files...")
  for file in y_files:
    filename = os.path.basename(file)
    with open(file, "rb") as f:
      raw = f.read()
      script = f"{solution_code}\n\n{entry_point}({repr(raw.decode('utf-8', errors='ignore'))})"

    try:
      result = subprocess.run(['python3', '-'], input=script, text=True, capture_output=True, timeout=timeout)
      if result.returncode == 0:
        passed += 1
      else:
        if not first_error:
          first_error = f"Failed on valid JSON '{filename}': {result.stderr.strip()}"
          if stop_on_error:
            break

    except subprocess.TimeoutExpired:
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
        script = f"""
        {solution_code}

        try:
          {entry_point}({repr(raw.decode('utf-8', errors='replace'))})
          exit(1)
        except Exception:
          exit(0)
        """

      try:
        result = subprocess.run(['python3', '-'], input=script, text=True, capture_output=True, timeout=timeout)
        if result.returncode == 0:
          passed += 1
        else:
          if not first_error:
            first_error = f"Accepted on invalid JSON '{filename}': {result.stderr.strip()}"
            if stop_on_error: 
              break

      except subprocess.TimeoutExpired:
        pass

  return {
    "passed": passed,
    "total": total,
    "is_correct": total == passed,
    "first_error": first_error
  }