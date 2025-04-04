import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    DATABASE = os.path.join(basedir, "survey.db")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt_secret")
