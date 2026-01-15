import os
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

# --- 1. IMPORT YOUR TOOL ---
# Make sure the file name 'finance_tools' matches what you named your file in Step 1
from inventorylevel import analyze_inventory_levels, analyze_inventory_levels_from_api
from custom_finance_tool import analyze_business_health_custom, analyze_company_snapshot_custom

# --- 2. SETUP THE BRAIN (LLM) ---
# Use an environment variable for secrets. Set `OPENAI_API_KEY` in your shell.
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("Warning: OPENAI_API_KEY is not set. The agent may not run correctly.")

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    api_key=api_key,
)

# --- 3. CONNECT TOOL TO AGENT ---
# We put the tool in a list, just like the diagram shows
tools = [
    analyze_inventory_levels,
    analyze_inventory_levels_from_api,
    analyze_business_health_custom,
    analyze_company_snapshot_custom,
]

# This function wraps the LLM and the Tools together (The Blue Box in your diagram)
agent_executor = create_react_agent(llm, tools)

# --- 4. RUN THE CHAT LOOP ---
print("🤖 AI Inventory Manager is ready!")
print("Try asking (manual): 'COGS is 5000, beginning inventory 1000, ending inventory 1200. Analyze inventory levels.'")
print("Try asking (API): 'Analyze inventory levels for TSLA using the API.'")
print("Tip (India): use exchange suffix like 'RELIANCE.NS' or 'RELIANCE.BO'.")
print("Tip (API Key): set AC_API_KEY for Indian market endpoints.")

while True:
    user_input = input("\nYou: ")
    if user_input.lower() in ["quit", "exit"]:
        break
    
    # This sends your text to the Agent
    events = agent_executor.stream(
        {"messages": [HumanMessage(content=user_input)]},
        stream_mode="values"
    )

    # Print the AI's final answer
    for event in events:
        message = event["messages"][-1]
        if message.type == "ai" and not message.tool_calls:
            print(f"\nAI: {message.content}")