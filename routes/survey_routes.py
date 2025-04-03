from flask import Blueprint, request, jsonify, current_app, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from MySQLdb.cursors import DictCursor
from flask import redirect
import requests
from flask import session

survey_bp = Blueprint("survey", __name__)

@survey_bp.route("", methods=["POST"])
@jwt_required()
def create_survey():
    data = request.get_json()
    title = data.get("title")
    description = data.get("description")
    user_id = get_jwt_identity()

    if not title:
        return jsonify({"error": "Survey title is required"}), 400

    mysql = current_app.mysql
    cursor = mysql.connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO surveys (title, description, created_by) VALUES (%s, %s, %s)",
            (title, description, user_id)
        )
        mysql.connection.commit()
        return jsonify({"message": "Survey created successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

@survey_bp.route("/my-surveys", methods=["GET"])
@jwt_required()
def get_user_surveys():
    user_id = get_jwt_identity()
    mysql = current_app.mysql
    cursor = mysql.connection.cursor(DictCursor)
    try:
        cursor.execute("SELECT * FROM surveys WHERE created_by = %s", (user_id,))
        surveys = cursor.fetchall()
        return jsonify({"surveys": surveys}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

@survey_bp.route("/<int:survey_id>/add-question", methods=["POST"])
@jwt_required()
def add_question(survey_id):
    mysql = current_app.mysql
    cursor = mysql.connection.cursor(DictCursor)

    try:
        # ✅ Get JSON from the POST request
        data = request.get_json()
        question_text = data.get("question_text")

        if not question_text:
            return jsonify({"error": "Question text is required"}), 400

        # ✅ Insert question
        cursor.execute(
            "INSERT INTO questions (survey_id, question_text) VALUES (%s, %s)",
            (survey_id, question_text)
        )
        mysql.connection.commit()

        return jsonify({"message": "Question added successfully"}), 201

    except Exception as e:
        print("Error adding question:", e)
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()


@survey_bp.route("/<int:survey_id>/questions", methods=["GET"])
@jwt_required()
def get_questions(survey_id):
    mysql = current_app.mysql
    cursor = mysql.connection.cursor(DictCursor)
    try:
        cursor.execute(
            "SELECT question_id, question_text FROM questions WHERE survey_id = %s",
            (survey_id,)
        )
        questions = cursor.fetchall()
        return jsonify({"questions": questions}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

@survey_bp.route("/<int:survey_id>/answer", methods=["POST"])
@jwt_required()
def submit_survey_answer(survey_id):
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        question_id = data.get("question_id")
        answer_text = data.get("answer")

        if not all([question_id, answer_text]):
            return jsonify({"error": "Missing question or answer"}), 400

        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO responses (survey_id, question_id, user_id, answer_text)
            VALUES (%s, %s, %s, %s)
        """, (survey_id, question_id, user_id, answer_text))
        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Answer submitted successfully"}), 201

    except Exception as e:
        print("Error submitting answer:", e)
        return jsonify({"error": str(e)}), 500

@survey_bp.route("/<int:survey_id>/responses", methods=["GET"])
@jwt_required()
def get_survey_responses(survey_id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)

        cursor.execute("""
            SELECT 
                a.answer_text, 
                q.question_text, 
                q.question_id
            FROM responses a
            JOIN questions q ON a.question_id = q.question_id
            WHERE a.survey_id = %s
        """, (survey_id,))

        responses = cursor.fetchall()
        cursor.close()

        return jsonify({"responses": responses})  # ✅ wrap in JSON!

    except Exception as e:
        print("Error fetching responses:", e)
        return jsonify({"error": str(e)}), 500
    
@survey_bp.route('/<int:survey_id>/delete', methods=['POST'])
@jwt_required()
def delete_survey(survey_id):
    try:
        cur = current_app.mysql.connection.cursor()

        # First delete responses linked to survey's questions
        cur.execute("""
            DELETE FROM responses 
            WHERE question_id IN (
                SELECT question_id FROM questions WHERE survey_id = %s
            )
        """, (survey_id,))

        # Then delete the questions
        cur.execute("DELETE FROM questions WHERE survey_id = %s", (survey_id,))

        # Finally delete the survey itself
        cur.execute("DELETE FROM surveys WHERE survey_id = %s", (survey_id,))

        current_app.mysql.connection.commit()
        cur.close()

        return jsonify({"message": f"✅ Survey {survey_id} deleted successfully"}), 200

    except Exception as e:
        current_app.mysql.connection.rollback()
        print("❌ Delete error:", e)
        return jsonify({"error": "Failed to delete survey", "details": str(e)}), 500
