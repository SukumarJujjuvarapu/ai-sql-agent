import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from groq import Groq

# --- 1. CONFIGURATION ---
# Set GROQ_API_KEY in environment or .env file
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# PASTE YOUR DATABASE PATH HERE (Use the one that worked!):
DB_PATH = r"C:\Users\Sukku\OneDrive\Desktop\P1\Chinook_Sqlite.sqlite"

# Setup the AI Client
client = Groq(api_key=GROQ_API_KEY)

# --- 2. HELPER FUNCTIONS ---

def get_db_schema():
    """
    Reads the database to find out table names and columns.
    This gives the AI the 'context' it needs to write correct SQL.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Get the 'CREATE TABLE' statements for all tables
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        
        # Join them into one big string
        schema = "\n".join([t[0] for t in tables if t[0] is not None])
        return schema
    except Exception as e:
        return f"Error reading DB: {e}"

def run_query(sql):
    """Runs the SQL query on the database."""
    conn = sqlite3.connect(DB_PATH)
    try:
        if sql.strip().upper().startswith("SELECT"):
            df = pd.read_sql(sql, conn)
            conn.close()
            return df
        else:
            conn.close()
            return "Error: For safety, this agent only allows SELECT queries."
    except Exception as e:
        conn.close()
        return f"Error running SQL: {e}"

def get_ai_sql(user_question):
    """
    The Real Brain: Sends Schema + Question to Groq AI.
    """
    print(f"🤖 AI is thinking...")
    
    schema_context = get_db_schema()
    
    system_prompt = f"""
    You are a SQL Expert. 
    Here is the database schema:
    {schema_context}
    
    Write a SQLite query to answer the user's question.
    RULES:
    1. Return ONLY the SQL code. No markdown, no explanations, no ```sql tags.
    2. Use JOINs if data is in multiple tables.
    3. Limit results to 10 rows if not specified.
    """

    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question}
        ],
        model="llama-3.3-70b-versatile", # Free, fast, and good at SQL
    )

    # Clean up the response (remove ```sql if the AI adds it)
    sql = chat_completion.choices[0].message.content
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql

# --- 3. MAIN APP LOOP ---
def agent_loop():
    print("--- 🧠 REAL Text-to-SQL Agent (Powered by Llama 3) ---")
    print(f"Target Database: {os.path.basename(DB_PATH)}")
    
    while True:
        user_input = input("\nAsk a data question (or 'exit'): ")
        if user_input.lower() in ['exit', 'quit']:
            break
        
        # 1. Ask AI
        generated_sql = get_ai_sql(user_input)
        print(f"\n📄 Generated SQL:\n{generated_sql}")
        
        # 2. Run Query
        print("\n🚀 Executing...")
        result = run_query(generated_sql)
        
        # 3. Show Results
        if isinstance(result, pd.DataFrame):
            if result.empty:
                print("⚠️ Query ran successfully, but returned no data.")
            else:
                print(result)
                
                # 4. Auto-Plot (Simple Logic)
                # If the result has exactly 2 columns (Text + Number), make a chart
                if result.shape[1] == 2:
                    try:
                        col_x = result.columns[0] # Names
                        col_y = result.columns[1] # Numbers
                        # Check if the second column is actually numeric
                        if pd.api.types.is_numeric_dtype(result[col_y]):
                            print("\n📊 Generating Graph...")
                            plt.figure(figsize=(10, 6))
                            plt.bar(result[col_x].astype(str), result[col_y], color='teal')
                            plt.title(f"{col_x} vs {col_y}")
                            plt.xticks(rotation=45)
                            plt.tight_layout()
                            plt.show()
                    except Exception as e:
                        print(f"(Could not generate graph: {e})")
        else:
            print(result) # Print Error Message

if __name__ == "__main__":
    agent_loop()