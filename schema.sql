CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    username TEXT NOT NULL,
    pw TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS  quizzes (
    id INTEGER PRIMARY KEY,
    quiz_subject TEXT NOT NULL,
    question_count INTEGER NOT NULL,
    quiz_date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS student_quiz (
    student_id INTEGER NOT NULL REFERENCES students(id),
    quiz_id INTEGER NOT NULL REFERENCES quizzes(id),
    score INTEGER NOT NULL,
    PRIMARY KEY (student_id, quiz_id)
);