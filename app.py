from flask import Flask, render_template, request, redirect, session, flash, g
from db import get_db, close_db         # MySQL connection functions
from config import Config               #  MySQL settings

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config["MYSQL_PASSWORD"]  
app.teardown_appcontext(close_db)


# -------------------- In-Memory Demo Storage -------------------- #
users = [{"user_id": 1, "username": "admin", "password": "password"}]
surveys = []
questions = []
responses = []

# -------------------- Routes -------------------- #

@app.route("/")
def home():
    return "🎉  Survey App is Live!"

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = next((u for u in users if u["username"] == username and u["password"] == password), None)
        if user:
            session["user_id"] = user["user_id"]
            flash("✅ Logged in successfully.")
            return redirect("/dashboard")
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

#-------------Signup Route----------------------#
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form.get("email", "")

        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (username, email, password)
                VALUES (%s, %s, %s)
            """, (username, email, password))
            db.commit()
            flash("🎉 Signup complete! Please login.")
            return redirect("/login")
        except Exception as e:
            return render_template("signup.html", error="Username or email may already exist.")
    return render_template("signup.html")



@app.route("/dashboard")
def dashboard():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")
    user_surveys = [s for s in surveys if s["created_by"] == user_id]
    return render_template("dashboard.html", surveys=user_surveys)


@app.route("/create-survey", methods=["GET", "POST"])
def create_survey():
    if "user_id" not in session:
        return redirect("/login")
    
    if request.method == "POST":
        survey_id = len(surveys) + 1
        surveys.append({
            "survey_id": survey_id,
            "title": request.form["title"],
            "description": request.form["description"],
            "created_by": session["user_id"]
        })
        flash("✅ Survey created!")
        return redirect("/dashboard")
    return render_template("create_survey.html")


@app.route("/surveys/<int:survey_id>/questions", methods=["GET", "POST"])
def add_questions(survey_id):
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        question_text = request.form["question_text"]
        questions.append({
            "question_id": len(questions) + 1,
            "survey_id": survey_id,
            "question_text": question_text
        })
        flash("➕ Question added.")

    survey_questions = [q for q in questions if q["survey_id"] == survey_id]
    return render_template("add_questions.html", questions=survey_questions, survey_id=survey_id)


@app.route("/surveys/<int:survey_id>/answer", methods=["GET", "POST"])
def answer_survey(survey_id):
    if "user_id" not in session:
        return redirect("/login")

    if "answered_questions" not in session:
        session["answered_questions"] = []

    if request.method == "POST":
        answer = request.form["answer"]
        question_id = int(request.form["question_id"])
        responses.append({
            "survey_id": survey_id,
            "question_id": question_id,
            "user_id": session["user_id"],
            "answer": answer
        })
        session["answered_questions"].append(question_id)

    unanswered = [
        q for q in questions
        if q["survey_id"] == survey_id and q["question_id"] not in session["answered_questions"]
    ]

    if not unanswered:
        return render_template("answer.html", done=True, survey_id=survey_id)

    return render_template("answer.html", question=unanswered[0], survey_id=survey_id)


@app.route("/surveys/<int:survey_id>/responses")
def view_responses(survey_id):
    if "user_id" not in session:
        return redirect("/login")

    grouped = {}
    for r in responses:
        if r["survey_id"] == survey_id:
            question_text = next((q["question_text"] for q in questions if q["question_id"] == r["question_id"]), "Unknown")
            grouped.setdefault(question_text, []).append(r["answer"])

    return render_template("view_responses.html", grouped_responses=grouped, survey_id=survey_id)

@app.route("/surveys/<int:survey_id>/delete", methods=["POST"])
def delete_survey(survey_id):
    if "user_id" not in session:
        return redirect("/login")

    global surveys, questions, responses
    surveys = [s for s in surveys if s["survey_id"] != survey_id]
    questions = [q for q in questions if q["survey_id"] != survey_id]
    responses = [r for r in responses if r["survey_id"] != survey_id]
    
    flash("🗑️ Survey deleted.")
    return redirect("/dashboard")



@app.route("/logout")
def logout():
    session.clear()
    flash("👋 Logged out.")
    return redirect("/login")

# -------------------- Main -------------------- #

if __name__ == "__main__":
    app.run(debug=True)
