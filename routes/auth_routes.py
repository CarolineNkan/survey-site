from flask import Blueprint, request, jsonify, render_template, redirect, session
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
from db import get_db

auth_bp = Blueprint("auth", __name__)

# ✅ Signup Route (API or Web)
@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.form if request.form else request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"error": "All fields are required."}), 400

    db = get_db()
    cursor = db.cursor()
    try:
        hashed_password = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, hashed_password)
        )
        db.commit()

        # Redirect if coming from a web form
        if request.form:
            return redirect("/login")

        return jsonify({"message": "✅ Signup successful"}), 201

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400

    finally:
        cursor.close()

# ✅ Login Route (API or Web)
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.form if request.form else request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

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
            return jsonify({"error": "Incorrect password"}), 401

        token = create_access_token(identity=str(user_id), expires_delta=timedelta(hours=1))

        if request.form:
            session["access_token"] = token
            return redirect("/dashboard")

        return jsonify({"token": token}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()


# ✅ Debug route (optional)
@auth_bp.route("/test", methods=["GET"])
def test_auth():
    return jsonify({"message": "✅ Auth route working!"})
