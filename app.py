import os
from flask import Flask, render_template, request, redirect, session, flash
from flask_cors import CORS
from flask_jwt_extended import JWTManager, decode_token
from config import Config
from db import get_db, close_db
from routes.auth_routes import auth_bp
from routes.survey_routes import survey_bp
import requests
from collections import defaultdict

API_HOST = os.getenv("API_HOST", "https://survey-site-1.onrender.com")  # Use your deployed URL

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = "secret123"
app.config["JWT_SECRET_KEY"] = "your_jwt_key"

# Initialize extensions
CORS(app)
jwt = JWTManager(app)
app.teardown_appcontext(close_db)

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(survey_bp, url_prefix="/api/surveys")


@app.route("/")
def home():
    return "🎉 Survey API is working!"


# ---------------- Frontend Routes ---------------- #

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = {
            "username": request.form["username"],
            "password": request.form["password"]
        }
        try:
            res = requests.post(f"{API_HOST}/api/auth/login", json=data)
            if res.status_code == 200:
                token = res.json().get("token") or res.json().get("access_token")
                if not token:
                    return render_template("login.html", error="No token received")
                session["token"] = token
                decoded = decode_token(token)
                session["user_id"] = decoded["sub"]
                return redirect("/dashboard")
            else:
                try:
                    error = res.json().get("error", "Login failed")
                except ValueError:
                    error = res.text or "Login failed"
                return render_template("login.html", error=error)
        except Exception as e:
            return render_template("login.html", error=f"Server error: {str(e)}")

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        data = {
            "username": request.form["username"],
            "email": request.form["email"],
            "password": request.form["password"]
        }
        try:
            res = requests.post(f"{API_HOST}/api/auth/signup", json=data)
            if res.status_code == 201:
                return redirect("/login")
            else:
                try:
                    error = res.json().get("error", "Signup failed")
                except ValueError:
                    error = res.text or "Signup failed"
                return render_template("signup.html", error=error)
        except Exception as e:
            return render_template("signup.html", error=f"Server error: {str(e)}")
    return render_template("signup.html")


@app.route("/dashboard")
def dashboard():
    if "token" not in session:
        flash("⚠️ You need to login.")
        return redirect("/login")

    headers = {"Authorization": f"Bearer {session['token']}"}
    try:
        res = requests.get(f"{API_HOST}/api/surveys/my-surveys", headers=headers)
        if res.status_code == 200:
            surveys = res.json().get("surveys", [])
            return render_template("dashboard.html", surveys=surveys)
        else:
            return render_template("dashboard.html", error="Failed to load surveys.")
    except Exception as e:
        return render_template("dashboard.html", error="Error: " + str(e))


@app.route("/logout")
def logout():
    session.clear()
    flash("🚪 Logged out successfully.")
    return redirect("/login")
