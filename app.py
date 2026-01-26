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
import tempfile
if os.path.exists("/tmp"):
    APP_DB_PATH = "/tmp/app_database.db"
else:
    APP_DB_PATH = "app_database.db"

# Default sample database - works locally and on cloud
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "Chinook_Sqlite.sqlite")

# Check if default database exists
if not os.path.exists(DEFAULT_DB_PATH):
    # Fallback for cloud deployment
    DEFAULT_DB_PATH = "Chinook_Sqlite.sqlite"

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
except Exception as e:
    client = None

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="AI Data Analyst Pro",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- RAZORPAY VERIFICATION META TAG ---
# This helps Razorpay verify the website ownership
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
        conn = sqlite3.connect(db_path)
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        conn.close()
        return db_path
    except Exception as e:
        raise Exception(f"Error converting CSV: {str(e)}")

def excel_to_sqlite(excel_path, db_path):
    """Convert Excel file to SQLite database (each sheet = table)"""
    try:
        excel_file = pd.ExcelFile(excel_path)
        if not excel_file.sheet_names:
            raise ValueError("Excel file has no sheets")
        conn = sqlite3.connect(db_path)
        
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            # Clean sheet name for SQL table
            clean_name = sheet_name.replace(" ", "_").replace("-", "_")
            df.to_sql(clean_name, conn, if_exists='replace', index=False)
        
        conn.close()
        return db_path
    except Exception as e:
        raise Exception(f"Error converting Excel: {str(e)}")

# ============================================================
#                    SQL & AI FUNCTIONS
# ============================================================

def get_db_schema(db_path):
    """Get database schema"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        return "\n".join([t[0] for t in tables if t[0] is not None])
    except Exception as e:
        return str(e)

def run_query(sql, db_path):
    """Execute SQL query on database"""
    conn = sqlite3.connect(db_path)
    try:
        if sql.strip().upper().startswith("SELECT"):
            df = pd.read_sql(sql, conn)
            conn.close()
            return df
        else:
            conn.close()
            return "Error: SELECT queries only for security."
    except Exception as e:
        conn.close()
        return f"Error: {e}"

def get_ai_sql(user_question, db_path):
    """Generate SQL from natural language using AI"""
    if client is None:
        return "SELECT 'Error: AI not configured. Please add GROQ_API_KEY in secrets.' as message"
    
    schema_context = get_db_schema(db_path)
    system_prompt = f"""
    You are an expert SQL analyst. Database Schema:
    {schema_context}
    
    Write a SQLite query to answer the user's question.
    Return ONLY the SQL query - no markdown, no explanation, just raw SQL.
    Make sure the query is valid SQLite syntax.
    """
    
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question}
            ],
            model="llama-3.3-70b-versatile",
        )
        sql = completion.choices[0].message.content
        return sql.replace("```sql", "").replace("```", "").strip()
    except Exception as e:
        return f"SELECT 'Error: {str(e)}' as message"

# ============================================================
#                    EXPORT FUNCTIONS
# ============================================================

def export_to_excel(df):
    """Export DataFrame to Excel bytes"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Results')
    output.seek(0)
    return output

def export_to_csv(df):
    """Export DataFrame to CSV bytes"""
    return df.to_csv(index=False).encode('utf-8')

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
        
        # Question
        elements.append(Paragraph(f"<b>Question:</b> {question}", styles['Normal']))
        elements.append(Spacer(1, 12))
        
        # SQL Query
        elements.append(Paragraph(f"<b>SQL Query:</b>", styles['Normal']))
        elements.append(Paragraph(f"<code>{sql_query}</code>", styles['Code']))
        elements.append(Spacer(1, 12))
        
        # Data Table
        elements.append(Paragraph("<b>Results:</b>", styles['Normal']))
        elements.append(Spacer(1, 6))
        
        # Convert DataFrame to table data
        table_data = [df.columns.tolist()] + df.head(50).values.tolist()
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
    except:
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
<style>
    /* ========== ROOT VARIABLES ========== */
    :root {
        --primary: #667eea;
        --primary-dark: #5a67d8;
        --secondary: #764ba2;
        --accent: #f093fb;
        --success: #10b981;
        --warning: #f59e0b;
        --error: #ef4444;
        --text-primary: #1e293b;
        --text-secondary: #475569;
        --text-muted: #64748b;
        --bg-light: #f8fafc;
        --bg-card: rgba(255, 255, 255, 0.95);
        --border-light: #e2e8f0;
        --shadow-sm: 0 2px 8px rgba(0,0,0,0.06);
        --shadow-md: 0 4px 20px rgba(0,0,0,0.08);
        --shadow-lg: 0 10px 40px rgba(0,0,0,0.12);
        --radius-sm: 8px;
        --radius-md: 12px;
        --radius-lg: 16px;
        --radius-xl: 24px;
        --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    /* ========== GLOBAL STYLES ========== */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    * {
        box-sizing: border-box;
    }
    
    html, body, [data-testid="stAppViewContainer"] {
        overflow-x: hidden !important;
        max-width: 100vw !important;
    }
    
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf4 50%, #dfe6f0 100%);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* ========== TYPOGRAPHY ========== */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', sans-serif;
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        line-height: 1.3;
    }
    
    p, span, label, div {
        color: var(--text-secondary);
        line-height: 1.6;
    }
    
    /* ========== MAIN HEADER ========== */
    .main-header {
        font-size: clamp(1.5rem, 5vw, 3rem);
        font-weight: 800;
        background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 50%, var(--accent) 100%);
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
        font-size: clamp(0.9rem, 2.5vw, 1.2rem);
        color: var(--text-muted) !important;
        margin-bottom: 1.5rem;
        font-weight: 400;
        padding: 0 1rem;
        line-height: 1.6;
    }
    
    /* ========== GLASSMORPHISM CARDS ========== */
    .glass-card {
        background: var(--bg-card);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-radius: var(--radius-xl);
        border: 1px solid rgba(255, 255, 255, 0.5);
        padding: clamp(1rem, 3vw, 2rem);
        box-shadow: var(--shadow-md);
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
    }
    .tier-free { 
        background: linear-gradient(135deg, #94a3b8, #64748b); 
        color: #ffffff !important; 
        border: 2px solid #475569;
        font-weight: 700;
    }
    .tier-starter { background: linear-gradient(135deg, #60a5fa, #3b82f6); color: white; }
    .tier-pro { background: linear-gradient(135deg, #fbbf24, #f59e0b); color: white; }
    .tier-enterprise { background: linear-gradient(135deg, #34d399, #10b981); color: white; }
    
    /* ========== PRICING CARDS ========== */
    .pricing-card {
        background: var(--bg-card);
        backdrop-filter: blur(10px);
        border: 2px solid var(--border-light);
        border-radius: var(--radius-xl);
        padding: clamp(1rem, 3vw, 2rem);
        text-align: center;
        transition: var(--transition);
        position: relative;
        overflow: hidden;
        height: 100%;
        display: flex;
        flex-direction: column;
    }
    .pricing-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, var(--primary), var(--secondary));
    }
    .pricing-card:hover {
        transform: translateY(-5px);
        box-shadow: var(--shadow-lg);
        border-color: var(--primary);
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
        background: linear-gradient(135deg, var(--primary), var(--secondary));
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
        opacity: 0.3;
    }
    
    /* ========== FEATURE CARDS ========== */
    .feature-card {
        background: white;
        border-radius: var(--radius-lg);
        padding: clamp(1rem, 2.5vw, 1.5rem);
        text-align: center;
        box-shadow: var(--shadow-sm);
        transition: var(--transition);
        border: 1px solid #f1f5f9;
        height: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 160px;
    }
    .feature-card:hover {
        transform: translateY(-3px);
        box-shadow: var(--shadow-md);
    }
    .feature-card h4 {
        color: var(--text-primary) !important;
        font-size: clamp(0.85rem, 2vw, 1rem) !important;
        font-weight: 600 !important;
        margin: 0.5rem 0 0.3rem 0 !important;
    }
    .feature-card p {
        color: var(--text-muted) !important;
        font-size: clamp(0.7rem, 1.8vw, 0.85rem) !important;
        line-height: 1.4 !important;
        margin: 0 !important;
    }
    .feature-icon {
        font-size: clamp(1.8rem, 4vw, 2.5rem);
        margin-bottom: 0.5rem;
    }
    
    /* ========== BUTTONS ========== */
    .stButton > button {
        width: 100%;
        border-radius: var(--radius-md);
        font-weight: 600;
        font-size: clamp(0.8rem, 2vw, 1rem);
        padding: 0.7rem 1.2rem;
        transition: var(--transition);
        border: none;
        box-shadow: var(--shadow-sm);
        min-height: 44px;
        cursor: pointer;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-md);
    }
    .stButton > button:active {
        transform: scale(0.98);
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        color: white;
    }
    
    /* ========== FORM INPUTS ========== */
    .stTextInput > div > div > input,
    .stTextArea textarea {
        border-radius: var(--radius-md);
        border: 2px solid var(--border-light);
        padding: 0.75rem 1rem;
        font-size: 16px !important;
        transition: var(--transition);
        background: white;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea textarea:focus {
        border-color: var(--primary);
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15);
        outline: none;
    }
    
    /* Form labels */
    .stTextInput label, .stSelectbox label, .stFileUploader label, .stTextArea label {
        color: var(--text-primary) !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        margin-bottom: 0.3rem;
    }
    
    /* ========== TABS ========== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px !important;
        background: rgba(241, 245, 249, 0.8) !important;
        border-radius: var(--radius-md) !important;
        padding: 4px !important;
        flex-wrap: wrap;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: var(--radius-sm) !important;
        font-weight: 600 !important;
        padding: 10px 16px !important;
        color: var(--text-secondary) !important;
        background: transparent !important;
        font-size: 0.9rem;
        white-space: nowrap;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--primary), var(--secondary)) !important;
        color: white !important;
    }
    .stTabs [data-baseweb="tab-border"],
    .stTabs [data-baseweb="tab-highlight"] {
        display: none !important;
    }
    
    /* ========== SIDEBAR ========== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%) !important;
    }
    [data-testid="stSidebar"] * {
        color: #e2e8f0 !important;
    }
    [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h4 {
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    /* Sidebar Progress Bar - Force purple gradient */
    [data-testid="stSidebar"] .stProgress > div {
        background: rgba(255, 255, 255, 0.15) !important;
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
        background: linear-gradient(90deg, #667eea, #764ba2, #a855f7) !important;
        border-radius: 10px !important;
    }
    /* Hide any red/default color */
    [data-testid="stSidebar"] .stProgress [style*="background"] {
        background: linear-gradient(90deg, #667eea, #764ba2) !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        color: #ffffff !important;
    }
    [data-testid="stSidebar"] .stButton > button {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255, 255, 255, 0.2);
    }
    
    /* ========== DATA DISPLAY ========== */
    .stDataFrame {
        border-radius: var(--radius-lg);
        overflow: hidden;
        box-shadow: var(--shadow-sm);
    }
    
    /* ========== ALERTS ========== */
    .stAlert {
        border-radius: var(--radius-md);
        border: none;
        padding: 0.75rem 1rem;
    }
    
    /* ========== DOWNLOAD BUTTONS ========== */
    .stDownloadButton > button {
        background: linear-gradient(135deg, var(--success), #059669);
        color: white;
        border: none;
        border-radius: var(--radius-md);
    }
    
    /* ========== SELECTBOX ========== */
    .stSelectbox > div > div {
        border-radius: var(--radius-md);
    }
    
    /* ========== PROGRESS BAR - Global ========== */
    .stProgress > div {
        background: rgba(102, 126, 234, 0.2) !important;
        border-radius: 10px !important;
    }
    .stProgress > div > div,
    .stProgress > div > div > div,
    [data-testid="stProgressBar"] > div,
    [role="progressbar"] > div {
        background: linear-gradient(90deg, #667eea, #764ba2, #f093fb) !important;
        background-color: #667eea !important;
        border-radius: 10px !important;
    }
    
    /* ========== FILE UPLOADER ========== */
    .stFileUploader {
        border: 2px dashed var(--primary);
        border-radius: var(--radius-lg);
        padding: 1rem;
        background: rgba(102, 126, 234, 0.03);
        transition: var(--transition);
    }
    .stFileUploader:hover {
        background: rgba(102, 126, 234, 0.08);
        border-color: var(--secondary);
    }
    
    /* ========== DIVIDER ========== */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--border-light), transparent);
        margin: 1.5rem 0;
    }
    
    /* ========== EXPANDERS ========== */
    .streamlit-expanderHeader {
        background: rgba(255,255,255,0.8);
        border-radius: var(--radius-md);
        font-weight: 600;
    }
    
    /* ========== CODE BLOCKS ========== */
    .stCodeBlock {
        border-radius: var(--radius-md);
    }
    
    /* ========== METRICS ========== */
    [data-testid="stMetricValue"] {
        font-size: clamp(1.5rem, 4vw, 2rem);
        font-weight: 700;
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
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
    
    /* ========== ANIMATIONS ========== */
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    @keyframes slideUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .fade-in { animation: fadeIn 0.5s ease-out; }
    .slide-up { animation: slideUp 0.5s ease-out; }
    
    /* ========================================================
                    RESPONSIVE BREAKPOINTS
    ======================================================== */
    
    /* TABLETS (768px - 1024px) */
    @media screen and (max-width: 1024px) {
        .pricing-card {
            padding: 1.25rem;
        }
        .feature-card {
            min-height: 150px;
        }
    }
    
    /* MOBILE LANDSCAPE & SMALL TABLETS (576px - 768px) */
    @media screen and (max-width: 768px) {
        /* Layout */
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: 0.75rem !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="column"] {
            flex: 1 1 calc(50% - 0.5rem) !important;
            min-width: calc(50% - 0.5rem) !important;
            max-width: 100% !important;
        }
        
        /* Typography */
        .main-header {
            font-size: 1.5rem !important;
            padding: 0.75rem !important;
        }
        .hero-subtitle {
            font-size: 0.9rem !important;
            padding: 0 0.75rem !important;
        }
        
        /* Cards */
        .pricing-card {
            padding: 1rem !important;
            margin-bottom: 0.75rem;
        }
        .pricing-card h2 { font-size: 1.5rem !important; }
        .pricing-card h3 { font-size: 0.95rem !important; }
        .pricing-card p { font-size: 0.8rem !important; margin: 0.2rem 0 !important; }
        
        .feature-card {
            padding: 0.875rem !important;
            min-height: 130px !important;
        }
        .feature-card h4 { font-size: 0.85rem !important; }
        .feature-card p { font-size: 0.75rem !important; }
        .feature-icon { font-size: 1.75rem !important; }
        
        /* Buttons */
        .stButton > button {
            padding: 0.6rem 0.75rem !important;
            font-size: 0.85rem !important;
        }
        
        /* Forms */
        .stTextInput > div > div > input {
            padding: 0.7rem !important;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab"] {
            padding: 8px 12px !important;
            font-size: 0.8rem !important;
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] {
            min-width: 260px !important;
        }
        
        /* Section headers */
        h3, h4 {
            font-size: 1rem !important;
        }
        
        /* Footer */
        .footer-container {
            padding: 1.25rem 1rem !important;
        }
        .footer-links {
            flex-direction: column !important;
            gap: 0.5rem !important;
        }
        .footer-divider { display: none !important; }
    }
    
    /* MOBILE PORTRAIT (max-width: 576px) */
    @media screen and (max-width: 576px) {
        /* Stack everything vertically */
        [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
            gap: 0.5rem !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="column"] {
            flex: 1 1 100% !important;
            width: 100% !important;
            min-width: 100% !important;
            max-width: 100% !important;
            padding: 0 !important;
        }
        
        /* Typography */
        .main-header {
            font-size: 1.35rem !important;
            padding: 0.5rem !important;
            line-height: 1.3 !important;
        }
        .hero-subtitle {
            font-size: 0.85rem !important;
            line-height: 1.5 !important;
        }
        
        /* Cards - full width, compact */
        .pricing-card {
            padding: 0.875rem !important;
            border-radius: 14px !important;
        }
        .pricing-card h2 { font-size: 1.4rem !important; }
        .pricing-card h3 { font-size: 0.9rem !important; }
        .pricing-card p { 
            font-size: 0.75rem !important; 
            line-height: 1.4 !important;
            margin: 0.15rem 0 !important;
        }
        .pricing-card i { font-size: 0.75rem !important; }
        .pricing-card hr { margin: 0.5rem 0 !important; }
        
        .feature-card {
            padding: 0.75rem !important;
            min-height: 110px !important;
            border-radius: 12px !important;
        }
        .feature-card h4 { font-size: 0.8rem !important; }
        .feature-card p { font-size: 0.7rem !important; }
        .feature-icon { font-size: 1.5rem !important; margin-bottom: 0.3rem !important; }
        
        /* Buttons - full touch targets */
        .stButton > button {
            padding: 0.65rem !important;
            font-size: 0.8rem !important;
            min-height: 44px !important;
        }
        
        /* Forms - prevent iOS zoom */
        .stTextInput > div > div > input {
            font-size: 16px !important;
            padding: 0.65rem !important;
        }
        
        /* Tabs - horizontal scroll */
        .stTabs [data-baseweb="tab-list"] {
            flex-wrap: nowrap !important;
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch;
            scrollbar-width: none;
            -ms-overflow-style: none;
        }
        .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
            display: none;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 8px 14px !important;
            font-size: 0.78rem !important;
            flex-shrink: 0;
        }
        
        /* Section headers */
        h3, h4 {
            font-size: 0.95rem !important;
            line-height: 1.3 !important;
        }
        h3 i, h4 i {
            font-size: 0.9rem !important;
            margin-right: 6px !important;
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] {
            padding: 0.5rem !important;
        }
        [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h4 {
            font-size: 0.95rem !important;
        }
        
        /* Trust items */
        .trust-item i { font-size: 1.4rem !important; }
        .trust-item p { font-size: 0.7rem !important; }
        
        /* Alerts */
        .stAlert {
            padding: 0.6rem !important;
            font-size: 0.8rem !important;
        }
        
        /* Code blocks */
        .stCodeBlock {
            font-size: 0.7rem !important;
        }
        
        /* Footer */
        .footer-container {
            padding: 1rem 0.75rem !important;
            border-radius: 12px !important;
            margin-top: 1.5rem !important;
        }
        .footer-brand { flex-direction: column !important; gap: 4px !important; }
        .footer-logo { font-size: 1.2rem !important; }
        .footer-title { font-size: 1rem !important; }
        .footer-tagline { font-size: 0.75rem !important; }
        .footer-link {
            padding: 0.5rem 1rem !important;
            font-size: 0.8rem !important;
            width: 80% !important;
        }
        .footer-bottom p { font-size: 0.7rem !important; }
        .footer-copyright { font-size: 0.65rem !important; }
        
        /* Data tables */
        .stDataFrame {
            font-size: 0.75rem !important;
        }
        
        /* Download buttons */
        .stDownloadButton > button {
            font-size: 0.78rem !important;
            padding: 0.5rem !important;
        }
        
        /* File uploader */
        .stFileUploader {
            padding: 0.6rem !important;
        }
    }
    
    /* EXTRA SMALL (max-width: 375px) */
    @media screen and (max-width: 375px) {
        .main-header { font-size: 1.2rem !important; }
        .hero-subtitle { font-size: 0.8rem !important; }
        .pricing-card h2 { font-size: 1.25rem !important; }
        .pricing-card p { font-size: 0.7rem !important; }
        .feature-card { min-height: 100px !important; }
        .stButton > button { font-size: 0.75rem !important; }
    }
    
    /* ========== TOUCH DEVICE OPTIMIZATIONS ========== */
    @media (hover: none) and (pointer: coarse) {
        /* Disable hover transforms on touch */
        .pricing-card:hover,
        .feature-card:hover {
            transform: none;
        }
        
        /* Active states for touch feedback */
        .pricing-card:active,
        .feature-card:active,
        .stButton > button:active {
            transform: scale(0.98);
            opacity: 0.9;
        }
        
        /* Larger touch targets */
        .stRadio label,
        .stCheckbox label {
            padding: 0.5rem 0;
            min-height: 44px;
            display: flex;
            align-items: center;
        }
    }
    
    /* ========== LANDSCAPE MOBILE ========== */
    @media screen and (max-height: 500px) and (orientation: landscape) {
        .main-header { font-size: 1.2rem !important; padding: 0.3rem !important; }
        .hero-subtitle { font-size: 0.8rem !important; margin-bottom: 0.5rem !important; }
        .pricing-card, .feature-card { padding: 0.6rem !important; }
    }
    
    /* ========== HIGH DPI DISPLAYS ========== */
    @media (-webkit-min-device-pixel-ratio: 2), (min-resolution: 192dpi) {
        .glass-card, .pricing-card, .feature-card {
            border-width: 0.5px;
        }
    }
    
    /* ========== DARK MODE SUPPORT (if user prefers) ========== */
    @media (prefers-color-scheme: dark) {
        /* Keep light theme for now but ready for future */
    }
    
    /* ========== REDUCED MOTION ========== */
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }
    
    /* ========== PRINT STYLES ========== */
    @media print {
        .stButton, [data-testid="stSidebar"], .footer-container {
            display: none !important;
        }
        .stApp {
            background: white !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
#                    LOGIN/REGISTER PAGE
# ============================================================

def show_auth_page():
    """Display login/register page"""
    # Hero Section
    st.markdown('''
    <div style="text-align: center; padding: 2rem 0;">
        <h1 class="main-header" style="color: #1e293b;"><i class="fa-solid fa-robot" style="margin-right: 12px;"></i>AI Data Analyst Pro</h1>
        <p class="hero-subtitle" style="color: #475569;">Transform your data into powerful insights using natural language.<br>
        <span style="color: #667eea; font-weight: 600;">No SQL knowledge required.</span></p>
    </div>
    ''', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            st.markdown('<h4 style="color: #1e293b; font-weight: 600; margin-bottom: 1rem;"><i class="fa-solid fa-hand-wave" style="color: #667eea; margin-right: 8px;"></i>Welcome Back!</h4>', unsafe_allow_html=True)
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="you@example.com")
                password = st.text_input("Password", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("Login", use_container_width=True)
                
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
            st.markdown('<h4 style="color: #1e293b; font-weight: 600; margin-bottom: 1rem;"><i class="fa-solid fa-sparkles" style="color: #667eea; margin-right: 8px;"></i>Create Your Account</h4>', unsafe_allow_html=True)
            with st.form("register_form"):
                name = st.text_input("Full Name", placeholder="John Doe")
                email = st.text_input("Email", placeholder="you@example.com", key="reg_email")
                password = st.text_input("Password", type="password", placeholder="••••••••", key="reg_pass")
                password2 = st.text_input("Confirm Password", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("Create Account", use_container_width=True)
                
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
    
    # Features showcase with beautiful cards
    st.markdown("---")
    st.markdown('''
    <div style="text-align: center; margin: 2rem 0;">
        <h2 style="color: #1e293b;"><i class="fa-solid fa-bolt" style="color: #667eea; margin-right: 10px;"></i>Powerful Features</h2>
        <p style="color: #64748b;">Everything you need to analyze data like a pro</p>
    </div>
    ''', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('''
        <div class="feature-card">
            <div class="feature-icon"><i class="fa-solid fa-chart-pie" style="color: #667eea;"></i></div>
            <h4 style="color: #1e293b; font-weight: 600;">Smart Charts</h4>
            <p style="color: #475569;">Auto-generate beautiful visualizations</p>
        </div>
        ''', unsafe_allow_html=True)
    with col2:
        st.markdown('''
        <div class="feature-card">
            <div class="feature-icon"><i class="fa-solid fa-comments" style="color: #764ba2;"></i></div>
            <h4 style="color: #1e293b; font-weight: 600;">Natural Language</h4>
            <p style="color: #475569;">Ask questions in plain English</p>
        </div>
        ''', unsafe_allow_html=True)
    with col3:
        st.markdown('''
        <div class="feature-card">
            <div class="feature-icon"><i class="fa-solid fa-database" style="color: #f59e0b;"></i></div>
            <h4 style="color: #1e293b; font-weight: 600;">Any Data Source</h4>
            <p style="color: #475569;">CSV, Excel, or SQLite databases</p>
        </div>
        ''', unsafe_allow_html=True)
    with col4:
        st.markdown('''
        <div class="feature-card">
            <div class="feature-icon"><i class="fa-solid fa-file-export" style="color: #10b981;"></i></div>
            <h4 style="color: #1e293b; font-weight: 600;">Export Anywhere</h4>
            <p style="color: #475569;">Download as PDF, Excel, or CSV</p>
        </div>
        ''', unsafe_allow_html=True)
    
    # Trust indicators
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('''
        <div class="trust-item" style="text-align: center; padding: 0.5rem;">
            <i class="fa-solid fa-shield-halved" style="font-size: 1.8rem; color: #667eea;"></i>
            <p style="color: #475569; font-size: 0.85rem; margin-top: 0.5rem; font-weight: 500;">Secure & Private</p>
        </div>
        ''', unsafe_allow_html=True)
    with col2:
        st.markdown('''
        <div class="trust-item" style="text-align: center; padding: 0.5rem;">
            <i class="fa-solid fa-bolt-lightning" style="font-size: 1.8rem; color: #f59e0b;"></i>
            <p style="color: #475569; font-size: 0.85rem; margin-top: 0.5rem; font-weight: 500;">Lightning Fast</p>
        </div>
        ''', unsafe_allow_html=True)
    with col3:
        st.markdown('''
        <div class="trust-item" style="text-align: center; padding: 0.5rem;">
            <i class="fa-solid fa-flag" style="font-size: 1.8rem; color: #10b981;"></i>
            <p style="color: #475569; font-size: 0.85rem; margin-top: 0.5rem; font-weight: 500;">Made in India</p>
        </div>
        ''', unsafe_allow_html=True)

# ============================================================
#                    PRICING PAGE
# ============================================================

def show_pricing_page():
    """Display pricing page"""
    st.markdown('''
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="font-size: 2.5rem; margin-bottom: 0.5rem; color: #1e293b;"><i class="fa-solid fa-gem" style="color: #667eea; margin-right: 12px;"></i>Choose Your Plan</h1>
        <p style="color: #64748b; font-size: 1.1rem;">Unlock the full power of AI data analysis</p>
    </div>
    ''', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="pricing-card">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;"><i class="fa-solid fa-gift" style="color: #64748b;"></i></div>
            <h3 style="margin: 0; color: #1e293b; font-weight: 700;">Free</h3>
            <h2 style="color: #667eea;">₹0</h2>
            <p style="color: #64748b;">Forever free</p>
            <hr style="margin: 1rem 0;">
            <p style="color: #374151;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>5 queries/day</p>
            <p style="color: #374151;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>Basic charts</p>
            <p style="color: #374151;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>CSV upload</p>
            <p style="color: #94a3b8;"><i class="fa-solid fa-xmark" style="margin-right: 8px;"></i>Query history</p>
            <p style="color: #94a3b8;"><i class="fa-solid fa-xmark" style="margin-right: 8px;"></i>PDF export</p>
        </div>
        """, unsafe_allow_html=True)
        if st.session_state.user["subscription_tier"] == "free":
            st.button("Current Plan", disabled=True, key="free_btn")
    
    with col2:
        st.markdown("""
        <div class="pricing-card" style="border-color: #3b82f6; border-width: 2px;">
            <div style="background: linear-gradient(135deg, #3b82f6, #1d4ed8); color: white; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.7rem; display: inline-block; margin-bottom: 0.5rem;">POPULAR</div>
            <div style="font-size: 2rem; margin-bottom: 0.5rem;"><i class="fa-solid fa-rocket" style="color: #3b82f6;"></i></div>
            <h3 style="margin: 0; color: #1e293b; font-weight: 700;">Starter</h3>
            <h2 style="color: #667eea;">₹499<span style="font-size: 1rem; color: #64748b;">/mo</span></h2>
            <p style="color: #64748b;">For individuals</p>
            <hr style="margin: 1rem 0;">
            <p style="color: #374151;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>50 queries/day</p>
            <p style="color: #374151;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>All chart types</p>
            <p style="color: #374151;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>Excel upload</p>
            <p style="color: #374151;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>Query history</p>
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
            <h3 style="margin: 0; color: #1e293b; font-weight: 700;">Pro</h3>
            <h2 style="color: #667eea;">₹1,499<span style="font-size: 1rem; color: #64748b;">/mo</span></h2>
            <p style="color: #64748b;">For teams</p>
            <hr style="margin: 1rem 0;">
            <p style="color: #374151;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>500 queries/day</p>
            <p style="color: #374151;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>All chart types</p>
            <p style="color: #374151;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>All file types</p>
            <p style="color: #374151;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>Full history</p>
            <p style="color: #374151;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>PDF export</p>
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
            <h3 style="margin: 0; color: #1e293b; font-weight: 700;">Enterprise</h3>
            <h2 style="color: #667eea;">₹4,999<span style="font-size: 1rem; color: #64748b;">/mo</span></h2>
            <p style="color: #64748b;">For organizations</p>
            <hr style="margin: 1rem 0;">
            <p style="color: #374151;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>Unlimited queries</p>
            <p style="color: #374151;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>Priority support</p>
            <p style="color: #374151;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>Custom integrations</p>
            <p style="color: #374151;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>Full history</p>
            <p style="color: #374151;"><i class="fa-solid fa-check" style="color: #10b981; margin-right: 8px;"></i>All exports</p>
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
    tier = user["subscription_tier"]
    
    # --- SIDEBAR ---
    with st.sidebar:
        # User profile section
        st.markdown(f'<h3 style="color: #ffffff;"><i class="fa-solid fa-user-circle" style="margin-right: 8px; color: #667eea;"></i>{user["name"]}</h3>', unsafe_allow_html=True)
        tier_class = f"tier-{tier}"
        st.markdown(f'<span class="tier-badge {tier_class}">{tier.upper()}</span>', unsafe_allow_html=True)
        
        # Query limit indicator
        user_info = get_user_info(user["id"])
        limits = {"free": 5, "starter": 50, "pro": 500, "enterprise": 99999}
        if user_info:
            queries_today = user_info["queries_today"] if user_info["last_query_date"] == datetime.now().date().isoformat() else 0
            remaining = limits.get(tier, 5) - queries_today
        else:
            remaining = limits.get(tier, 5)
        remaining = max(0, remaining)  # Ensure non-negative
        st.progress(min(1.0, remaining / limits.get(tier, 5)))
        st.caption(f"{remaining} queries remaining today")
        
        st.divider()
        
        # Navigation
        st.markdown('<h4 style="margin-bottom: 10px; color: #ffffff !important;"><i class="fa-solid fa-compass" style="margin-right: 8px; color: #667eea;"></i>Navigation</h4>', unsafe_allow_html=True)
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
    st.markdown(f'<h1 class="main-header" style="color: #1e293b;"><i class="fa-solid fa-robot" style="margin-right: 12px;"></i>AI Data Analyst Pro</h1>', unsafe_allow_html=True)
    
    # Route to different pages
    if page == "Pricing" or st.session_state.get("show_pricing"):
        st.session_state.show_pricing = False
        show_pricing_page()
        return
    
    elif page == "Data Sources":
        show_data_sources_page()
        return
    
    elif page == "Query History":
        show_history_page()
        return
    
    elif page == "Settings":
        show_settings_page()
        return
    
    # --- QUERY DATA PAGE (Default) ---
    
    # Current database info
    db_name = os.path.basename(st.session_state.current_db) if st.session_state.current_db else "No database selected"
    
    # Check if database exists
    if st.session_state.current_db and not os.path.exists(st.session_state.current_db):
        st.warning(f"Database file not found. Switching to default sample database.")
        st.session_state.current_db = DEFAULT_DB_PATH
        db_name = os.path.basename(DEFAULT_DB_PATH)
    
    st.info(f"**Active Database:** {db_name}")
    
    # Query input
    st.markdown('<h3 style="color: #1e293b; font-weight: 600;"><i class="fa-solid fa-message" style="color: #667eea; margin-right: 10px;"></i>Ask Your Data</h3>', unsafe_allow_html=True)
    
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
            can_query, remaining = check_query_limit(user["id"], tier)
            
            if not can_query:
                st.error(f"Daily query limit reached! Upgrade your plan for more queries.")
                if tier == "free":
                    st.info("Upgrade to Starter for 50 queries/day")
            else:
                with st.spinner("AI is analyzing your question..."):
                    sql_code = get_ai_sql(user_query, st.session_state.current_db)
                    st.session_state.sql_code = sql_code
                    st.session_state.current_question = user_query
                    
                    if not show_sql:
                        result = run_query(sql_code, st.session_state.current_db)
                        st.session_state.result_df = result
                        
                        # Update query count
                        update_query_count(user["id"])
                        
                        # Save to history (for paid users)
                        if tier != "free":
                            result_preview = result.head(10).to_string() if isinstance(result, pd.DataFrame) else str(result)
                            save_query_history(user["id"], user_query, sql_code, result_preview)
        else:
            st.warning("Please enter a question first!")
    
    # Display results
    if st.session_state.sql_code:
        st.markdown('<h3 style="color: #1e293b;"><i class="fa-solid fa-code" style="color: #667eea; margin-right: 10px;"></i>Generated SQL</h3>', unsafe_allow_html=True)
        st.code(st.session_state.sql_code, language="sql")
    
    if st.session_state.result_df is not None:
        result = st.session_state.result_df
        
        if isinstance(result, pd.DataFrame):
            # Results header with export buttons
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col1:
                st.markdown('<h3 style="color: #1e293b;"><i class="fa-solid fa-table" style="color: #667eea; margin-right: 10px;"></i>Results</h3>', unsafe_allow_html=True)
            
            with col2:
                csv_data = export_to_csv(result)
                st.download_button(
                    "CSV",
                    csv_data,
                    file_name="results.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col3:
                excel_data = export_to_excel(result)
                st.download_button(
                    "Excel",
                    excel_data,
                    file_name="results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            with col4:
                if tier in ["pro", "enterprise"]:
                    pdf_data = generate_pdf_report(result, st.session_state.current_question or "Query", st.session_state.sql_code)
                    if pdf_data:
                        st.download_button(
                            "PDF",
                            pdf_data,
                            file_name="report.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    else:
                        st.button("PDF", disabled=True, help="Install reportlab for PDF export")
                else:
                    st.button("PDF", disabled=True, help="Upgrade to Pro for PDF export")
            
            # Data table
            st.dataframe(result, use_container_width=True)
            st.caption(f"Showing {len(result)} rows")
            
            # Visualization
            if len(result.columns) > 1:
                st.markdown('<h3 style="color: #1e293b;"><i class="fa-solid fa-chart-column" style="color: #667eea; margin-right: 10px;"></i>Visualization</h3>', unsafe_allow_html=True)
                
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    chart_type = st.selectbox(
                        "Chart Type:",
                        ["Bar Chart", "Line Chart", "Pie Chart", "Scatter Plot", "Area Chart"]
                    )
                
                with col2:
                    # Prepare chart data
                    chart_data = result.set_index(result.columns[0])
                    numeric_df = chart_data.select_dtypes(include=['number'])
                    
                    if not numeric_df.empty:
                        try:
                            if chart_type == "Bar Chart":
                                st.bar_chart(numeric_df)
                            elif chart_type == "Line Chart":
                                st.line_chart(numeric_df)
                            elif chart_type == "Area Chart":
                                st.area_chart(numeric_df)
                            elif chart_type == "Scatter Plot":
                                st.scatter_chart(numeric_df)
                            elif chart_type == "Pie Chart":
                                if len(numeric_df.columns) > 0:
                                    fig = px.pie(
                                        result,
                                        names=result.columns[0],
                                        values=numeric_df.columns[0],
                                        title="Distribution"
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                                else:
                                    st.warning("No numeric column for pie chart")
                        except Exception as e:
                            st.warning(f"Could not render chart: {str(e)}")
                    else:
                        st.warning("No numeric data available for visualization")
        else:
            st.error(result)

# ============================================================
#                    DATA SOURCES PAGE
# ============================================================

def show_data_sources_page():
    """Data sources management page"""
    st.markdown('<h3 style="color: #1e293b;"><i class="fa-solid fa-folder-open" style="color: #667eea; margin-right: 10px;"></i>Data Sources</h3>', unsafe_allow_html=True)
    
    tier = st.session_state.user["subscription_tier"]
    
    # File upload section
    st.markdown('<h4 style="color: #1e293b;"><i class="fa-solid fa-cloud-arrow-up" style="color: #764ba2; margin-right: 8px;"></i>Upload New Data</h4>', unsafe_allow_html=True)
    
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
    st.markdown('<h4 style="color: #1e293b;"><i class="fa-solid fa-hard-drive" style="color: #764ba2; margin-right: 8px;"></i>Your Data Sources</h4>', unsafe_allow_html=True)
    
    user_files = get_user_files(st.session_state.user["id"])
    
    # Default database option
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown('<p><i class="fa-solid fa-database" style="color: #667eea; margin-right: 8px;"></i><b>Chinook Sample Database</b> (Default)</p>', unsafe_allow_html=True)
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
            st.markdown(f'<p><i class="fa-solid fa-file" style="color: #667eea; margin-right: 8px;"></i><b>{filename}</b></p>', unsafe_allow_html=True)
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
    st.markdown('<h3 style="color: #1e293b;"><i class="fa-solid fa-clock-rotate-left" style="color: #667eea; margin-right: 10px;"></i>Query History</h3>', unsafe_allow_html=True)
    
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
    st.markdown('<h3 style="color: #1e293b;"><i class="fa-solid fa-gear" style="color: #667eea; margin-right: 10px;"></i>Settings</h3>', unsafe_allow_html=True)
    
    user = st.session_state.user
    user_info = get_user_info(user["id"])
    
    # Handle case where user_info is None
    if user_info is None:
        st.error("Unable to load user information. Please log out and log in again.")
        return
    
    # Account info
    st.markdown('<h4 style="color: #1e293b;"><i class="fa-solid fa-user" style="color: #764ba2; margin-right: 8px;"></i>Account Information</h4>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Name", value=user_info["name"], disabled=True)
    with col2:
        st.text_input("Email", value=user_info["email"], disabled=True)
    
    st.divider()
    
    # Subscription info
    st.markdown('<h4 style="color: #1e293b;"><i class="fa-solid fa-crown" style="color: #f59e0b; margin-right: 8px;"></i>Subscription</h4>', unsafe_allow_html=True)
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
    st.markdown('<h4 style="color: #1e293b;"><i class="fa-solid fa-triangle-exclamation" style="color: #ef4444; margin-right: 8px;"></i>Danger Zone</h4>', unsafe_allow_html=True)
    with st.expander("Delete Account"):
        st.warning("This action cannot be undone. All your data will be permanently deleted.")
        if st.button("Delete My Account", type="secondary"):
            st.error("Contact support@yourdomain.com to delete your account")

# ============================================================
#                    MAIN ENTRY POINT
# ============================================================

if st.session_state.authenticated:
    show_main_app()
else:
    show_auth_page()

# --- FOOTER ---
st.markdown(
    """
    <div class="footer-container">
        <div class="footer-brand">
            <span class="footer-logo"><i class="fa-solid fa-chart-line"></i></span>
            <span class="footer-title">AI Data Analyst Pro</span>
        </div>
        <p class="footer-tagline">Transform your data into insights with the power of AI</p>
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
            <p class="footer-copyright">© 2025 AI Data Analyst Pro. All rights reserved.</p>
        </div>
    </div>
    <style>
    .footer-container {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border-radius: 20px;
        padding: 40px 30px;
        margin-top: 50px;
        text-align: center;
        box-shadow: 0 -10px 40px rgba(102, 126, 234, 0.15);
    }
    .footer-brand {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        margin-bottom: 10px;
    }
    .footer-logo {
        font-size: 2rem;
        color: #667eea;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.1); }
    }
    .footer-title {
        font-size: 1.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .footer-tagline {
        color: #a0a0a0;
        font-size: 0.95rem;
        margin-bottom: 25px;
    }
    .footer-links {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 20px;
        flex-wrap: wrap;
        margin-bottom: 25px;
    }
    .footer-link {
        color: #ffffff;
        text-decoration: none;
        padding: 10px 20px;
        border-radius: 25px;
        background: rgba(102, 126, 234, 0.2);
        transition: all 0.3s ease;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }
    .footer-link:hover {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        transform: translateY(-3px);
        box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
    }
    .footer-divider {
        color: #4a4a6a;
    }
    .footer-bottom {
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        padding-top: 20px;
        margin-top: 10px;
    }
    .footer-bottom p {
        color: #b0b0b0;
        margin: 5px 0;
    }
    .footer-copyright {
        font-size: 0.8rem;
        color: #707090 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)