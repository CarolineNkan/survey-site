from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/test", methods=["GET"])
def test_auth():
    return jsonify({"message": "Auth blueprint is working ✅"})


@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"error": "Missing fields"}), 400

    hashed_password = generate_password_hash(password)

    mysql = current_app.mysql
    cursor = mysql.connection.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
            (username, email, hashed_password)
        )
        mysql.connection.commit()
        return jsonify({"message": "User registered successfully ✅"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Missing credentials"}), 400

    mysql = current_app.mysql
    cursor = mysql.connection.cursor()

    try:
        # Case-insensitive username match
        cursor.execute("SELECT user_id, password FROM users WHERE LOWER(username) = LOWER(%s)", (username,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "User not found"}), 404

        user_id, hashed_pw = user

        if not check_password_hash(hashed_pw, password):
            return jsonify({"error": "Invalid password"}), 401

        # Generate JWT token
        access_token = create_access_token(
            identity=str(user_id),
            expires_delta=timedelta(hours=1)
        )

        return jsonify({"token": access_token}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
