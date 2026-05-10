from flask import Flask, render_template, request, redirect, session, flash
import joblib
import os
import sqlite3
import requests
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

API_KEY = os.getenv("NEWS_API_KEY", "01005f5f946a4d8b9c232a8ee206c88d")
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key_123")

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect(os.path.join(BASE_DIR, "database.db"))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()
def get_db():
    return sqlite3.connect("database.db")

# ---------------- LOAD MODEL ----------------

model_path = os.path.join(BASE_DIR, "model", "model.pkl")
vectorizer_path = os.path.join(BASE_DIR, "model", "vectorizer.pkl")

model = joblib.load(model_path)
vectorizer = joblib.load(vectorizer_path)

# ---------------- REGISTER ----------------
from werkzeug.security import generate_password_hash

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # ✅ ADD HERE
        hashed_password = generate_password_hash(password)

        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hashed_password)
        )

        conn.commit()
        conn.close()

        flash("Registered successfully!")
        return redirect('/login')

    return render_template('register.html')
# ---------------- LOGIN ----------------
from werkzeug.security import check_password_hash

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user[2], password):
            session['user'] = username
            return redirect('/')
        else:
            flash("Invalid login")

    return render_template('login.html')

# ---------------- HOME ----------------
@app.route('/')
def home():
    if 'user' not in session:
        return redirect('/login')
    return render_template("index.html")

# ---------------- NEWS ----------------
@app.route('/news')
def news():
    try:
        url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={API_KEY}"
        res = requests.get(url)
        data = res.json()

        articles = data.get('articles', [])

        return render_template("news.html", articles=articles)

    except Exception as e:
        return f"Error loading news: {str(e)}"

# ---------------- PREDICT ----------------
@app.route('/predict', methods=['POST'])
def predict():
    news = request.form['news']

    vector = vectorizer.transform([news])
    prediction = model.predict(vector)[0]

    # ✅ ADD THIS
    prob = model.predict_proba(vector)[0]
    confidence = round(max(prob) * 100, 2)

    result = "Fake News" if prediction == 0 else "Real News"

    # ✅ UPDATE RETURN
    return render_template("index.html", prediction=result, confidence=confidence)

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000 ,debug=True)