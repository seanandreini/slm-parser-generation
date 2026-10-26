JSON_PROMPT = """Write a python function called 'parse_json(json_str)' that takes a string 'json_str' and
parses the JSON without using standard libraries such as 'json' or 'eval'.

Requirements:
1. If 'json_str' is a valid JSON, the function must return the corresponding Python structure (dict, list, str, int, float, bool, None).
2. If 'json_str' contains syntax errors or is malstructured, the function MUST throw an exception (e.g. ValueError or SyntaxError).

Return JUST the Python code inside a ```python block."""

SELF_DEBUG = """The previously generated code failed the test suite.
Here is the code that failed:
{previous_code}
Here is the error encountered during execution: {error_message}
Requirements:
The function 'parse_json(json_str)' takes a string 'json_str' and
parses the JSON without using standard libraries such as 'json' or 'eval'.
1. If 'json_str' is a valid JSON, the function must return the corresponding Python structure (dict, list, str, int, float, bool, None).
2. If 'json_str' contains syntax errors or is malstructured, the function MUST throw an exception (e.g. ValueError or SyntaxError).

Fix the code above and return JUST the Python code inside a ```python block.
"""

PROMPTS = {
  "json": JSON_PROMPT,
  "self_debug": SELF_DEBUG
}