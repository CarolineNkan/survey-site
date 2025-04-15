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

#-----------Login Route--------------#
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT user_id, password FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and user["password"] == password:
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


#-----------Dashboard Route--------#
@app.route("/dashboard")
def dashboard():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    # Fetch all surveys with their author's username
    cursor.execute("""
        SELECT s.survey_id, s.title, s.description, u.username AS author
        FROM surveys s
        JOIN users u ON s.created_by = u.user_id
    """)
    surveys = cursor.fetchall()

    #  Get the current logged-in user's username
    cursor.execute("SELECT username FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    username = user["username"] if user else "User"

    return render_template("dashboard.html", surveys=surveys, username=username)


#----------CreateSurvey Route----------#
@app.route("/create-survey", methods=["GET", "POST"])
def create_survey():
    if "user_id" not in session:
        return redirect("/login")
    
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        created_by = session["user_id"]

        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO surveys (title, description, created_by)
            VALUES (%s, %s, %s)
        """, (title, description, created_by))
        db.commit()
        flash("✅ Survey created!")
        return redirect("/dashboard")

    return render_template("create_survey.html")
#---------Addquestions Route----------#
@app.route("/surveys/<int:survey_id>/questions", methods=["GET", "POST"])
def add_questions(survey_id):
    if "user_id" not in session:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    if request.method == "POST":
        question_text = request.form["question_text"]
        try:
            cursor.execute(
                "INSERT INTO questions (survey_id, question_text) VALUES (%s, %s)",
                (survey_id, question_text)
            )
            db.commit()
            flash("➕ Question added.")
        except Exception as e:
            db.rollback()
            return render_template("add_questions.html", error=str(e), survey_id=survey_id)

    # Fetch all questions for the current survey
    cursor.execute(
        "SELECT question_id, question_text FROM questions WHERE survey_id = %s",
        (survey_id,)
    )
    survey_questions = cursor.fetchall()

    return render_template("add_questions.html", questions=survey_questions, survey_id=survey_id)


#------------Answerquestions Route--------#
@app.route("/surveys/<int:survey_id>/answer", methods=["GET", "POST"])
def answer_survey(survey_id):
    if "user_id" not in session:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    # Get or initialize answered questions in session
    if "answered_questions" not in session:
        session["answered_questions"] = []

    if request.method == "POST":
        answer = request.form["answer"]
        question_id = int(request.form["question_id"])

        try:
            cursor.execute("""
                INSERT INTO responses (survey_id, question_id, user_id, answer_text)
                VALUES (%s, %s, %s, %s)
            """, (survey_id, question_id, session["user_id"], answer))
            db.commit()
            session["answered_questions"].append(question_id)
        except Exception as e:
            db.rollback()
            return render_template("answer.html", error=str(e), survey_id=survey_id)

    # Fetch unanswered questions
    cursor.execute("""
        SELECT question_id, question_text FROM questions
        WHERE survey_id = %s
    """, (survey_id,))
    all_questions = cursor.fetchall()

    answered = session.get("answered_questions", [])
    next_question = next((q for q in all_questions if q["question_id"] not in answered), None)

    if not next_question:
        return render_template("answer.html", done=True, survey_id=survey_id)

    return render_template("answer.html", question=next_question, survey_id=survey_id)
#------------Viewresponses Route------#
@app.route("/surveys/<int:survey_id>/responses")
def view_responses(survey_id):
    if "user_id" not in session:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("""
            SELECT q.question_text, r.answer_text
            FROM responses r
            JOIN questions q ON r.question_id = q.question_id
            WHERE r.survey_id = %s
        """, (survey_id,))
        rows = cursor.fetchall()

        grouped = {}
        for row in rows:
            grouped.setdefault(row["question_text"], []).append(row["answer_text"])

        return render_template("view_responses.html", grouped_responses=grouped, survey_id=survey_id)

    except Exception as e:
        return render_template("view_responses.html", error=str(e), grouped_responses={}, survey_id=survey_id)

@app.route("/surveys/<int:survey_id>/delete", methods=["POST"])
def delete_survey(survey_id):
    if "user_id" not in session:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()
    try:
        # Delete responses tied to questions in this survey
        cursor.execute("""
            DELETE FROM responses 
            WHERE question_id IN (
                SELECT question_id FROM questions WHERE survey_id = %s
            )
        """, (survey_id,))

        # Delete questions for this survey
        cursor.execute("DELETE FROM questions WHERE survey_id = %s", (survey_id,))

        # Finally, delete the survey
        cursor.execute("DELETE FROM surveys WHERE survey_id = %s", (survey_id,))

        db.commit()
        flash("🗑️ Survey and related data deleted successfully.")
    except Exception as e:
        db.rollback()
        flash(f"⚠️ Failed to delete survey: {e}")
    finally:
        cursor.close()

    return redirect("/dashboard")



@app.route("/logout")
def logout():
    session.clear()
    flash("👋 Logged out.")
    return redirect("/login")

# -------------------- Main -------------------- #

if __name__ == "__main__":
    app.run(debug=True)
