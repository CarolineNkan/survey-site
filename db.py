import pymysql
from flask import g, current_app

def get_db():
    if "db" not in g:
        g.db = pymysql.connect(
            host=current_app.config["MYSQL_HOST"],
            user=current_app.config["MYSQL_USER"],
            password=current_app.config["MYSQL_PASSWORD"],
            database=current_app.config["MYSQL_DB"],
            port=current_app.config["MYSQL_PORT"],  # ← Only if you're using a port like 33060
            cursorclass=pymysql.cursors.DictCursor
        )
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
