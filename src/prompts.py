JSON_PROMPT = """Write a python function called 'parse_json(json_str)' that takes a string 'json_str' and
parses the JSON RFC 8259 without using standard libraries such as 'json' or 'eval'.

Requirements:
1. If 'json_str' is a valid JSON, the function must return the corresponding Python structure (dict, list, str, int, float, bool, None).
2. If 'json_str' contains syntax errors or is malstructured, the function MUST throw an exception (e.g. ValueError or SyntaxError).

Return JUST the Python code inside a ```python block."""

SELF_DEBUG = """The previously generated code failed the test suite.
Here is the code that failed:
```python
{code}
```
Here is the error encountered during execution: {error_message}
Requirements:
The function 'parse_json(json_str)' takes a string 'json_str' and
parses the JSON RFC 8259 without using standard libraries such as 'json' or 'eval'.
1. If 'json_str' is a valid JSON, the function must return the corresponding Python structure (dict, list, str, int, float, bool, None).
2. If 'json_str' contains syntax errors or is malstructured, the function MUST throw an exception (e.g. ValueError or SyntaxError).

Fix the code above and return JUST the Python code inside a ```python block.
"""

VERIFIER_PROMPT = """
Specifications: {original_prompt}
Code: ```python
{code}
```
This function should meet the following requirements:
The function 'parse_json(json_str)' takes a string 'json_str' and
parses the JSON RFC 8259 without using standard libraries such as 'json' or 'eval'.
1. If 'json_str' is a valid JSON, the function must return the corresponding Python structure (dict, list, str, int, float, bool, None).
2. If 'json_str' contains syntax errors or is malstructured, the function MUST throw an exception (e.g. ValueError or SyntaxError).

Report only bugs you can demonstrate with a concrete input. Do not invent issues; if you find none, say so.
For every bug report an input, the expected result, the actual result, and a short fix.
You should NOT return the whole code.
"""

JUDGE_PROMPT = """
Specifications: {original_prompt}
Code: ```python
{code}
```
Review: {review}
You are the final judge. A reviewer has reviewed the code above and reported possible bugs, or it may have said there are no bugs. 
Decide whether the code must be fixed.
Do NOT trust the reviewer blindly. For each reported bug check it against the code and the specifications.
A bug counts only if it goes against the specifications. 
For each confirmed bug write: input, expected output, actual output, and a short fix.
If you cannot trace a concrete input that fails, the bug is NOT confirmed.
If you accept the code, say so. Otherwise, list only 3 confirmed bugs.

Reason first, then end with exactly one of these lines:
DECISION: accept
DECISION: reject
"""

SOLVER_PROMPT = """{original_prompt}
Here is your previous solution:
```python
{code}
```

A reviewer found the following problems:
{feedback}

Fix ONLY the problems listed above. Do not change any behavior that is not
listed, and do not rewrite parts of the code that are already correct.
Return the complete corrected code in a single ```python block, with no explanation.
"""

MAIN_PROMPTS = {
  "json": JSON_PROMPT
}

PROMPTS = {
  "self_debug": SELF_DEBUG,
  "verifier": VERIFIER_PROMPT,
  "judge": JUDGE_PROMPT,
  "solver": SOLVER_PROMPT
}