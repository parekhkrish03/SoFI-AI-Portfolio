# SoFI AI Portfolio (Local)

## Prereqs
- Python 3.10+

## Install

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Required environment variables

### PowerShell

```powershell
$env:AC_API_KEY="YOUR_API_KEY_HERE"   # required for /server/* endpoints
$env:OPENAI_API_KEY="YOUR_OPENAI_KEY_HERE"  # only required for main.py agent
```

### cmd.exe

```bat
set AC_API_KEY=YOUR_API_KEY_HERE
set OPENAI_API_KEY=YOUR_OPENAI_KEY_HERE
```

## Run

Finance metrics (DSI/DSO/DPO/CCC):

```bat
python custom_finance_tool.py RELIANCE.NS
```

Agent REPL (tools):

```bat
python main.py
```

Try in REPL:
- `Analyze business health for RELIANCE.NS`
- `Analyze company snapshot for RELIANCE.NS`
- `Analyze inventory levels for RELIANCE.NS using the API`
