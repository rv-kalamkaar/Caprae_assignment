# Caprae_assignment

This is a Flask-based intelligent web scraping tool. It analyzes any company website to extract meaningful insights including:

✅ Internal links

✅ Contact information (emails & phone numbers)

✅ Key leadership profiles

✅ Technology stack

✅ SWOT analysis based on visible web content

Project Structure - 

Caprae_assignment/
├── Backend/
│   ├── app.py              # Flask backend server
│   ├── scraper.py          # Selenium-based multi-page scraper
│   ├── analyzer.py         # SWOT analysis engine
│   └── requirements.txt
└── frontend/
    ├── index.html          # UI interface
    ├── style.css           # Responsive styling
    └── script.js           # Logic, animations, CSV download

Features
----------------
🔎 Intelligent Web Scraping
-Uses Selenium to extract data from the homepage and internal subpages like /about, /team, /contact

-Finds and analyzes leadership profiles, LinkedIn links, and contact info

📈 Advanced SWOT Analysis
-Uses keyword classification and contextual sentence parsing

-Categorizes key phrases into Strengths, Weaknesses, Opportunities, and Threats

🌐 Tech Stack Detection
-Recognizes signs of technologies like WordPress, React, Shopify, Google Analytics, etc.

📊 Clean UI with CSV Export
-Built using plain HTML, CSS, and JavaScript

-Interactive transitions, responsive design

-Exports all results as CSV

⚙️ Installation
----------------
Prerequisites
1. Python 3.8+
2. Chrome browser installed

✅ Technologies Used
----------------
Python, Flask

Selenium, BeautifulSoup

HTML, CSS, JavaScript

CSV Export functionality

ChromeDriverManager for auto-driver setup



