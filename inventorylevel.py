from langchain.tools import tool

# This is the "A TOOL" box from your diagram
@tool
def analyze_inventory_levels(
    cogs: float, 
    beginning_inventory: float, 
    ending_inventory: float
) -> str:
    """
    Calculates inventory health metrics like Turnover Ratio and Days Sales of Inventory (DSI).
    
    Use this tool when the user asks about:
    - Inventory efficiency
    - How fast products are selling
    - Risk of dead stock or obsolescence
    
    Inputs:
    - cogs: Cost of Goods Sold (Annual).
    - beginning_inventory: Inventory value at start of year.
    - ending_inventory: Inventory value at end of year.
    """
    
    # --- LOGIC GOES HERE (We will do this in Step 2) ---
    # 1. Calculate Average Inventory
    # We take the average because inventory fluctuates throughout the year
    avg_inventory = (beginning_inventory + ending_inventory) / 2
    
    # Safety Check: Avoid dividing by zero if they have no inventory
    if avg_inventory == 0:
        return "Error: Average inventory is zero. Cannot calculate turnover."

    # 2. Calculate Inventory Turnover Ratio
    # Formula: Cost of Goods Sold / Average Inventory
    turnover_ratio = cogs / avg_inventory
    
    # 3. Calculate Days Sales of Inventory (DSI)
    # This tells us how many days it takes to sell the entire stock
    days_to_sell = 365 / turnover_ratio
    
    # 4. Create the Output String
    result = f"""
    INVENTORY ANALYSIS:
    - Turnover Ratio: {turnover_ratio:.2f}x
    - Days to Sell: {days_to_sell:.1f} days
    """
    
    # 5. Add "Analyst" Insights (The Smart Part)
    if days_to_sell > 120:
        result += "\n⚠️ RED FLAG: Inventory is sitting for over 4 months. Risks: Obsolescence, High Storage Costs."
    elif days_to_sell < 15:
        result += "\n⚠️ WARNING: Inventory is moving too fast (under 15 days). Risk of stockouts (running out of product)."
    else:
        result += "\n✅ HEALTHY: Inventory levels are balanced."
        
    return result