import os

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DATABASE = os.path.join(BASE_DIR, "survey.db")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret")

