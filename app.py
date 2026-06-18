from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import os
import joblib
import re
from collections import Counter
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "sentiscope_secret_key"

DATABASE = "database/reviews.db"

model = None
vectorizer = None

try:
    model = joblib.load("sentiment_model.pkl")
    vectorizer = joblib.load("vectorizer.pkl")
except:
    print("Model files not found. Dashboard will still work.")

def init_db():
    os.makedirs("database", exist_ok=True)

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        review_text TEXT,
        sentiment TEXT,
        confidence REAL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("SELECT * FROM users WHERE email=?", ("admin@sentiscope.com",))
    admin = cursor.fetchone()

    if admin is None:
        cursor.execute(
            "INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",
            (
                "Administrator",
                "admin@sentiscope.com",
                generate_password_hash("admin123"),
                "admin"
            )
        )

    conn.commit()
    conn.close()

init_db()

@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")

    return render_template(
        "home.html",
        user=session["name"],
        role=session["role"]
    )

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO users(name,email,password) VALUES(?,?,?)",
                (name, email, password)
            )

            conn.commit()
            conn.close()

            flash("Registration Successful")
            return redirect("/login")

        except Exception as e:
            flash("Email already exists")
            print(e)

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        )

        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            session["user"] = user[0]
            session["name"] = user[1]
            session["role"] = user[4]
            return redirect("/")

        flash("Invalid Email or Password")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/predict", methods=["POST"])
def predict():
    if "user" not in session:
        return redirect("/login")

    review = request.form["review"]

    sentiment = "Neutral"
    confidence = 50

    if model and vectorizer:
        vector = vectorizer.transform([review])
        sentiment = model.predict(vector)[0]
        confidence = round(max(model.predict_proba(vector)[0]) * 100, 2)

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO reviews(username, review_text, sentiment, confidence)
        VALUES(?,?,?,?)
        """,
        (session["name"], review, sentiment, confidence)
    )

    conn.commit()
    conn.close()

    emoji = "😐"
    if sentiment == "Positive":
        emoji = "😊"
    elif sentiment == "Negative":
        emoji = "😠"

    return render_template(
        "result.html",
        review=review,
        sentiment=sentiment,
        confidence=confidence,
        emoji=emoji,
        role=session["role"],
        user=session["name"]
    )

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM reviews ORDER BY id DESC")
    reviews = cursor.fetchall()
    conn.close()

    total = len(reviews)
    positive = len([r for r in reviews if r[3] == "Positive"])
    negative = len([r for r in reviews if r[3] == "Negative"])
    neutral = len([r for r in reviews if r[3] == "Neutral"])

    avg_confidence = 0
    if total > 0:
        avg_confidence = round(sum(r[4] for r in reviews) / total, 2)

    positive_rate = 0
    negative_rate = 0
    neutral_rate = 0

    if total > 0:
        positive_rate = round((positive / total) * 100, 1)
        negative_rate = round((negative / total) * 100, 1)
        neutral_rate = round((neutral / total) * 100, 1)

    text = ""
    for r in reviews:
        text += " " + str(r[2])

    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())

    stop_words = {
        "the","is","a","an","of","and","to","for","with",
        "this","that","was","are","very","good","bad","not",
        "but","have","has","had"
    }

    words = [w for w in words if w not in stop_words and len(w) > 2]
    keywords = [w for w, c in Counter(words).most_common(10)]

    return render_template(
        "dashboard.html",
        name=session["name"],
        role=session["role"],
        reviews=reviews,
        total=total,
        positive=positive,
        negative=negative,
        neutral=neutral,
        avg_confidence=avg_confidence,
        positive_rate=positive_rate,
        negative_rate=negative_rate,
        neutral_rate=neutral_rate,
        keywords=keywords
    )

@app.route("/admin")
def admin():
    if "user" not in session:
        return redirect("/login")

    if session["role"] != "admin":
        return redirect("/")

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    cursor.execute("SELECT * FROM reviews")
    reviews = cursor.fetchall()

    total_users = len(users)
    total_reviews = len(reviews)

    positive_reviews = len([r for r in reviews if r[3] == "Positive"])
    negative_reviews = len([r for r in reviews if r[3] == "Negative"])
    neutral_reviews = len([r for r in reviews if r[3] == "Neutral"])

    conn.close()

    return render_template(
        "admin.html",
        users=users,
        reviews=reviews,
        total_users=total_users,
        total_reviews=total_reviews,
        positive_reviews=positive_reviews,
        negative_reviews=negative_reviews,
        neutral_reviews=neutral_reviews,
        role=session["role"],
        user=session["name"]
    )

if __name__ == "__main__":
    app.run(debug=True)
