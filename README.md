# 🤰 Pregbot — Pregnancy Health Predictor & Chatbot

A trusted, AI-powered pregnancy health chatbot built with Machine Learning (ML), Natural Language Processing (NLP), and Explainable AI (XAI). Pregbot provides intelligent predictions and transparent reasoning to support expecting mothers and healthcare professionals.

---

## 🔍 About the Project

Pregbot is designed to assist users with pregnancy-related health queries by leveraging ML models trained on medical data. Unlike black-box AI systems, Pregbot integrates **Explainable AI (XAI)** to clearly communicate *why* a prediction is made — increasing trust and clinical interpretability.

---

## ✨ Features

- 💬 **Conversational Chatbot** — NLP-powered interface for natural pregnancy health queries
- 🔮 **Health Predictions** — ML-based risk prediction for pregnancy-related conditions
- 🧠 **Explainable AI (XAI)** — Transparent reasoning behind every prediction
- 🔐 **User Authentication** — Secure login and registration system
- 🩺 **Doctor Dashboard** — Separate interface for medical professionals
- 📊 **Patient Dashboard** — Personalised health insights for users

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| ML / NLP | Scikit-learn, NLP libraries |
| XAI | Explainability libraries (LIME / SHAP) |
| Frontend | HTML, CSS |
| Database | SQL (db.sql) |

---

## 📁 Project Structure

```
pregbot_predictor/
├── app.py                  # Main Flask application
├── config.py               # App configuration
├── db.sql                  # Database schema
├── requirements.txt        # Python dependencies
├── index.html              # Landing page
├── login.html              # Login page
├── register.html           # Registration page
├── dashboard.html          # Patient dashboard
├── doctor_dashboard.html   # Doctor dashboard
├── symptom_check.html      # Symptom checker interface
├── profile.html            # User profile
├── layout.html             # Base layout template
└── App.bat                 # Windows launcher script
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/ashok123gunti/pregbot_predictor.git
cd pregbot_predictor

# Install dependencies
pip install -r requirements.txt

# Set up the database
mysql -u root -p < db.sql

# Run the application
python app.py
```

Then open your browser and go to `http://localhost:5000`

---

## 👨‍💻 Author

**Gunti Ashok**
- GitHub: [@ashok123gunti](https://github.com/ashok123gunti)
- LinkedIn: [gunti-ashok](https://www.linkedin.com/in/gunti-ashok-34b400291/)

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).
