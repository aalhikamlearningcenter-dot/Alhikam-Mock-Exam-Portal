import os
import sqlite3
from functools import wraps
from flask import (
    Flask,
    request,
    redirect,
    url_for,
    render_template_string,
    session,
    flash,
)
from werkzeug.security import generate_password_hash, check_password_hash


# ============================================================
# ALHIKAM MOCK EXAM PORTAL
# ============================================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    "alhikam-mock-change-this-secret-key",


DATABASE = os.getenv("DATABASE_PATH", "/app/mock_exam.db")

)


# ============================================================
# DATABASE
# ============================================================

def get_db():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def init_db():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            tutor_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            explanation TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (subject_id)
                REFERENCES subjects(id),

            FOREIGN KEY (tutor_id)
                REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            subject_id INTEGER NOT NULL,
            duration_minutes INTEGER NOT NULL DEFAULT 30,
            total_questions INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (subject_id)
                REFERENCES subjects(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS exam_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,

            FOREIGN KEY (exam_id)
                REFERENCES exams(id),

            FOREIGN KEY (question_id)
                REFERENCES questions(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            total_questions INTEGER NOT NULL DEFAULT 0,
            percentage REAL NOT NULL DEFAULT 0,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            submitted_at TIMESTAMP,

            FOREIGN KEY (exam_id)
                REFERENCES exams(id),

            FOREIGN KEY (student_id)
                REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            selected_answer TEXT,
            is_correct INTEGER NOT NULL DEFAULT 0,

            FOREIGN KEY (attempt_id)
                REFERENCES attempts(id),

            FOREIGN KEY (question_id)
                REFERENCES questions(id)
        )
    """)

    subjects = [
        "Biology",
        "Chemistry",
        "Physics",
        "Mathematics",
        "English",
        "Agricultural Science",
        "Geography",
        "Economics",
        "Government",
        "Literature",
        "History",
        "CRS",
        "IRS",
    ]

    for subject in subjects:

        conn.execute(
            """
            INSERT OR IGNORE INTO subjects (name)
            VALUES (?)
            """,
            (subject,),
        )

    conn.commit()

    conn.close()


# ============================================================
# CREATE ADMIN FROM ENVIRONMENT VARIABLES
# ============================================================

def create_admin_from_environment():

    admin_email = os.getenv(
        "ADMIN_EMAIL",
        "",
    ).strip().lower()

    admin_password = os.getenv(
        "ADMIN_PASSWORD",
        "",
    )

    admin_name = os.getenv(
        "ADMIN_NAME",
        "Alhikam Administrator",
    ).strip()

    if not admin_email or not admin_password:

        return

    conn = get_db()

    existing = conn.execute("""
        SELECT id
        FROM users
        WHERE email = ?
    """, (
        admin_email,
    )).fetchone()

    if not existing:

        conn.execute("""
            INSERT INTO users
            (
                full_name,
                email,
                password_hash,
                role
            )
            VALUES (?, ?, ?, 'admin')
        """, (
            admin_name,
            admin_email,
            generate_password_hash(
                admin_password
            ),
        ))

        conn.commit()

    conn.close()


# ============================================================
# LOGIN HELPERS
# ============================================================

def current_user():

    user_id = session.get("user_id")

    if not user_id:

        return None

    conn = get_db()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()

    conn.close()

    return user


def login_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if not current_user():

            return redirect(
                url_for("login")
            )

        return view(*args, **kwargs)

    return wrapped


def role_required(*roles):

    def decorator(view):

        @wraps(view)
        def wrapped(*args, **kwargs):

            user = current_user()

            if not user:

                return redirect(
                    url_for("login")
                )

            if user["role"] not in roles:

                return "Access denied", 403

            return view(*args, **kwargs)

        return wrapped

    return decorator


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():

    if current_user():

        return redirect(
            url_for("dashboard")
        )

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>

<title>Alhikam Mock Exam Portal</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<style>

body {
    font-family: Arial, sans-serif;
    background: #f4f7f6;
    margin: 0;
}

.container {
    max-width: 900px;
    margin: 80px auto;
    padding: 20px;
    text-align: center;
}

.card {
    background: white;
    padding: 40px;
    border-radius: 15px;
    box-shadow: 0 5px 20px rgba(0,0,0,.08);
}

h1 {
    color: #087f5b;
}

.btn {
    display: inline-block;
    padding: 13px 25px;
    margin: 8px;
    background: #087f5b;
    color: white;
    text-decoration: none;
    border-radius: 8px;
}

.btn.secondary {
    background: #333;
}

</style>

</head>

<body>

<div class="container">

<div class="card">

<h1>
Alhikam Learning Center
</h1>

<h2>
Mock Examination Portal
</h2>

<p>
Online CBT examination platform for
students and tutors.
</p>

<a class="btn"
   href="{{ url_for('login') }}">
Login
</a>

<a class="btn secondary"
   href="{{ url_for('register') }}">
Student Registration
</a>

</div>

</div>

</body>

</html>
""")


# ============================================================
# REGISTER STUDENT
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not full_name or not email or not password:

            flash(
                "Please fill all fields."
            )

            return redirect(
                url_for("register")
            )

        if len(password) < 6:

            flash(
                "Password must be at least 6 characters."
            )

            return redirect(
                url_for("register")
            )

        conn = get_db()

        try:

            conn.execute(
                """
                INSERT INTO users
                (
                    full_name,
                    email,
                    password_hash,
                    role
                )
                VALUES (?, ?, ?, 'student')
                """,
                (
                    full_name,
                    email,
                    generate_password_hash(password),
                ),
            )

            conn.commit()

            flash(
                "Registration successful. Please login."
            )

            return redirect(
                url_for("login")
            )

        except sqlite3.IntegrityError:

            flash(
                "Email already exists."
            )

        finally:

            conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>

<title>Student Registration</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<style>

body {
    font-family: Arial;
    background: #f4f7f6;
}

.box {
    max-width: 450px;
    margin: 50px auto;
    background: white;
    padding: 30px;
    border-radius: 15px;
}

input {
    width: 100%;
    padding: 12px;
    margin: 8px 0;
    box-sizing: border-box;
}

button {
    width: 100%;
    padding: 13px;
    background: #087f5b;
    color: white;
    border: 0;
    border-radius: 7px;
}

a {
    color: #087f5b;
}

.flash {
    background: #fff3cd;
    padding: 12px;
    border-radius: 7px;
    margin-bottom: 15px;
}

</style>

</head>

<body>

<div class="box">

<h2>
Student Registration
</h2>

{% with messages = get_flashed_messages() %}

{% for message in messages %}

<div class="flash">
{{ message }}
</div>

{% endfor %}

{% endwith %}

<form method="POST">

<input
    type="text"
    name="full_name"
    placeholder="Full Name"
    required
>

<input
    type="email"
    name="email"
    placeholder="Email"
    required
>

<input
    type="password"
    name="password"
    placeholder="Password"
    required
>

<button type="submit">
Create Account
</button>

</form>

<p>

Already have an account?

<a href="{{ url_for('login') }}">
Login
</a>

</p>

</div>

</body>

</html>
""")


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        conn = get_db()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password_hash"],
            password,
        ):

            session.clear()

            session["user_id"] = user["id"]

            session["role"] = user["role"]

            return redirect(
                url_for("dashboard")
            )

        flash(
            "Invalid email or password."
        )

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>

<title>Login</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<style>

body {
    font-family: Arial;
    background: #f4f7f6;
}

.box {
    max-width: 450px;
    margin: 60px auto;
    background: white;
    padding: 30px;
    border-radius: 15px;
}

input {
    width: 100%;
    padding: 12px;
    margin: 8px 0;
    box-sizing: border-box;
}

button {
    width: 100%;
    padding: 13px;
    background: #087f5b;
    color: white;
    border: 0;
    border-radius: 7px;
}

.flash {
    background: #fff3cd;
    padding: 12px;
    border-radius: 7px;
    margin-bottom: 15px;
}

</style>

</head>

<body>

<div class="box">

<h2>
Alhikam Mock Portal
</h2>

{% with messages = get_flashed_messages() %}

{% for message in messages %}

<div class="flash">
{{ message }}
</div>

{% endfor %}

{% endwith %}

<form method="POST">

<input
    type="email"
    name="email"
    placeholder="Email"
    required
>

<input
    type="password"
    name="password"
    placeholder="Password"
    required
>

<button>
Login
</button>

</form>

<p>

New student?

<a href="{{ url_for('register') }}">
Register
</a>

</p>

</div>

</body>

</html>
""")


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
@login_required
def dashboard():

    user = current_user()

    if user["role"] == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    if user["role"] == "tutor":

        return redirect(
            url_for("tutor_dashboard")
        )

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>

<title>Student Dashboard</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<style>

body {
    font-family: Arial;
    background: #f4f7f6;
    margin: 0;
}

.header {
    background: #087f5b;
    color: white;
    padding: 20px;
}

.container {
    max-width: 1000px;
    margin: auto;
    padding: 20px;
}

.card {
    background: white;
    padding: 25px;
    margin: 15px 0;
    border-radius: 12px;
}

.btn {
    display: inline-block;
    padding: 10px 18px;
    background: #087f5b;
    color: white;
    text-decoration: none;
    border-radius: 7px;
}

</style>

</head>

<body>

<div class="header">

<h2>
Welcome, {{ user["full_name"] }}
</h2>

</div>

<div class="container">

<div class="card">

<h3>
Student Dashboard
</h3>

<p>
Your Mock Exam Portal is ready.
</p>

<a class="btn"
   href="{{ url_for('available_exams') }}">
Available Mock Exams
</a>

</div>

<div class="card">

<h3>
My Results
</h3>

<a class="btn"
   href="{{ url_for('my_results') }}">
View Results
</a>

</div>

<div class="card">

<a href="{{ url_for('logout') }}">
Logout
</a>

</div>

</div>

</body>

</html>
""",
        user=user,
    )


# ============================================================
# AVAILABLE EXAMS
# ============================================================

@app.route("/exams")
@role_required("student")
def available_exams():

    conn = get_db()

    exams = conn.execute("""
        SELECT
            exams.*,
            subjects.name AS subject_name
        FROM exams
        JOIN subjects
            ON subjects.id = exams.subject_id
        WHERE exams.status = 'published'
        ORDER BY exams.id DESC
    """).fetchall()

    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>

<title>Available Exams</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<style>

body {
    font-family: Arial;
    background: #f4f7f6;
}

.container {
    max-width: 900px;
    margin: auto;
    padding: 20px;
}

.exam {
    background: white;
    padding: 20px;
    margin: 15px 0;
    border-radius: 12px;
}

.btn {
    background: #087f5b;
    color: white;
    padding: 10px 18px;
    text-decoration: none;
    border-radius: 7px;
    display: inline-block;
}

</style>

</head>

<body>

<div class="container">

<h2>
Available Mock Exams
</h2>

{% if exams %}

{% for exam in exams %}

<div class="exam">

<h3>
{{ exam["title"] }}
</h3>

<p>
Subject:
{{ exam["subject_name"] }}
</p>

<p>
Questions:
{{ exam["total_questions"] }}
</p>

<p>
Duration:
{{ exam["duration_minutes"] }} minutes
</p>

<a class="btn"
   href="{{ url_for(
       'start_exam',
       exam_id=exam['id']
   ) }}">
Start Exam
</a>

</div>

{% endfor %}

{% else %}

<div class="exam">

<p>
No published mock exams yet.
</p>

</div>

{% endif %}

<a href="{{ url_for('dashboard') }}">
← Dashboard
</a>

</div>

</body>

</html>
""",
        exams=exams,
    )


# ============================================================
# MY RESULTS
# ============================================================

@app.route("/results")
@role_required("student")
def my_results():

    user = current_user()

    conn = get_db()

    results = conn.execute("""
        SELECT
            attempts.*,
            exams.title,
            subjects.name AS subject_name
        FROM attempts
        JOIN exams
            ON exams.id = attempts.exam_id
        JOIN subjects
            ON subjects.id = exams.subject_id
        WHERE attempts.student_id = ?
        ORDER BY attempts.id DESC
    """, (
        user["id"],
    )).fetchall()

    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>

<title>My Results</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<style>

body {
    font-family: Arial;
    background: #f4f7f6;
    padding: 20px;
}

.result {
    background: white;
    padding: 20px;
    margin: 15px 0;
    border-radius: 12px;
}

</style>

</head>

<body>

<h2>
My Results
</h2>

{% if results %}

{% for result in results %}

<div class="result">

<h3>
{{ result["title"] }}
</h3>

<p>
Subject:
{{ result["subject_name"] }}
</p>

<p>
Score:
{{ result["score"] }}/{{ result["total_questions"] }}
</p>

<p>
Percentage:
{{ "%.2f"|format(result["percentage"]) }}%
</p>

</div>

{% endfor %}

{% else %}

<p>
You have not taken any mock exam yet.
</p>

{% endif %}

<a href="{{ url_for('dashboard') }}">
← Dashboard
</a>

</body>

</html>
""",
        results=results,
    )


# ============================================================
# TUTOR DASHBOARD
# ============================================================

@app.route("/tutor")
@role_required("tutor")
def tutor_dashboard():

    user = current_user()

    conn = get_db()

    questions = conn.execute("""
        SELECT
            questions.*,
            subjects.name AS subject_name
        FROM questions
        JOIN subjects
            ON subjects.id = questions.subject_id
        WHERE questions.tutor_id = ?
        ORDER BY questions.id DESC
    """, (
        user["id"],
    )).fetchall()

    approved_count = conn.execute("""
        SELECT COUNT(*)
        FROM questions
        WHERE tutor_id = ?
          AND status = 'approved'
    """, (
        user["id"],
    )).fetchone()[0]

    pending_count = conn.execute("""
        SELECT COUNT(*)
        FROM questions
        WHERE tutor_id = ?
          AND status = 'pending'
    """, (
        user["id"],
    )).fetchone()[0]

    rejected_count = conn.execute("""
        SELECT COUNT(*)
        FROM questions
        WHERE tutor_id = ?
          AND status = 'rejected'
    """, (
        user["id"],
    )).fetchone()[0]

    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>

<title>Tutor Dashboard</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<style>

body {
    font-family: Arial;
    background: #f4f7f6;
    padding: 20px;
    margin: 0;
}

.container {
    max-width: 1000px;
    margin: auto;
}

.card {
    background: white;
    padding: 20px;
    margin: 15px 0;
    border-radius: 12px;
}

.grid {
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(160px, 1fr));
    gap: 15px;
}

.stat {
    background: white;
    padding: 20px;
    border-radius: 12px;
}

.number {
    font-size: 30px;
    font-weight: bold;
    color: #087f5b;
}

.btn {
    display: inline-block;
    padding: 11px 18px;
    background: #087f5b;
    color: white;
    text-decoration: none;
    border-radius: 7px;
    margin: 5px;
}

.question {
    border-top: 1px solid #ddd;
    padding: 18px 0;
}

.pending {
    color: #d97706;
    font-weight: bold;
}

.approved {
    color: #087f5b;
    font-weight: bold;
}

.rejected {
    color: #c92a2a;
    font-weight: bold;
}

</style>

</head>

<body>

<div class="container">

<h2>
Tutor Dashboard
</h2>

<p>
Welcome,
<strong>{{ user["full_name"] }}</strong>
</p>


<div class="grid">

<div class="stat">

<p>
Approved
</p>

<div class="number">
{{ approved_count }}
</div>

</div>

<div class="stat">

<p>
Pending
</p>

<div class="number">
{{ pending_count }}
</div>

</div>

<div class="stat">

<p>
Rejected
</p>

<div class="number">
{{ rejected_count }}
</div>

</div>

</div>


<div class="card">

<h3>
Tutor Actions
</h3>

<a class="btn"
   href="{{ url_for('tutor_new_question') }}">
➕ Submit New Question
</a>

<a class="btn"
   href="{{ url_for('tutor_results') }}">
📊 Student Results
</a>

</div>


<div class="card">

<h3>
My Questions
</h3>

{% for question in questions %}

<div class="question">

<strong>
{{ question["question_text"] }}
</strong>

<p>
Subject:
{{ question["subject_name"] }}
</p>

<p>
Status:

{% if question["status"] == "approved" %}

<span class="approved">
Approved
</span>

{% elif question["status"] == "rejected" %}

<span class="rejected">
Rejected
</span>

{% else %}

<span class="pending">
Pending
</span>

{% endif %}

</p>

<p>
Correct Answer:
{{ question["correct_answer"] }}
</p>

</div>

{% else %}

<p>
You have not submitted any questions.
</p>

{% endfor %}

</div>


<a href="{{ url_for('logout') }}">
Logout
</a>

</div>

</body>

</html>
""",
        user=user,
        questions=questions,
        approved_count=approved_count,
        pending_count=pending_count,
        rejected_count=rejected_count,
    )


# ============================================================
# TUTOR - NEW QUESTION
# ============================================================

@app.route(
    "/tutor/questions/new",
    methods=["GET", "POST"]
)
@role_required("tutor")
def tutor_new_question():

    user = current_user()

    conn = get_db()

    subjects = conn.execute("""
        SELECT *
        FROM subjects
        ORDER BY name ASC
    """).fetchall()

    conn.close()

    if request.method == "POST":

        subject_id = request.form.get(
            "subject_id"
        )

        question_text = request.form.get(
            "question_text",
            ""
        ).strip()

        option_a = request.form.get(
            "option_a",
            ""
        ).strip()

        option_b = request.form.get(
            "option_b",
            ""
        ).strip()

        option_c = request.form.get(
            "option_c",
            ""
        ).strip()

        option_d = request.form.get(
            "option_d",
            ""
        ).strip()

        correct_answer = request.form.get(
            "correct_answer",
            ""
        ).strip().upper()

        explanation = request.form.get(
            "explanation",
            ""
        ).strip()

        if not all([
            subject_id,
            question_text,
            option_a,
            option_b,
            option_c,
            option_d,
            correct_answer,
        ]):

            flash(
                "Please complete all required fields."
            )

            return redirect(
                url_for("tutor_new_question")
            )

        if correct_answer not in {
            "A",
            "B",
            "C",
            "D",
        }:

            flash(
                "Correct answer must be A, B, C or D."
            )

            return redirect(
                url_for("tutor_new_question")
            )

        conn = get_db()

        subject = conn.execute("""
            SELECT id
            FROM subjects
            WHERE id = ?
        """, (
            subject_id,
        )).fetchone()

        if not subject:

            conn.close()

            flash(
                "Selected subject does not exist."
            )

            return redirect(
                url_for("tutor_new_question")
            )

        conn.execute("""
            INSERT INTO questions
            (
                subject_id,
                tutor_id,
                question_text,
                option_a,
                option_b,
                option_c,
                option_d,
                correct_answer,
                explanation,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (
            subject_id,
            user["id"],
            question_text,
            option_a,
            option_b,
            option_c,
            option_d,
            correct_answer,
            explanation,
        ))

        conn.commit()

        conn.close()

        flash(
            "Question submitted successfully and is now pending admin approval."
        )

        return redirect(
            url_for("tutor_dashboard")
        )

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>

<title>Submit Question</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<style>

body {
    font-family: Arial;
    background: #f4f7f6;
    margin: 0;
    padding: 20px;
}

.container {
    max-width: 800px;
    margin: auto;
}

.card {
    background: white;
    padding: 25px;
    border-radius: 12px;
}

input,
textarea,
select {
    width: 100%;
    box-sizing: border-box;
    padding: 12px;
    margin: 7px 0 15px;
}

textarea {
    min-height: 120px;
}

button {
    width: 100%;
    padding: 13px;
    background: #087f5b;
    color: white;
    border: 0;
    border-radius: 7px;
    cursor: pointer;
}

.flash {
    background: #fff3cd;
    padding: 12px;
    border-radius: 7px;
    margin-bottom: 15px;
}

</style>

</head>

<body>

<div class="container">

<h2>
Submit New Question
</h2>

<div class="card">

{% with messages = get_flashed_messages() %}

{% for message in messages %}

<div class="flash">
{{ message }}
</div>

{% endfor %}

{% endwith %}

<form method="POST">

<label>
Subject
</label>

<select
    name="subject_id"
    required
>

<option value="">
Select Subject
</option>

{% for subject in subjects %}

<option value="{{ subject['id'] }}">
{{ subject["name"] }}
</option>

{% endfor %}

</select>


<label>
Question
</label>

<textarea
    name="question_text"
    placeholder="Write the question..."
    required
></textarea>


<label>
Option A
</label>

<input
    type="text"
    name="option_a"
    required
>


<label>
Option B
</label>

<input
    type="text"
    name="option_b"
    required
>


<label>
Option C
</label>

<input
    type="text"
    name="option_c"
    required
>


<label>
Option D
</label>

<input
    type="text"
    name="option_d"
    required
>


<label>
Correct Answer
</label>

<select
    name="correct_answer"
    required
>

<option value="">
Select Correct Answer
</option>

<option value="A">
A
</option>

<option value="B">
B
</option>

<option value="C">
C
</option>

<option value="D">
D
</option>

</select>


<label>
Explanation
</label>

<textarea
    name="explanation"
    placeholder="Optional explanation for students..."
></textarea>


<button type="submit">
Submit Question
</button>

</form>

</div>

<p>

<a href="{{ url_for('tutor_dashboard') }}">
← Back to Tutor Dashboard
</a>

</p>

</div>

</body>

</html>
""",
        subjects=subjects,
    )


# ============================================================
# TUTOR - STUDENT RESULTS
# ============================================================

@app.route("/tutor/results")
@role_required("tutor")
def tutor_results():

    user = current_user()

    conn = get_db()

    results = conn.execute("""
        SELECT DISTINCT
            attempts.id,
            users.full_name AS student_name,
            users.email AS student_email,
            exams.title AS exam_title,
            subjects.name AS subject_name,
            attempts.score,
            attempts.total_questions,
            attempts.percentage,
            attempts.started_at,
            attempts.submitted_at

        FROM attempts

        JOIN users
            ON users.id = attempts.student_id

        JOIN exams
            ON exams.id = attempts.exam_id

        JOIN subjects
            ON subjects.id = exams.subject_id

        JOIN exam_questions
            ON exam_questions.exam_id = exams.id

        JOIN questions
            ON questions.id = exam_questions.question_id

        WHERE questions.tutor_id = ?
          AND attempts.submitted_at IS NOT NULL

        ORDER BY attempts.submitted_at DESC
    """, (
        user["id"],
    )).fetchall()

    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>

<title>Tutor Student Results</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<style>

body {
    font-family: Arial;
    background: #f4f7f6;
    margin: 0;
    padding: 20px;
}

.container {
    max-width: 1100px;
    margin: auto;
}

.card {
    background: white;
    padding: 20px;
    margin: 15px 0;
    border-radius: 12px;
    overflow-x: auto;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th,
td {
    padding: 12px;
    border-bottom: 1px solid #ddd;
    text-align: left;
}

th {
    background: #087f5b;
    color: white;
}

.score {
    font-weight: bold;
    color: #087f5b;
}

</style>

</head>

<body>

<div class="container">

<h2>
Student Results
</h2>

<div class="card">

{% if results %}

<table>

<thead>

<tr>

<th>
Student
</th>

<th>
Email
</th>

<th>
Exam
</th>

<th>
Subject
</th>

<th>
Score
</th>

<th>
Percentage
</th>

<th>
Submitted
</th>

</tr>

</thead>

<tbody>

{% for result in results %}

<tr>

<td>
{{ result["student_name"] }}
</td>

<td>
{{ result["student_email"] }}
</td>

<td>
{{ result["exam_title"] }}
</td>

<td>
{{ result["subject_name"] }}
</td>

<td class="score">

{{ result["score"] }}
/
{{ result["total_questions"] }}

</td>

<td>

{{ "%.2f"|format(result["percentage"]) }}%

</td>

<td>

{{ result["submitted_at"] }}

</td>

</tr>

{% endfor %}

</tbody>

</table>

{% else %}

<p>
No student results are available yet.
</p>

{% endif %}

</div>

<a href="{{ url_for('tutor_dashboard') }}">
← Tutor Dashboard
</a>

</div>

</body>

</html>
""",
        results=results,
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin")
@role_required("admin")
def admin_dashboard():

    conn = get_db()

    students = conn.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE role = 'student'
    """).fetchone()[0]

    tutors = conn.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE role = 'tutor'
    """).fetchone()[0]

    questions = conn.execute("""
        SELECT COUNT(*)
        FROM questions
    """).fetchone()[0]

    exams = conn.execute("""
        SELECT COUNT(*)
        FROM exams
    """).fetchone()[0]

    pending_questions = conn.execute("""
        SELECT COUNT(*)
        FROM questions
        WHERE status = 'pending'
    """).fetchone()[0]

    published_exams = conn.execute("""
        SELECT COUNT(*)
        FROM exams
        WHERE status = 'published'
    """).fetchone()[0]

    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>

<title>Admin Dashboard</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<style>

body {
    font-family: Arial;
    background: #f4f7f6;
    margin: 0;
}

.container {
    max-width: 1000px;
    margin: auto;
    padding: 20px;
}

.header {
    background: #087f5b;
    color: white;
    padding: 20px;
}

.grid {
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(180px, 1fr));
    gap: 15px;
}

.card {
    background: white;
    padding: 20px;
    border-radius: 12px;
    margin-top: 20px;
}

.stat {
    font-size: 30px;
    font-weight: bold;
    color: #087f5b;
}

.btn {
    display: block;
    background: #087f5b;
    color: white;
    text-decoration: none;
    padding: 13px;
    border-radius: 8px;
    margin: 10px 0;
}

</style>

</head>

<body>

<div class="header">

<h2>
Alhikam Mock Admin
</h2>

</div>

<div class="container">

<div class="grid">

<div class="card">
<p>Students</p>
<div class="stat">
{{ students }}
</div>
</div>

<div class="card">
<p>Tutors</p>
<div class="stat">
{{ tutors }}
</div>
</div>

<div class="card">
<p>Questions</p>
<div class="stat">
{{ questions }}
</div>
</div>

<div class="card">
<p>Mock Exams</p>
<div class="stat">
{{ exams }}
</div>
</div>

<div class="card">
<p>Pending Questions</p>
<div class="stat">
{{ pending_questions }}
</div>
</div>

<div class="card">
<p>Published Exams</p>
<div class="stat">
{{ published_exams }}
</div>
</div>

</div>


<div class="card">

<h3>
Management
</h3>

<a class="btn"
   href="{{ url_for('admin_questions') }}">
📝 Manage Questions
</a>

<a class="btn"
   href="{{ url_for('admin_exams') }}">
📚 Manage Mock Exams
</a>

<a class="btn"
   href="{{ url_for('admin_tutors') }}">
👨‍🏫 Manage Tutors
</a>

<a class="btn"
   href="{{ url_for('admin_results') }}">
📊 Student Results
</a>

</div>


<div class="card">

<a href="{{ url_for('logout') }}">
Logout
</a>

</div>

</div>

</body>

</html>
""",
        students=students,
        tutors=tutors,
        questions=questions,
        exams=exams,
        pending_questions=pending_questions,
        published_exams=published_exams,
    )


# ============================================================
# ADMIN - QUESTION MANAGEMENT
# ============================================================

@app.route("/admin/questions")
@role_required("admin")
def admin_questions():

    conn = get_db()

    questions = conn.execute("""
        SELECT
            questions.*,
            subjects.name AS subject_name,
            users.full_name AS tutor_name
        FROM questions
        JOIN subjects
            ON subjects.id = questions.subject_id
        JOIN users
            ON users.id = questions.tutor_id
        ORDER BY questions.id DESC
    """).fetchall()

    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>

<title>Question Management</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<style>

body {
    font-family: Arial;
    background: #f4f7f6;
    margin: 0;
}

.container {
    max-width: 1000px;
    margin: auto;
    padding: 20px;
}

.card {
    background: white;
    padding: 20px;
    margin: 15px 0;
    border-radius: 12px;
}

.question {
    border-top: 1px solid #ddd;
    padding-top: 20px;
    margin-top: 20px;
}

button {
    padding: 11px 18px;
    border: 0;
    border-radius: 7px;
    color: white;
    cursor: pointer;
}

.approve {
    background: #087f5b;
}

.reject {
    background: #c92a2a;
}

.pending {
    color: #d97706;
    font-weight: bold;
}

.approved {
    color: #087f5b;
    font-weight: bold;
}

.rejected {
    color: #c92a2a;
    font-weight: bold;
}

.flash {
    background: #fff3cd;
    padding: 12px;
    border-radius: 7px;
}

</style>

</head>

<body>

<div class="container">

<h2>
Question Management
</h2>

{% with messages = get_flashed_messages() %}

{% for message in messages %}

<div class="flash">
{{ message }}
</div>

{% endfor %}

{% endwith %}


<div class="card">

<h3>
All Questions
</h3>

{% for question in questions %}

<div class="question">

<p>
<strong>
{{ question["question_text"] }}
</strong>
</p>

<p>
Subject:
{{ question["subject_name"] }}
</p>

<p>
Tutor:
{{ question["tutor_name"] }}
</p>

<p>
Correct Answer:
{{ question["correct_answer"] }}
</p>

<p>
Status:

{% if question["status"] == "approved" %}

<span class="approved">
Approved
</span>

{% elif question["status"] == "rejected" %}

<span class="rejected">
Rejected
</span>

{% else %}

<span class="pending">
Pending
</span>

{% endif %}

</p>


{% if question["status"] != "approved" %}

<form
    method="POST"
    action="{{ url_for(
        'question_status',
        question_id=question['id'],
        status='approved'
    ) }}"
    style="display:inline;"
>

<button
    class="approve"
    type="submit"
>

Approve

</button>

</form>

{% endif %}


{% if question["status"] != "rejected" %}

<form
    method="POST"
    action="{{ url_for(
        'question_status',
        question_id=question['id'],
        status='rejected'
    ) }}"
    style="display:inline;"
>

<button
    class="reject"
    type="submit"
>

Reject

</button>

</form>

{% endif %}

</div>

{% else %}

<p>
No questions available.
</p>

{% endfor %}

</div>


<a href="{{ url_for('admin_dashboard') }}">
← Admin Dashboard
</a>

</div>

</body>

</html>
""")


# ============================================================
# ADMIN - QUESTION STATUS
# ============================================================

@app.route(
    "/admin/questions/<int:question_id>/status/<status>",
    methods=["POST"]
)
@role_required("admin")
def question_status(
    question_id,
    status
):

    if status not in {
        "approved",
        "rejected",
        "pending",
    }:

        return "Invalid status.", 400

    conn = get_db()

    question = conn.execute("""
        SELECT id
        FROM questions
        WHERE id = ?
    """, (
        question_id,
    )).fetchone()

    if not question:

        conn.close()

        return "Question not found.", 404

    conn.execute("""
        UPDATE questions
        SET status = ?
        WHERE id = ?
    """, (
        status,
        question_id,
    ))

    conn.commit()

    conn.close()

    flash(
        f"Question status changed to {status}."
    )

    return redirect(
        url_for("admin_questions")
    )


# ============================================================
# ADMIN - CREATE QUESTION
# ============================================================

@app.route(
    "/admin/questions/create",
    methods=["POST"]
)
@role_required("admin")
def admin_create_question():

    subject_id = request.form.get(
        "subject_id"
    )

    question_text = request.form.get(
        "question_text",
        ""
    ).strip()

    option_a = request.form.get(
        "option_a",
        ""
    ).strip()

    option_b = request.form.get(
        "option_b",
        ""
    ).strip()

    option_c = request.form.get(
        "option_c",
        ""
    ).strip()

    option_d = request.form.get(
        "option_d",
        ""
    ).strip()

    correct_answer = request.form.get(
        "correct_answer",
        ""
    ).strip().upper()

    explanation = request.form.get(
        "explanation",
        ""
    ).strip()

    if not all([
        subject_id,
        question_text,
        option_a,
        option_b,
        option_c,
        option_d,
        correct_answer,
    ]):

        flash(
            "Please complete all required fields."
        )

        return redirect(
            url_for("admin_questions")
        )

    if correct_answer not in {
        "A",
        "B",
        "C",
        "D",
    }:

        flash(
            "Invalid correct answer."
        )

        return redirect(
            url_for("admin_questions")
        )

    admin = current_user()

    conn = get_db()

    conn.execute("""
        INSERT INTO questions
        (
            subject_id,
            tutor_id,
            question_text,
            option_a,
            option_b,
            option_c,
            option_d,
            correct_answer,
            explanation,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'approved')
    """, (
        subject_id,
        admin["id"],
        question_text,
        option_a,
        option_b,
        option_c,
        option_d,
        correct_answer,
        explanation,
    ))

    conn.commit()

    conn.close()

    flash(
        "Question created successfully."
    )

    return redirect(
        url_for("admin_questions")
    )


# ============================================================
# ADMIN - TUTOR MANAGEMENT
# ============================================================

@app.route("/admin/tutors")
@role_required("admin")
def admin_tutors():

    conn = get_db()

    tutors = conn.execute("""
        SELECT
            id,
            full_name,
            email,
            created_at
        FROM users
        WHERE role = 'tutor'
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>

<title>Tutor Management</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<style>

body {
    font-family: Arial;
    background: #f4f7f6;
    padding: 20px;
}

.container {
    max-width: 900px;
    margin: auto;
}

.card {
    background: white;
    padding: 20px;
    margin: 15px 0;
    border-radius: 12px;
}

input {
    width: 100%;
    box-sizing: border-box;
    padding: 12px;
    margin: 7px 0 12px;
}

button {
    padding: 12px 20px;
    background: #087f5b;
    color: white;
    border: 0;
    border-radius: 7px;
}

.tutor {
    border-top: 1px solid #ddd;
    padding: 15px 0;
}

.flash {
    background: #fff3cd;
    padding: 12px;
    border-radius: 7px;
}

</style>

</head>

<body>

<div class="container">

<h2>
Tutor Management
</h2>


{% with messages = get_flashed_messages() %}

{% for message in messages %}

<div class="flash">
{{ message }}
</div>

{% endfor %}

{% endwith %}


<div class="card">

<h3>
Create Tutor Account
</h3>

<form method="POST"
      action="{{ url_for('admin_create_tutor') }}">

<input
    name="full_name"
    placeholder="Tutor Full Name"
    required
>

<input
    type="email"
    name="email"
    placeholder="Tutor Email"
    required
>

<input
    type="password"
    name="password"
    placeholder="Temporary Password"
    minlength="6"
    required
>

<button type="submit">
Create Tutor
</button>

</form>

</div>


<div class="card">

<h3>
Registered Tutors
</h3>

{% for tutor in tutors %}

<div class="tutor">

<strong>
{{ tutor["full_name"] }}
</strong>

<p>
Email:
{{ tutor["email"] }}
</p>

<p>
Created:
{{ tutor["created_at"] }}
</p>

</div>

{% else %}

<p>
No tutors registered yet.
</p>

{% endfor %}

</div>


<a href="{{ url_for('admin_dashboard') }}">
← Admin Dashboard
</a>

</div>

</body>

</html>
""",
        tutors=tutors,
    )


# ============================================================
# ADMIN - CREATE TUTOR
# ============================================================

@app.route(
    "/admin/tutors/create",
    methods=["POST"]
)
@role_required("admin")
def admin_create_tutor():

    full_name = request.form.get(
        "full_name",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip().lower()

    password = request.form.get(
        "password",
        ""
    )

    if not full_name or not email or not password:

        flash(
            "Please complete all tutor fields."
        )

        return redirect(
            url_for("admin_tutors")
        )

    if len(password) < 6:

        flash(
            "Tutor password must be at least 6 characters."
        )

        return redirect(
            url_for("admin_tutors")
        )

    conn = get_db()

    try:

        conn.execute("""
            INSERT INTO users
            (
                full_name,
                email,
                password_hash,
                role
            )
            VALUES (?, ?, ?, 'tutor')
        """, (
            full_name,
            email,
            generate_password_hash(password),
        ))

        conn.commit()

        flash(
            "Tutor account created successfully."
        )

    except sqlite3.IntegrityError:

        flash(
            "That email already exists."
        )

    finally:

        conn.close()

    return redirect(
        url_for("admin_tutors")
    )


# ============================================================
# ADMIN - CREATE MOCK EXAM
# ============================================================

@app.route("/admin/exams")
@role_required("admin")
def admin_exams():

    conn = get_db()

    exams = conn.execute("""
        SELECT
            exams.*,
            subjects.name AS subject_name
        FROM exams
        JOIN subjects
            ON subjects.id = exams.subject_id
        ORDER BY exams.id DESC
    """).fetchall()

    subjects = conn.execute("""
        SELECT *
        FROM subjects
        ORDER BY name ASC
    """).fetchall()

    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>

<title>Mock Exams</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<style>

body {
    font-family: Arial;
    background: #f4f7f6;
}

.container {
    max-width: 1000px;
    margin: auto;
    padding: 20px;
}

.card {
    background: white;
    padding: 20px;
    margin: 15px 0;
    border-radius: 12px;
}

input,
select {
    width: 100%;
    box-sizing: border-box;
    padding: 11px;
    margin: 7px 0 12px;
}

button {
    padding: 11px 18px;
    border: 0;
    border-radius: 7px;
    background: #087f5b;
    color: white;
}

.exam {
    border-top: 1px solid #ddd;
    padding: 18px 0;
}

.flash {
    background: #fff3cd;
    padding: 12px;
    border-radius: 7px;
}

</style>

</head>

<body>

<div class="container">

<h2>
Mock Exam Management
</h2>


{% with messages = get_flashed_messages() %}

{% for message in messages %}

<div class="flash">
{{ message }}
</div>

{% endfor %}

{% endwith %}


<div class="card">

<h3>
Create Mock Exam
</h3>

<form
    method="POST"
    action="{{ url_for('admin_create_exam') }}"
>

<label>
Exam Title
</label>

<input
    name="title"
    placeholder="Example: JAMB Biology Mock 01"
    required
>


<label>
Subject
</label>

<select name="subject_id" required>

<option value="">
Select Subject
</option>

{% for subject in subjects %}

<option value="{{ subject['id'] }}">
{{ subject['name'] }}
</option>

{% endfor %}

</select>


<label>
Duration in Minutes
</label>

<input
    type="number"
    name="duration_minutes"
    value="30"
    min="1"
    max="300"
    required
>


<button type="submit">
Create Mock
</button>

</form>

</div>


<div class="card">

<h3>
Existing Mock Exams
</h3>

{% for exam in exams %}

<div class="exam">

<h3>
{{ exam["title"] }}
</h3>

<p>
Subject:
{{ exam["subject_name"] }}
</p>

<p>
Duration:
{{ exam["duration_minutes"] }}
minutes
</p>

<p>
Questions:
{{ exam["total_questions"] }}
</p>

<p>
Status:
<strong>
{{ exam["status"] }}
</strong>
</p>

<a href="{{ url_for(
    'manage_exam_questions',
    exam_id=exam['id']
) }}">
Manage Questions
</a>

</div>

{% else %}

<p>
No mock exams created yet.
</p>

{% endfor %}

</div>


<a href="{{ url_for('admin_dashboard') }}">
← Admin Dashboard
</a>

</div>

</body>

</html>
""",
        exams=exams,
        subjects=subjects,
    )


# ============================================================
# ADMIN - CREATE EXAM
# ============================================================

@app.route(
    "/admin/exams/create",
    methods=["POST"]
)
@role_required("admin")
def admin_create_exam():

    title = request.form.get(
        "title",
        ""
    ).strip()

    subject_id = request.form.get(
        "subject_id"
    )

    duration = request.form.get(
        "duration_minutes",
        "30"
    )

    if not title or not subject_id:

        flash(
            "Please complete all fields."
        )

        return redirect(
            url_for("admin_exams")
        )

    try:

        duration = int(duration)

    except ValueError:

        flash(
            "Invalid duration."
        )

        return redirect(
            url_for("admin_exams")
        )

    if duration < 1 or duration > 300:

        flash(
            "Duration must be between 1 and 300 minutes."
        )

        return redirect(
            url_for("admin_exams")
        )

    conn = get_db()

    subject = conn.execute("""
        SELECT id
        FROM subjects
        WHERE id = ?
    """, (
        subject_id,
    )).fetchone()

    if not subject:

        conn.close()

        flash(
            "Subject not found."
        )

        return redirect(
            url_for("admin_exams")
        )

    conn.execute("""
        INSERT INTO exams
        (
            title,
            subject_id,
            duration_minutes,
            total_questions,
            status
        )
        VALUES (?, ?, ?, 0, 'draft')
    """, (
        title,
        subject_id,
        duration,
    ))

    conn.commit()

    conn.close()

    flash(
        "Mock exam created successfully."
    )

    return redirect(
        url_for("admin_exams")
    )


# ============================================================
# ADMIN - MANAGE EXAM QUESTIONS
# ============================================================

@app.route(
    "/admin/exams/<int:exam_id>/questions"
)
@role_required("admin")
def manage_exam_questions(exam_id):

    conn = get_db()

    exam = conn.execute("""
        SELECT
            exams.*,
            subjects.name AS subject_name
        FROM exams
        JOIN subjects
            ON subjects.id = exams.subject_id
        WHERE exams.id = ?
    """, (
        exam_id,
    )).fetchone()

    if not exam:

        conn.close()

        return "Exam not found.", 404

    questions = conn.execute("""
        SELECT
            questions.*
        FROM questions
        WHERE questions.subject_id = ?
          AND questions.status = 'approved'
          AND questions.id NOT IN (
              SELECT question_id
              FROM exam_questions
              WHERE exam_id = ?
          )
        ORDER BY questions.id DESC
    """, (
        exam["subject_id"],
        exam_id,
    )).fetchall()

    selected_questions = conn.execute("""
        SELECT
            questions.*
        FROM exam_questions
        JOIN questions
            ON questions.id = exam_questions.question_id
        WHERE exam_questions.exam_id = ?
        ORDER BY exam_questions.id ASC
    """, (
        exam_id,
    )).fetchall()

    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>

<title>Manage Exam</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<style>

body {
    font-family: Arial;
    background: #f4f7f6;
}

.container {
    max-width: 1000px;
    margin: auto;
    padding: 20px;
}

.card {
    background: white;
    padding: 20px;
    margin: 15px 0;
    border-radius: 12px;
}

.question {
    padding: 15px;
    border-top: 1px solid #ddd;
}

button {
    padding: 10px 16px;
    border: 0;
    border-radius: 7px;
    background: #087f5b;
    color: white;
}

.publish {
    background: #c92a2a;
}

</style>

</head>

<body>

<div class="container">

<h2>
{{ exam["title"] }}
</h2>

<p>
Subject:
{{ exam["subject_name"] }}
</p>

<p>
Duration:
{{ exam["duration_minutes"] }}
minutes
</p>


<div class="card">

<h3>
Questions in this Mock
</h3>

{% for question in selected_questions %}

<div class="question">

<strong>
{{ loop.index }}.
{{ question["question_text"] }}
</strong>

<p>
Correct answer:
{{ question["correct_answer"] }}
</p>

</div>

{% else %}

<p>
No questions added yet.
</p>

{% endfor %}

</div>


<div class="card">

<h3>
Add Approved Questions
</h3>

{% for question in questions %}

<div class="question">

<p>
{{ question["question_text"] }}
</p>

<form
    method="POST"
    action="{{ url_for(
        'add_question_to_exam',
        exam_id=exam['id'],
        question_id=question['id']
    ) }}"
>

<button type="submit">
+ Add Question
</button>

</form>

</div>

{% else %}

<p>
No additional approved questions available
for this subject.
</p>

{% endfor %}

</div>


<div class="card">

<h3>
Publish Exam
</h3>

<p>
Current questions:

<strong>
{{ selected_questions|length }}
</strong>

</p>

{% if selected_questions|length > 0 %}

<form
    method="POST"
    action="{{ url_for(
        'publish_exam',
        exam_id=exam['id']
    ) }}"
>

<button
    class="publish"
    type="submit"
>

Publish Mock Exam

</button>

</form>

{% else %}

<p>
Add questions before publishing.
</p>

{% endif %}

</div>


<a href="{{ url_for('admin_exams') }}">
← Back to Mock Exams
</a>

</div>

</body>

</html>
""",
        exam=exam,
        questions=questions,
        selected_questions=selected_questions,
    )


# ============================================================
# ADD QUESTION TO EXAM
# ============================================================

@app.route(
    "/admin/exams/<int:exam_id>/questions/<int:question_id>/add",
    methods=["POST"]
)
@role_required("admin")
def add_question_to_exam(
    exam_id,
    question_id
):

    conn = get_db()

    exam = conn.execute("""
        SELECT *
        FROM exams
        WHERE id = ?
    """, (
        exam_id,
    )).fetchone()

    question = conn.execute("""
        SELECT *
        FROM questions
        WHERE id = ?
          AND status = 'approved'
    """, (
        question_id,
    )).fetchone()

    if not exam or not question:

        conn.close()

        return "Exam or question not found.", 404

    if question["subject_id"] != exam["subject_id"]:

        conn.close()

        return (
            "Question subject does not match exam subject.",
            400,
        )

    existing = conn.execute("""
        SELECT id
        FROM exam_questions
        WHERE exam_id = ?
          AND question_id = ?
    """, (
        exam_id,
        question_id,
    )).fetchone()

    if not existing:

        conn.execute("""
            INSERT INTO exam_questions
            (
                exam_id,
                question_id
            )
            VALUES (?, ?)
        """, (
            exam_id,
            question_id,
        ))

        total = conn.execute("""
            SELECT COUNT(*)
            FROM exam_questions
            WHERE exam_id = ?
        """, (
            exam_id,
        )).fetchone()[0]

        conn.execute("""
            UPDATE exams
            SET total_questions = ?
            WHERE id = ?
        """, (
            total,
            exam_id,
        ))

        conn.commit()

    conn.close()

    return redirect(
        url_for(
            "manage_exam_questions",
            exam_id=exam_id,
        )
    )


# ============================================================
# PUBLISH EXAM
# ============================================================

@app.route(
    "/admin/exams/<int:exam_id>/publish",
    methods=["POST"]
)
@role_required("admin")
def publish_exam(exam_id):

    conn = get_db()

    total = conn.execute("""
        SELECT COUNT(*)
        FROM exam_questions
        WHERE exam_id = ?
    """, (
        exam_id,
    )).fetchone()[0]

    if total < 1:

        conn.close()

        flash(
            "You must add at least one question before publishing."
        )

        return redirect(
            url_for(
                "manage_exam_questions",
                exam_id=exam_id,
            )
        )

    conn.execute("""
        UPDATE exams
        SET
            status = 'published',
            total_questions = ?
        WHERE id = ?
    """, (
        total,
        exam_id,
    ))

    conn.commit()

    conn.close()

    flash(
        "Mock exam published successfully."
    )

    return redirect(
        url_for("admin_exams")
    )


# ============================================================
# ADMIN - STUDENT RESULTS
# ============================================================

@app.route("/admin/results")
@role_required("admin")
def admin_results():

    conn = get_db()

    results = conn.execute("""
        SELECT
            attempts.id,
            users.full_name AS student_name,
            users.email AS student_email,
            exams.title AS exam_title,
            subjects.name AS subject_name,
            attempts.score,
            attempts.total_questions,
            attempts.percentage,
            attempts.started_at,
            attempts.submitted_at
        FROM attempts
        JOIN users
            ON users.id = attempts.student_id
        JOIN exams
            ON exams.id = attempts.exam_id
        JOIN subjects
            ON subjects.id = exams.subject_id
        WHERE attempts.submitted_at IS NOT NULL
        ORDER BY attempts.submitted_at DESC
    """).fetchall()

    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>

<title>Student Results</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<style>

body {
    font-family: Arial;
    background: #f4f7f6;
    padding: 20px;
}

.container {
    max-width: 1200px;
    margin: auto;
}

.card {
    background: white;
    padding: 20px;
    border-radius: 12px;
    overflow-x: auto;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th,
td {
    padding: 12px;
    border-bottom: 1px solid #ddd;
    text-align: left;
}

th {
    background: #087f5b;
    color: white;
}

</style>

</head>

<body>

<div class="container">

<h2>
All Student Results
</h2>

<div class="card">

{% if results %}

<table>

<thead>

<tr>

<th>
Student
</th>

<th>
Email
</th>

<th>
Exam
</th>

<th>
Subject
</th>

<th>
Score
</th>

<th>
Percentage
</th>

<th>
Submitted
</th>

</tr>

</thead>

<tbody>

{% for result in results %}

<tr>

<td>
{{ result["student_name"] }}
</td>

<td>
{{ result["student_email"] }}
</td>

<td>
{{ result["exam_title"] }}
</td>

<td>
{{ result["subject_name"] }}
</td>

<td>
{{ result["score"] }}/{{ result["total_questions"] }}
</td>

<td>
{{ "%.2f"|format(result["percentage"]) }}%
</td>

<td>
{{ result["submitted_at"] }}
</td>

</tr>

{% endfor %}

</tbody>

</table>

{% else %}

<p>
No student has completed an exam yet.
</p>

{% endif %}

</div>

<p>

<a href="{{ url_for('admin_dashboard') }}">
← Admin Dashboard
</a>

</p>

</div>

</body>

</html>
""",
        results=results,
    )


# ============================================================
# START EXAM
# ============================================================

@app.route(
    "/exam/<int:exam_id>/start"
)
@role_required("student")
def start_exam(exam_id):

    user = current_user()

    conn = get_db()

    exam = conn.execute("""
        SELECT
            exams.*,
            subjects.name AS subject_name
        FROM exams
        JOIN subjects
            ON subjects.id = exams.subject_id
        WHERE exams.id = ?
          AND exams.status = 'published'
    """, (
        exam_id,
    )).fetchone()

    if not exam:

        conn.close()

        return (
            "Exam not found or not available.",
            404,
        )

    questions = conn.execute("""
        SELECT
            questions.id,
            questions.question_text,
            questions.option_a,
            questions.option_b,
            questions.option_c,
            questions.option_d
        FROM exam_questions
        JOIN questions
            ON questions.id = exam_questions.question_id
        WHERE exam_questions.exam_id = ?
          AND questions.status = 'approved'
        ORDER BY exam_questions.id ASC
    """, (
        exam_id,
    )).fetchall()

    conn.close()

    if not questions:

        return (
            "This exam has no approved questions yet.",
            400,
        )

    conn = get_db()

    cursor = conn.execute("""
        INSERT INTO attempts
        (
            exam_id,
            student_id,
            total_questions
        )
        VALUES (?, ?, ?)
    """, (
        exam_id,
        user["id"],
        len(questions),
    ))

    attempt_id = cursor.lastrowid

    conn.commit()

    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>

<title>
{{ exam["title"] }}
</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<style>

body {
    font-family: Arial, sans-serif;
    background: #f4f7f6;
    margin: 0;
}

.header {
    background: #087f5b;
    color: white;
    padding: 15px;
    position: sticky;
    top: 0;
    z-index: 10;
}

.container {
    max-width: 800px;
    margin: auto;
    padding: 20px;
}

.timer {
    background: #222;
    color: white;
    padding: 12px;
    border-radius: 8px;
    text-align: center;
    font-size: 20px;
    margin-bottom: 20px;
}

.question {
    display: none;
    background: white;
    padding: 25px;
    border-radius: 12px;
}

.question.active {
    display: block;
}

.option {
    display: block;
    padding: 14px;
    margin: 10px 0;
    background: #f1f3f5;
    border-radius: 8px;
    cursor: pointer;
}

.option:hover {
    background: #e6f4ef;
}

.navigation {
    margin-top: 20px;
    display: flex;
    justify-content: space-between;
    gap: 10px;
}

button {
    padding: 12px 20px;
    border: 0;
    border-radius: 7px;
    cursor: pointer;
}

.next {
    background: #087f5b;
    color: white;
}

.previous {
    background: #555;
    color: white;
}

.submit {
    background: #c92a2a;
    color: white;
}

</style>

</head>

<body>

<div class="header">

<strong>
{{ exam["title"] }}
</strong>

</div>

<div class="container">

<div class="timer">

Time remaining:

<span id="timer">
{{ exam["duration_minutes"] }}:00
</span>

</div>


<form
    method="POST"
    action="{{ url_for(
        'submit_exam',
        attempt_id=attempt_id
    ) }}"
    id="examForm"
>

{% for question in questions %}

<div
    class="question
    {% if loop.first %}active{% endif %}"
    data-index="{{ loop.index0 }}"
>

<h3>

Question
{{ loop.index }}
of
{{ questions|length }}

</h3>

<p>
{{ question["question_text"] }}
</p>


<label class="option">

<input
    type="radio"
    name="question_{{ question["id"] }}"
    value="A"
>

A.
{{ question["option_a"] }}

</label>


<label class="option">

<input
    type="radio"
    name="question_{{ question["id"] }}"
    value="B"
>

B.
{{ question["option_b"] }}

</label>


<label class="option">

<input
    type="radio"
    name="question_{{ question["id"] }}"
    value="C"
>

C.
{{ question["option_c"] }}

</label>


<label class="option">

<input
    type="radio"
    name="question_{{ question["id"] }}"
    value="D"
>

D.
{{ question["option_d"] }}

</label>

</div>

{% endfor %}


<div class="navigation">

<button
    type="button"
    class="previous"
    onclick="previousQuestion()"
>

Previous

</button>


<button
    type="button"
    class="next"
    onclick="nextQuestion()"
    id="nextButton"
>

Next

</button>


<button
    type="submit"
    class="submit"
    id="submitButton"
    style="display:none;"
>

Submit Exam

</button>

</div>

</form>

</div>


<script>

let currentQuestion = 0;

const questions =
    document.querySelectorAll(".question");

const nextButton =
    document.getElementById("nextButton");

const submitButton =
    document.getElementById("submitButton");


function showQuestion(index) {

    questions.forEach(
        function(question, i) {

            question.classList.toggle(
                "active",
                i === index
            );

        }
    );

    if (index === questions.length - 1) {

        nextButton.style.display =
            "none";

        submitButton.style.display =
            "inline-block";

    } else {

        nextButton.style.display =
            "inline-block";

        submitButton.style.display =
            "none";

    }

}


function nextQuestion() {

    if (
        currentQuestion
        < questions.length - 1
    ) {

        currentQuestion++;

        showQuestion(
            currentQuestion
        );

    }

}


function previousQuestion() {

    if (currentQuestion > 0) {

        currentQuestion--;

        showQuestion(
            currentQuestion
        );

    }

}


/* =========================================================
   TIMER
   ========================================================= */

let totalSeconds =
    {{ exam["duration_minutes"] }} * 60;


function updateTimer() {

    const minutes =
        Math.floor(
            totalSeconds / 60
        );

    const seconds =
        totalSeconds % 60;


    document.getElementById(
        "timer"
    ).innerText =

        String(minutes)
        .padStart(2, "0")

        + ":"

        +

        String(seconds)
        .padStart(2, "0");


    if (totalSeconds <= 0) {

        document.getElementById(
            "examForm"
        ).submit();

        return;

    }

    totalSeconds--;

}


setInterval(
    updateTimer,
    1000
);

updateTimer();


/* =========================================================
   PREVENT ACCIDENTAL PAGE LEAVE
   ========================================================= */

window.addEventListener(
    "beforeunload",
    function(event) {

        event.preventDefault();

        event.returnValue = "";

    }
);

</script>

</body>

</html>
""",
        exam=exam,
        questions=questions,
        attempt_id=attempt_id,
    )


# ============================================================
# SUBMIT EXAM
# ============================================================

@app.route(
    "/exam/submit/<int:attempt_id>",
    methods=["POST"]
)
@role_required("student")
def submit_exam(attempt_id):

    user = current_user()

    conn = get_db()

    attempt = conn.execute("""
        SELECT *
        FROM attempts
        WHERE id = ?
          AND student_id = ?
    """, (
        attempt_id,
        user["id"],
    )).fetchone()

    if not attempt:

        conn.close()

        return (
            "Exam attempt not found.",
            404,
        )

    if attempt["submitted_at"]:

        conn.close()

        return redirect(
            url_for(
                "exam_result",
                attempt_id=attempt_id,
            )
        )

    questions = conn.execute("""
        SELECT
            questions.id,
            questions.correct_answer
        FROM exam_questions
        JOIN questions
            ON questions.id = exam_questions.question_id
        WHERE exam_questions.exam_id = ?
    """, (
        attempt["exam_id"],
    )).fetchall()

    score = 0

    for question in questions:

        question_id = question["id"]

        selected_answer = request.form.get(
            f"question_{question_id}"
        )

        is_correct = 0

        if (
            selected_answer
            and selected_answer.upper()
            == question["correct_answer"].upper()
        ):

            is_correct = 1

            score += 1

        conn.execute("""
            INSERT INTO answers
            (
                attempt_id,
                question_id,
                selected_answer,
                is_correct
            )
            VALUES (?, ?, ?, ?)
        """, (
            attempt_id,
            question_id,
            selected_answer,
            is_correct,
        ))

    total_questions = len(
        questions
    )

    percentage = 0

    if total_questions > 0:

        percentage = (
            score / total_questions
        ) * 100

    conn.execute("""
        UPDATE attempts

        SET
            score = ?,
            total_questions = ?,
            percentage = ?,
            submitted_at = CURRENT_TIMESTAMP

        WHERE id = ?
    """, (
        score,
        total_questions,
        percentage,
        attempt_id,
    ))

    conn.commit()

    conn.close()

    return redirect(
        url_for(
            "exam_result",
            attempt_id=attempt_id,
        )
    )


# ============================================================
# EXAM RESULT
# ============================================================

@app.route(
    "/exam/result/<int:attempt_id>"
)
@role_required("student")
def exam_result(attempt_id):

    user = current_user()

    conn = get_db()

    result = conn.execute("""
        SELECT
            attempts.*,
            exams.title,
            subjects.name AS subject_name
        FROM attempts
        JOIN exams
            ON exams.id = attempts.exam_id
        JOIN subjects
            ON subjects.id = exams.subject_id
        WHERE attempts.id = ?
          AND attempts.student_id = ?
    """, (
        attempt_id,
        user["id"],
    )).fetchone()

    if not result:

        conn.close()

        return (
            "Result not found.",
            404,
        )

    answers = conn.execute("""
        SELECT
            answers.*,
            questions.question_text,
            questions.option_a,
            questions.option_b,
            questions.option_c,
            questions.option_d,
            questions.correct_answer,
            questions.explanation
        FROM answers
        JOIN questions
            ON questions.id = answers.question_id
        WHERE answers.attempt_id = ?
        ORDER BY answers.id ASC
    """, (
        attempt_id,
    )).fetchall()

    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>

<title>
Exam Result
</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<style>

body {
    font-family: Arial;
    background: #f4f7f6;
}

.container {
    max-width: 800px;
    margin: auto;
    padding: 20px;
}

.result {
    background: white;
    padding: 30px;
    border-radius: 15px;
    text-align: center;
}

.score {
    font-size: 40px;
    font-weight: bold;
    color: #087f5b;
}

.answer {
    background: white;
    padding: 20px;
    margin-top: 15px;
    border-radius: 12px;
}

.correct {
    color: green;
}

.wrong {
    color: red;
}

.btn {
    display: inline-block;
    padding: 12px 20px;
    background: #087f5b;
    color: white;
    text-decoration: none;
    border-radius: 7px;
}

</style>

</head>

<body>

<div class="container">

<div class="result">

<h2>
{{ result["title"] }}
</h2>

<p>
{{ result["subject_name"] }}
</p>

<div class="score">

{{ result["score"] }}/{{ result["total_questions"] }}

</div>

<h3>
{{ "%.2f"|format(result["percentage"]) }}%
</h3>

<p>
Exam completed successfully.
</p>

<a
    class="btn"
    href="{{ url_for('dashboard') }}"
>
Back to Dashboard
</a>

</div>


<h2>
Answer Review
</h2>


{% for answer in answers %}

<div class="answer">

<h3>
Question {{ loop.index }}
</h3>

<p>
{{ answer["question_text"] }}
</p>

<p>

Your answer:

<strong>

{% if answer["selected_answer"] %}

{{ answer["selected_answer"] }}

{% else %}

Not answered

{% endif %}

</strong>

</p>


<p>

Correct answer:

<strong>
{{ answer["correct_answer"] }}
</strong>

</p>


{% if answer["is_correct"] %}

<p class="correct">
✓ Correct
</p>

{% else %}

<p class="wrong">
✗ Wrong
</p>

{% endif %}


{% if answer["explanation"] %}

<p>

<strong>
Explanation:
</strong>

{{ answer["explanation"] }}

</p>

{% endif %}

</div>

{% endfor %}

</div>

</body>

</html>
""",
        result=result,
        answers=answers,
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("index")
    )


# ============================================================
# STARTUP
# ============================================================

init_db()

create_admin_from_environment()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv(
                "PORT",
                5000,
            )
        ),
        debug=False,
    )