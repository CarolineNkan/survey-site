from flask import Blueprint, request, jsonify, session
from db import get_db

survey_bp = Blueprint("survey", __name__)

# ✅ Create a new survey
@survey_bp.route("", methods=["POST"])
def create_survey():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    title = data.get("title")
    description = data.get("description")
    user_id = session["user_id"]

    if not title:
        return jsonify({"error": "Survey title is required"}), 400

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            "INSERT INTO surveys (title, description, created_by) VALUES (?, ?, ?)",
            (title, description, user_id)
        )
        db.commit()
        return jsonify({"message": "Survey created successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

# ✅ Get all surveys created by the current user
@survey_bp.route("/my-surveys", methods=["GET"])
def get_user_surveys():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT * FROM surveys WHERE created_by = ?", (user_id,))
        surveys = cursor.fetchall()
        return jsonify({"surveys": [dict(row) for row in surveys]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

@survey_bp.route("/<int:survey_id>/add-question", methods=["POST"])
def add_question(survey_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    # 🔁 Use form instead of JSON
    question_text = request.form.get("question_text")

    if not question_text:
        return jsonify({"error": "Question text is required"}), 400

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            "INSERT INTO questions (survey_id, question_text) VALUES (?, ?)",
            (survey_id, question_text)
        )
        db.commit()
        return jsonify({"message": "Question added successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

# ✅ Get all questions for a survey
@survey_bp.route("/<int:survey_id>/questions", methods=["GET"])
def get_questions(survey_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            "SELECT question_id, question_text FROM questions WHERE survey_id = ?",
            (survey_id,)
        )
        questions = cursor.fetchall()
        return jsonify({"questions": [dict(row) for row in questions]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

# ✅ Submit an answer
@survey_bp.route("/<int:survey_id>/answer", methods=["POST"])
def submit_survey_answer(survey_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    data = request.get_json()
    question_id = data.get("question_id")
    answer_text = data.get("answer")

    if not question_id or not answer_text:
        return jsonify({"error": "Missing question or answer"}), 400

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("""
            INSERT INTO responses (survey_id, question_id, user_id, answer_text)
            VALUES (?, ?, ?, ?)
        """, (survey_id, question_id, user_id, answer_text))
        db.commit()
        return jsonify({"message": "Answer submitted successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

# ✅ View responses for a survey
@survey_bp.route("/<int:survey_id>/responses", methods=["GET"])
def get_survey_responses(survey_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("""
            SELECT 
                a.answer_text, 
                q.question_text, 
                q.question_id
            FROM responses a
            JOIN questions q ON a.question_id = q.question_id
            WHERE a.survey_id = ?
        """, (survey_id,))
        responses = cursor.fetchall()
        return jsonify({"responses": [dict(row) for row in responses]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

# ✅ Delete a survey (and associated data)
@survey_bp.route("/<int:survey_id>/delete", methods=["POST"])
def delete_survey(survey_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db()
    cur = db.cursor()
    try:
        # Delete responses
        cur.execute("""
            DELETE FROM responses 
            WHERE question_id IN (
                SELECT question_id FROM questions WHERE survey_id = ?
            )
        """, (survey_id,))

        # Delete questions
        cur.execute("DELETE FROM questions WHERE survey_id = ?", (survey_id,))

        # Delete survey
        cur.execute("DELETE FROM surveys WHERE survey_id = ?", (survey_id,))

        db.commit()
        return jsonify({"message": f"✅ Survey {survey_id} deleted successfully"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": "Failed to delete survey", "details": str(e)}), 500
    finally:
        cur.close()
