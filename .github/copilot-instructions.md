## Purpose
Help an AI coding agent become productive quickly in this repository by describing the project's architecture, conventions, integration points, and common edit locations.

## Big Picture
- **What:** Small Python toolkit that wires data-processing "tools" into a reactive agent (LLM + tools).
- **Major components:**
  - `main.py`: Agent bootstrap (creates LLM, registers tools, runs a REPL loop).
  - `inventorylevel.py`: Example domain tool — computes inventory metrics. Decorated with `@tool` and returns a text summary.
  - `custom_finance_tool.py`: Tool that fetches financial data from a remote API, maps JSON keys, computes financial ratios, and produces a report.

## Patterns & Conventions (project-specific)
- Tools are plain functions decorated with `@tool` from `langchain.tools`. They accept primitives (str/float) and return a `str` summary (see `analyze_inventory_levels` and `analyze_business_health_custom`).
- Keep I/O separated into layers inside each tool:
  1. Input layer — fetch or receive raw values (e.g., `fetch_from_vercel` in `custom_finance_tool.py`).
  2. Translation (mapping) — map API JSON keys to local variable names (`data.get('revenue')`, etc.).
  3. Logic — calculations (DSI/DSO/DPO/CCC, turnover ratios).
  4. Presentation — format a human-readable text report to return.
- Tools should perform minimal printing and return structured text; the agent handles orchestration and streaming.

## Key Integration Points
- LLM + agent initialization in `main.py`: uses `ChatOpenAI` (from `langchain_openai`) and `create_react_agent` (from `langgraph.prebuilt`). Keep `tools = [ ... ]` in sync with imported tool functions.
- External dependencies the code expects (install these in the environment): `langchain`, `langchain_openai`, `langgraph`, `langchain_core`, and `requests`.
- API endpoint and keys:
  - `custom_finance_tool.py` sets `BASE_URL` and constructs `endpoint = f"{BASE_URL}/stock/{ticker}"`. Verify this matches your deployed API.
  - `main.py` contains placeholder OpenAI API key values — do NOT commit real secrets. Use environment variables instead.

## Common Edit Locations (examples)
- If the custom API returns different JSON keys, edit the mapping block in `custom_finance_tool.py` (between the comment "MAP DATA (The Translation Layer)" and the try/except). Example keys to confirm: `revenue`, `costOfGoodsSold`, `inventory`, `accountsReceivable`, `accountsPayable`, `orderBook`.
- To add a new tool:
  1. Create `mytool.py` with a function decorated `@tool` that accepts primitives and returns `str`.
  2. Import the function in `main.py` and add it to `tools` list.
  3. Restart the REPL to register the tool.

## Run / Debug (Windows `cmd.exe`)
- Create a virtualenv and install deps (example):

```bat
python -m venv .venv
.venv\Scripts\activate
pip install langchain langchain_openai langgraph requests
```

- Set OpenAI key in the current cmd session and run the agent:

```bat
set OPENAI_API_KEY=sk-REPLACE_WITH_YOUR_KEY
python main.py
```

## Safety & Secrets
- Never paste long-lived API keys into files. Use `set` (Windows) or environment variables in your runtime.
- The repo currently contains placeholder keys and incorrectly-formatted strings in `main.py` — replace them with an environment-driven config.

## Short Examples (copyable edits)
- Map API keys (in `custom_finance_tool.py`):

```py
# Replace these with the exact keys returned by your API
revenue = float(data.get('revenue', 0))
cogs = float(data.get('costOfGoodsSold', 0))
```

- Add a tool to `main.py`:

```py
from my_new_tool import my_tool_function
tools = [analyze_inventory_levels, my_tool_function]
```

## What to ask the repo maintainers
- Confirm the real API paths and an example JSON response for `BASE_URL` endpoints.
- Preferred dependency pinning (requirements.txt / pyproject.toml) for reproducible runs.

---
If any section is unclear or you want this file to include additional examples (unit test patterns, CI commands, or a `requirements.txt`), tell me which area to expand. 
