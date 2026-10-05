# Agrosathi AI

**Smart Agriculture / Smart Farming platform for farmers**

Agrosathi AI is a Flask-based web application that brings farm information and AI-assisted farming tools into one place. The project supports farmer/farm management, weather information, AI tools, and multilingual UI support for English, Hindi, and Marathi.

## Tech Stack

- Python
- Flask
- HTML5
- CSS3
- JavaScript
- SQLite (local development)
- REST APIs
- Groq API integration used by the current AI modules

## Main Project Areas

- Farmer registration and login
- Dashboard
- Farm details / multiple farm management
- Weather
- AI Tools
- Soil Report Analyzer
- Crop Recommendation
- Disease Detection
- Crop Health Analysis
- Fertilizer Advisor
- Irrigation Planner
- Crop Calendar
- Weather Intelligence
- Farm Risk & Yield Analysis
- Farming Assistant
- Smart Farming Reminder
- English / Hindi / Marathi language support

## Project Structure

```text
agrosathi-ai/
├── app.py
├── config.py
├── database.py
├── soil_analyzer.py
├── crop_recommendation.py
├── disease_detection.py
├── crop_health.py
├── fertilizer_advisor.py
├── irrigation_planner.py
├── requirements.txt
├── README.md
├── .gitignore
├── .env.example
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── farm-details.html
│   ├── farmer-details.html
│   ├── weather.html
│   ├── ai-tools/
│   └── ...
└── static/
    ├── css/
    │   └── style.css
    ├── js/
    │   ├── script.js
    │   └── language.js
    └── images/
        └── ...
```

## Local Setup

### 1. Clone the repository

```powershell
git clone https://github.com/samarthpatare/agrosathi-ai.git
cd agrosathi-ai
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Create your private environment file

```powershell
Copy-Item .env.example .env
```

Open `.env` and add your own API key and secret values. **Never commit `.env` to GitHub.**

### 5. Run the application

```powershell
python app.py
```

Then open the local Flask URL shown by the application.

## Security

Private API keys, passwords, `.env`, local databases, Python cache files, and virtual environments should not be committed to GitHub.

## Project Status

This repository contains the current project files supplied for the Agrosathi AI GitHub upload. The existing UI and project structure are preserved rather than redesigned.
