import os
from flask import Flask, render_template, request, redirect, session, flash
from config import Config
from db import get_db, close_db
from routes.auth_routes import auth_bp
from routes.survey_routes import survey_bp
from flask_cors import CORS
from collections import defaultdict
from werkzeug.security import check_password_hash, generate_password_hash

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
        except Exception:
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
    cursor.execute("SELECT * FROM surveys WHERE created_by = ?", (user_id,))
    surveys = cursor.fetchall()

    return render_template("dashboard.html", surveys=surveys)

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
        cursor.execute(
            "INSERT INTO surveys (title, description, created_by) VALUES (?, ?, ?)",
            (title, description, user_id)
        )
        db.commit()
        flash("✅ Survey created!")
        return redirect("/dashboard")

    return render_template("create_survey.html")

@app.route("/surveys/<int:survey_id>/questions", methods=["GET", "POST"])
def add_questions(survey_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("⚠️ Login required.")
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    if request.method == "POST":
        question_text = request.form.get("question_text")  # ✅ Correct field name
        if question_text:
            try:
                cursor.execute(
                    "INSERT INTO questions (survey_id, question_text) VALUES (?, ?)",
                    (survey_id, question_text)
                )
                db.commit()
                flash("✅ Question added!")
            except Exception as e:
                flash(f"❌ Failed to add question: {str(e)}")

    cursor.execute("SELECT question_text FROM questions WHERE survey_id = ?", (survey_id,))
    questions = cursor.fetchall()

    return render_template("add_questions.html", survey_id=survey_id, questions=questions)


@app.route("/surveys/<int:survey_id>/answer", methods=["GET", "POST"])
def answer_survey(survey_id):
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    db = get_db()
    cursor = db.cursor()

    if request.method == "POST":
        answer = request.form.get("answer")
        question_id = request.form.get("question_id")

        if answer and question_id:
            cursor.execute("""
                INSERT INTO responses (survey_id, question_id, user_id, answer_text)
                VALUES (?, ?, ?, ?)
            """, (survey_id, question_id, user_id, answer))
            db.commit()

    # 🔄 Fetch all questions
    cursor.execute("""
        SELECT q.question_id, q.question_text
        FROM questions q
        WHERE q.survey_id = ?
    """, (survey_id,))
    questions = cursor.fetchall()

    # 🔍 Get already answered questions
    cursor.execute("""
        SELECT question_id FROM responses
        WHERE survey_id = ? AND user_id = ?
    """, (survey_id, user_id))
    answered_ids = [row["question_id"] for row in cursor.fetchall()]

    # ⏭️ Pick next unanswered question
    next_question = next((q for q in questions if q["question_id"] not in answered_ids), None)

    if not next_question:
        return render_template("answer.html", done=True)

    return render_template("answer.html", question=next_question, survey_id=survey_id)

@app.route("/surveys/<int:survey_id>/responses")
def view_responses(survey_id):
    if "user_id" not in session:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT 
            a.answer_text, 
            q.question_text 
        FROM responses a
        JOIN questions q ON a.question_id = q.question_id
        WHERE a.survey_id = ?
    """, (survey_id,))
    responses = cursor.fetchall()

    grouped = defaultdict(list)
    for answer, question in responses:
        grouped[question].append(answer)

    return render_template("view_responses.html", grouped_responses=grouped, survey_id=survey_id)
