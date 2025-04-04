from flask import Blueprint, request, jsonify, current_app, render_template, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.form if request.form else request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"error": "Missing fields"}), 400

    hashed_password = generate_password_hash(password)
    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, hashed_password)
        )
        db.commit()

        if request.form:
            return redirect("/login")
        return jsonify({"message": "User registered successfully ✅"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.form if request.form else request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Missing credentials"}), 400

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            "SELECT user_id, password FROM users WHERE LOWER(username) = LOWER(?)",
            (username,)
        )
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "User not found"}), 404

        user_id, hashed_pw = user

        if not check_password_hash(hashed_pw, password):
            return jsonify({"error": "Invalid password"}), 401

        session["user_id"] = user_id

        if request.form:
            return redirect("/dashboard")

        return jsonify({"message": "Login successful"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
