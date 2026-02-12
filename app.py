import streamlit as st
import os
import sqlite3
import pandas as pd
from groq import Groq
import plotly.express as px
import hashlib
import json
from datetime import datetime, timedelta
from io import BytesIO
import razorpay
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

# ============================================================
#                    🚀 AI DATA ANALYST PRO
#              Revenue-Generating SaaS Application
#                    🇮🇳 Made in India
# ============================================================

# --- CONFIGURATION (Uses environment variables for deployment) ---
# Set these in Streamlit Cloud Secrets or .env file
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Razorpay Configuration (Set in Streamlit Cloud Secrets)
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

# Pricing in INR (paise for Razorpay: ₹499 = 49900 paise)
PRICING = {
    "starter": {"monthly": 49900, "yearly": 499900, "display": "₹499/mo"},
    "pro": {"monthly": 149900, "yearly": 1499900, "display": "₹1,499/mo"},
    "enterprise": {"monthly": 499900, "yearly": 4999900, "display": "₹4,999/mo"}
}

# App Database (for users, history, subscriptions)
# Use /tmp for cloud deployment (Streamlit Cloud has writable /tmp)
if os.path.exists("/tmp"):
    APP_DB_PATH = "/tmp/app_database.db"
else:
    APP_DB_PATH = "app_database.db"

# Default sample database - works locally and on cloud
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Chinook_Sqlite.sqlite")

# Check if default database exists, create a demo one if not
if not os.path.exists(DEFAULT_DB_PATH):
    # Try fallback path
    _fallback = "Chinook_Sqlite.sqlite"
    if os.path.exists(_fallback):
        DEFAULT_DB_PATH = _fallback
    else:
        # Create a minimal sample database so the app never crashes
        try:
            _demo_conn = sqlite3.connect(DEFAULT_DB_PATH)
            _demo_cur = _demo_conn.cursor()
            _demo_cur.execute('''CREATE TABLE IF NOT EXISTS customers (
                CustomerId INTEGER PRIMARY KEY, FirstName TEXT, LastName TEXT,
                Company TEXT, City TEXT, Country TEXT, Email TEXT, TotalSpent REAL)''')
            _demo_cur.execute('''CREATE TABLE IF NOT EXISTS invoices (
                InvoiceId INTEGER PRIMARY KEY, CustomerId INTEGER, InvoiceDate TEXT,
                BillingCity TEXT, BillingCountry TEXT, Total REAL,
                FOREIGN KEY (CustomerId) REFERENCES customers(CustomerId))''')
            _demo_cur.execute('''CREATE TABLE IF NOT EXISTS products (
                ProductId INTEGER PRIMARY KEY, Name TEXT, Category TEXT, Price REAL, Stock INTEGER)''')
            _sample_customers = [
                (1,'Rahul','Sharma','TCS','Mumbai','India','rahul@tcs.com',1250.50),
                (2,'Priya','Patel','Infosys','Bangalore','India','priya@infosys.com',980.75),
                (3,'Amit','Kumar','Wipro','Hyderabad','India','amit@wipro.com',2100.00),
                (4,'Sneha','Reddy','HCL','Chennai','India','sneha@hcl.com',750.25),
                (5,'Vikram','Singh','Reliance','Delhi','India','vikram@rel.com',3200.00),
                (6,'Ananya','Gupta','Flipkart','Bangalore','India','ananya@flip.com',1800.50),
                (7,'Ravi','Verma','Zoho','Chennai','India','ravi@zoho.com',950.00),
                (8,'Meera','Nair','Freshworks','Chennai','India','meera@fresh.com',1500.75),
                (9,'Arjun','Desai','Razorpay','Bangalore','India','arjun@razor.com',2800.25),
                (10,'Kavya','Iyer','Swiggy','Hyderabad','India','kavya@swiggy.com',600.50),
            ]
            _demo_cur.executemany('INSERT OR IGNORE INTO customers VALUES (?,?,?,?,?,?,?,?)', _sample_customers)
            _sample_invoices = [
                (1,1,'2025-01-15','Mumbai','India',450.00),
                (2,2,'2025-01-20','Bangalore','India',320.75),
                (3,3,'2025-02-01','Hyderabad','India',700.00),
                (4,1,'2025-02-10','Mumbai','India',800.50),
                (5,5,'2025-02-15','Delhi','India',1200.00),
                (6,4,'2025-03-01','Chennai','India',750.25),
                (7,6,'2025-03-10','Bangalore','India',900.50),
                (8,3,'2025-03-15','Hyderabad','India',1400.00),
                (9,9,'2025-04-01','Bangalore','India',2800.25),
                (10,7,'2025-04-10','Chennai','India',950.00),
                (11,8,'2025-04-15','Chennai','India',1500.75),
                (12,10,'2025-05-01','Hyderabad','India',600.50),
                (13,2,'2025-05-10','Bangalore','India',660.00),
                (14,5,'2025-05-20','Delhi','India',2000.00),
                (15,6,'2025-06-01','Bangalore','India',900.00),
            ]
            _demo_cur.executemany('INSERT OR IGNORE INTO invoices VALUES (?,?,?,?,?,?)', _sample_invoices)
            _sample_products = [
                (1,'Data Analytics Basic','Software',499.00,100),
                (2,'AI Insights Pro','Software',1499.00,50),
                (3,'Enterprise Suite','Software',4999.00,20),
                (4,'Training Workshop','Service',2999.00,30),
                (5,'Custom Dashboard','Service',9999.00,10),
            ]
            _demo_cur.executemany('INSERT OR IGNORE INTO products VALUES (?,?,?,?,?)', _sample_products)
            _demo_conn.commit()
            _demo_conn.close()
        except Exception:
            pass  # App will handle missing DB gracefully downstream

# Initialize Razorpay Client
try:
    if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
        razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    else:
        razorpay_client = None
except Exception:
    razorpay_client = None

# Initialize Groq Client
try:
    if GROQ_API_KEY:
        client = Groq(api_key=GROQ_API_KEY)
    else:
        client = None
except Exception:
    client = None

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="AI Data Analyst Pro",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- RAZORPAY VERIFICATION META TAG ---
st.markdown("""
<meta name="razorpay-site-verification" content="ai-data-analyst-pro-sukumar" />
""", unsafe_allow_html=True)

# ============================================================
#                    DATABASE SETUP
# ============================================================

def init_app_database():
    """Initialize the application database with all required tables"""
    conn = sqlite3.connect(APP_DB_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            subscription_tier TEXT DEFAULT 'free',
            subscription_expires TIMESTAMP,
            stripe_customer_id TEXT,
            queries_today INTEGER DEFAULT 0,
            last_query_date DATE
        )
    ''')
    
    # Query history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS query_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            sql_query TEXT NOT NULL,
            result_preview TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Uploaded databases table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uploaded_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Payment history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            stripe_payment_id TEXT,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'usd',
            status TEXT NOT NULL,
            plan_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_app_database()

# ============================================================
#                    AUTHENTICATION FUNCTIONS
# ============================================================

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(email, password, name):
    """Create a new user account"""
    conn = sqlite3.connect(APP_DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
            (email.lower(), hash_password(password), name)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return True, user_id
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Email already exists"

def authenticate_user(email, password):
    """Authenticate user login"""
    conn = sqlite3.connect(APP_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, subscription_tier, subscription_expires FROM users WHERE email = ? AND password_hash = ?",
        (email.lower(), hash_password(password))
    )
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {
            "id": user[0],
            "name": user[1],
            "email": email.lower(),
            "subscription_tier": user[2],
            "subscription_expires": user[3]
        }
    return None

def get_user_info(user_id):
    """Get user information by ID"""
    conn = sqlite3.connect(APP_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT email, name, subscription_tier, subscription_expires, queries_today, last_query_date FROM users WHERE id = ?",
        (user_id,)
    )
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {
            "email": user[0],
            "name": user[1],
            "subscription_tier": user[2],
            "subscription_expires": user[3],
            "queries_today": user[4] or 0,
            "last_query_date": user[5]
        }
    return None

def update_query_count(user_id):
    """Update daily query count for user"""
    conn = sqlite3.connect(APP_DB_PATH)
    cursor = conn.cursor()
    today = datetime.now().date().isoformat()
    
    cursor.execute("SELECT last_query_date, queries_today FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    
    # Handle case where user doesn't exist
    if result is None:
        conn.close()
        return 1
    
    if result[0] == today:
        new_count = (result[1] or 0) + 1
    else:
        new_count = 1
    
    cursor.execute(
        "UPDATE users SET queries_today = ?, last_query_date = ? WHERE id = ?",
        (new_count, today, user_id)
    )
    conn.commit()
    conn.close()
    return new_count

def check_query_limit(user_id, tier):
    """Check if user has exceeded query limit"""
    limits = {"free": 5, "starter": 50, "pro": 500, "enterprise": 99999}
    user_info = get_user_info(user_id)
    today = datetime.now().date().isoformat()
    
    # Handle case where user_info is None or last_query_date is None
    if user_info is None:
        return True, limits.get(tier, 5)
    
    if user_info["last_query_date"] != today:
        return True, limits.get(tier, 5)
    
    return user_info["queries_today"] < limits.get(tier, 5), limits.get(tier, 5) - user_info["queries_today"]

# ============================================================
#                    QUERY HISTORY FUNCTIONS
# ============================================================

def save_query_history(user_id, question, sql_query, result_preview):
    """Save query to history"""
    conn = sqlite3.connect(APP_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO query_history (user_id, question, sql_query, result_preview) VALUES (?, ?, ?, ?)",
        (user_id, question, sql_query, result_preview[:500] if result_preview else None)
    )
    conn.commit()
    conn.close()

def get_query_history(user_id, limit=20):
    """Get user's query history"""
    conn = sqlite3.connect(APP_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT question, sql_query, result_preview, created_at FROM query_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    )
    history = cursor.fetchall()
    conn.close()
    return history

def clear_query_history(user_id):
    """Clear user's query history"""
    conn = sqlite3.connect(APP_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM query_history WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# ============================================================
#                    FILE UPLOAD FUNCTIONS
# ============================================================

def save_uploaded_file(user_id, uploaded_file, file_type):
    """Save uploaded file and return path"""
    # Create uploads directory - use /tmp for cloud deployment
    if os.path.exists("/tmp"):
        upload_dir = f"/tmp/uploads/user_{user_id}"
    else:
        upload_dir = f"uploads/user_{user_id}"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{uploaded_file.name}"
    file_path = os.path.join(upload_dir, safe_filename)
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Record in database
    conn = sqlite3.connect(APP_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO uploaded_files (user_id, filename, file_path, file_type) VALUES (?, ?, ?, ?)",
        (user_id, uploaded_file.name, file_path, file_type)
    )
    conn.commit()
    conn.close()
    
    return file_path

def get_user_files(user_id):
    """Get list of user's uploaded files"""
    conn = sqlite3.connect(APP_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, filename, file_path, file_type, uploaded_at FROM uploaded_files WHERE user_id = ? ORDER BY uploaded_at DESC",
        (user_id,)
    )
    files = cursor.fetchall()
    conn.close()
    return files

def csv_to_sqlite(csv_path, db_path, table_name="data"):
    """Convert CSV file to SQLite database"""
    try:
        df = pd.read_csv(csv_path)
        if df.empty:
            raise ValueError("CSV file is empty")
        with sqlite3.connect(db_path) as conn:
            df.to_sql(table_name, conn, if_exists='replace', index=False)
        return db_path
    except Exception as e:
        raise Exception(f"Error converting CSV: {str(e)}")

def excel_to_sqlite(excel_path, db_path):
    """Convert Excel file to SQLite database (each sheet = table)"""
    try:
        excel_file = pd.ExcelFile(excel_path)
        if not excel_file.sheet_names:
            raise ValueError("Excel file has no sheets")
        
        with sqlite3.connect(db_path) as conn:
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                # Clean sheet name for SQL table
                clean_name = sheet_name.replace(" ", "_").replace("-", "_")
                df.to_sql(clean_name, conn, if_exists='replace', index=False)
        return db_path
    except Exception as e:
        raise Exception(f"Error converting Excel: {str(e)}")

# ============================================================
#                    SQL & AI FUNCTIONS
# ============================================================

def get_db_schema(db_path):
    """Get database schema"""
    if not db_path or not os.path.exists(db_path):
        return "Error: Database file not found."
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
        schema = "\n".join([t[0] for t in tables if t[0] is not None])
        return schema if schema else "No tables found in database."
    except Exception as e:
        return f"Error reading schema: {str(e)}"

def run_query(sql, db_path):
    """Execute SQL query on database"""
    if not db_path or not os.path.exists(db_path):
        return "Error: Database file not found. Please upload a file or select a data source."
    if not sql or not sql.strip():
        return "Error: No SQL query generated."
    try:
        # Clean the SQL
        clean_sql = sql.strip()
        if not (clean_sql.upper().startswith("SELECT") or clean_sql.upper().startswith("WITH")):
            return "Error: Only SELECT queries are allowed for security."
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA query_only = ON;")  # Extra safety
        df = pd.read_sql(clean_sql, conn)
        conn.close()
        if df.empty:
            return pd.DataFrame({'Message': ['Query returned no results. Try a different question.']})
        return df
    except sqlite3.OperationalError as e:
        return f"SQL Error: {str(e)}. Try rephrasing your question."
    except sqlite3.DatabaseError as e:
        return f"Database Error: {str(e)}. The database file may be corrupted."
    except Exception as e:
        return f"Error: {str(e)}"

def get_ai_sql(user_question, db_path):
    """Generate SQL from natural language using AI"""
    if client is None:
        return "SELECT 'Error: AI not configured. Please add GROQ_API_KEY in Streamlit Secrets or .env file.' as message"
    
    if not db_path or not os.path.exists(db_path):
        return "SELECT 'Error: No database selected. Please upload a file first.' as message"
    
    schema_context = get_db_schema(db_path)
    if schema_context.startswith("Error") or schema_context == "No tables found in database.":
        return f"SELECT '{schema_context}' as message"
    
    system_prompt = f"""
    You are an expert SQL analyst. Database Schema:
    {schema_context}
    
    Write a SQLite query to answer the user's question.
    Return ONLY the SQL query - no markdown, no explanation, just raw SQL.
    Make sure the query is valid SQLite syntax.
    Always use SELECT statements only.
    If the question cannot be answered with the available tables, return a SELECT statement explaining why.
    """
    
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=1000,
        )
        sql = completion.choices[0].message.content
        if not sql:
            return "SELECT 'Error: AI returned empty response. Please try again.' as message"
        # Clean the SQL response
        sql = sql.replace("```sql", "").replace("```", "").strip()
        # Remove any leading/trailing explanation text
        lines = sql.split('\n')
        sql_lines = [l for l in lines if not l.strip().startswith('--') or l.strip().upper().startswith('SELECT')]
        cleaned = '\n'.join(sql_lines).strip()
        return cleaned if cleaned else sql
    except Exception as e:
        error_msg = str(e).replace("'", "")
        return f"SELECT 'AI Error: {error_msg}' as message"

# ============================================================
#                    EXPORT FUNCTIONS
# ============================================================

def export_to_excel(df):
    """Export DataFrame to Excel bytes"""
    try:
        output = BytesIO()
        # Convert problematic types to strings for Excel compatibility
        df_export = df.copy()
        for col in df_export.columns:
            if df_export[col].dtype == 'object':
                df_export[col] = df_export[col].astype(str)
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Results')
        output.seek(0)
        return output
    except Exception:
        # Fallback: export as CSV in Excel-compatible format
        output = BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return output

def export_to_csv(df):
    """Export DataFrame to CSV bytes"""
    return df.to_csv(index=False).encode('utf-8')

def safe_format_value(value):
    """Safely format a numeric value, handling NaN, Inf, and None"""
    try:
        if value is None:
            return "N/A"
        import math
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return "N/A"
        if abs(value) >= 1_000_000:
            return f"{value/1_000_000:.2f}M"
        elif abs(value) >= 1_000:
            return f"{value/1_000:.2f}K"
        elif isinstance(value, float):
            return f"{value:.2f}"
        else:
            return f"{value:,}"
    except (TypeError, ValueError, OverflowError):
        return "N/A"

def generate_pdf_report(df, question, sql_query):
    """Generate a simple PDF report"""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        
        output = BytesIO()
        doc = SimpleDocTemplate(output, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        elements.append(Paragraph("AI Data Analyst Pro - Report", styles['Title']))
        elements.append(Spacer(1, 12))
        
        # Question - sanitize for XML
        safe_question = str(question).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        elements.append(Paragraph(f"<b>Question:</b> {safe_question}", styles['Normal']))
        elements.append(Spacer(1, 12))
        
        # SQL Query - sanitize for XML
        safe_sql = str(sql_query).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        elements.append(Paragraph(f"<b>SQL Query:</b>", styles['Normal']))
        elements.append(Paragraph(f"<code>{safe_sql}</code>", styles['Code']))
        elements.append(Spacer(1, 12))
        
        # Data Table
        elements.append(Paragraph("<b>Results:</b>", styles['Normal']))
        elements.append(Spacer(1, 6))
        
        # Convert DataFrame to table data - sanitize all values
        table_header = [str(c)[:30] for c in df.columns.tolist()]
        table_rows = []
        for row in df.head(50).values.tolist():
            safe_row = [str(v)[:50] if v is not None else "" for v in row]
            table_rows.append(safe_row)
        table_data = [table_header] + table_rows
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)
        
        # Timestamp
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        
        doc.build(elements)
        output.seek(0)
        return output
    except ImportError:
        return None

# ============================================================
#                    PAYMENT FUNCTIONS (RAZORPAY)
# ============================================================

def create_razorpay_order(user_id, plan_tier, billing_cycle="monthly"):
    """Create Razorpay order for payment"""
    try:
        if razorpay_client is None:
            return None, "Razorpay not configured"
        
        amount = PRICING[plan_tier][billing_cycle]
        
        order_data = {
            "amount": amount,
            "currency": "INR",
            "receipt": f"order_{user_id}_{plan_tier}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "notes": {
                "user_id": str(user_id),
                "plan_tier": plan_tier,
                "billing_cycle": billing_cycle
            }
        }
        
        order = razorpay_client.order.create(data=order_data)
        return order, None
    except Exception as e:
        return None, str(e)

def verify_razorpay_payment(payment_id, order_id, signature):
    """Verify Razorpay payment signature"""
    try:
        if razorpay_client is None:
            return False
        
        params = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }
        razorpay_client.utility.verify_payment_signature(params)
        return True
    except Exception:
        return False

def record_payment(user_id, payment_id, order_id, amount, plan_tier, status="success"):
    """Record payment in database"""
    conn = sqlite3.connect(APP_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO payments (user_id, stripe_payment_id, amount, currency, status, plan_type) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, payment_id, amount/100, "INR", status, plan_tier)
    )
    conn.commit()
    conn.close()

def upgrade_user_subscription(user_id, tier, duration_days=30):
    """Upgrade user's subscription tier"""
    conn = sqlite3.connect(APP_DB_PATH)
    cursor = conn.cursor()
    expires = (datetime.now() + timedelta(days=duration_days)).isoformat()
    cursor.execute(
        "UPDATE users SET subscription_tier = ?, subscription_expires = ? WHERE id = ?",
        (tier, expires, user_id)
    )
    conn.commit()
    conn.close()

# ============================================================
#                    SESSION STATE INITIALIZATION
# ============================================================

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "result_df" not in st.session_state:
    st.session_state.result_df = None
if "sql_code" not in st.session_state:
    st.session_state.sql_code = None
if "current_db" not in st.session_state:
    st.session_state.current_db = DEFAULT_DB_PATH
if "current_question" not in st.session_state:
    st.session_state.current_question = None

# ============================================================
#                    CUSTOM CSS
# ============================================================

st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Sora:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
    /* ========== ROOT VARIABLES ========== */
    :root {
        --primary: #0f766e;
        --primary-dark: #0b5f57;
        --secondary: #f97316;
        --accent: #0ea5e9;
        --success: #16a34a;
        --warning: #f59e0b;
        --error: #dc2626;
        --text-primary: #1a1a2e;
        --text-secondary: #374151;
        --text-muted: #6b7280;
        --bg-light: #f0f2f5;
        --bg-card: rgba(255, 255, 255, 0.55);
        --bg-glass: rgba(255, 255, 255, 0.25);
        --bg-glass-strong: rgba(255, 255, 255, 0.65);
        --border-glass: rgba(255, 255, 255, 0.35);
        --border-light: rgba(255, 255, 255, 0.18);
        --shadow-glass: 0 8px 32px rgba(0, 0, 0, 0.08);
        --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.06);
        --shadow-md: 0 8px 24px rgba(0, 0, 0, 0.1);
        --shadow-lg: 0 20px 60px rgba(0, 0, 0, 0.15);
        --shadow-glow: 0 0 40px rgba(15, 118, 110, 0.15);
        --radius-sm: 10px;
        --radius-md: 14px;
        --radius-lg: 18px;
        --radius-xl: 24px;
        --radius-2xl: 32px;
        --blur: blur(20px);
        --blur-heavy: blur(40px);
        --transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        --transition-fast: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    /* ========== GLOBAL STYLES ========== */
    * {
        box-sizing: border-box;
    }
    
    html, body, [data-testid="stAppViewContainer"] {
        overflow-x: hidden !important;
        max-width: 100vw !important;
    }
    
    .stApp {
        background:
            radial-gradient(ellipse 900px 900px at 0% 0%, rgba(15, 118, 110, 0.28), transparent 60%),
            radial-gradient(ellipse 700px 700px at 100% 0%, rgba(249, 115, 22, 0.22), transparent 55%),
            radial-gradient(ellipse 600px 600px at 50% 40%, rgba(14, 165, 233, 0.18), transparent 50%),
            radial-gradient(ellipse 500px 500px at 80% 80%, rgba(168, 85, 247, 0.14), transparent 50%),
            radial-gradient(ellipse 400px 400px at 20% 70%, rgba(249, 115, 22, 0.16), transparent 50%),
            linear-gradient(180deg, #f8fafc 0%, #f0f4f8 40%, #e6ecf2 100%);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Hide anchor link icons next to headings */
    [data-testid="stHeaderActionElements"] { display: none !important; }
    a.header-anchor, .header-anchor { display: none !important; }
    h1 a, h2 a, h3 a, h4 a, h5 a, h6 a { display: none !important; }
    
    /* ========== TYPOGRAPHY ========== */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Sora', 'Inter', sans-serif;
        color: var(--text-primary) !important;
        font-weight: 700 !important;
        line-height: 1.3;
    }
    
    p, span, label, div {
        color: var(--text-secondary);
        line-height: 1.6;
    }
    
    /* ========== MAIN HEADER ========== */
    .main-header {
        font-size: clamp(1.5rem, 5vw, 2.5rem);
        font-weight: 800;
        background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 40%, var(--secondary) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        padding: 1rem 0.5rem;
        letter-spacing: -0.5px;
        animation: fadeInDown 0.6s ease-out;
    }
    
    @keyframes fadeInDown {
        from { opacity: 0; transform: translateY(-15px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* ========== HERO SUBTITLE ========== */
    .hero-subtitle {
        text-align: center;
        font-size: clamp(0.9rem, 2.5vw, 1.15rem);
        color: var(--text-muted) !important;
        margin-bottom: 1.5rem;
        font-weight: 400;
        padding: 0 1rem;
        line-height: 1.6;
    }

    /* ========== GLASSMORPHISM CORE ========== */
    .glass {
        background: rgba(255, 255, 255, 0.35);
        backdrop-filter: blur(24px) saturate(180%);
        -webkit-backdrop-filter: blur(24px) saturate(180%);
        border: 1.5px solid rgba(255, 255, 255, 0.5);
        border-radius: var(--radius-xl);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1), inset 0 1px 0 rgba(255,255,255,0.6);
        transition: var(--transition);
    }
    .glass:hover {
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.14), var(--shadow-glow), inset 0 1px 0 rgba(255,255,255,0.7);
        transform: translateY(-3px);
        border-color: rgba(255, 255, 255, 0.65);
    }

    .glass-card {
        background: rgba(255, 255, 255, 0.4);
        backdrop-filter: blur(24px) saturate(180%);
        -webkit-backdrop-filter: blur(24px) saturate(180%);
        border-radius: var(--radius-xl);
        border: 1.5px solid rgba(255, 255, 255, 0.5);
        padding: clamp(1rem, 3vw, 2rem);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1), inset 0 1px 0 rgba(255,255,255,0.6);
        transition: var(--transition);
    }
    .glass-card:hover {
        box-shadow: 0 16px 48px rgba(0, 0, 0, 0.14), 0 0 30px rgba(15,118,110,0.12), inset 0 1px 0 rgba(255,255,255,0.7);
        transform: translateY(-4px);
        border-color: rgba(255, 255, 255, 0.65);
    }

    /* ========== AUTH CONTAINER (Salesai-style split) ========== */
    .auth-container {
        display: flex;
        min-height: 70vh;
        border-radius: var(--radius-2xl);
        overflow: hidden;
        box-shadow: var(--shadow-lg);
        border: 1px solid var(--border-glass);
        background: var(--bg-glass-strong);
        backdrop-filter: var(--blur-heavy);
        -webkit-backdrop-filter: var(--blur-heavy);
    }
    .auth-left {
        flex: 1;
        background: linear-gradient(135deg, #0f766e 0%, #0b3b35 40%, #0b1320 100%);
        padding: 3rem;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        position: relative;
        overflow: hidden;
    }
    .auth-left::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle at 30% 40%, rgba(14, 165, 233, 0.15), transparent 50%),
                    radial-gradient(circle at 70% 60%, rgba(249, 115, 22, 0.1), transparent 50%);
        animation: auroraFloat 12s ease-in-out infinite alternate;
    }
    @keyframes auroraFloat {
        0% { transform: translate(0, 0) rotate(0deg); }
        100% { transform: translate(-30px, 20px) rotate(3deg); }
    }
    .auth-left-content {
        position: relative;
        z-index: 2;
        text-align: center;
        color: #ffffff;
    }
    .auth-left-content h1 {
        color: #ffffff !important;
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 1rem;
        -webkit-text-fill-color: #ffffff !important;
        text-shadow: 0 2px 20px rgba(0,0,0,0.3);
    }
    .auth-left-content p {
        color: rgba(255,255,255,0.8) !important;
        font-size: 1.05rem;
        line-height: 1.7;
        max-width: 380px;
    }
    .auth-floating-card {
        background: rgba(255,255,255,0.1);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255,255,255,0.15);
        border-radius: 16px;
        padding: 1.25rem;
        margin-top: 2rem;
        width: 100%;
        max-width: 320px;
    }
    .auth-floating-card .stat-row {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 0.75rem;
    }
    .auth-floating-card .stat-row:last-child { margin-bottom: 0; }
    .auth-floating-card .stat-icon {
        width: 40px;
        height: 40px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1rem;
    }
    .auth-floating-card .stat-text {
        color: rgba(255,255,255,0.9) !important;
        font-size: 0.9rem;
        font-weight: 500;
    }
    .auth-floating-card .stat-value {
        color: #2dd4bf !important;
        font-weight: 700;
        font-size: 1.1rem;
    }
    .auth-right {
        flex: 1;
        padding: 3rem;
        display: flex;
        flex-direction: column;
        justify-content: center;
        background: rgba(255,255,255,0.85);
        backdrop-filter: blur(30px);
    }
    .auth-right h2 {
        font-family: 'Sora', sans-serif;
        font-size: 1.8rem;
        font-weight: 800;
        color: var(--text-primary) !important;
        margin-bottom: 0.5rem;
    }
    .auth-right .auth-subtitle {
        color: var(--text-muted) !important;
        font-size: 0.95rem;
        margin-bottom: 2rem;
    }

    /* ========== TIER BADGES ========== */
    .tier-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.4rem 1rem;
        border-radius: 25px;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        box-shadow: var(--shadow-sm);
        backdrop-filter: blur(8px);
    }
    .tier-free { 
        background: linear-gradient(135deg, rgba(148,163,184,0.8), rgba(91,122,124,0.8)); 
        color: #ffffff !important; 
        border: 1px solid rgba(255,255,255,0.2);
        font-weight: 700;
    }
    .tier-starter { background: linear-gradient(135deg, #2dd4bf, #0ea5e9); color: white; }
    .tier-pro { background: linear-gradient(135deg, #fbbf24, #f59e0b); color: white; }
    .tier-enterprise { background: linear-gradient(135deg, #34d399, #10b981); color: white; }
    
    /* ========== PRICING CARDS (glass) ========== */
    .pricing-card {
        background: rgba(255, 255, 255, 0.35);
        backdrop-filter: blur(24px) saturate(180%);
        -webkit-backdrop-filter: blur(24px) saturate(180%);
        border: 1.5px solid rgba(255, 255, 255, 0.5);
        border-radius: var(--radius-xl);
        padding: clamp(1rem, 3vw, 2rem);
        text-align: center;
        transition: var(--transition);
        position: relative;
        overflow: hidden;
        height: 100%;
        display: flex;
        flex-direction: column;
        box-shadow: 0 8px 32px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.6);
    }
    .pricing-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, var(--primary), var(--accent), var(--secondary));
    }
    .pricing-card:hover {
        transform: translateY(-6px);
        box-shadow: 0 20px 60px rgba(0,0,0,0.14), var(--shadow-glow), inset 0 1px 0 rgba(255,255,255,0.7);
        border-color: rgba(255, 255, 255, 0.65);
        background: rgba(255, 255, 255, 0.5);
    }
    .pricing-card h3 {
        font-size: clamp(1rem, 2.5vw, 1.3rem);
        margin-bottom: 0.5rem;
        color: var(--text-primary) !important;
        font-weight: 700 !important;
    }
    .pricing-card h2 {
        font-size: clamp(1.5rem, 4vw, 2.5rem);
        font-weight: 800;
        background: linear-gradient(135deg, var(--primary), var(--accent));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0.5rem 0;
    }
    .pricing-card p {
        color: var(--text-secondary) !important;
        font-size: clamp(0.75rem, 2vw, 0.9rem);
        line-height: 1.5;
        margin: 0.3rem 0;
    }
    .pricing-card hr {
        margin: 0.75rem 0;
        opacity: 0.2;
        border-color: rgba(15, 118, 110, 0.15);
    }
    
    /* ========== FEATURE CARDS (glass) ========== */
    .feature-card {
        background: rgba(255, 255, 255, 0.35);
        backdrop-filter: blur(24px) saturate(180%);
        -webkit-backdrop-filter: blur(24px) saturate(180%);
        border-radius: var(--radius-lg);
        padding: clamp(1rem, 2.5vw, 1.5rem);
        text-align: center;
        box-shadow: 0 8px 32px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.6);
        transition: var(--transition);
        border: 1.5px solid rgba(255, 255, 255, 0.5);
        height: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 160px;
        position: relative;
        overflow: hidden;
    }
    .feature-card::after {
        content: '';
        position: absolute;
        inset: 0;
        border-radius: inherit;
        background: linear-gradient(135deg, rgba(15,118,110,0.05), rgba(14,165,233,0.05));
        opacity: 0;
        transition: opacity 0.4s;
    }
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: var(--shadow-md), var(--shadow-glow);
        border-color: rgba(15,118,110,0.25);
    }
    .feature-card:hover::after { opacity: 1; }
    .feature-card h4 {
        color: var(--text-primary) !important;
        font-size: clamp(0.85rem, 2vw, 1rem) !important;
        font-weight: 600 !important;
        margin: 0.5rem 0 0.3rem 0 !important;
        position: relative;
        z-index: 1;
    }
    .feature-card p {
        color: var(--text-muted) !important;
        font-size: clamp(0.7rem, 1.8vw, 0.85rem) !important;
        line-height: 1.4 !important;
        margin: 0 !important;
        position: relative;
        z-index: 1;
    }
    .feature-icon {
        font-size: clamp(1.8rem, 4vw, 2.5rem);
        margin-bottom: 0.5rem;
        position: relative;
        z-index: 1;
    }
    
    /* ========== BUTTONS (glass style) ========== */
    .stButton > button,
    .stFormSubmitButton > button {
        width: 100%;
        border-radius: var(--radius-md);
        font-weight: 700;
        font-size: clamp(0.85rem, 2vw, 1rem);
        padding: 0.85rem 1.2rem;
        transition: var(--transition);
        border: none;
        box-shadow: 0 4px 15px rgba(15, 118, 110, 0.3);
        min-height: 48px;
        cursor: pointer;
        background: linear-gradient(135deg, var(--primary), var(--accent)) !important;
        color: #ffffff !important;
        letter-spacing: 0.3px;
    }
    .stButton > button:hover,
    .stFormSubmitButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(15, 118, 110, 0.4), var(--shadow-glow);
        background: linear-gradient(135deg, var(--primary-dark), var(--primary)) !important;
    }
    .stButton > button:active,
    .stFormSubmitButton > button:active {
        transform: scale(0.98);
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--primary), var(--accent)) !important;
        color: white !important;
        border: none;
    }
    
    /* ========== FORM INPUTS (glass) ========== */
    .stTextInput > div > div > input,
    .stTextArea textarea,
    .stSelectbox > div > div,
    .stNumberInput > div > div > input {
        border-radius: var(--radius-md);
        border: 1.5px solid rgba(255, 255, 255, 0.5);
        padding: 0.85rem 1rem;
        font-size: 16px !important;
        transition: var(--transition);
        background: rgba(255, 255, 255, 0.45) !important;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        color: var(--text-primary) !important;
        -webkit-text-fill-color: var(--text-primary) !important;
        caret-color: var(--primary) !important;
        box-shadow: inset 0 1px 3px rgba(0,0,0,0.04), 0 2px 8px rgba(0,0,0,0.04);
    }
    .stTextInput > div > div > input::placeholder,
    .stTextArea textarea::placeholder {
        color: #94a3b8 !important;
        -webkit-text-fill-color: #94a3b8 !important;
        opacity: 1 !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea textarea:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--primary);
        box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.15), 0 0 20px rgba(15, 118, 110, 0.1);
        outline: none;
        background: rgba(255, 255, 255, 0.7) !important;
    }
    
    /* Select box text */
    .stSelectbox > div > div > div {
        color: var(--text-primary) !important;
        -webkit-text-fill-color: var(--text-primary) !important;
    }
    .stSelectbox [data-baseweb="select"] span {
        color: var(--text-primary) !important;
        -webkit-text-fill-color: var(--text-primary) !important;
    }
    
    /* Password input */
    .stTextInput input[type="password"] {
        color: var(--text-primary) !important;
        -webkit-text-fill-color: var(--text-primary) !important;
        background: rgba(255, 255, 255, 0.7) !important;
    }
    
    /* Form labels */
    .stTextInput label, .stSelectbox label, .stFileUploader label, .stTextArea label, .stNumberInput label {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        margin-bottom: 0.3rem;
    }
    
    /* ========== TABS (glass) ========== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px !important;
        background: rgba(255, 255, 255, 0.35) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border: 1px solid rgba(255, 255, 255, 0.5) !important;
        border-radius: var(--radius-md) !important;
        padding: 5px !important;
        flex-wrap: wrap;
        box-shadow: 0 4px 16px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,0.6);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: var(--radius-sm) !important;
        font-weight: 600 !important;
        padding: 10px 20px !important;
        color: var(--text-secondary) !important;
        background: transparent !important;
        font-size: 0.9rem;
        white-space: nowrap;
        transition: var(--transition-fast);
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--primary), var(--accent)) !important;
        color: white !important;
        box-shadow: 0 4px 15px rgba(15, 118, 110, 0.35);
    }
    .stTabs [data-baseweb="tab-border"],
    .stTabs [data-baseweb="tab-highlight"] {
        display: none !important;
    }

    /* ========== FORMS CONTAINER (glass) ========== */
    [data-testid="stForm"] {
        background: rgba(255, 255, 255, 0.4) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.5) !important;
        border-radius: var(--radius-xl) !important;
        padding: 2rem !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.7) !important;
    }
    
    /* ========== SIDEBAR (glass dark) ========== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(11, 19, 32, 0.97) 0%, rgba(15, 31, 27, 0.97) 100%) !important;
        backdrop-filter: var(--blur-heavy) !important;
        border-right: 1px solid rgba(255,255,255,0.06);
    }
    [data-testid="stSidebar"] * {
        color: #e2e8f0 !important;
    }
    [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h4 {
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] .stProgress > div {
        background: rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        overflow: hidden !important;
    }
    [data-testid="stSidebar"] .stProgress > div > div {
        background: transparent !important;
    }
    [data-testid="stSidebar"] .stProgress > div > div > div,
    [data-testid="stSidebar"] [data-testid="stProgressBar"] > div > div,
    [data-testid="stSidebar"] [role="progressbar"],
    [data-testid="stSidebar"] [role="progressbar"] > div {
        background: linear-gradient(90deg, #0f766e, #14b8a6, #0ea5e9) !important;
        border-radius: 10px !important;
    }
    [data-testid="stSidebar"] .stProgress [style*="background"] {
        background: linear-gradient(90deg, #0f766e, #14b8a6) !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        color: #ffffff !important;
    }
    [data-testid="stSidebar"] .stButton > button {
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.12);
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255, 255, 255, 0.16);
        border-color: rgba(15, 118, 110, 0.4);
    }
    
    /* ========== DATA DISPLAY ========== */
    .stDataFrame {
        border-radius: var(--radius-lg);
        overflow: hidden;
        box-shadow: var(--shadow-glass);
        border: 1px solid var(--border-glass);
    }
    
    /* ========== ALERTS ========== */
    .stAlert {
        border-radius: var(--radius-md);
        border: none;
        padding: 0.75rem 1rem;
        backdrop-filter: blur(8px);
    }
    
    /* ========== DOWNLOAD BUTTONS ========== */
    .stDownloadButton > button {
        background: linear-gradient(135deg, var(--success), #15803d);
        color: white;
        border: none;
        border-radius: var(--radius-md);
    }
    
    /* ========== PROGRESS BAR ========== */
    .stProgress > div {
        background: rgba(15, 118, 110, 0.12) !important;
        border-radius: 10px !important;
    }
    .stProgress > div > div,
    .stProgress > div > div > div,
    [data-testid="stProgressBar"] > div,
    [role="progressbar"] > div {
        background: linear-gradient(90deg, #0f766e, #14b8a6, #0ea5e9) !important;
        border-radius: 10px !important;
    }
    
    /* ========== FILE UPLOADER (glass) ========== */
    .stFileUploader {
        border: 2px dashed rgba(15, 118, 110, 0.3);
        border-radius: var(--radius-lg);
        padding: 1rem;
        background: var(--bg-glass);
        backdrop-filter: blur(8px);
        transition: var(--transition);
    }
    .stFileUploader:hover {
        background: rgba(14, 165, 233, 0.06);
        border-color: var(--accent);
        box-shadow: var(--shadow-glow);
    }
    
    /* ========== DIVIDER ========== */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(15,118,110,0.2), transparent);
        margin: 1.5rem 0;
    }
    
    /* ========== EXPANDERS ========== */
    .streamlit-expanderHeader {
        background: var(--bg-glass);
        backdrop-filter: blur(8px);
        border-radius: var(--radius-md);
        font-weight: 600;
    }
    
    /* ========== CODE BLOCKS ========== */
    .stCodeBlock {
        border-radius: var(--radius-md);
        border: 1px solid var(--border-glass);
    }
    
    /* ========== METRICS ========== */
    [data-testid="stMetricValue"] {
        font-size: clamp(1.5rem, 4vw, 2rem);
        font-weight: 700;
        background: linear-gradient(135deg, var(--primary), var(--accent));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* ========== DASHBOARD STYLES (glass) ========== */
    .dashboard-header {
        background: linear-gradient(135deg, rgba(11, 19, 32, 0.95) 0%, rgba(11, 59, 53, 0.95) 100%);
        backdrop-filter: var(--blur);
        border-radius: 18px 18px 0 0;
        padding: 1rem 1.5rem;
        margin-bottom: 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .dashboard-header h2 {
        color: #ffffff !important;
        font-size: 1.25rem !important;
        font-weight: 600 !important;
        margin: 0 !important;
    }
    .dashboard-container {
        background: var(--bg-glass-strong);
        backdrop-filter: var(--blur);
        border-radius: 0 0 18px 18px;
        padding: 1rem;
        margin-top: 0;
        border: 1px solid var(--border-glass);
        border-top: none;
    }
    .kpi-card {
        background: var(--bg-glass-strong);
        backdrop-filter: blur(12px);
        border-radius: var(--radius-md);
        padding: 1.25rem;
        text-align: center;
        box-shadow: var(--shadow-glass);
        border: 1px solid var(--border-glass);
        transition: var(--transition);
    }
    .kpi-card:hover {
        transform: translateY(-3px);
        box-shadow: var(--shadow-md), var(--shadow-glow);
        border-color: rgba(15,118,110,0.25);
    }
    .kpi-label {
        font-size: 0.8rem;
        color: var(--text-muted);
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.5rem;
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: 700;
        color: var(--primary);
        line-height: 1.2;
    }
    .kpi-value.green { color: #16a34a; }
    .kpi-value.purple { color: #8b5cf6; }
    .kpi-value.orange { color: #f97316; }
    .kpi-value.blue { color: #0ea5e9; }
    .chart-card {
        background: var(--bg-glass-strong);
        backdrop-filter: blur(12px);
        border-radius: var(--radius-md);
        padding: 1rem;
        box-shadow: var(--shadow-glass);
        border: 1px solid var(--border-glass);
        margin-bottom: 1rem;
    }
    .chart-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid rgba(15,118,110,0.12);
    }
    .chart-title i {
        margin-right: 8px;
        color: var(--accent);
    }
    
    /* ========== TRUST ITEMS ========== */
    .trust-item {
        text-align: center;
        padding: 0.75rem;
    }
    .trust-item i {
        font-size: clamp(1.5rem, 3vw, 2rem);
        margin-bottom: 0.5rem;
    }
    .trust-item p {
        color: var(--text-secondary) !important;
        font-size: clamp(0.75rem, 1.8vw, 0.9rem) !important;
        font-weight: 500;
        margin-top: 0.3rem;
    }

    /* ========== GLOSSY HOW-IT-WORKS STEP CARDS ========== */
    .step-card {
        background: rgba(255, 255, 255, 0.35);
        backdrop-filter: blur(24px) saturate(180%);
        -webkit-backdrop-filter: blur(24px) saturate(180%);
        border: 1.5px solid rgba(255, 255, 255, 0.5);
        border-radius: var(--radius-xl);
        padding: 2rem 1.5rem;
        text-align: center;
        transition: var(--transition);
        position: relative;
        overflow: hidden;
        box-shadow: 0 8px 32px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.6);
    }
    .step-card::before {
        content: '';
        position: absolute;
        top: -40%;
        left: -40%;
        width: 180%;
        height: 180%;
        background: radial-gradient(circle, rgba(15, 118, 110, 0.06), transparent 60%);
        opacity: 0;
        transition: opacity 0.5s;
    }
    .step-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 16px 48px rgba(0,0,0,0.12), var(--shadow-glow), inset 0 1px 0 rgba(255,255,255,0.7);
        border-color: rgba(255, 255, 255, 0.65);
    }
    .step-card:hover::before { opacity: 1; }
    .step-icon {
        width: 70px;
        height: 70px;
        border-radius: 50%;
        margin: 0 auto 1rem;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.8rem;
        position: relative;
        z-index: 1;
    }
    .step-card h4 {
        position: relative;
        z-index: 1;
    }
    .step-card p {
        position: relative;
        z-index: 1;
    }
    
    /* ========== BENEFIT GLASS CARDS ========== */
    .benefit-card {
        background: rgba(255, 255, 255, 0.35);
        backdrop-filter: blur(24px) saturate(180%);
        -webkit-backdrop-filter: blur(24px) saturate(180%);
        border: 1.5px solid rgba(255, 255, 255, 0.5);
        border-radius: var(--radius-lg);
        padding: 1.5rem;
        transition: var(--transition);
        height: 100%;
        position: relative;
        overflow: hidden;
        box-shadow: 0 8px 32px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.6);
    }
    .benefit-card::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--primary), var(--accent));
        opacity: 0;
        transition: opacity 0.4s;
    }
    .benefit-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 16px 48px rgba(0,0,0,0.12), var(--shadow-glow), inset 0 1px 0 rgba(255,255,255,0.7);
        border-color: rgba(255, 255, 255, 0.65);
    }
    .benefit-card:hover::after { opacity: 1; }

    /* ========== WHO-FOR GLASS CARDS ========== */
    .who-card {
        background: rgba(255, 255, 255, 0.35);
        backdrop-filter: blur(24px) saturate(180%);
        -webkit-backdrop-filter: blur(24px) saturate(180%);
        border: 1.5px solid rgba(255, 255, 255, 0.5);
        border-radius: var(--radius-xl);
        padding: 2rem;
        height: 100%;
        transition: var(--transition);
        position: relative;
        overflow: hidden;
        box-shadow: 0 8px 32px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.6);
    }
    .who-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
    }
    .who-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 16px 48px rgba(0,0,0,0.12), var(--shadow-glow), inset 0 1px 0 rgba(255,255,255,0.7);
    }

    /* ========== SECTION BADGE ========== */
    .section-badge {
        display: inline-block;
        background: rgba(255, 255, 255, 0.4);
        backdrop-filter: blur(16px) saturate(180%);
        -webkit-backdrop-filter: blur(16px) saturate(180%);
        color: var(--secondary) !important;
        padding: 0.5rem 1.5rem;
        border-radius: 25px;
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        border: 1.5px solid rgba(255, 255, 255, 0.5);
        box-shadow: 0 4px 16px rgba(249, 115, 22, 0.12), inset 0 1px 0 rgba(255,255,255,0.6);
    }
    
    /* ========== ANIMATIONS ========== */
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    @keyframes slideUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-8px); }
    }
    .fade-in { animation: fadeIn 0.5s ease-out; }
    .slide-up { animation: slideUp 0.5s ease-out; }

    /* ========== RESPONSIVE ========== */
    @media screen and (max-width: 1024px) {
        .pricing-card { padding: 1.25rem; }
        .feature-card { min-height: 150px; }
        .auth-container { flex-direction: column; min-height: auto; }
        .auth-left { padding: 2rem; min-height: 300px; }
        .auth-right { padding: 2rem; }
    }
    
    /* ========== RESPONSIVE: TABLET (768px) ========== */
    @media screen and (max-width: 768px) {
        [data-testid="stAppViewContainer"] > div { padding: 0.5rem !important; }
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: 0.75rem !important;
            margin: 0 !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="column"] {
            flex: 1 1 calc(50% - 0.5rem) !important;
            min-width: calc(50% - 0.5rem) !important;
            max-width: 100% !important;
            padding: 0 !important;
        }
        .main-header { font-size: 1.6rem !important; padding: 0.75rem 0.5rem !important; }
        .hero-subtitle { font-size: 0.95rem !important; padding: 0 0.5rem !important; margin-bottom: 1rem !important; }
        .pricing-card { padding: 1rem !important; margin-bottom: 0.75rem !important; border-radius: 16px !important; }
        .feature-card { padding: 1rem !important; min-height: 140px !important; margin-bottom: 0.5rem !important; }
        .stButton > button,
        .stFormSubmitButton > button { padding: 0.7rem 1rem !important; font-size: 0.9rem !important; min-height: 48px !important; }
        .stTextInput > div > div > input,
        .stTextArea textarea,
        .stNumberInput > div > div > input {
            padding: 0.75rem !important;
            font-size: 16px !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            flex-wrap: nowrap !important;
            overflow-x: auto !important;
            scrollbar-width: none !important;
        }
        .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display: none !important; }
        .stTabs [data-baseweb="tab"] { padding: 10px 16px !important; font-size: 0.85rem !important; flex-shrink: 0 !important; }
        .footer-container { padding: 1.5rem 1rem !important; margin-top: 2rem !important; border-radius: 20px !important; }
        .footer-links { flex-direction: row !important; flex-wrap: wrap !important; gap: 0.75rem !important; }
        .glass-card { padding: 1.25rem !important; border-radius: 18px !important; }
        .step-card { padding: 1.5rem 1rem !important; }
        .benefit-card { padding: 1.25rem !important; }
        .who-card { padding: 1.5rem !important; }
        .section-badge { font-size: 0.8rem !important; padding: 0.4rem 1.2rem !important; }
        .trust-item { padding: 0.5rem !important; }
        .trust-item i { font-size: 1.4rem !important; }
        .trust-item p { font-size: 0.75rem !important; }
        [data-testid="stForm"] { padding: 1.5rem !important; border-radius: 18px !important; }
        .dashboard-header { padding: 0.75rem 1rem !important; border-radius: 14px 14px 0 0 !important; }
        .dashboard-container { padding: 0.75rem !important; border-radius: 0 0 14px 14px !important; }
    }

    /* ========== RESPONSIVE: MOBILE (576px) ========== */
    @media screen and (max-width: 576px) {
        html, body { overflow-x: hidden !important; }
        [data-testid="stAppViewContainer"] { padding: 0 !important; }
        [data-testid="stAppViewContainer"] > div { padding: 0.25rem !important; }
        [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
            gap: 0.75rem !important;
            width: 100% !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="column"] {
            flex: 1 1 100% !important;
            width: 100% !important;
            min-width: 100% !important;
            max-width: 100% !important;
            padding: 0 0.25rem !important;
        }
        .main-header { font-size: 1.35rem !important; padding: 0.5rem !important; letter-spacing: -0.3px !important; }
        .hero-subtitle { font-size: 0.88rem !important; padding: 0 0.5rem !important; }
        h1 { font-size: 1.5rem !important; }
        h2 { font-size: 1.25rem !important; }
        h3 { font-size: 1.1rem !important; }
        .pricing-card { padding: 1.25rem !important; border-radius: 16px !important; }
        .pricing-card h2 { font-size: 1.75rem !important; }
        .pricing-card p { font-size: 0.82rem !important; }
        .feature-card { padding: 1rem !important; min-height: 120px !important; }
        .stButton > button,
        .stFormSubmitButton > button { 
            padding: 0.85rem 1rem !important; font-size: 0.95rem !important; 
            min-height: 50px !important; border-radius: 12px !important; 
        }
        .stTextInput > div > div > input,
        .stTextArea textarea,
        .stNumberInput > div > div > input {
            font-size: 16px !important; padding: 0.85rem !important; border-radius: 12px !important;
        }
        /* Auth page */
        [data-testid="stForm"] { padding: 1.25rem !important; border-radius: 16px !important; }
        .glass-card { padding: 1.25rem !important; border-radius: 16px !important; }
        .step-card { padding: 1.25rem 1rem !important; border-radius: 16px !important; }
        .step-icon { width: 56px !important; height: 56px !important; font-size: 1.4rem !important; }
        .benefit-card { padding: 1.25rem !important; border-radius: 14px !important; }
        .who-card { padding: 1.25rem !important; border-radius: 16px !important; }
        .section-badge { font-size: 0.75rem !important; padding: 0.35rem 1rem !important; }
        /* Dashboard */
        .dashboard-header { padding: 0.75rem 1rem !important; border-radius: 14px 14px 0 0 !important; }
        .dashboard-container { padding: 0.75rem !important; border-radius: 0 0 14px 14px !important; }
        .kpi-card { padding: 0.875rem !important; border-radius: 12px !important; }
        .kpi-label { font-size: 0.7rem !important; }
        .kpi-value { font-size: 1.4rem !important; }
        .chart-card { padding: 0.75rem !important; border-radius: 12px !important; }
        /* Sidebar */
        [data-testid="stSidebar"] { width: 280px !important; padding: 1rem 0.75rem !important; }
        /* Footer */
        .footer-container { padding: 1.25rem 0.75rem !important; border-radius: 18px !important; }
        .footer-links { flex-direction: column !important; gap: 0.5rem !important; width: 100% !important; }
        .footer-link { width: 90% !important; justify-content: center !important; }
        .footer-brand { flex-direction: column !important; gap: 6px !important; }
        .footer-title { font-size: 1.2rem !important; }
        .footer-logo { font-size: 1.6rem !important; }
        /* Trust bar */
        .trust-item { padding: 0.4rem !important; }
        .trust-item i { font-size: 1.2rem !important; margin-bottom: 0.25rem !important; }
        .trust-item p { font-size: 0.7rem !important; }
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] { padding: 3px !important; border-radius: 12px !important; }
        .stTabs [data-baseweb="tab"] { padding: 8px 14px !important; font-size: 0.82rem !important; }
        /* Philosophy section values */
        .auth-container { flex-direction: column !important; }
        .auth-left { padding: 2rem 1.5rem !important; min-height: 200px; }
        .auth-left-content h1 { font-size: 1.4rem !important; }
        .auth-right { padding: 1.5rem 1rem !important; }
    }

    /* ========== RESPONSIVE: SMALL MOBILE (375px) ========== */
    @media screen and (max-width: 375px) {
        .main-header { font-size: 1.15rem !important; }
        h1 { font-size: 1.3rem !important; }
        h2 { font-size: 1.1rem !important; }
        .pricing-card h2 { font-size: 1.5rem !important; }
        .feature-card { min-height: 110px !important; }
        .stButton > button,
        .stFormSubmitButton > button { font-size: 0.88rem !important; padding: 0.8rem !important; }
        .stTextInput > div > div > input,
        .stTextArea textarea { font-size: 16px !important; padding: 0.75rem !important; }
        [data-testid="stForm"] { padding: 1rem 0.75rem !important; border-radius: 14px !important; }
        .glass-card { padding: 1rem !important; }
        .step-card { padding: 1rem 0.75rem !important; }
        .who-card { padding: 1rem !important; }
        .footer-container { padding: 1rem 0.5rem !important; border-radius: 14px !important; }
        .footer-links a { font-size: 0.8rem !important; }
        .trust-item p { font-size: 0.65rem !important; }
        .section-badge { font-size: 0.7rem !important; padding: 0.3rem 0.8rem !important; }
    }

    /* ========== TOUCH DEVICES ========== */
    @media (hover: none) and (pointer: coarse) {
        .pricing-card:hover, .feature-card:hover, .glass-card:hover,
        .benefit-card:hover, .step-card:hover, .who-card:hover,
        .glass:hover { transform: none !important; }
        .pricing-card:active, .feature-card:active, .glass-card:active,
        .step-card:active, .benefit-card:active, .who-card:active {
            transform: scale(0.98) !important; opacity: 0.95 !important;
        }
        .stButton > button:active, .stFormSubmitButton > button:active {
            transform: scale(0.97) !important; opacity: 0.9 !important;
        }
        .stRadio label, .stCheckbox label { padding: 0.75rem 0 !important; min-height: 48px !important; }
        .stButton > button, .stFormSubmitButton > button { min-height: 50px !important; }
        /* Larger tap targets */
        .stTextInput > div > div > input,
        .stTextArea textarea,
        .stNumberInput > div > div > input { min-height: 48px !important; }
    }

    /* ========== LANDSCAPE MOBILE ========== */
    @media screen and (max-height: 500px) and (orientation: landscape) {
        .main-header { font-size: 1.2rem !important; }
        .pricing-card, .feature-card { padding: 0.75rem !important; }
        [data-testid="stForm"] { padding: 1rem !important; }
    }

    /* ========== HIGH DPI ========== */
    @media (-webkit-min-device-pixel-ratio: 2), (min-resolution: 192dpi) {
        .glass-card, .pricing-card, .feature-card, .step-card, .benefit-card, .who-card { border-width: 1px; }
    }

    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            animation-duration: 0.01ms !important;
            transition-duration: 0.01ms !important;
        }
    }

    @media print {
        .stButton, [data-testid="stSidebar"], .footer-container { display: none !important; }
        .stApp { background: white !important; }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
#                    LOGIN/REGISTER PAGE
# ============================================================

def show_auth_page():
    """Display landing page with login/register"""
    
    # ========== DECORATIVE GRADIENT BLOBS ==========
    st.markdown('''
    <div class="decor-blobs" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 0; overflow: hidden;">
        <div style="position: absolute; top: -10%; left: -5%; width: min(500px, 70vw); height: min(500px, 70vw); border-radius: 50%;
             background: radial-gradient(circle, rgba(249,115,22,0.25) 0%, transparent 70%); filter: blur(60px);"></div>
        <div style="position: absolute; top: 20%; right: -5%; width: min(450px, 65vw); height: min(450px, 65vw); border-radius: 50%;
             background: radial-gradient(circle, rgba(15,118,110,0.22) 0%, transparent 70%); filter: blur(60px);"></div>
        <div style="position: absolute; bottom: 10%; left: 15%; width: min(400px, 55vw); height: min(400px, 55vw); border-radius: 50%;
             background: radial-gradient(circle, rgba(168,85,247,0.18) 0%, transparent 70%); filter: blur(60px);"></div>
        <div style="position: absolute; top: 50%; right: 20%; width: min(350px, 50vw); height: min(350px, 50vw); border-radius: 50%;
             background: radial-gradient(circle, rgba(14,165,233,0.2) 0%, transparent 70%); filter: blur(60px);"></div>
        <div style="position: absolute; bottom: -5%; right: 10%; width: min(300px, 45vw); height: min(300px, 45vw); border-radius: 50%;
             background: radial-gradient(circle, rgba(249,115,22,0.2) 0%, transparent 70%); filter: blur(50px);"></div>
    </div>
    ''', unsafe_allow_html=True)
    
    # ========== HERO + AUTH SECTION (Glass Card Center) ==========
    st.markdown('''
    <div style="text-align: center; margin: 1rem 0 0.5rem; position: relative; z-index: 1; padding: 0 1rem;">
        <h1 style="font-family: 'Sora', sans-serif; font-size: clamp(1.5rem, 5vw, 3rem); font-weight: 800;
            background: linear-gradient(135deg, #0f766e, #0ea5e9, #f97316);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
            margin-bottom: 0.5rem; line-height: 1.2;">
            AI Data Analyst Pro
        </h1>
        <p style="color: #6b7280; font-size: clamp(0.85rem, 2.5vw, 1.05rem); max-width: 500px; margin: 0 auto; padding: 0 0.5rem;">
            Transform your data into actionable insights with AI-powered analytics
        </p>
    </div>
    ''', unsafe_allow_html=True)
    
    # Center the auth card
    spacer_left, auth_col, spacer_right = st.columns([1.5, 3, 1.5])
    
    with auth_col:
        st.markdown('''
        <div style="text-align: center; padding: 0.25rem 0 0.5rem;">
            <h2 style="font-family: 'Sora', sans-serif; font-size: clamp(1.2rem, 4vw, 1.6rem); font-weight: 700; color: #1a1a2e !important; margin-bottom: 0.15rem;">
                Welcome Back
            </h2>
            <p style="color: #6b7280 !important; font-size: clamp(0.8rem, 2vw, 0.9rem);">
                Sign in or create your free account
            </p>
        </div>
        ''', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🔐 Login", "✨ Register"])
        
        with tab1:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="you@example.com")
                password = st.text_input("Password", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("Sign In →", use_container_width=True)
                
                if submitted:
                    if email and password:
                        user = authenticate_user(email, password)
                        if user:
                            st.session_state.authenticated = True
                            st.session_state.user = user
                            st.success("✅ Login successful!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ Invalid email or password")
                    else:
                        st.warning("⚠️ Please fill in all fields")
        
        with tab2:
            with st.form("register_form"):
                name = st.text_input("Full Name", placeholder="John Doe")
                email = st.text_input("Email", placeholder="you@example.com", key="reg_email")
                password = st.text_input("Password", type="password", placeholder="••••••••", key="reg_pass")
                password2 = st.text_input("Confirm Password", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("Create Free Account →", use_container_width=True)
                
                if submitted:
                    if name and email and password and password2:
                        if password != password2:
                            st.error("❌ Passwords do not match")
                        elif len(password) < 6:
                            st.error("❌ Password must be at least 6 characters")
                        else:
                            success, result = create_user(email, password, name)
                            if success:
                                st.success("🎉 Account created! Please login.")
                                st.balloons()
                            else:
                                st.error(f"❌ {result}")
                    else:
                        st.warning("⚠️ Please fill in all fields")
    
    # Trust indicators bar
    st.markdown('''
    <div style="display: flex; justify-content: center; gap: clamp(1rem, 3vw, 2.5rem); flex-wrap: wrap; margin: 2rem auto 3rem; padding: clamp(0.75rem, 2vw, 1.25rem) clamp(1rem, 3vw, 2rem);
         max-width: 700px; width: calc(100% - 1rem);
         background: rgba(255,255,255,0.4); backdrop-filter: blur(24px) saturate(180%); -webkit-backdrop-filter: blur(24px) saturate(180%);
         border: 1.5px solid rgba(255,255,255,0.5); border-radius: clamp(16px, 4vw, 24px); 
         box-shadow: 0 8px 32px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.6);">
        <div class="trust-item"><i class="fa-solid fa-shield-halved" style="color: #10b981;"></i><p>Enterprise Security</p></div>
        <div class="trust-item"><i class="fa-solid fa-bolt" style="color: #f59e0b;"></i><p>Lightning Fast</p></div>
        <div class="trust-item"><i class="fa-solid fa-brain" style="color: #8b5cf6;"></i><p>AI Powered</p></div>
        <div class="trust-item"><i class="fa-solid fa-lock" style="color: #0ea5e9;"></i><p>Data Privacy First</p></div>
    </div>
    ''', unsafe_allow_html=True)
    
    # ========== HOW IT WORKS SECTION ==========
    st.markdown('''
    <div style="text-align: center; margin: clamp(2rem, 6vw, 4rem) 0 2rem; padding: 0 1rem;">
        <span class="section-badge">HOW IT WORKS</span>
        <h2 style="font-size: clamp(1.25rem, 4vw, 2.5rem); font-weight: 700; margin-top: 1.5rem; line-height: 1.3;">
            Dataset → Intelligence in 3 clicks
        </h2>
    </div>
    ''', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('''
        <div class="step-card">
            <div class="step-icon" style="background: linear-gradient(135deg, rgba(15,118,110,0.15), rgba(14,165,233,0.1));">
                <i class="fa-solid fa-cloud-arrow-up" style="color: #0f766e;"></i>
            </div>
            <h4>1. Upload</h4>
            <p style="color: var(--text-muted); font-size: 0.9rem;">Send, Upload or Connect your dataset - CSV, Excel, SQLite</p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col2:
        st.markdown('''
        <div class="step-card">
            <div class="step-icon" style="background: linear-gradient(135deg, rgba(22,163,74,0.15), rgba(187,247,208,0.3));">
                <i class="fa-solid fa-wand-magic-sparkles" style="color: #16a34a;"></i>
            </div>
            <h4>2. Ask</h4>
            <p style="color: var(--text-muted); font-size: 0.9rem;">Ask questions in plain English - our AI understands you</p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col3:
        st.markdown('''
        <div class="step-card">
            <div class="step-icon" style="background: linear-gradient(135deg, rgba(217,119,6,0.15), rgba(253,230,138,0.3));">
                <i class="fa-solid fa-chart-line" style="color: #d97706;"></i>
            </div>
            <h4>3. Analyze</h4>
            <p style="color: var(--text-muted); font-size: 0.9rem;">Auto-analyze your data and receive automated insights</p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col4:
        st.markdown('''
        <div class="step-card">
            <div class="step-icon" style="background: linear-gradient(135deg, rgba(249,115,22,0.15), rgba(254,215,170,0.3));">
                <i class="fa-solid fa-share-nodes" style="color: #f97316;"></i>
            </div>
            <h4>4. Share</h4>
            <p style="color: var(--text-muted); font-size: 0.9rem;">Share and automate data refresh & report distribution</p>
        </div>
        ''', unsafe_allow_html=True)
    
    # ========== BENEFITS SECTION ==========
    st.markdown('''
    <div style="text-align: center; margin: clamp(2rem, 6vw, 4rem) 0 2rem; padding: 0 1rem;">
        <span class="section-badge">BENEFITS</span>
        <h2 style="font-size: clamp(1.25rem, 4vw, 2.5rem); font-weight: 700; margin-top: 1.5rem; line-height: 1.3;">
            How will AI Data Analyst Pro help you<br>make better decisions faster?
        </h2>
    </div>
    ''', unsafe_allow_html=True)
    
    # Row 1 of benefits
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('''
        <div class="benefit-card">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 1rem;">
                <i class="fa-solid fa-bolt" style="font-size: 1.5rem; color: #ea580c;"></i>
                <h4 style="margin: 0; font-weight: 600;">Instant Insights</h4>
            </div>
            <p style="color: var(--text-muted); font-size: 0.9rem; line-height: 1.6;">
                Instantly see the story your data is hiding. Just upload your data, and our AI will create compelling visuals for you.
            </p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col2:
        st.markdown('''
        <div class="benefit-card">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 1rem;">
                <i class="fa-solid fa-broom" style="font-size: 1.5rem; color: #f59e0b;"></i>
                <h4 style="margin: 0; font-weight: 600;">Effortless Data Cleaning</h4>
            </div>
            <p style="color: var(--text-muted); font-size: 0.9rem; line-height: 1.6;">
                Say goodbye to format errors and typos. AI handles cleaning automatically, so you can focus on insights.
            </p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col3:
        st.markdown('''
        <div class="benefit-card">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 1rem;">
                <i class="fa-solid fa-computer-mouse" style="font-size: 1.5rem; color: #f59e0b;"></i>
                <h4 style="margin: 0; font-weight: 600;">1-Click Explore & Play</h4>
            </div>
            <p style="color: var(--text-muted); font-size: 0.9rem; line-height: 1.6;">
                Customize with one-click selections like date grouping, segmentation, filtering, and theme changes.
            </p>
        </div>
        ''', unsafe_allow_html=True)
    
    # Row 2 of benefits
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('''
        <div class="benefit-card">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 1rem;">
                <i class="fa-solid fa-file-lines" style="font-size: 1.5rem; color: #0f766e;"></i>
                <h4 style="margin: 0; font-weight: 600;">Customizable Reports</h4>
            </div>
            <p style="color: var(--text-muted); font-size: 0.9rem; line-height: 1.6;">
                Create multiple reports tailored to different audiences. Include only the relevant charts, KPIs, or tabular data.
            </p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col2:
        st.markdown('''
        <div class="benefit-card">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 1rem;">
                <i class="fa-solid fa-users" style="font-size: 1.5rem; color: #ea580c;"></i>
                <h4 style="margin: 0; font-weight: 600;">Seamless Collaboration</h4>
            </div>
            <p style="color: var(--text-muted); font-size: 0.9rem; line-height: 1.6;">
                Share interactive visuals via email or link. Leave comments and annotations on charts for team discussions.
            </p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col3:
        st.markdown('''
        <div class="benefit-card">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 1rem;">
                <i class="fa-solid fa-arrows-rotate" style="font-size: 1.5rem; color: #ea580c;"></i>
                <h4 style="margin: 0; font-weight: 600;">Automated Workflows</h4>
            </div>
            <p style="color: var(--text-muted); font-size: 0.9rem; line-height: 1.6;">
                No more repetitive work. Schedule updates and reporting daily, weekly, monthly or quarterly.
            </p>
        </div>
        ''', unsafe_allow_html=True)
    
    # Row 3 of benefits
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('''
        <div class="benefit-card">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 1rem;">
                <i class="fa-solid fa-clock" style="font-size: 1.5rem; color: #ef4444;"></i>
                <h4 style="margin: 0; font-weight: 600;">Save 80% of your time</h4>
            </div>
            <p style="color: var(--text-muted); font-size: 0.9rem; line-height: 1.6;">
                Experience how quickly AI converts your data into actionable insights. No learning curve, no formulas.
            </p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col2:
        st.markdown('''
        <div class="benefit-card">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 1rem;">
                <i class="fa-solid fa-rocket" style="font-size: 1.5rem; color: #0f766e;"></i>
                <h4 style="margin: 0; font-weight: 600;">Built to be productive!</h4>
            </div>
            <p style="color: var(--text-muted); font-size: 0.9rem; line-height: 1.6;">
                Designed for on-demand analysis. It automates data combining, cleaning, pivoting, and visualizing.
            </p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col3:
        st.markdown('''
        <div class="benefit-card">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 1rem;">
                <i class="fa-solid fa-shield-halved" style="font-size: 1.5rem; color: #10b981;"></i>
                <h4 style="margin: 0; font-weight: 600;">Secure Data Processing</h4>
            </div>
            <p style="color: var(--text-muted); font-size: 0.9rem; line-height: 1.6;">
                Our platform ensures your data stays secure. Your raw data is never sent to LLMs or third-party systems.
            </p>
        </div>
        ''', unsafe_allow_html=True)
    
    # ========== WHO IS IT FOR SECTION ==========
    st.markdown('''
    <div style="text-align: center; margin: clamp(2rem, 6vw, 4rem) 0 2rem; padding: 0 1rem;">
        <span class="section-badge">WHO IS IT FOR</span>
        <h2 style="font-size: clamp(1.25rem, 4vw, 2.5rem); font-weight: 700; margin-top: 1.5rem; line-height: 1.3;">
            Use 90% of your time on actual analysis.<br>Not on correcting, cleaning and pivoting.
        </h2>
    </div>
    ''', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('''
        <div class="who-card" style="border-top: 4px solid #ea580c;">
            <p style="color: #ea580c !important; font-size: 0.85rem; font-weight: 600; margin-bottom: 0.5rem;">Make decisions 10X faster!</p>
            <h3 style="font-weight: 700; margin-bottom: 1rem;">For Management</h3>
            <p style="color: var(--text-muted); font-size: 0.9rem; line-height: 1.6;">
                <b>Pain Points:</b> Limited analytical skills, scattered data across tools, existing tools require expertise.<br><br>
                <b>Solution:</b> AI agents automate data cleaning and analysis, enabling quick, comprehensive reports without complexity.
            </p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col2:
        st.markdown('''
        <div class="who-card" style="border-top: 4px solid #0ea5e9;">
            <p style="color: #0369a1 !important; font-size: 0.85rem; font-weight: 600; margin-bottom: 0.5rem;">Work together seamlessly!</p>
            <h3 style="font-weight: 700; margin-bottom: 1rem;">For Teams</h3>
            <p style="color: var(--text-muted); font-size: 0.9rem; line-height: 1.6;">
                <b>Pain Points:</b> Disorganized files, limited data analyst availability, complex analytics tools.<br><br>
                <b>Solution:</b> Easy collaboration with team members, quick root cause analysis, and automated insights.
            </p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col3:
        st.markdown('''
        <div class="who-card" style="border-top: 4px solid #16a34a;">
            <p style="color: #16a34a !important; font-size: 0.85rem; font-weight: 600; margin-bottom: 0.5rem;">Easily manage client requests!</p>
            <h3 style="font-weight: 700; margin-bottom: 1rem;">For Consultants</h3>
            <p style="color: var(--text-muted); font-size: 0.9rem; line-height: 1.6;">
                <b>Pain Points:</b> Data spread across multiple client systems, time-consuming manual analysis.<br><br>
                <b>Solution:</b> Quick data combining, automated report generation, and seamless client deliverables.
            </p>
        </div>
        ''', unsafe_allow_html=True)
    
    # ========== WHY AI DATA ANALYSIS SECTION ==========
    st.markdown('''
    <div style="text-align: center; margin: clamp(2rem, 6vw, 4rem) 0 2rem; padding: 0 1rem;">
        <span class="section-badge">WHY AI DATA ANALYSIS?</span>
        <h2 style="font-size: clamp(1.25rem, 4vw, 2.5rem); font-weight: 700; margin-top: 1.5rem; line-height: 1.3;">
            How does AI Data Analyst Pro use<br>AI for Data Analytics
        </h2>
    </div>
    ''', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('''
        <div class="glass-card" style="margin-bottom: 1rem; background: linear-gradient(135deg, rgba(15,118,110,0.08), rgba(14,165,233,0.06));">
            <div style="display: flex; gap: 1rem; margin-bottom: 1rem;">
                <div style="width: 50px; height: 50px; background: rgba(15,118,110,0.12); border-radius: 12px; display: flex; align-items: center; justify-content: center;">
                    <i class="fa-solid fa-chart-column" style="font-size: 1.25rem; color: #0f766e;"></i>
                </div>
                <div style="width: 50px; height: 50px; background: rgba(14,165,233,0.1); border-radius: 12px; display: flex; align-items: center; justify-content: center;">
                    <i class="fa-solid fa-arrow-right" style="font-size: 1rem; color: #94a3b8;"></i>
                </div>
                <div style="width: 50px; height: 50px; background: rgba(16,185,129,0.12); border-radius: 12px; display: flex; align-items: center; justify-content: center;">
                    <i class="fa-solid fa-chart-line" style="font-size: 1.25rem; color: #10b981;"></i>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 0.5rem;">
                <i class="fa-solid fa-check" style="color: #ea580c;"></i>
                <h4 style="margin: 0; font-weight: 700;">Rapid Insight in Data</h4>
            </div>
            <p style="color: var(--text-muted); font-size: 0.9rem; line-height: 1.6;">
                Leverage AI data analytics to swiftly uncover trends and patterns, transforming raw data into actionable insights in seconds.
            </p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col2:
        st.markdown('''
        <div class="glass-card" style="margin-bottom: 1rem; background: linear-gradient(135deg, rgba(249,115,22,0.06), rgba(245,158,11,0.06));">
            <div style="display: flex; gap: 1rem; margin-bottom: 1rem;">
                <div style="width: 50px; height: 50px; background: rgba(15,118,110,0.12); border-radius: 12px; display: flex; align-items: center; justify-content: center;">
                    <i class="fa-solid fa-table" style="font-size: 1.25rem; color: #0f766e;"></i>
                </div>
                <div style="width: 50px; height: 50px; background: rgba(14,165,233,0.1); border-radius: 12px; display: flex; align-items: center; justify-content: center;">
                    <i class="fa-solid fa-arrow-right" style="font-size: 1rem; color: #94a3b8;"></i>
                </div>
                <div style="width: 50px; height: 50px; background: rgba(245,158,11,0.12); border-radius: 12px; display: flex; align-items: center; justify-content: center;">
                    <i class="fa-solid fa-chart-pie" style="font-size: 1.25rem; color: #f59e0b;"></i>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 0.5rem;">
                <i class="fa-solid fa-bolt" style="color: #f59e0b;"></i>
                <h4 style="margin: 0; font-weight: 700;">Effortless Visualization</h4>
            </div>
            <p style="color: var(--text-muted); font-size: 0.9rem; line-height: 1.6;">
                AI data analysis automates the creation of visually compelling charts and graphs, making complex data easy to understand.
            </p>
        </div>
        ''', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('''
        <div class="glass-card" style="background: linear-gradient(135deg, rgba(14,165,233,0.06), rgba(139,92,246,0.06));">
            <div style="width: 50px; height: 50px; background: rgba(14,165,233,0.12); border-radius: 12px; display: flex; align-items: center; justify-content: center; margin-bottom: 1rem;">
                <i class="fa-solid fa-comments" style="font-size: 1.25rem; color: #0ea5e9;"></i>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 0.5rem;">
                <i class="fa-solid fa-bars" style="color: #0f766e;"></i>
                <h4 style="margin: 0; font-weight: 700;">Quick Answers</h4>
            </div>
            <p style="color: var(--text-muted); font-size: 0.9rem; line-height: 1.6;">
                Get immediate answers to your data queries with AI-driven analysis, eliminating manual calculations and enhancing speed.
            </p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col2:
        st.markdown('''
        <div class="glass-card" style="background: linear-gradient(135deg, rgba(239,68,68,0.06), rgba(249,115,22,0.06));">
            <div style="width: 50px; height: 50px; background: rgba(239,68,68,0.1); border-radius: 12px; display: flex; align-items: center; justify-content: center; margin-bottom: 1rem;">
                <i class="fa-solid fa-shield-halved" style="font-size: 1.25rem; color: #ef4444;"></i>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 0.5rem;">
                <i class="fa-solid fa-lock" style="color: #ef4444;"></i>
                <h4 style="margin: 0; font-weight: 700;">Data Privacy First</h4>
            </div>
            <p style="color: var(--text-muted); font-size: 0.9rem; line-height: 1.6;">
                Our AI ensures your data stays secure by never sharing your raw data with LLMs or third-party systems.
            </p>
        </div>
        ''', unsafe_allow_html=True)
    
    # ========== PHILOSOPHY SECTION ==========
    st.markdown('''
    <div class="glass-card" style="background: linear-gradient(135deg, rgba(15,118,110,0.1) 0%, rgba(14,165,233,0.08) 50%, rgba(139,92,246,0.06) 100%);
         padding: clamp(1.5rem, 4vw, 3rem) clamp(1rem, 3vw, 2rem); margin: 4rem 0; text-align: center; border-radius: clamp(18px, 4vw, 28px);">
        <span class="section-badge">Our Philosophy</span>
        <h2 style="font-size: clamp(1.25rem, 4vw, 2.25rem); font-weight: 700; margin-top: 1.5rem; margin-bottom: 1rem;">
            At AI Data Analyst Pro, we believe
        </h2>
        <p style="color: var(--text-muted); font-size: clamp(0.85rem, 2vw, 1rem); max-width: 800px; margin: 0 auto 2rem; line-height: 1.7; padding: 0 0.5rem;">
            that everyone should be able to analyse their data and should not have to rely on others to make sense of it. 
            Our core values are driven by this belief, which is why we relentlessly focus on 'safety', 'ease of use', 
            'data analysis your way,' and 'automation'.
        </p>
        <div style="display: flex; justify-content: center; gap: clamp(1.5rem, 4vw, 3rem); flex-wrap: wrap; margin-top: 2rem;">
            <div style="text-align: center; min-width: 100px;">
                <span style="font-size: clamp(1.5rem, 4vw, 2rem);">🔒</span>
                <h4 style="margin: 0.5rem 0 0.25rem; font-size: clamp(0.85rem, 2vw, 1rem);">Safety First</h4>
                <p style="color: var(--text-muted); font-size: clamp(0.75rem, 1.8vw, 0.85rem);">No leaking of sensitive data</p>
            </div>
            <div style="text-align: center; min-width: 100px;">
                <span style="font-size: clamp(1.5rem, 4vw, 2rem);">⚡</span>
                <h4 style="margin: 0.5rem 0 0.25rem; font-size: clamp(0.85rem, 2vw, 1rem);">80% time saved</h4>
                <p style="color: var(--text-muted); font-size: clamp(0.75rem, 1.8vw, 0.85rem);">analysis + repetitive tasks</p>
            </div>
            <div style="text-align: center; min-width: 100px;">
                <span style="font-size: clamp(1.5rem, 4vw, 2rem);">🚀</span>
                <h4 style="margin: 0.5rem 0 0.25rem; font-size: clamp(0.85rem, 2vw, 1rem);">Start now</h4>
                <p style="color: var(--text-muted); font-size: clamp(0.75rem, 1.8vw, 0.85rem);">no tech integration</p>
            </div>
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    # ========== CTA SECTION ==========
    st.markdown('''
    <div style="text-align: center; margin: 3rem 0; padding: 0 1rem;">
        <span class="section-badge">WE ARE GROWING</span>
        <h2 style="font-size: clamp(1.25rem, 4vw, 2rem); font-weight: 700; margin-top: 1.5rem; line-height: 1.3;">
            Try AI Data Analyst Pro now.<br>
            Say Good-Bye to SQL, vLOOKUP and Pivot tables.
        </h2>
    </div>
    ''', unsafe_allow_html=True)

# ============================================================
#                    PRICING PAGE
# ============================================================

def show_pricing_page():
    """Display pricing page"""
    # Safety check
    if not st.session_state.user:
        st.warning("Please log in to view pricing.")
        return
    
    st.markdown('''
    <div style="text-align: center; margin-bottom: 2rem; padding: 0 1rem;">
        <h1 style="font-size: clamp(1.5rem, 5vw, 2.5rem); margin-bottom: 0.5rem;"><i class="fa-solid fa-gem" style="color: var(--primary); margin-right: 12px;"></i>Choose Your Plan</h1>
        <p style="color: var(--text-muted); font-size: clamp(0.9rem, 2.5vw, 1.1rem);">Unlock the full power of AI data analysis</p>
    </div>
    ''', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="pricing-card">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;"><i class="fa-solid fa-gift" style="color: #5b7a7c;"></i></div>
            <h3 style="margin: 0; color: #102a2e; font-weight: 700;">Free</h3>
            <h2 style="color: #0f766e;">₹0</h2>
            <p style="color: #5b7a7c;">Forever free</p>
            <hr style="margin: 1rem 0;">
            <p style="color: #2f4f52;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>5 queries/day</p>
            <p style="color: #2f4f52;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>Basic charts</p>
            <p style="color: #2f4f52;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>CSV upload</p>
            <p style="color: #94a3b8;"><i class="fa-solid fa-xmark" style="margin-right: 8px;"></i>Query history</p>
            <p style="color: #94a3b8;"><i class="fa-solid fa-xmark" style="margin-right: 8px;"></i>PDF export</p>
        </div>
        """, unsafe_allow_html=True)
        if st.session_state.user["subscription_tier"] == "free":
            st.button("Current Plan", disabled=True, key="free_btn")
    
    with col2:
        st.markdown("""
        <div class="pricing-card" style="border-color: #0ea5e9; border-width: 2px;">
            <div style="background: linear-gradient(135deg, #0ea5e9, #0284c7); color: white; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.7rem; display: inline-block; margin-bottom: 0.5rem;">POPULAR</div>
            <div style="font-size: 2rem; margin-bottom: 0.5rem;"><i class="fa-solid fa-rocket" style="color: #0ea5e9;"></i></div>
            <h3 style="margin: 0; color: #102a2e; font-weight: 700;">Starter</h3>
            <h2 style="color: #0f766e;">₹499<span style="font-size: 1rem; color: #5b7a7c;">/mo</span></h2>
            <p style="color: #5b7a7c;">For individuals</p>
            <hr style="margin: 1rem 0;">
            <p style="color: #2f4f52;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>50 queries/day</p>
            <p style="color: #2f4f52;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>All chart types</p>
            <p style="color: #2f4f52;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>Excel upload</p>
            <p style="color: #2f4f52;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>Query history</p>
            <p style="color: #94a3b8;"><i class="fa-solid fa-xmark" style="margin-right: 8px;"></i>PDF export</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.user["subscription_tier"] == "starter":
            st.button("Current Plan", disabled=True, key="starter_current")
        else:
            if st.button("Upgrade to Starter", key="starter_btn", use_container_width=True):
                upgrade_user_subscription(st.session_state.user["id"], "starter", 30)
                st.session_state.user["subscription_tier"] = "starter"
                st.success("Upgraded to Starter! (Demo Mode)")
                st.balloons()
                st.rerun()
    
    with col3:
        st.markdown("""
        <div class="pricing-card" style="border-color: #f59e0b; border-width: 2px;">
            <div style="background: linear-gradient(135deg, #f59e0b, #d97706); color: white; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.7rem; display: inline-block; margin-bottom: 0.5rem;">BEST VALUE</div>
            <div style="font-size: 2rem; margin-bottom: 0.5rem;"><i class="fa-solid fa-star" style="color: #f59e0b;"></i></div>
            <h3 style="margin: 0; color: #102a2e; font-weight: 700;">Pro</h3>
            <h2 style="color: #0f766e;">₹1,499<span style="font-size: 1rem; color: #5b7a7c;">/mo</span></h2>
            <p style="color: #5b7a7c;">For teams</p>
            <hr style="margin: 1rem 0;">
            <p style="color: #2f4f52;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>500 queries/day</p>
            <p style="color: #2f4f52;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>All chart types</p>
            <p style="color: #2f4f52;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>All file types</p>
            <p style="color: #2f4f52;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>Full history</p>
            <p style="color: #2f4f52;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>PDF export</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.user["subscription_tier"] == "pro":
            st.button("Current Plan", disabled=True, key="pro_current")
        else:
            if st.button("Upgrade to Pro", key="pro_btn", use_container_width=True):
                upgrade_user_subscription(st.session_state.user["id"], "pro", 30)
                st.session_state.user["subscription_tier"] = "pro"
                st.success("Upgraded to Pro! (Demo Mode)")
                st.balloons()
                st.rerun()
    
    with col4:
        st.markdown("""
        <div class="pricing-card" style="border-color: #10b981; border-width: 2px;">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;"><i class="fa-solid fa-building" style="color: #10b981;"></i></div>
            <h3 style="margin: 0; color: #102a2e; font-weight: 700;">Enterprise</h3>
            <h2 style="color: #0f766e;">₹4,999<span style="font-size: 1rem; color: #5b7a7c;">/mo</span></h2>
            <p style="color: #5b7a7c;">For organizations</p>
            <hr style="margin: 1rem 0;">
            <p style="color: #2f4f52;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>Unlimited queries</p>
            <p style="color: #2f4f52;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>Priority support</p>
            <p style="color: #2f4f52;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>Custom integrations</p>
            <p style="color: #2f4f52;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>Full history</p>
            <p style="color: #2f4f52;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>All exports</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.user["subscription_tier"] == "enterprise":
            st.button("Current Plan", disabled=True, key="enterprise_current")
        else:
            if st.button("Upgrade to Enterprise", key="enterprise_btn", use_container_width=True):
                upgrade_user_subscription(st.session_state.user["id"], "enterprise", 30)
                st.session_state.user["subscription_tier"] = "enterprise"
                st.success("Upgraded to Enterprise! (Demo Mode)")
                st.balloons()
                st.rerun()
    
    # Payment Notice
    st.divider()
    st.info("**Demo Mode:** Upgrades are instant for testing. Real payments via Razorpay coming soon!")

# ============================================================
#                    MAIN APPLICATION
# ============================================================

def show_main_app():
    """Display main application"""
    user = st.session_state.user
    if not user:
        st.session_state.authenticated = False
        st.rerun()
        return
    
    tier = user.get("subscription_tier", "free")
    
    # --- SIDEBAR ---
    with st.sidebar:
        # User profile section
        user_name = user.get("name", "User")
        st.markdown(f'<h3 style="color: #ffffff;"><i class="fa-solid fa-user-circle" style="margin-right: 8px; color: #0f766e;"></i>{user_name}</h3>', unsafe_allow_html=True)
        tier_class = f"tier-{tier}"
        st.markdown(f'<span class="tier-badge {tier_class}">{tier.upper()}</span>', unsafe_allow_html=True)
        
        # Query limit indicator
        try:
            user_info = get_user_info(user["id"])
            limits = {"free": 5, "starter": 50, "pro": 500, "enterprise": 99999}
            if user_info:
                queries_today = user_info["queries_today"] if user_info.get("last_query_date") == datetime.now().date().isoformat() else 0
                remaining = limits.get(tier, 5) - queries_today
            else:
                remaining = limits.get(tier, 5)
        except Exception:
            remaining = limits.get(tier, 5) if 'limits' in dir() else 5
            limits = {"free": 5, "starter": 50, "pro": 500, "enterprise": 99999}
        remaining = max(0, remaining)  # Ensure non-negative
        total = max(1, limits.get(tier, 5))  # Prevent division by zero
        percentage = min(100, (remaining / total) * 100)
        
        # Custom styled progress bar
        st.markdown(f'''
        <div style="margin: 1rem 0;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                <span style="font-size: 0.8rem; color: #a0aec0;">Queries</span>
                <span style="font-size: 0.8rem; color: #e2e8f0; font-weight: 600;">{remaining}/{total}</span>
            </div>
            <div style="background: rgba(255,255,255,0.1); border-radius: 10px; height: 10px; overflow: hidden;">
                <div style="
                    width: {percentage}%;
                    height: 100%;
                    background: linear-gradient(90deg, #0f766e, #f97316, #14b8a6);
                    border-radius: 10px;
                    transition: width 0.5s ease;
                "></div>
            </div>
            <p style="font-size: 0.75rem; color: #94a3b8; margin-top: 6px; text-align: center;">
                <i class="fa-solid fa-bolt" style="color: #f59e0b; margin-right: 4px;"></i>
                {remaining} remaining today
            </p>
        </div>
        ''', unsafe_allow_html=True)
        
        st.divider()
        
        # Navigation
        st.markdown('<h4 style="margin-bottom: 10px; color: #ffffff !important;"><i class="fa-solid fa-compass" style="margin-right: 8px; color: #0f766e;"></i>Navigation</h4>', unsafe_allow_html=True)
        page = st.radio(
            "Go to:",
            ["Query Data", "Data Sources", "Query History", "Pricing", "Settings"],
            label_visibility="collapsed"
        )
        
        st.divider()
        
        # Quick upgrade button for free users
        if tier == "free":
            if st.button("Upgrade Now", use_container_width=True):
                st.session_state.show_pricing = True
                st.rerun()
        
        # Logout button
        if st.button("Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()
    
    # --- MAIN CONTENT ---
    st.markdown(f'<h1 class="main-header"><i class="fa-solid fa-robot" style="margin-right: 12px;"></i>AI Data Analyst Pro</h1>', unsafe_allow_html=True)
    
    # Route to different pages
    if page == "Pricing" or st.session_state.get("show_pricing"):
        st.session_state.show_pricing = False
        try:
            show_pricing_page()
        except Exception as e:
            st.error(f"Error loading pricing page. Please refresh.")
        return
    
    elif page == "Data Sources":
        try:
            show_data_sources_page()
        except Exception as e:
            st.error(f"Error loading data sources. Please refresh.")
        return
    
    elif page == "Query History":
        try:
            show_history_page()
        except Exception as e:
            st.error(f"Error loading history. Please refresh.")
        return
    
    elif page == "Settings":
        try:
            show_settings_page()
        except Exception as e:
            st.error(f"Error loading settings. Please refresh.")
        return
    
    # --- QUERY DATA PAGE (Default) ---
    
    # Current database info
    db_name = os.path.basename(st.session_state.current_db) if st.session_state.current_db else "No database selected"
    
    # Check if database exists
    if not st.session_state.current_db or not os.path.exists(st.session_state.current_db):
        st.session_state.current_db = DEFAULT_DB_PATH
        db_name = os.path.basename(DEFAULT_DB_PATH)
        if not os.path.exists(DEFAULT_DB_PATH):
            st.error("No database available. Please upload a file from the Data Sources page.")
            return
    
    st.markdown(f'''
    <div class="glass-card" style="padding: 0.75rem 1.25rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 10px;
         background: linear-gradient(135deg, rgba(15,118,110,0.08), rgba(14,165,233,0.08));">
        <i class="fa-solid fa-database" style="color: var(--primary); font-size: 1.1rem;"></i>
        <span style="font-weight: 600;">Active Database:</span>
        <span style="color: var(--primary); font-weight: 500;">{db_name}</span>
    </div>
    ''', unsafe_allow_html=True)
    
    # Query input
    st.markdown('<h3><i class="fa-solid fa-message" style="color: var(--primary); margin-right: 10px;"></i>Ask Your Data</h3>', unsafe_allow_html=True)
    
    with st.form("query_form"):
        user_query = st.text_input(
            "Enter your question:",
            placeholder="e.g., Show me top 10 customers by total spending"
        )
        
        col1, col2 = st.columns([3, 1])
        with col1:
            submitted = st.form_submit_button("Run Analysis", use_container_width=True)
        with col2:
            show_sql = st.form_submit_button("Show SQL Only")
    
    # Process query
    if submitted or show_sql:
        if user_query:
            # Check query limit
            try:
                can_query, remaining = check_query_limit(user["id"], tier)
            except Exception:
                can_query, remaining = True, 5
            
            if not can_query:
                st.error(f"Daily query limit reached! Upgrade your plan for more queries.")
                if tier == "free":
                    st.info("Upgrade to Starter for 50 queries/day")
            else:
                with st.spinner("AI is analyzing your question..."):
                    try:
                        sql_code = get_ai_sql(user_query, st.session_state.current_db)
                        st.session_state.sql_code = sql_code
                        st.session_state.current_question = user_query
                        
                        if not show_sql:
                            result = run_query(sql_code, st.session_state.current_db)
                            st.session_state.result_df = result
                            
                            # Update query count
                            try:
                                update_query_count(user["id"])
                            except Exception:
                                pass
                            
                            # Save to history (for paid users)
                            if tier != "free":
                                try:
                                    result_preview = result.head(10).to_string() if isinstance(result, pd.DataFrame) else str(result)
                                    save_query_history(user["id"], user_query, sql_code, result_preview)
                                except Exception:
                                    pass
                    except Exception as e:
                        st.error(f"An error occurred while processing your query. Please try again.")
        else:
            st.warning("Please enter a question first!")
    
    # Display results
    if st.session_state.sql_code:
        st.markdown('<h3><i class="fa-solid fa-code" style="color: var(--primary); margin-right: 10px;"></i>Generated SQL</h3>', unsafe_allow_html=True)
        st.code(st.session_state.sql_code, language="sql")
    
    if st.session_state.result_df is not None:
        result = st.session_state.result_df
        
        if isinstance(result, pd.DataFrame):
            # Dashboard Header
            query_title = st.session_state.current_question or "Query Results"
            st.markdown(f'''
            <div class="dashboard-header">
                <h2><i class="fa-solid fa-chart-line" style="margin-right: 10px;"></i>{query_title[:50]}{"..." if len(query_title) > 50 else ""}</h2>
            </div>
            ''', unsafe_allow_html=True)
            
            # Dashboard Container Start
            st.markdown('<div class="dashboard-container">', unsafe_allow_html=True)
            
            # KPI Cards Row - Auto-generate from numeric columns
            numeric_cols = result.select_dtypes(include=['number']).columns.tolist()
            if numeric_cols:
                kpi_colors = ['blue', 'green', 'purple', 'orange']
                num_kpis = min(4, len(numeric_cols))
                kpi_cols = st.columns(num_kpis)
                
                for i, col_name in enumerate(numeric_cols[:num_kpis]):
                    with kpi_cols[i]:
                        try:
                            col_data = result[col_name].dropna()
                            if len(col_data) == 0:
                                formatted_value = "N/A"
                                stat_label = col_name[:25]
                            else:
                                # Determine best stat to show
                                if col_data.nunique() == len(col_data):  # Likely unique values, show sum
                                    stat_value = col_data.sum()
                                    stat_label = f"Total {col_name}"
                                else:
                                    stat_value = col_data.mean()
                                    stat_label = f"Avg. {col_name}"
                                formatted_value = safe_format_value(stat_value)
                        except Exception:
                            formatted_value = "N/A"
                            stat_label = col_name[:25]
                        
                        st.markdown(f'''
                        <div class="kpi-card">
                            <div class="kpi-label">{stat_label[:25]}</div>
                            <div class="kpi-value {kpi_colors[i % 4]}">{formatted_value}</div>
                        </div>
                        ''', unsafe_allow_html=True)
                
                # Additional KPI: Row count and column count
                kpi_cols2 = st.columns(4)
                with kpi_cols2[0]:
                    st.markdown(f'''
                    <div class="kpi-card">
                        <div class="kpi-label">Total Records</div>
                        <div class="kpi-value blue">{len(result):,}</div>
                    </div>
                    ''', unsafe_allow_html=True)
                with kpi_cols2[1]:
                    st.markdown(f'''
                    <div class="kpi-card">
                        <div class="kpi-label">Data Columns</div>
                        <div class="kpi-value purple">{len(result.columns)}</div>
                    </div>
                    ''', unsafe_allow_html=True)
                if len(numeric_cols) > 0:
                    try:
                        max_val = result[numeric_cols[0]].dropna().max() if len(result[numeric_cols[0]].dropna()) > 0 else None
                        min_val = result[numeric_cols[0]].dropna().min() if len(result[numeric_cols[0]].dropna()) > 0 else None
                    except Exception:
                        max_val = None
                        min_val = None
                    with kpi_cols2[2]:
                        st.markdown(f'''
                        <div class="kpi-card">
                            <div class="kpi-label">Max {numeric_cols[0][:15]}</div>
                            <div class="kpi-value green">{safe_format_value(max_val)}</div>
                        </div>
                        ''', unsafe_allow_html=True)
                    with kpi_cols2[3]:
                        st.markdown(f'''
                        <div class="kpi-card">
                            <div class="kpi-label">Min {numeric_cols[0][:15]}</div>
                            <div class="kpi-value orange">{safe_format_value(min_val)}</div>
                        </div>
                        ''', unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Export buttons row
            exp_col1, exp_col2, exp_col3 = st.columns(3)
            with exp_col1:
                try:
                    csv_data = export_to_csv(result)
                    st.download_button(
                        "📥 Download CSV",
                        csv_data,
                        file_name="results.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                except Exception:
                    st.button("📥 CSV Error", disabled=True, use_container_width=True)
            with exp_col2:
                try:
                    excel_data = export_to_excel(result)
                    st.download_button(
                        "📥 Download Excel",
                        excel_data,
                        file_name="results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                except Exception:
                    st.button("📥 Excel Error", disabled=True, use_container_width=True)
            with exp_col3:
                if tier in ["pro", "enterprise"]:
                    try:
                        pdf_data = generate_pdf_report(result, st.session_state.current_question or "Query", st.session_state.sql_code or "")
                        if pdf_data:
                            st.download_button(
                                "📥 Download PDF",
                                pdf_data,
                                file_name="report.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                        else:
                            st.button("📥 PDF", disabled=True, help="Install reportlab for PDF export", use_container_width=True)
                    except Exception:
                        st.button("📥 PDF", disabled=True, help="PDF generation failed", use_container_width=True)
                else:
                    st.button("📥 PDF (Pro)", disabled=True, help="Upgrade to Pro for PDF export", use_container_width=True)
            
            # Charts Grid Layout
            if len(result.columns) > 1 and len(numeric_cols) > 0:
                st.markdown("<br>", unsafe_allow_html=True)
                
                try:
                    # Prepare chart data - ensure we have valid data
                    chart_data = result.dropna(subset=[numeric_cols[0]]).head(20)
                    if len(chart_data) == 0:
                        st.info("No valid data for chart visualization.")
                    else:
                        label_col = result.columns[0]
                        chart_col1, chart_col2 = st.columns(2)
                        
                        with chart_col1:
                            # Bar Chart
                            st.markdown('''
                            <div class="chart-card">
                                <div class="chart-title"><i class="fa-solid fa-chart-column"></i>Distribution Analysis</div>
                            </div>
                            ''', unsafe_allow_html=True)
                            try:
                                fig_bar = px.bar(
                                    chart_data.head(15), 
                                    x=label_col, 
                                    y=numeric_cols[0],
                                    color_discrete_sequence=['#0ea5e9'],
                                    template='plotly_white'
                                )
                                fig_bar.update_layout(
                                    margin=dict(l=20, r=20, t=30, b=40),
                                    height=300,
                                    xaxis_title="",
                                    yaxis_title=numeric_cols[0],
                                    font=dict(size=11)
                                )
                                fig_bar.update_xaxes(tickangle=45)
                                st.plotly_chart(fig_bar, use_container_width=True)
                            except Exception:
                                try:
                                    st.bar_chart(result.set_index(label_col)[numeric_cols[0]].head(15))
                                except Exception:
                                    st.info("Bar chart not available for this data.")
                        
                        with chart_col2:
                            # Pie Chart
                            st.markdown('''
                            <div class="chart-card">
                                <div class="chart-title"><i class="fa-solid fa-chart-pie"></i>Proportional Breakdown</div>
                            </div>
                            ''', unsafe_allow_html=True)
                            try:
                                pie_data = chart_data.head(10).copy()
                                pie_data[numeric_cols[0]] = pie_data[numeric_cols[0]].abs()
                                fig_pie = px.pie(
                                    pie_data, 
                                    names=label_col, 
                                    values=numeric_cols[0],
                                    color_discrete_sequence=px.colors.qualitative.Set2,
                                    template='plotly_white'
                                )
                                fig_pie.update_layout(
                                    margin=dict(l=20, r=20, t=30, b=20),
                                    height=300,
                                    font=dict(size=11),
                                    showlegend=True,
                                    legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02)
                                )
                                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                                st.plotly_chart(fig_pie, use_container_width=True)
                            except Exception:
                                st.info("Pie chart not available for this data.")
                        
                        # Second row of charts
                        chart_col3, chart_col4 = st.columns(2)
                        
                        with chart_col3:
                            # Line Chart
                            st.markdown('''
                            <div class="chart-card">
                                <div class="chart-title"><i class="fa-solid fa-chart-line"></i>Trend Analysis</div>
                            </div>
                            ''', unsafe_allow_html=True)
                            try:
                                fig_line = px.line(
                                    chart_data.head(20), 
                                    x=label_col, 
                                    y=numeric_cols[0],
                                    markers=True,
                                    color_discrete_sequence=['#0ea5e9'],
                                    template='plotly_white'
                                )
                                fig_line.update_layout(
                                    margin=dict(l=20, r=20, t=30, b=40),
                                    height=300,
                                    xaxis_title="",
                                    yaxis_title=numeric_cols[0],
                                    font=dict(size=11)
                                )
                                fig_line.update_xaxes(tickangle=45)
                                st.plotly_chart(fig_line, use_container_width=True)
                            except Exception:
                                try:
                                    st.line_chart(result.set_index(label_col)[numeric_cols[0]].head(20))
                                except Exception:
                                    st.info("Line chart not available for this data.")
                        
                        with chart_col4:
                            # Horizontal Bar Chart
                            st.markdown('''
                            <div class="chart-card">
                                <div class="chart-title"><i class="fa-solid fa-bars"></i>Ranking View</div>
                            </div>
                            ''', unsafe_allow_html=True)
                            try:
                                sorted_data = chart_data.head(10).sort_values(by=numeric_cols[0], ascending=True)
                                fig_hbar = px.bar(
                                    sorted_data, 
                                    y=label_col, 
                                    x=numeric_cols[0],
                                    orientation='h',
                                    color=numeric_cols[0],
                                    color_continuous_scale='Viridis',
                                    template='plotly_white'
                                )
                                fig_hbar.update_layout(
                                    margin=dict(l=20, r=20, t=30, b=20),
                                    height=300,
                                    xaxis_title=numeric_cols[0],
                                    yaxis_title="",
                                    font=dict(size=11),
                                    coloraxis_showscale=False
                                )
                                st.plotly_chart(fig_hbar, use_container_width=True)
                            except Exception:
                                st.info("Ranking chart not available for this data.")
                except Exception:
                    st.info("Charts could not be generated for this data. Showing table view only.")
            
            # Data Table Section
            st.markdown('''
            <div class="chart-card">
                <div class="chart-title"><i class="fa-solid fa-table"></i>Data Table</div>
            </div>
            ''', unsafe_allow_html=True)
            try:
                st.dataframe(result, use_container_width=True, height=400)
                st.caption(f"Showing {len(result)} rows × {len(result.columns)} columns")
            except Exception:
                st.table(result.head(50))
            
            # Close dashboard container
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.error(result)

# ============================================================
#                    DATA SOURCES PAGE
# ============================================================

def show_data_sources_page():
    """Data sources management page"""
    st.markdown('<h3><i class="fa-solid fa-folder-open" style="color: var(--primary); margin-right: 10px;"></i>Data Sources</h3>', unsafe_allow_html=True)
    
    tier = st.session_state.user["subscription_tier"]
    
    # File upload section
    st.markdown('<h4><i class="fa-solid fa-cloud-arrow-up" style="color: var(--secondary); margin-right: 8px;"></i>Upload New Data</h4>', unsafe_allow_html=True)
    
    # File type restrictions based on tier
    if tier == "free":
        allowed_types = ["csv"]
        st.caption("Free tier: CSV files only. Upgrade for Excel & SQLite support.")
    elif tier == "starter":
        allowed_types = ["csv", "xlsx", "xls"]
        st.caption("Starter tier: CSV and Excel files")
    else:
        allowed_types = ["csv", "xlsx", "xls", "sqlite", "db"]
        st.caption("Pro/Enterprise: All file types supported")
    
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=allowed_types,
        help="Upload your data file to start analyzing"
    )
    
    if uploaded_file:
        file_ext = uploaded_file.name.split('.')[-1].lower()
        
        if st.button("Process File", use_container_width=True):
            with st.spinner("Processing file..."):
                try:
                    user_id = st.session_state.user["id"]
                    file_path = save_uploaded_file(user_id, uploaded_file, file_ext)
                    
                    # Convert to SQLite if needed
                    if file_ext == "csv":
                        db_path = file_path.replace('.csv', '.db')
                        csv_to_sqlite(file_path, db_path)
                        st.session_state.current_db = db_path
                    elif file_ext in ["xlsx", "xls"]:
                        db_path = file_path.replace(f'.{file_ext}', '.db')
                        excel_to_sqlite(file_path, db_path)
                        st.session_state.current_db = db_path
                    elif file_ext in ["sqlite", "db"]:
                        st.session_state.current_db = file_path
                    
                    st.success(f"File processed! Now using: {uploaded_file.name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error processing file: {e}")
    
    st.divider()
    
    # User's uploaded files
    st.markdown('<h4><i class="fa-solid fa-hard-drive" style="color: var(--secondary); margin-right: 8px;"></i>Your Data Sources</h4>', unsafe_allow_html=True)
    
    user_files = get_user_files(st.session_state.user["id"])
    
    # Default database option
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown('<p><i class="fa-solid fa-database" style="color: #0f766e; margin-right: 8px;"></i><b>Chinook Sample Database</b> (Default)</p>', unsafe_allow_html=True)
    with col2:
        if st.button("Use", key="use_default"):
            st.session_state.current_db = DEFAULT_DB_PATH
            st.success("Switched to Chinook database")
            st.rerun()
    with col3:
        if st.session_state.current_db == DEFAULT_DB_PATH:
            st.markdown('<span style="color: #10b981;"><i class="fa-solid fa-circle-check"></i> Active</span>', unsafe_allow_html=True)
    
    # List user files
    for file in user_files:
        file_id, filename, file_path, file_type, uploaded_at = file
        db_path = file_path.replace(f'.{file_type}', '.db') if file_type in ['csv', 'xlsx', 'xls'] else file_path
        
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.markdown(f'<p><i class="fa-solid fa-file" style="color: #0f766e; margin-right: 8px;"></i><b>{filename}</b></p>', unsafe_allow_html=True)
            st.caption(f"Uploaded: {uploaded_at[:10]}")
        with col2:
            if st.button("Use", key=f"use_{file_id}"):
                if os.path.exists(db_path):
                    st.session_state.current_db = db_path
                    st.success(f"Switched to {filename}")
                    st.rerun()
                else:
                    st.error("Database file not found")
        with col3:
            if st.session_state.current_db == db_path:
                st.markdown('<span style="color: #10b981;"><i class="fa-solid fa-circle-check"></i> Active</span>', unsafe_allow_html=True)
    
    if not user_files:
        st.info("No files uploaded yet. Upload your first dataset above!")

# ============================================================
#                    HISTORY PAGE
# ============================================================

def show_history_page():
    """Query history page"""
    st.markdown('<h3><i class="fa-solid fa-clock-rotate-left" style="color: var(--primary); margin-right: 10px;"></i>Query History</h3>', unsafe_allow_html=True)
    
    tier = st.session_state.user["subscription_tier"]
    
    if tier == "free":
        st.warning("Query history is available on Starter plan and above.")
        st.button("Upgrade to Starter", on_click=lambda: st.session_state.update({"show_pricing": True}))
        return
    
    # Get history
    history = get_query_history(st.session_state.user["id"])
    
    if history:
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("Clear History"):
                clear_query_history(st.session_state.user["id"])
                st.success("History cleared!")
                st.rerun()
        
        for idx, (question, sql, preview, timestamp) in enumerate(history):
            timestamp_display = timestamp[:16] if timestamp and len(timestamp) >= 16 else (timestamp or "Unknown")
            question_display = question[:50] if question else "No question"
            with st.expander(f"**{question_display}{'...' if question and len(question) > 50 else ''}** - {timestamp_display}"):
                st.markdown("**Question:**")
                st.write(question)
                st.markdown("**SQL Query:**")
                st.code(sql, language="sql")
                if preview:
                    st.markdown("**Result Preview:**")
                    st.text(preview[:300] + "..." if len(preview) > 300 else preview)
                
                # Re-run button
                if st.button("Run Again", key=f"rerun_{idx}"):
                    result = run_query(sql, st.session_state.current_db)
                    st.session_state.result_df = result
                    st.session_state.sql_code = sql
                    st.session_state.current_question = question
    else:
        st.info("No queries yet. Start analyzing your data!")

# ============================================================
#                    SETTINGS PAGE
# ============================================================

def show_settings_page():
    """Settings page"""
    st.markdown('<h3><i class="fa-solid fa-gear" style="color: var(--primary); margin-right: 10px;"></i>Settings</h3>', unsafe_allow_html=True)
    
    user = st.session_state.user
    user_info = get_user_info(user["id"])
    
    # Handle case where user_info is None
    if user_info is None:
        st.error("Unable to load user information. Please log out and log in again.")
        return
    
    # Account info
    st.markdown('<h4><i class="fa-solid fa-user" style="color: var(--secondary); margin-right: 8px;"></i>Account Information</h4>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Name", value=user_info["name"], disabled=True)
    with col2:
        st.text_input("Email", value=user_info["email"], disabled=True)
    
    st.divider()
    
    # Subscription info
    st.markdown('<h4><i class="fa-solid fa-crown" style="color: var(--warning); margin-right: 8px;"></i>Subscription</h4>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        tier_display = user_info["subscription_tier"].upper() if user_info["subscription_tier"] else "FREE"
        st.text_input("Current Plan", value=tier_display, disabled=True)
    with col2:
        expires = user_info["subscription_expires"]
        if expires and len(expires) >= 10:
            expires_display = expires[:10]
        else:
            expires_display = "N/A"
        st.text_input("Expires", value=expires_display, disabled=True)
    
    if user_info["subscription_tier"] != "enterprise":
        if st.button("Upgrade Plan"):
            st.session_state.show_pricing = True
            st.rerun()
    
    st.divider()
    
    # Danger zone
    st.markdown('<h4><i class="fa-solid fa-triangle-exclamation" style="color: var(--error); margin-right: 8px;"></i>Danger Zone</h4>', unsafe_allow_html=True)
    with st.expander("Delete Account"):
        st.warning("This action cannot be undone. All your data will be permanently deleted.")
        if st.button("Delete My Account", type="secondary"):
            st.error("Contact support@yourdomain.com to delete your account")

# ============================================================
#                    MAIN ENTRY POINT
# ============================================================

try:
    if st.session_state.authenticated:
        if st.session_state.user is None:
            st.session_state.authenticated = False
            st.rerun()
        else:
            show_main_app()
    else:
        show_auth_page()
except Exception as e:
    st.error("Something went wrong. Please refresh the page.")
    if st.button("🔄 Refresh App"):
        st.session_state.clear()
        st.rerun()

# --- FOOTER ---
st.markdown(
    """
    <div class="footer-container">
        <div class="footer-brand">
            <span class="footer-logo"><i class="fa-solid fa-chart-line"></i></span>
            <span class="footer-title">AI Data Analyst Pro</span>
        </div>
        <p class="footer-tagline">Transform your data into insights with the power of AI.</p>
        <div class="footer-links">
            <a href="https://www.linkedin.com/in/sukumar-jujjuvarapu/" target="_blank" class="footer-link">
                <i class="fa-brands fa-linkedin"></i> LinkedIn
            </a>
            <span class="footer-divider">•</span>
            <a href="https://github.com/SukumarJujjuvarapu" target="_blank" class="footer-link">
                <i class="fa-brands fa-github"></i> GitHub
            </a>
            <span class="footer-divider">•</span>
            <a href="https://sukumarjujjuvarapu.github.io/" target="_blank" class="footer-link">
                <i class="fa-solid fa-globe"></i> Portfolio
            </a>
        </div>
        <div class="footer-bottom">
            <p><i class="fa-solid fa-flag" style="color: #ff9933;"></i> Developed by <b>Sukumar Jujjuvarapu</b></p>
            <p class="footer-copyright">&copy; 2026 AI Data Analyst Pro. All rights reserved.</p>
        </div>
    </div>
    <style>
    .footer-container {
        background: rgba(255,255,255,0.35);
        backdrop-filter: blur(24px) saturate(180%);
        -webkit-backdrop-filter: blur(24px) saturate(180%);
        border-radius: 28px;
        padding: 40px 30px;
        margin-top: 50px;
        text-align: center;
        box-shadow: 0 8px 32px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.6), 0 0 40px rgba(15,118,110,0.08);
        border: 1.5px solid rgba(255,255,255,0.5);
    }
    .footer-brand {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        margin-bottom: 12px;
    }
    .footer-logo {
        font-size: 2.2rem;
        color: #0ea5e9;
        animation: pulse 2s infinite;
        filter: drop-shadow(0 0 8px rgba(14, 165, 233, 0.4));
    }
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.1); }
    }
    .footer-title {
        font-size: 1.6rem;
        font-weight: 800;
        background: linear-gradient(135deg, #0f766e 0%, #14b8a6 50%, #0ea5e9 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -0.3px;
    }
    .footer-tagline {
        color: #6b7280 !important;
        font-size: 0.95rem;
        margin-bottom: 28px;
        line-height: 1.6;
    }
    .footer-links {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 16px;
        flex-wrap: wrap;
        margin-bottom: 28px;
    }
    .footer-link {
        color: #1a1a2e !important;
        text-decoration: none;
        padding: 10px 22px;
        border-radius: 25px;
        background: rgba(15, 118, 110, 0.08);
        border: 1px solid rgba(15, 118, 110, 0.15);
        transition: all 0.3s ease;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-weight: 500;
        font-size: 0.9rem;
        backdrop-filter: blur(8px);
    }
    .footer-link:hover {
        background: linear-gradient(135deg, #0f766e 0%, #0ea5e9 100%);
        color: #ffffff !important;
        transform: translateY(-3px);
        box-shadow: 0 5px 20px rgba(14, 165, 233, 0.35);
        border-color: transparent;
    }
    .footer-divider {
        color: #d1d5db;
    }
    .footer-bottom {
        border-top: 1px solid rgba(15,118,110,0.1);
        padding-top: 20px;
        margin-top: 10px;
    }
    .footer-bottom p {
        color: #6b7280 !important;
        margin: 5px 0;
        font-size: 0.9rem;
    }
    .footer-copyright {
        font-size: 0.8rem;
        color: #9ca3af !important;
        margin-top: 8px !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)
