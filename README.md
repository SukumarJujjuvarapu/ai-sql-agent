# 🤖 AI Data Analyst Pro

> **Transform your data into insights using natural language** - A revenue-generating SaaS application

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://streamlit.io/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org/)
[![Stripe](https://img.shields.io/badge/Stripe-626CD9?style=for-the-badge&logo=Stripe&logoColor=white)](https://stripe.com/)

---

## ✨ Features

| Feature | Free | Starter ($9/mo) | Pro ($29/mo) | Enterprise ($99/mo) |
|---------|------|-----------------|--------------|---------------------|
| Queries/day | 5 | 50 | 500 | Unlimited |
| CSV Upload | ✅ | ✅ | ✅ | ✅ |
| Excel Upload | ❌ | ✅ | ✅ | ✅ |
| SQLite Upload | ❌ | ❌ | ✅ | ✅ |
| Query History | ❌ | ✅ | ✅ | ✅ |
| PDF Export | ❌ | ❌ | ✅ | ✅ |
| Priority Support | ❌ | ❌ | ❌ | ✅ |

### Core Capabilities
- 📤 **Upload CSV/Excel/SQLite** - Bring your own data
- 🗣️ **English → SQL via LLM** - Ask questions in plain English
- 📊 **Charts & Dashboards** - Bar, Line, Pie, Scatter, Area charts
- 🔐 **User Authentication** - Secure login/register system
- 📜 **Query History** - Save and replay past queries
- 📥 **Export PDF/Excel/CSV** - Download your results
- 💳 **Stripe Payments** - Subscription billing built-in

---

## 🚀 Quick Start

### 1. Clone & Install
```bash
git clone https://github.com/yourusername/ai-data-analyst-pro.git
cd ai-data-analyst-pro
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy the example environment file
copy .env.example .env   # Windows
cp .env.example .env     # Mac/Linux

# Edit .env with your API keys
```

### 3. Run the App
```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser!

---

## 🔧 Configuration

### Required API Keys

1. **Groq API Key** (for LLM)
   - Go to https://console.groq.com/keys
   - Create a new API key
   - Add to `.env`: `GROQ_API_KEY=gsk_xxxxx`

2. **Stripe Keys** (for payments)
   - Go to https://dashboard.stripe.com/apikeys
   - Copy your test keys first
   - Add to `.env`:
     ```
     STRIPE_SECRET_KEY=sk_test_xxxxx
     STRIPE_PUBLISHABLE_KEY=pk_test_xxxxx
     ```

### Setting Up Stripe Products

1. Go to https://dashboard.stripe.com/products
2. Create 3 products: Starter, Pro, Enterprise
3. Add monthly pricing to each
4. Copy the Price IDs to your `.env` file

---

## 📁 Project Structure

```
ai-data-analyst-pro/
├── app.py                 # Main Streamlit application
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── .env.example           # Environment template
├── .env                   # Your secrets (git-ignored)
├── app_database.db        # User/history database (auto-created)
├── Chinook_Sqlite.sqlite  # Sample database
└── uploads/               # User uploaded files
    └── user_{id}/         # Per-user upload folders
```

---

## 🌐 Deployment

### Deploy to Streamlit Cloud (Free)

1. Push code to GitHub
2. Go to https://share.streamlit.io/
3. Connect your repo
4. Add secrets in Streamlit Cloud dashboard:
   ```toml
   GROQ_API_KEY = "gsk_xxxxx"
   STRIPE_SECRET_KEY = "sk_live_xxxxx"
   STRIPE_PUBLISHABLE_KEY = "pk_live_xxxxx"
   ```

### Deploy to Railway/Render

```bash
# Procfile
web: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

### Deploy with Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

---

## 💳 Stripe Webhook Setup

For production, set up webhooks to handle subscription events:

1. Go to https://dashboard.stripe.com/webhooks
2. Add endpoint: `https://yourdomain.com/webhook`
3. Select events:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
4. Copy webhook secret to `.env`

---

## 🔒 Security Checklist

- [ ] Never commit `.env` file
- [ ] Use environment variables for all secrets
- [ ] Enable HTTPS in production
- [ ] Use Stripe's live keys only in production
- [ ] Regularly rotate API keys
- [ ] Add rate limiting for production

---

## 📈 Revenue Model

| Tier | Monthly | Yearly | Target Users |
|------|---------|--------|--------------|
| Free | $0 | $0 | Lead generation |
| Starter | $9 | $90 | Individual analysts |
| Pro | $29 | $290 | Small teams |
| Enterprise | $99 | $990 | Organizations |

**Potential MRR with 100 paid users:**
- 50 Starter × $9 = $450
- 40 Pro × $29 = $1,160
- 10 Enterprise × $99 = $990
- **Total: $2,600/month**

---

## 🛠️ Tech Stack

- **Frontend:** Streamlit
- **Backend:** Python, SQLite
- **AI/LLM:** Groq (Llama 3.3 70B)
- **Payments:** Stripe
- **Charts:** Plotly, Matplotlib
- **Export:** ReportLab (PDF), OpenPyXL (Excel)

---

## 👨‍💻 Author

**Sukumar Jujjuvarapu**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/sukumar-jujjuvarapu/)
[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/SukumarJujjuvarapu)
[![Portfolio](https://img.shields.io/badge/Portfolio-255E63?style=for-the-badge&logo=About.me&logoColor=white)](https://sukumarjujjuvarapu.github.io/)

---

## 📄 License

MIT License - feel free to use for your own SaaS!

---

## 🙏 Support

If you find this useful, please ⭐ the repo!

For business inquiries: sukumar@yourdomain.com