import os
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

# --- 1. IMPORT YOUR TOOL ---
# Make sure the file name 'finance_tools' matches what you named your file in Step 1
from inventorylevel import analyze_inventory_levels

# --- 2. SETUP THE BRAIN (LLM) ---
# Replace this with your actual OpenAI API Key
# os.environ["OPENAI_API_KEY"] = "sk-X-api-key = “c5627fd644a4e4cfdbac004fc4af6da25326fb4247d43bf45c8b3fb2b2ef3244”" 

llm = ChatOpenAI(
    model="gpt-4o", 
    temperature=0, 
    api_key="sk-proj-X-api-key = “c5627fd644a4e4cfdbac004fc4af6da25326fb4247d43bf45c8b3fb2b2ef3244”"  # <--- Paste your key inside these quotes
)

# --- 3. CONNECT TOOL TO AGENT ---
# We put the tool in a list, just like the diagram shows
tools = [analyze_inventory_levels]

# This function wraps the LLM and the Tools together (The Blue Box in your diagram)
agent_executor = create_react_agent(llm, tools)

# --- 4. RUN THE CHAT LOOP ---
print("🤖 AI Inventory Manager is ready!")
print("Try asking: 'The company has 5000 COGS, started with 1000 inventory and ended with 1200. Is this healthy?'")

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