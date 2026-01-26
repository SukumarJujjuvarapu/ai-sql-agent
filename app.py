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
APP_DB_PATH = "app_database.db"

# Default sample database - works locally and on cloud
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "Chinook_Sqlite.sqlite")

# Check if default database exists
if not os.path.exists(DEFAULT_DB_PATH):
    # Fallback for cloud deployment
    DEFAULT_DB_PATH = "Chinook_Sqlite.sqlite"

# Initialize Razorpay Client
try:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
except:
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
    # Create uploads directory
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
    df = pd.read_csv(csv_path)
    conn = sqlite3.connect(db_path)
    df.to_sql(table_name, conn, if_exists='replace', index=False)
    conn.close()
    return db_path

def excel_to_sqlite(excel_path, db_path):
    """Convert Excel file to SQLite database (each sheet = table)"""
    excel_file = pd.ExcelFile(excel_path)
    conn = sqlite3.connect(db_path)
    
    for sheet_name in excel_file.sheet_names:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        # Clean sheet name for SQL table
        clean_name = sheet_name.replace(" ", "_").replace("-", "_")
        df.to_sql(clean_name, conn, if_exists='replace', index=False)
    
    conn.close()
    return db_path

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
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    .tier-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .tier-free { background: #e2e8f0; color: #475569; }
    .tier-starter { background: #dbeafe; color: #1e40af; }
    .tier-pro { background: #fef3c7; color: #92400e; }
    .tier-enterprise { background: #d1fae5; color: #065f46; }
    .pricing-card {
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        transition: transform 0.2s;
    }
    .pricing-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
#                    LOGIN/REGISTER PAGE
# ============================================================

def show_auth_page():
    """Display login/register page"""
    st.markdown('<h1 class="main-header">🤖 AI Data Analyst Pro</h1>', unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>Transform your data into insights with natural language</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
        
        with tab1:
            st.subheader("Welcome Back!")
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
                            st.success("Login successful!")
                            st.rerun()
                        else:
                            st.error("Invalid email or password")
                    else:
                        st.warning("Please fill in all fields")
        
        with tab2:
            st.subheader("Create Account")
            with st.form("register_form"):
                name = st.text_input("Full Name", placeholder="John Doe")
                email = st.text_input("Email", placeholder="you@example.com", key="reg_email")
                password = st.text_input("Password", type="password", placeholder="••••••••", key="reg_pass")
                password2 = st.text_input("Confirm Password", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("Create Account", use_container_width=True)
                
                if submitted:
                    if name and email and password and password2:
                        if password != password2:
                            st.error("Passwords do not match")
                        elif len(password) < 6:
                            st.error("Password must be at least 6 characters")
                        else:
                            success, result = create_user(email, password, name)
                            if success:
                                st.success("Account created! Please login.")
                            else:
                                st.error(result)
                    else:
                        st.warning("Please fill in all fields")
    
    # Features showcase
    st.markdown("---")
    st.markdown("### ✨ Features")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("#### 📊 Smart Charts")
        st.write("Auto-generate visualizations from your data")
    with col2:
        st.markdown("#### 🗣️ Natural Language")
        st.write("Ask questions in plain English")
    with col3:
        st.markdown("#### 📁 Any Data Source")
        st.write("CSV, Excel, or SQLite databases")
    with col4:
        st.markdown("#### 📥 Export Anywhere")
        st.write("Download as PDF, Excel, or CSV")

# ============================================================
#                    PRICING PAGE
# ============================================================

def show_pricing_page():
    """Display pricing page"""
    st.markdown("## 💎 Upgrade Your Plan")
    st.markdown("Choose the perfect plan for your data analysis needs")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="pricing-card">
            <h3>🆓 Free</h3>
            <h2>$0</h2>
            <p>Forever free</p>
            <hr>
            <p>✅ 5 queries/day</p>
            <p>✅ Basic charts</p>
            <p>✅ CSV upload</p>
            <p>❌ Query history</p>
            <p>❌ PDF export</p>
        </div>
        """, unsafe_allow_html=True)
        if st.session_state.user["subscription_tier"] == "free":
            st.button("Current Plan", disabled=True, key="free_btn")
    
    with col2:
        st.markdown("""
        <div class="pricing-card" style="border-color: #3b82f6;">
            <h3>🚀 Starter</h3>
            <h2>₹499/mo</h2>
            <p>For individuals</p>
            <hr>
            <p>✅ 50 queries/day</p>
            <p>✅ All chart types</p>
            <p>✅ Excel upload</p>
            <p>✅ Query history</p>
            <p>❌ PDF export</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.user["subscription_tier"] == "starter":
            st.button("✅ Current Plan", disabled=True, key="starter_current")
        else:
            if st.button("🚀 Upgrade to Starter - ₹499", key="starter_btn", use_container_width=True):
                upgrade_user_subscription(st.session_state.user["id"], "starter", 30)
                st.session_state.user["subscription_tier"] = "starter"
                st.success("🎉 Upgraded to Starter! (Demo Mode)")
                st.balloons()
                st.rerun()
    
    with col3:
        st.markdown("""
        <div class="pricing-card" style="border-color: #f59e0b;">
            <h3>⭐ Pro</h3>
            <h2>₹1,499/mo</h2>
            <p>For teams</p>
            <hr>
            <p>✅ 500 queries/day</p>
            <p>✅ All chart types</p>
            <p>✅ All file types</p>
            <p>✅ Full history</p>
            <p>✅ PDF export</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.user["subscription_tier"] == "pro":
            st.button("✅ Current Plan", disabled=True, key="pro_current")
        else:
            if st.button("⭐ Upgrade to Pro - ₹1,499", key="pro_btn", use_container_width=True):
                upgrade_user_subscription(st.session_state.user["id"], "pro", 30)
                st.session_state.user["subscription_tier"] = "pro"
                st.success("🎉 Upgraded to Pro! (Demo Mode)")
                st.balloons()
                st.rerun()
    
    with col4:
        st.markdown("""
        <div class="pricing-card" style="border-color: #10b981;">
            <h3>🏢 Enterprise</h3>
            <h2>₹4,999/mo</h2>
            <p>For organizations</p>
            <hr>
            <p>✅ Unlimited queries</p>
            <p>✅ Priority support</p>
            <p>✅ Custom integrations</p>
            <p>✅ Full history</p>
            <p>✅ All exports</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.user["subscription_tier"] == "enterprise":
            st.button("✅ Current Plan", disabled=True, key="enterprise_current")
        else:
            if st.button("🏢 Upgrade to Enterprise - ₹4,999", key="enterprise_btn", use_container_width=True):
                upgrade_user_subscription(st.session_state.user["id"], "enterprise", 30)
                st.session_state.user["subscription_tier"] = "enterprise"
                st.success("🎉 Upgraded to Enterprise! (Demo Mode)")
                st.balloons()
                st.rerun()
    
    # Payment Notice
    st.divider()
    st.info("💡 **Demo Mode:** Upgrades are instant for testing. Real payments via Razorpay coming soon!")

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
        st.markdown(f"### 👤 {user['name']}")
        tier_class = f"tier-{tier}"
        st.markdown(f'<span class="tier-badge {tier_class}">{tier.upper()}</span>', unsafe_allow_html=True)
        
        # Query limit indicator
        user_info = get_user_info(user["id"])
        limits = {"free": 5, "starter": 50, "pro": 500, "enterprise": 99999}
        remaining = limits.get(tier, 5) - (user_info["queries_today"] if user_info["last_query_date"] == datetime.now().date().isoformat() else 0)
        st.progress(remaining / limits.get(tier, 5))
        st.caption(f"🔥 {remaining} queries remaining today")
        
        st.divider()
        
        # Navigation
        st.markdown("### 📍 Navigation")
        page = st.radio(
            "Go to:",
            ["🔍 Query Data", "📁 Data Sources", "📜 Query History", "💎 Pricing", "⚙️ Settings"],
            label_visibility="collapsed"
        )
        
        st.divider()
        
        # Quick upgrade button for free users
        if tier == "free":
            if st.button("⚡ Upgrade Now", use_container_width=True):
                st.session_state.show_pricing = True
                st.rerun()
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()
    
    # --- MAIN CONTENT ---
    st.markdown(f'<h1 class="main-header">🤖 AI Data Analyst Pro</h1>', unsafe_allow_html=True)
    
    # Route to different pages
    if page == "💎 Pricing" or st.session_state.get("show_pricing"):
        st.session_state.show_pricing = False
        show_pricing_page()
        return
    
    elif page == "📁 Data Sources":
        show_data_sources_page()
        return
    
    elif page == "📜 Query History":
        show_history_page()
        return
    
    elif page == "⚙️ Settings":
        show_settings_page()
        return
    
    # --- QUERY DATA PAGE (Default) ---
    
    # Current database info
    db_name = os.path.basename(st.session_state.current_db)
    st.info(f"📊 **Active Database:** {db_name}")
    
    # Query input
    st.markdown("### 💬 Ask Your Data")
    
    with st.form("query_form"):
        user_query = st.text_input(
            "Enter your question:",
            placeholder="e.g., Show me top 10 customers by total spending"
        )
        
        col1, col2 = st.columns([3, 1])
        with col1:
            submitted = st.form_submit_button("🚀 Run Analysis", use_container_width=True)
        with col2:
            show_sql = st.form_submit_button("📝 Show SQL Only")
    
    # Process query
    if submitted or show_sql:
        if user_query:
            # Check query limit
            can_query, remaining = check_query_limit(user["id"], tier)
            
            if not can_query:
                st.error(f"❌ Daily query limit reached! Upgrade your plan for more queries.")
                if tier == "free":
                    st.info("💡 Upgrade to Starter for 50 queries/day")
            else:
                with st.spinner("🤖 AI is analyzing your question..."):
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
            st.warning("⚠️ Please enter a question first!")
    
    # Display results
    if st.session_state.sql_code:
        st.markdown("### 📜 Generated SQL")
        st.code(st.session_state.sql_code, language="sql")
    
    if st.session_state.result_df is not None:
        result = st.session_state.result_df
        
        if isinstance(result, pd.DataFrame):
            # Results header with export buttons
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col1:
                st.markdown("### 📋 Results")
            
            with col2:
                csv_data = export_to_csv(result)
                st.download_button(
                    "📥 CSV",
                    csv_data,
                    file_name="results.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col3:
                excel_data = export_to_excel(result)
                st.download_button(
                    "📥 Excel",
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
                            "📥 PDF",
                            pdf_data,
                            file_name="report.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    else:
                        st.button("📥 PDF", disabled=True, help="Install reportlab for PDF export")
                else:
                    st.button("📥 PDF", disabled=True, help="Upgrade to Pro for PDF export")
            
            # Data table
            st.dataframe(result, use_container_width=True)
            st.caption(f"Showing {len(result)} rows")
            
            # Visualization
            if len(result.columns) > 1:
                st.markdown("### 📊 Visualization")
                
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
                        if chart_type == "Bar Chart":
                            st.bar_chart(numeric_df)
                        elif chart_type == "Line Chart":
                            st.line_chart(numeric_df)
                        elif chart_type == "Area Chart":
                            st.area_chart(numeric_df)
                        elif chart_type == "Scatter Plot":
                            st.scatter_chart(numeric_df)
                        elif chart_type == "Pie Chart":
                            fig = px.pie(
                                result,
                                names=result.columns[0],
                                values=numeric_df.columns[0],
                                title="Distribution"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("No numeric data available for visualization")
        else:
            st.error(result)

# ============================================================
#                    DATA SOURCES PAGE
# ============================================================

def show_data_sources_page():
    """Data sources management page"""
    st.markdown("### 📁 Data Sources")
    
    tier = st.session_state.user["subscription_tier"]
    
    # File upload section
    st.markdown("#### 📤 Upload New Data")
    
    # File type restrictions based on tier
    if tier == "free":
        allowed_types = ["csv"]
        st.caption("🆓 Free tier: CSV files only. Upgrade for Excel & SQLite support.")
    elif tier == "starter":
        allowed_types = ["csv", "xlsx", "xls"]
        st.caption("🚀 Starter tier: CSV and Excel files")
    else:
        allowed_types = ["csv", "xlsx", "xls", "sqlite", "db"]
        st.caption("⭐ Pro/Enterprise: All file types supported")
    
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=allowed_types,
        help="Upload your data file to start analyzing"
    )
    
    if uploaded_file:
        file_ext = uploaded_file.name.split('.')[-1].lower()
        
        if st.button("📥 Process File", use_container_width=True):
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
                    
                    st.success(f"✅ File processed! Now using: {uploaded_file.name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error processing file: {e}")
    
    st.divider()
    
    # User's uploaded files
    st.markdown("#### 📂 Your Data Sources")
    
    user_files = get_user_files(st.session_state.user["id"])
    
    # Default database option
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.write("📊 **Chinook Sample Database** (Default)")
    with col2:
        if st.button("Use", key="use_default"):
            st.session_state.current_db = DEFAULT_DB_PATH
            st.success("Switched to Chinook database")
            st.rerun()
    with col3:
        if st.session_state.current_db == DEFAULT_DB_PATH:
            st.write("✅ Active")
    
    # List user files
    for file in user_files:
        file_id, filename, file_path, file_type, uploaded_at = file
        db_path = file_path.replace(f'.{file_type}', '.db') if file_type in ['csv', 'xlsx', 'xls'] else file_path
        
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.write(f"📄 **{filename}**")
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
                st.write("✅ Active")
    
    if not user_files:
        st.info("No files uploaded yet. Upload your first dataset above!")

# ============================================================
#                    HISTORY PAGE
# ============================================================

def show_history_page():
    """Query history page"""
    st.markdown("### 📜 Query History")
    
    tier = st.session_state.user["subscription_tier"]
    
    if tier == "free":
        st.warning("⚠️ Query history is available on Starter plan and above.")
        st.button("⚡ Upgrade to Starter", on_click=lambda: st.session_state.update({"show_pricing": True}))
        return
    
    # Get history
    history = get_query_history(st.session_state.user["id"])
    
    if history:
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🗑️ Clear History"):
                clear_query_history(st.session_state.user["id"])
                st.success("History cleared!")
                st.rerun()
        
        for idx, (question, sql, preview, timestamp) in enumerate(history):
            with st.expander(f"**{question[:50]}{'...' if len(question) > 50 else ''}** - {timestamp[:16]}"):
                st.markdown("**Question:**")
                st.write(question)
                st.markdown("**SQL Query:**")
                st.code(sql, language="sql")
                if preview:
                    st.markdown("**Result Preview:**")
                    st.text(preview[:300] + "..." if len(preview) > 300 else preview)
                
                # Re-run button
                if st.button("🔄 Run Again", key=f"rerun_{idx}"):
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
    st.markdown("### ⚙️ Settings")
    
    user = st.session_state.user
    user_info = get_user_info(user["id"])
    
    # Account info
    st.markdown("#### 👤 Account Information")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Name", value=user_info["name"], disabled=True)
    with col2:
        st.text_input("Email", value=user_info["email"], disabled=True)
    
    st.divider()
    
    # Subscription info
    st.markdown("#### 💎 Subscription")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Current Plan", value=user_info["subscription_tier"].upper(), disabled=True)
    with col2:
        expires = user_info["subscription_expires"] or "N/A"
        st.text_input("Expires", value=expires[:10] if expires != "N/A" else expires, disabled=True)
    
    if user_info["subscription_tier"] != "enterprise":
        if st.button("⚡ Upgrade Plan"):
            st.session_state.show_pricing = True
            st.rerun()
    
    st.divider()
    
    # Danger zone
    st.markdown("#### ⚠️ Danger Zone")
    with st.expander("Delete Account"):
        st.warning("This action cannot be undone. All your data will be permanently deleted.")
        if st.button("🗑️ Delete My Account", type="secondary"):
            st.error("Contact support@yourdomain.com to delete your account")

# ============================================================
#                    MAIN ENTRY POINT
# ============================================================

if st.session_state.authenticated:
    show_main_app()
else:
    show_auth_page()

# --- FOOTER ---
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: grey;">
        <p>Developed by <b>Sukumar Jujjuvarapu</b></p>
        <a href="https://www.linkedin.com/in/sukumar-jujjuvarapu/" target="_blank">LinkedIn</a> | 
        <a href="https://github.com/SukumarJujjuvarapu" target="_blank">GitHub</a> |
        <a href="https://sukumarjujjuvarapu.github.io/" target="_blank">Portfolio</a>
    </div>
    """,
    unsafe_allow_html=True
)