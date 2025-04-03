from flask import Flask, render_template, request, redirect, session, flash
from flask_cors import CORS
from flask_jwt_extended import JWTManager, decode_token
from flask_mysqldb import MySQL
import requests
from config import Config
from routes.auth_routes import auth_bp
from routes.survey_routes import survey_bp



app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = "secret123"
app.config["JWT_SECRET_KEY"] = "your_jwt_key"

# Initialize extensions
CORS(app)
jwt = JWTManager(app)
mysql = MySQL(app)
app.mysql = mysql  # Make MySQL accessible from blueprints

# Register API blueprints
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

        res = requests.post("http://127.0.0.1:5000/api/auth/signup", json=data)
        if res.status_code == 201:
            return redirect("/login")
        else:
            return render_template("signup.html", error=res.json()["error"])

    return render_template("signup.html")

from flask_jwt_extended import decode_token

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = {
            "username": request.form["username"],
            "password": request.form["password"]
        }

        res = requests.post("http://127.0.0.1:5000/api/auth/login", json=data)

        if res.status_code == 200:
            print("Login response:", res.json())  # 🔍 Debug output

            # 🛠 Try both access_token and token just in case
            token = res.json().get("access_token") or res.json().get("token")

            if not token:
                return render_template("login.html", error="No token returned from server")

            session["token"] = token
            decoded = decode_token(token)
            session["user_id"] = decoded["sub"]
            return redirect("/dashboard")
        else:
            return render_template("login.html", error=res.json().get("error", "Login failed"))
    
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "token" not in session:
        return redirect("/login")

    headers = {
        "Authorization": f"Bearer {session['token']}"
    }
    res = requests.get("http://127.0.0.1:5000/api/surveys/my-surveys", headers=headers)

    if res.status_code == 200:
        surveys = res.json().get("surveys", [])
    else:
        surveys = []
        print("Dashboard API error:", res.status_code, res.text)

    return render_template("dashboard.html", surveys=surveys)

@app.route("/surveys/<int:survey_id>/delete", methods=["POST"])
def delete_survey(survey_id):
    if "token" not in session:
        return redirect("/login")

    headers = {"Authorization": f"Bearer {session['token']}"}

    try:
        res = requests.delete(
            f"http://127.0.0.1:5000/api/surveys/{survey_id}",
            headers=headers
        )
        if res.status_code == 200:
            flash("Survey deleted successfully!")
        else:
            flash(f"Failed to delete survey: {res.json().get('error', 'Unknown error')}")
    except Exception as e:
        print("Delete error:", e)
        flash("An error occurred while deleting the survey.")

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
        res = requests.post(
            "http://127.0.0.1:5000/api/surveys",
            json={"title": title, "description": description},
            headers=headers
        )

        try:
            if res.status_code == 201:
                return redirect("/dashboard")
            else:
                print("Create survey error:", res.status_code, res.text)  # Debug print
                return render_template(
                    "create_survey.html",
                    error=res.json().get("error", "Unknown error occurred.")
                )
        except ValueError:
            error_message = "Server returned invalid response."
            return render_template("create_survey.html", error=error_message)

    return render_template("create_survey.html")


@app.route("/surveys/<int:survey_id>/questions", methods=["GET", "POST"])
def add_question_ui(survey_id):
    if "token" not in session:
        return redirect("/login")

    headers = {"Authorization": f"Bearer {session['token']}"}

    if request.method == "POST":
        question_text = request.form["question_text"]
        data = {"question_text": question_text}

        try:
            res = requests.post(
                f"http://127.0.0.1:5000/api/surveys/{survey_id}/add-question",
                headers=headers,
                json=data
            )

            if res.status_code == 201:
                flash("✅ Question added successfully!")
                return redirect(f"/surveys/{survey_id}/questions")
            else:
                try:
                    error_msg = res.json().get("error", "Something went wrong.")
                except Exception as e:
                    print("⚠️ Failed to parse JSON response:", e)
                    error_msg = "Something went wrong. Server did not return a valid response."

                return render_template("questions.html", survey_id=survey_id, error=error_msg)

        except Exception as e:
            print("❌ Error in POST request:", e)
            return render_template("questions.html", survey_id=survey_id, error="Failed to add question.")

    # GET request to fetch questions
    try:
        res = requests.get(
            f"http://127.0.0.1:5000/api/surveys/{survey_id}/questions",
            headers=headers
        )
        print("Question fetch (GET) status:", res.status_code)
        print("Question fetch (GET) body:", res.text)
        res.raise_for_status()
        questions = res.json().get("questions", [])
    except Exception as e:
        print("❌ Error fetching questions:", e)
        return render_template("questions.html", survey_id=survey_id, error="Could not load questions")

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

        try:
            res = requests.post(
                f"http://127.0.0.1:5000/api/surveys/{survey_id}/answer",
                json={"question_id": question_id, "answer": answer},
                headers=headers
            )

            if res.status_code != 201:
                return render_template("answer.html", survey_id=survey_id, error=res.json().get("error"))

            # Save question as answered
            if "answered_questions" not in session:
                session["answered_questions"] = []
            session["answered_questions"].append(int(question_id))

        except Exception as e:
            print("POST failed:", e)
            return render_template("answer.html", survey_id=survey_id, error="Failed to submit answer")

    # 🐞 Check for questions
    try:
        res = requests.get(f"http://127.0.0.1:5000/api/surveys/{survey_id}/questions", headers=headers)
        print("Question fetch response:", res.status_code, res.text)
        questions = res.json().get("questions", [])
    except Exception as e:
        print("Error fetching questions:", e)
        return render_template("answer.html", survey_id=survey_id, error="Could not load questions")

    answered = session.get("answered_questions", [])
    next_question = next((q for q in questions if q["question_id"] not in answered), None)

    if not next_question:
        session.pop("answered_questions", None)
        return render_template("answer.html", survey_id=survey_id, done=True)

    return render_template("answer.html", survey_id=survey_id, question=next_question)

from collections import defaultdict

@app.route("/surveys/<int:survey_id>/responses")
def view_responses(survey_id):
    try:
        token = session.get("token")
        if not token:
            return redirect("/login")

        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(f"http://127.0.0.1:5000/api/surveys/{survey_id}/responses", headers=headers)
        res.raise_for_status()
        data = res.json()

        grouped = defaultdict(list)
        for response in data.get("responses", []):
            grouped[response["question_text"]].append(response)

        return render_template("view_responses.html", grouped_responses=grouped, survey_id=survey_id)

    except Exception as e:
        print("Error fetching grouped responses:", e)
        return render_template("view_responses.html", grouped_responses={}, survey_id=survey_id, error=str(e))
