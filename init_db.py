from db import get_db

schema = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT,
    password TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS surveys (
    survey_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    created_by INTEGER,
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS questions (
    question_id INTEGER PRIMARY KEY AUTOINCREMENT,
    survey_id INTEGER,
    question_text TEXT NOT NULL,
    FOREIGN KEY (survey_id) REFERENCES surveys(survey_id)
);

CREATE TABLE IF NOT EXISTS responses (
    response_id INTEGER PRIMARY KEY AUTOINCREMENT,
    survey_id INTEGER,
    question_id INTEGER,
    user_id INTEGER,
    answer_text TEXT,
    FOREIGN KEY (survey_id) REFERENCES surveys(survey_id),
    FOREIGN KEY (question_id) REFERENCES questions(question_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
"""

db = get_db()
db.executescript(schema)
db.commit()
print("✅ Database initialized.")
