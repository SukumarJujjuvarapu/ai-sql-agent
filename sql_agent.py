import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

# --- CONFIGURATION ---
DB_NAME = r"C:\Users\Sukku\OneDrive\Desktop\P1\Chinook_Sqlite.sqlite"

def run_query(sql):
    """Connects to the database and runs the SQL query."""
    conn = sqlite3.connect(DB_NAME)
    try:
        # Check if it's a SELECT query
        if sql.strip().upper().startswith("SELECT"):
            df = pd.read_sql(sql, conn)
            conn.close()
            return df
        else:
            # For non-select queries (safety)
            conn.close()
            return "Error: This agent only allows SELECT queries."
    except Exception as e:
        conn.close()
        return f"Error running SQL: {e}"

def get_ai_sql(user_question):
    """
    SIMULATED AI BRAIN
    In a real app, this sends 'user_question' to Gemini/OpenAI.
    For now, we return the correct SQL for the demo question.
    """
    print(f"🤖 AI is thinking about: '{user_question}'...")
    
    # HARDCODED LOGIC FOR TESTING
    if "most" in user_question.lower() and "spent" in user_question.lower():
        return """
        SELECT Customer.FirstName, Customer.LastName, SUM(Invoice.Total) as TotalSpent
        FROM Customer
        JOIN Invoice ON Customer.CustomerId = Invoice.CustomerId
        GROUP BY Customer.CustomerId
        ORDER BY TotalSpent DESC
        LIMIT 5
        """
    elif "tables" in user_question.lower():
        return "SELECT name FROM sqlite_master WHERE type='table';"
    else:
        return None

# --- MAIN AGENT LOOP ---
def agent_loop():
    print("--- 🕵️‍♂️ Text-to-SQL Agent Initialized ---")
    print("You can ask: 'Who spent the most money?' or 'Show me the tables'.")
    
    while True:
        user_input = input("\nAsk a question (or 'exit'): ")
        if user_input.lower() in ['exit', 'quit']:
            break
        
        # 1. Get SQL from the (Simulated) AI
        sql_query = get_ai_sql(user_input)
        
        if sql_query:
            print(f"\n📄 Generated SQL:\n{sql_query}")
            
            # 2. Run the SQL
            print("\n🚀 Executing Query...")
            result = run_query(sql_query)
            print(result)
            
            # 3. (Optional) Auto-Visualize if it's the spending data
            if "TotalSpent" in str(result):
                print("\n📊 Generating Graph...")
                try:
                    plt.figure(figsize=(8, 5))
                    plt.bar(result['FirstName'], result['TotalSpent'], color='purple')
                    plt.title("Top Spenders (Agent Generated)")
                    plt.show()
                except:
                    pass
        else:
            print("❌ I don't know that one yet! (Try asking about 'spending')")

if __name__ == "__main__":
    agent_loop()