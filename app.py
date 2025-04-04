import os
from flask import Flask, render_template, request, redirect, session, flash
from config import Config
from db import get_db, close_db
from routes.auth_routes import auth_bp
from routes.survey_routes import survey_bp
from flask_cors import CORS
from collections import defaultdict
import requests
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = "secret123"

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(survey_bp, url_prefix="/api/surveys")

# Middleware
CORS(app)
app.teardown_appcontext(close_db)

@app.route("/")
def home():
    return "🎉 Survey App is Live!"

# ---------------- Frontend Routes ---------------- #

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT user_id, password FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user[1], password):
            session["user_id"] = user[0]
            flash("✅ Logged in!")
            return redirect("/dashboard")
        else:
            return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")

from werkzeug.security import generate_password_hash

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        if not username or not password:
            return render_template("signup.html", error="Username and password required")

        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (username, email, password)
                VALUES (?, ?, ?)
            """, (username, email, generate_password_hash(password)))
            db.commit()
            flash("🎉 Signup successful!")
            return redirect("/login")
        except Exception as e:
            return render_template("signup.html", error="Username might already exist 🥲")

    return render_template("signup.html")


@app.route("/dashboard")
def dashboard():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in.")
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT * FROM surveys WHERE created_by = ?", (user_id,))
        surveys = cursor.fetchall()
        return render_template("dashboard.html", surveys=surveys)
    except Exception as e:
        return render_template("dashboard.html", error=str(e))


@app.route("/logout")
def logout():
    session.clear()
    flash("👋 Logged out successfully.")
    return redirect("/login")

@app.route("/create-survey", methods=["GET", "POST"])
def create_survey():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to create surveys.")
        return redirect("/login")

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")

        if not title:
            return render_template("create_survey.html", error="Survey title is required")

        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute(
                "INSERT INTO surveys (title, description, created_by) VALUES (?, ?, ?)",
                (title, description, user_id)
            )
            db.commit()
            flash("✅ Survey created!")
            return redirect("/dashboard")
        except Exception as e:
            return render_template("create_survey.html", error=f"Error: {str(e)}")

    return render_template("create_survey.html")


@app.route("/surveys/<int:survey_id>/questions", methods=["GET", "POST"])
def questions(survey_id):
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        question_text = request.form["question_text"]
        data = {"question_text": question_text}
        res = requests.post(f"http://127.0.0.1:5000/api/surveys/{survey_id}/add-question", json=data, cookies=session)
        if res.status_code == 201:
            flash("✅ Question added!")
        else:
            flash("❌ Failed to add question.")
        return redirect(f"/surveys/{survey_id}/questions")

    res = requests.get(f"http://127.0.0.1:5000/api/surveys/{survey_id}/questions", cookies=session)
    if res.status_code == 200:
        questions = res.json()["questions"]
        return render_template("questions.html", questions=questions, survey_id=survey_id)

    return render_template("questions.html", survey_id=survey_id, error="Unable to load questions.")

@app.route("/surveys/<int:survey_id>/answer", methods=["GET", "POST"])
def answer_survey(survey_id):
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        answer = request.form["answer"]
        question_id = request.form["question_id"]
        data = {"answer": answer, "question_id": question_id}
        requests.post(f"http://127.0.0.1:5000/api/surveys/{survey_id}/answer", json=data, cookies=session)

    res = requests.get(f"http://127.0.0.1:5000/api/surveys/{survey_id}/questions", cookies=session)
    questions = res.json().get("questions", [])
    answered = session.get("answered_questions", [])
    next_question = next((q for q in questions if q["question_id"] not in answered), None)

    if not next_question:
        return render_template("answer.html", done=True)

    session.setdefault("answered_questions", []).append(next_question["question_id"])
    return render_template("answer.html", question=next_question, survey_id=survey_id)

@app.route("/surveys/<int:survey_id>/responses")
def view_responses(survey_id):
    if "user_id" not in session:
        return redirect("/login")

    res = requests.get(f"http://127.0.0.1:5000/api/surveys/{survey_id}/responses", cookies=session)
    grouped = defaultdict(list)

    if res.status_code == 200:
        for r in res.json().get("responses", []):
            grouped[r["question_text"]].append(r)
    return render_template("view_responses.html", grouped_responses=grouped, survey_id=survey_id)

