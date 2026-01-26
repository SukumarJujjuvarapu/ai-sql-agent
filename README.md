# 🤖 AI Data Analyst Pro

> **Transform your data into insights using natural language** - Ask questions in English, get SQL results instantly!

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-Click_Here-brightgreen?style=for-the-badge)](https://sukumarjujjuvarapu-ai-sql-agent.streamlit.app/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://streamlit.io/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org/)
[![Made in India](https://img.shields.io/badge/Made_in-India_🇮🇳-orange?style=for-the-badge)]()

---

## 🎯 What is this?

Upload any database (CSV, Excel, SQLite) and ask questions in **plain English**. The AI converts your question to SQL, runs it, and shows you beautiful charts!

**Example:**
> "Show me top 10 customers by total sales" → Instant bar chart with data

---

## ✨ Features

| Feature | Free | Starter (₹499/mo) | Pro (₹1,499/mo) | Enterprise (₹4,999/mo) |
|---------|------|-------------------|-----------------|------------------------|
| Queries/day | 5 | 50 | 500 | Unlimited |
| CSV Upload | ✅ | ✅ | ✅ | ✅ |
| Excel Upload | ❌ | ✅ | ✅ | ✅ |
| SQLite Upload | ❌ | ❌ | ✅ | ✅ |
| Query History | ❌ | ✅ | ✅ | ✅ |
| PDF Export | ❌ | ❌ | ✅ | ✅ |
| Priority Support | ❌ | ❌ | ❌ | ✅ |

### 🔥 Core Capabilities

- 📤 **Multi-format Upload** - CSV, Excel (.xlsx), SQLite databases
- 🗣️ **Natural Language Queries** - Ask in English, get SQL results
- 📊 **Smart Charts** - Bar, Line, Pie, Scatter, Area (auto-suggested)
- 🔐 **User Authentication** - Secure login & registration
- 📜 **Query History** - Save, view, and replay past queries
- 📥 **Export Options** - Download as PDF, Excel, or CSV
- 💳 **Razorpay Payments** - Subscription billing (India)

---

## 🚀 Live Demo

👉 **[Try it now!](https://sukumarjujjuvarapu-ai-sql-agent.streamlit.app/)**

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Streamlit |
| AI/LLM | Groq (Llama 3.3-70b) |
| Database | SQLite |
| Charts | Plotly |
| Payments | Razorpay |
| Hosting | Streamlit Cloud |
| PDF Export | ReportLab |

---

## 📦 Local Installation

### 1. Clone the repo
```bash
git clone https://github.com/SukumarJujjuvarapu/ai-sql-agent.git
cd ai-sql-agent
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up environment variables
```bash
# Create .env file
copy .env.example .env

# Add your keys to .env:
# GROQ_API_KEY=your_groq_api_key
# RAZORPAY_KEY_ID=your_razorpay_key (optional)
# RAZORPAY_KEY_SECRET=your_razorpay_secret (optional)
```

### 4. Run the app
```bash
streamlit run app.py
```

### 5. Open in browser
```
http://localhost:8501
```

---

## 🔑 API Keys

| Service | Purpose | Get it from |
|---------|---------|-------------|
| Groq | AI/LLM for SQL generation | [console.groq.com](https://console.groq.com/) |
| Razorpay | Payments (optional) | [dashboard.razorpay.com](https://dashboard.razorpay.com/) |

---

## 📁 Project Structure

```
ai-sql-agent/
├── app.py                 # Main application
├── config.py              # Configuration
├── requirements.txt       # Dependencies
├── .env.example           # Environment template
├── Chinook_Sqlite.sqlite  # Sample database
├── docs/
│   └── index.html         # Landing page
└── README.md
```

---

## 🎬 How It Works

1. **Upload** your database (CSV/Excel/SQLite)
2. **Ask** a question in plain English
3. **AI** converts it to SQL using Llama 3.3
4. **Results** displayed as table + chart
5. **Export** as PDF/Excel/CSV

---

## 📊 Sample Queries

Try these with the sample Chinook database:

- "Show total sales by country"
- "Top 10 customers by purchase amount"
- "Monthly revenue trend for 2023"
- "Which genre has the most tracks?"
- "Average invoice total by city"

---

## 🤝 Contributing

Contributions welcome! Feel free to:
- 🐛 Report bugs
- 💡 Suggest features
- 🔧 Submit PRs

---

## 📄 License

MIT License - feel free to use for your own projects!

---

## 👨‍💻 Author

**Sukumar Jujjuvarapu**

- GitHub: [@SukumarJujjuvarapu](https://github.com/SukumarJujjuvarapu)
- Live App: [AI Data Analyst Pro](https://sukumarjujjuvarapu-ai-sql-agent.streamlit.app/)

---

## ⭐ Star this repo!

If you found this useful, give it a ⭐ on GitHub!

---

*Built with ❤️ in India 🇮🇳*
