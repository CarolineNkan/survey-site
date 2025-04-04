from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from db import get_db

survey_bp = Blueprint("survey", __name__)

# ✅ Create a new survey
@survey_bp.route("", methods=["POST"])
@jwt_required()
def create_survey():
    data = request.get_json()
    title = data.get("title")
    description = data.get("description")
    user_id = get_jwt_identity()

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
        return jsonify({"message": "✅ Survey created"}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

# ✅ Get surveys created by the user
@survey_bp.route("/my-surveys", methods=["GET"])
@jwt_required()
def get_my_surveys():
    user_id = get_jwt_identity()
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT * FROM surveys WHERE created_by = ?", (user_id,))
        surveys = [dict(row) for row in cursor.fetchall()]
        return jsonify({"surveys": surveys}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

# ✅ Add a question to a survey
@survey_bp.route("/<int:survey_id>/add-question", methods=["POST"])
@jwt_required()
def add_question(survey_id):
    data = request.get_json()
    question_text = data.get("question_text")

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
        return jsonify({"message": "✅ Question added"}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

# ✅ Get questions for a survey
@survey_bp.route("/<int:survey_id>/questions", methods=["GET"])
@jwt_required()
def get_questions(survey_id):
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            "SELECT question_id, question_text FROM questions WHERE survey_id = ?",
            (survey_id,)
        )
        questions = [dict(row) for row in cursor.fetchall()]
        return jsonify({"questions": questions}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

# ✅ Submit a survey answer
@survey_bp.route("/<int:survey_id>/answer", methods=["POST"])
@jwt_required()
def answer_survey(survey_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    question_id = data.get("question_id")
    answer_text = data.get("answer")

    if not all([question_id, answer_text]):
        return jsonify({"error": "Missing question or answer"}), 400

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            "INSERT INTO responses (survey_id, question_id, user_id, answer_text) VALUES (?, ?, ?, ?)",
            (survey_id, question_id, user_id, answer_text)
        )
        db.commit()
        return jsonify({"message": "✅ Answer submitted"}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

# ✅ View responses grouped by question
@survey_bp.route("/<int:survey_id>/responses", methods=["GET"])
@jwt_required()
def view_responses(survey_id):
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("""
            SELECT 
                r.answer_text, 
                q.question_text
            FROM responses r
            JOIN questions q ON r.question_id = q.question_id
            WHERE r.survey_id = ?
        """, (survey_id,))
        rows = cursor.fetchall()

        grouped = {}
        for answer_text, question_text in rows:
            grouped.setdefault(question_text, []).append(answer_text)

        return jsonify({"responses": grouped}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

# ✅ Delete survey + all related questions/responses
@survey_bp.route("/<int:survey_id>/delete", methods=["POST"])
@jwt_required()
def delete_survey(survey_id):
    db = get_db()
    cursor = db.cursor()
    try:
        # Delete responses linked to questions in the survey
        cursor.execute("""
            DELETE FROM responses 
            WHERE question_id IN (
                SELECT question_id FROM questions WHERE survey_id = ?
            )
        """, (survey_id,))

        cursor.execute("DELETE FROM questions WHERE survey_id = ?", (survey_id,))
        cursor.execute("DELETE FROM surveys WHERE survey_id = ?", (survey_id,))
        db.commit()
        return jsonify({"message": "🗑️ Survey deleted"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
