from flask import Flask, render_template, request, redirect, session, flash
from flask_cors import CORS
from flask_jwt_extended import JWTManager, decode_token
from flask_mysqldb import MySQL
from config import Config
from routes.auth_routes import auth_bp
from routes.survey_routes import survey_bp
import requests
from collections import defaultdict

# ✅ Render-safe deployed backend base URL
BASE_API_URL = "https://survey-site-98jc.onrender.com"

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = "secret123"
app.config["JWT_SECRET_KEY"] = "your_jwt_key"

# Initialize extensions
CORS(app)
jwt = JWTManager(app)
mysql = MySQL(app)
app.mysql = mysql

# Register API Blueprints
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(survey_bp, url_prefix="/api/surveys")

@app.route("/")
def home():
    return "🎉 Survey API is working!"

# ---------------- Frontend Routes ---------------- #

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        data = {
            "username": request.form["username"],
            "email": request.form["email"],
            "password": request.form["password"]
        }
        res = requests.post(f"{BASE_API_URL}/api/auth/signup", json=data)
        if res.status_code == 201:
            return redirect("/login")
        return render_template("signup.html", error=res.json()["error"])
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = {
            "username": request.form["username"],
            "password": request.form["password"]
        }
        res = requests.post(f"{BASE_API_URL}/api/auth/login", json=data)

        if res.status_code == 200:
            token = res.json().get("access_token") or res.json().get("token")
            if not token:
                return render_template("login.html", error="No token received")
            session["token"] = token
            decoded = decode_token(token)
            session["user_id"] = decoded["sub"]
            return redirect("/dashboard")
        return render_template("login.html", error=res.json().get("error", "Login failed"))
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "token" not in session:
        return redirect("/login")

    headers = {"Authorization": f"Bearer {session['token']}"}
    res = requests.get(f"{BASE_API_URL}/api/surveys/my-surveys", headers=headers)

    surveys = res.json().get("surveys", []) if res.status_code == 200 else []
    return render_template("dashboard.html", surveys=surveys)

@app.route("/surveys/<int:survey_id>/delete", methods=["POST"])
def delete_survey(survey_id):
    if "token" not in session:
        return redirect("/login")
    headers = {"Authorization": f"Bearer {session['token']}"}
    res = requests.post(f"{BASE_API_URL}/api/surveys/{survey_id}/delete", headers=headers)
    flash("✅ Deleted!" if res.status_code == 200 else "❌ Delete failed.")
    return redirect("/dashboard")

@app.route("/create-survey", methods=["GET", "POST"])
def create_survey_form():
    if "token" not in session:
        return redirect("/login")
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        if not title:
            return render_template("create_survey.html", error="Survey title is required")
        headers = {"Authorization": f"Bearer {session['token']}"}
        res = requests.post(f"{BASE_API_URL}/api/surveys", json={"title": title, "description": description}, headers=headers)
        if res.status_code == 201:
            return redirect("/dashboard")
        return render_template("create_survey.html", error=res.json().get("error", "Error creating survey"))
    return render_template("create_survey.html")

@app.route("/surveys/<int:survey_id>/questions", methods=["GET", "POST"])
def add_question_ui(survey_id):
    if "token" not in session:
        return redirect("/login")
    headers = {"Authorization": f"Bearer {session['token']}"}
    if request.method == "POST":
        question_text = request.form["question_text"]
        res = requests.post(f"{BASE_API_URL}/api/surveys/{survey_id}/add-question", headers=headers, json={"question_text": question_text})
        if res.status_code == 201:
            flash("✅ Question added!")
        else:
            flash(res.json().get("error", "Failed to add question."))
        return redirect(f"/surveys/{survey_id}/questions")
    # GET Questions
    try:
        res = requests.get(f"{BASE_API_URL}/api/surveys/{survey_id}/questions", headers=headers)
        questions = res.json().get("questions", []) if res.status_code == 200 else []
    except Exception:
        questions = []
    return render_template("questions.html", survey_id=survey_id, questions=questions)

@app.route("/surveys/<int:survey_id>/answer", methods=["GET", "POST"])
def answer_survey(survey_id):
    if "token" not in session:
        return redirect("/login")
    headers = {"Authorization": f"Bearer {session['token']}"}
    if request.method == "POST":
        answer = request.form.get("answer")
        question_id = request.form.get("question_id")
        if not answer or not question_id:
            return render_template("answer.html", survey_id=survey_id, error="Answer is required")
        res = requests.post(f"{BASE_API_URL}/api/surveys/{survey_id}/answer", json={"question_id": question_id, "answer": answer}, headers=headers)
        if res.status_code == 201:
            session.setdefault("answered_questions", []).append(int(question_id))
        else:
            return render_template("answer.html", survey_id=survey_id, error="Failed to submit")
    res = requests.get(f"{BASE_API_URL}/api/surveys/{survey_id}/questions", headers=headers)
    questions = res.json().get("questions", []) if res.status_code == 200 else []
    answered = session.get("answered_questions", [])
    next_question = next((q for q in questions if q["question_id"] not in answered), None)
    if not next_question:
        session.pop("answered_questions", None)
        return render_template("answer.html", survey_id=survey_id, done=True)
    return render_template("answer.html", survey_id=survey_id, question=next_question)

@app.route("/surveys/<int:survey_id>/responses")
def view_responses(survey_id):
    if "token" not in session:
        return redirect("/login")
    headers = {"Authorization": f"Bearer {session['token']}"}
    res = requests.get(f"{BASE_API_URL}/api/surveys/{survey_id}/responses", headers=headers)
    grouped = defaultdict(list)
    for r in res.json().get("responses", []):
        grouped[r["question_text"]].append(r)
    return render_template("view_responses.html", grouped_responses=grouped, survey_id=survey_id)
