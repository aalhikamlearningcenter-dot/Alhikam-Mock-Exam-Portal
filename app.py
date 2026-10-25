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
)


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DATABASE = os.getenv(
    "DATABASE_PATH",
    "/app/mock_exam.db",
)


# ============================================================
# DATABASE
# ============================================================

def get_db():

    conn = sqlite3.connect(
        DATABASE,
        timeout=30,
    )

    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def init_db():

    conn = get_db()

    try:

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


        # ==========================================
        # TUTOR APPLICATIONS
        # ==========================================

        conn.execute("""
            CREATE TABLE IF NOT EXISTS tutor_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT NOT NULL,
                subjects TEXT NOT NULL,
                qualification TEXT NOT NULL,
                experience TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    except Exception:
        conn.rollback()
        raise

    finally:
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
# HOME - DARK MODE
# ============================================================

@app.route("/")
def index():

    if current_user():
        return redirect(
            url_for("dashboard")
        )

    return render_template_string("""
<!DOCTYPE html>
<html lang="en">

<head>

<title>Alhikam Mock Exam Portal</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<meta name="theme-color" content="#071510">

<style>

* {
    box-sizing: border-box;
}

body {
    font-family: Arial, sans-serif;
    background: #071510;
    color: #f1f5f3;
    margin: 0;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
}

.container {
    width: 100%;
    max-width: 900px;
    margin: auto;
    text-align: center;
}

.card {
    background: linear-gradient(
        145deg,
        #10251c,
        #0a1b13
    );
    border: 1px solid #24543e;
    padding: 45px 30px;
    border-radius: 20px;
    box-shadow: 0 15px 40px rgba(0, 0, 0, 0.35);
}

.logo-icon {
    width: 75px;
    height: 75px;
    margin: 0 auto 20px;
    border-radius: 50%;
    background: #163b2b;
    border: 2px solid #b8860b;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #f5d77b;
    font-size: 30px;
    font-weight: bold;
}

h1 {
    color: #f5d77b;
    font-size: clamp(26px, 5vw, 38px);
    margin-bottom: 12px;
}

h2 {
    color: #55d6a3;
    font-size: clamp(20px, 4vw, 27px);
    margin-top: 10px;
}

p {
    color: #c4d4ca;
    line-height: 1.8;
    font-size: 16px;
    max-width: 600px;
    margin: 20px auto 25px;
}

.buttons {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 12px;
    margin-top: 25px;
}

.btn {
    display: inline-block;
    padding: 14px 25px;
    background: #087f5b;
    color: #ffffff;
    text-decoration: none;
    border: 1px solid #15966d;
    border-radius: 9px;
    font-weight: bold;
    transition: 0.2s;
}

.btn:hover {
    background: #0a9b6d;
    transform: translateY(-2px);
}

.btn.secondary {
    background: #b8860b;
    border-color: #d5a72b;
    color: #ffffff;
}

.btn.secondary:hover {
    background: #d5a72b;
}

.footer {
    color: #82998b;
    font-size: 13px;
    margin-top: 25px;
}

@media (max-width: 480px) {

    body {
        padding: 14px;
    }

    .card {
        padding: 32px 18px;
        border-radius: 15px;
    }

    .buttons {
        flex-direction: column;
    }

    .btn {
        width: 100%;
        padding: 14px 12px;
    }

}

</style>

</head>

<body>

<div class="container">

<div class="card">

<div class="logo-icon">
AL
</div>

<h1>
Alhikam Learning Center
</h1>

<h2>
Mock Examination Portal
</h2>

<p>
Welcome to Alhikam Learning Center's online
CBT examination platform. Students can take
mock examinations, check their results, and
qualified tutors can contribute to learning.
</p>

<div class="buttons">

<a class="btn"
   href="{{ url_for('login') }}">
Login
</a>

<a class="btn secondary"
   href="{{ url_for('register') }}">
Student Registration
</a>

</div>

<div class="footer">
Learn Today. Achieve Tomorrow.
<br>
© Alhikam Learning Center
</div>

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
<html lang="en">

<head>

<title>Student Registration - Alhikam Learning Center</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<meta name="theme-color" content="#071510">

<style>

* {
    box-sizing: border-box;
}

body {
    font-family: Arial, sans-serif;
    background: #071510;
    color: #f1f5f3;
    margin: 0;
    min-height: 100vh;
    padding: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.box {
    width: 100%;
    max-width: 450px;
    margin: 20px auto;
    background: #10251c;
    border: 1px solid #24543e;
    padding: 30px;
    border-radius: 16px;
    box-shadow: 0 12px 35px rgba(0, 0, 0, 0.35);
}

h2 {
    color: #f5d77b;
    text-align: center;
    margin-top: 0;
    margin-bottom: 25px;
}

input {
    width: 100%;
    padding: 13px;
    margin: 9px 0 15px;
    box-sizing: border-box;
    background: #071510;
    color: #ffffff;
    border: 1px solid #38634d;
    border-radius: 8px;
    font-size: 16px;
    outline: none;
}

input:focus {
    border-color: #55d6a3;
    box-shadow: 0 0 0 2px rgba(85, 214, 163, 0.12);
}

input::placeholder {
    color: #a8b9ae;
}

button {
    width: 100%;
    padding: 14px;
    background: #087f5b;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    font-size: 16px;
    font-weight: bold;
    cursor: pointer;
    margin-top: 5px;
}

button:hover {
    background: #0a9b6d;
}

a {
    color: #f5d77b;
    text-decoration: none;
}

a:hover {
    color: #ffffff;
    text-decoration: underline;
}

p {
    color: #d0ddd5;
    line-height: 1.6;
    text-align: center;
    margin-top: 22px;
}

.flash {
    background: #382d13;
    color: #ffe7a0;
    border: 1px solid #8c6c1c;
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 15px;
    overflow-wrap: anywhere;
}

@media (max-width: 480px) {
    body {
        padding: 14px;
    }

    .box {
        padding: 23px 18px;
    }
}

</style>

</head>

<body>

<div class="box">

<h2>
Alhikam Learning Center
<br>
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
    autocomplete="name"
    required
>

<input
    type="email"
    name="email"
    placeholder="Email"
    autocomplete="email"
    required
>

<input
    type="password"
    name="password"
    placeholder="Password (at least 6 characters)"
    autocomplete="new-password"
    minlength="6"
    required
>

<button type="submit">
Create Account
</button>

</form>

<p>
Already have an account?
<br>
<a href="{{ url_for('login') }}">
Login Here
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
* {
    box-sizing: border-box;
}

body {
    font-family: Arial, sans-serif;
    background: #071510;
    color: #f1f5f3;
    margin: 0;
    min-height: 100vh;
    padding: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.box {
    width: 100%;
    max-width: 450px;
    margin: auto;
    background: #10251c;
    border: 1px solid #24543e;
    padding: 30px;
    border-radius: 16px;
    box-shadow: 0 12px 35px rgba(0,0,0,.35);
}

h2 {
    color: #f5d77b;
    text-align: center;
    margin-bottom: 25px;
}

input {
    width: 100%;
    padding: 13px;
    margin: 8px 0 15px;
    background: #071510;
    color: white;
    border: 1px solid #38634d;
    border-radius: 8px;
    font-size: 16px;
}

input::placeholder {
    color: #a8b9ae;
}

button {
    width: 100%;
    padding: 14px;
    background: #087f5b;
    color: white;
    border: 0;
    border-radius: 8px;
    font-weight: bold;
    cursor: pointer;
}

button:hover {
    background: #0a9b6d;
}

a {
    color: #f5d77b;
}

p {
    color: #d0ddd5;
    text-align: center;
}

.flash {
    background: #382d13;
    color: #ffe7a0;
    border: 1px solid #8c6c1c;
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 15px;
}

@media (max-width: 480px) {
    .box {
        padding: 23px 18px;
    }
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
        return redirect(url_for("admin_dashboard"))

    if user["role"] == "tutor":
        return redirect(url_for("tutor_dashboard"))

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>

<title>Student Dashboard - ALHIKAM</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<style>

body {
    font-family: Arial, sans-serif;
    background: #071510;
    color: #f1f5f3;
    margin: 0;
}

.header {
    background: #064e3b;
    color: #ffffff;
    padding: 20px;
}

.container {
    max-width: 1000px;
    margin: auto;
    padding: 20px;
}

.card {
    background: #10251c;
    border: 1px solid #24543e;
    padding: 25px;
    margin: 15px 0;
    border-radius: 12px;
}

.btn {
    display: inline-block;
    padding: 12px 18px;
    margin: 5px 0;
    background: #087f5b;
    color: white;
    text-decoration: none;
    border-radius: 7px;
}

.btn:hover {
    background: #0a9b6d;
}

.tutor-btn {
    background: #b8860b;
    color: white;
}

.logout {
    color: #f5d77b;
}

</style>

</head>

<body>

<div class="header">

<h2>
Welcome, {{ user["full_name"] }}
</h2>

<p>ALHIKAM MOCK EXAM PORTAL</p>

</div>

<div class="container">

<div class="card">

<h3>Student Dashboard</h3>

<p>
Your Mock Exam Portal is ready.
</p>

<a class="btn"
   href="{{ url_for('available_exams') }}">
Available Mock Exams
</a>

</div>

<div class="card">

<h3>My Results</h3>

<a class="btn"
   href="{{ url_for('my_results') }}">
View Results
</a>

</div>

<div class="card">

<h3>Become a Tutor</h3>

<p>
Are you qualified to teach? Submit your tutor
application for admin review. You can become a
tutor after your application is approved.
</p>

<a class="btn tutor-btn"
   href="{{ url_for('tutor_registration') }}">
Register as a Tutor
</a>

</div>

<div class="card">

<a class="logout"
   href="{{ url_for('logout') }}">
Logout
</a>

</div>

</div>

</body>

</html>
""", user=user)


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

        # ----------------------------------------------------
        # VALIDATE REQUIRED FIELDS
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # VALIDATE CORRECT ANSWER
        # ----------------------------------------------------

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

        try:

            # ------------------------------------------------
            # CHECK SUBJECT
            # ------------------------------------------------

            subject = conn.execute("""
                SELECT id
                FROM subjects
                WHERE id = ?
            """, (
                subject_id,
            )).fetchone()

            if not subject:

                flash(
                    "Selected subject does not exist."
                )

                conn.close()

                return redirect(
                    url_for("tutor_new_question")
                )

            # ------------------------------------------------
            # INSERT QUESTION
            # ------------------------------------------------

            cursor = conn.execute("""
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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                "pending",
            ))

            # Get the ID of the newly submitted question
            question_id = cursor.lastrowid

            conn.commit()

            # ------------------------------------------------
            # VERIFY QUESTION WAS SAVED
            # ------------------------------------------------

            saved_question = conn.execute("""
                SELECT
                    id,
                    tutor_id,
                    subject_id,
                    status
                FROM questions
                WHERE id = ?
            """, (
                question_id,
            )).fetchone()

            if not saved_question:

                conn.close()

                flash(
                    "Question could not be saved."
                )

                return redirect(
                    url_for("tutor_new_question")
                )

            conn.close()

            flash(
                "Question submitted successfully. "
                "It is now pending admin approval."
            )

            return redirect(
                url_for("tutor_dashboard")
            )

        except Exception as e:

            conn.rollback()
            conn.close()

            print(
                "TUTOR QUESTION SUBMIT ERROR:",
                e
            )

            flash(
                "Unable to submit question. "
                "Please try again."
            )

            return redirect(
                url_for("tutor_new_question")
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
# ADMIN DASHBOARD - DARK MODE
# ============================================================

@app.route("/admin")
@role_required("admin")
def admin_dashboard():

    conn = get_db()

    students = conn.execute("""
        SELECT COUNT(*) FROM users
        WHERE role = 'student'
    """).fetchone()[0]

    tutors = conn.execute("""
        SELECT COUNT(*) FROM users
        WHERE role = 'tutor'
    """).fetchone()[0]

    questions = conn.execute("""
        SELECT COUNT(*) FROM questions
    """).fetchone()[0]

    exams = conn.execute("""
        SELECT COUNT(*) FROM exams
    """).fetchone()[0]

    pending_questions = conn.execute("""
        SELECT COUNT(*) FROM questions
        WHERE status = 'pending'
    """).fetchone()[0]

    published_exams = conn.execute("""
        SELECT COUNT(*) FROM exams
        WHERE status = 'published'
    """).fetchone()[0]

    try:
        pending_tutors = conn.execute("""
            SELECT COUNT(*)
            FROM tutor_applications
            WHERE status = 'pending'
        """).fetchone()[0]
    except Exception:
        pending_tutors = 0

    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">
<meta name="viewport"
      content="width=device-width, initial-scale=1">

<title>Alhikam Mock Admin</title>

<style>

* {
    box-sizing: border-box;
}

body {
    font-family: Arial, sans-serif;
    background: #050b08;
    color: #e8f0eb;
    margin: 0;
}

.header {
    background: linear-gradient(135deg, #062b20, #0b1711);
    border-bottom: 1px solid #b89235;
    padding: 24px 20px;
}

.header h2 {
    color: #f1ce72;
    margin: 0 0 8px;
    font-size: 25px;
}

.header p {
    color: #aabbb0;
    margin: 0;
    font-size: 14px;
}

.container {
    max-width: 1100px;
    margin: auto;
    padding: 18px;
}

.section-title {
    color: #f1ce72;
    margin: 25px 0 15px;
}

.grid {
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(140px, 1fr));
    gap: 13px;
}

.stat-card {
    background: #101c15;
    border: 1px solid #263e30;
    border-radius: 12px;
    padding: 18px 15px;
    min-width: 0;
}

.stat-label {
    color: #b7c7bc;
    font-size: 13px;
    line-height: 1.5;
    margin: 0 0 12px;
}

.stat {
    font-size: 29px;
    font-weight: bold;
    color: #f1ce72;
    overflow-wrap: anywhere;
}

.card {
    background: #0c1710;
    border: 1px solid #263e30;
    padding: 20px;
    border-radius: 14px;
    margin-top: 20px;
}

.card h3 {
    color: #f1ce72;
    margin-top: 0;
    margin-bottom: 18px;
}

.btn {
    display: block;
    background: #123d2b;
    border: 1px solid #286044;
    color: #f1f5f2;
    text-decoration: none;
    padding: 14px;
    border-radius: 9px;
    margin: 11px 0;
    font-size: 14px;
    font-weight: bold;
    line-height: 1.5;
    transition: background 0.2s;
}

.btn:hover {
    background: #1b573c;
}

.tutor-applications {
    background: #30250d;
    border: 1px solid #b89235;
    color: #f7d778;
}

.tutor-applications:hover {
    background: #493813;
}

.logout {
    display: inline-block;
    color: #f1ce72;
    text-decoration: none;
    padding: 10px 0;
}

.footer {
    text-align: center;
    color: #788b7d;
    font-size: 12px;
    padding: 20px 0;
}

@media (max-width: 380px) {
    .container {
        padding: 12px;
    }

    .grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 9px;
    }

    .stat-card {
        padding: 14px 11px;
    }

    .stat {
        font-size: 25px;
    }

    .card {
        padding: 15px;
    }
}

</style>

</head>

<body>

<div class="header">
    <h2>🎓 Alhikam Mock Admin</h2>
    <p>ADMINISTRATION DASHBOARD</p>
</div>

<div class="container">

<h3 class="section-title">📊 Overview</h3>

<div class="grid">

    <div class="stat-card">
        <p class="stat-label">Students</p>
        <div class="stat">{{ students }}</div>
    </div>

    <div class="stat-card">
        <p class="stat-label">Registered Tutors</p>
        <div class="stat">{{ tutors }}</div>
    </div>

    <div class="stat-card">
        <p class="stat-label">Questions</p>
        <div class="stat">{{ questions }}</div>
    </div>

    <div class="stat-card">
        <p class="stat-label">Mock Exams</p>
        <div class="stat">{{ exams }}</div>
    </div>

    <div class="stat-card">
        <p class="stat-label">Pending Questions</p>
        <div class="stat">{{ pending_questions }}</div>
    </div>

    <div class="stat-card">
        <p class="stat-label">Published Exams</p>
        <div class="stat">{{ published_exams }}</div>
    </div>

    <div class="stat-card">
        <p class="stat-label">Tutor Applications Awaiting Approval</p>
        <div class="stat">{{ pending_tutors }}</div>
    </div>

</div>

<div class="card">

    <h3>⚙️ Management</h3>

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

    <a class="btn tutor-applications"
       href="{{ url_for('admin_tutor_applications') }}">
       📋 Review Tutor Applications
       — {{ pending_tutors }} Pending
    </a>

    <a class="btn"
       href="{{ url_for('admin_results') }}">
       📊 Student Results
    </a>

</div>

<div class="card">
    <a class="logout"
       href="{{ url_for('logout') }}">
       ↩ Logout
    </a>
</div>

<div class="footer">
    ALHIKAM MOCK EXAM PORTAL
    <br>
    Learn Today. Achieve Tomorrow.
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
        pending_tutors=pending_tutors,
   )


# ============================================================
# ADMIN - QUESTION MANAGEMENT
# ============================================================

@app.route("/admin/questions")
@role_required("admin")
def admin_questions():

    conn = get_db()

    # Get every question directly
    questions = conn.execute("""
        SELECT
            id,
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
        FROM questions
        ORDER BY id DESC
    """).fetchall()

    # Convert SQLite rows to normal dictionaries
    questions = [dict(q) for q in questions]

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
    padding: 20px 0;
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
    margin-bottom: 10px;
}

.empty {
    background: #fff3cd;
    padding: 15px;
    border-radius: 8px;
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

{% if questions %}

{% for question in questions %}

<div class="question">

<p>
<strong>
{{ question["question_text"] }}
</strong>
</p>

<p>
<strong>Question ID:</strong>
{{ question["id"] }}
</p>

<p>
<strong>Subject ID:</strong>
{{ question["subject_id"] }}
</p>

<p>
<strong>Tutor ID:</strong>
{{ question["tutor_id"] }}
</p>

<p>
<strong>Correct Answer:</strong>
{{ question["correct_answer"] }}
</p>

<p>

<strong>Status:</strong>

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

{% endfor %}

{% else %}

<div class="empty">

<strong>
No questions available.
</strong>

</div>

{% endif %}

</div>


<a href="{{ url_for('admin_dashboard') }}">
← Admin Dashboard
</a>

</div>

</body>

</html>
""",
        questions=questions
    )

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
# TUTOR REGISTRATION
# ALHIKAM LEARNING CENTER
# Monthly Salary + Bank Details + Tutor Rules
# ============================================================

@app.route("/tutor-registration", methods=["GET", "POST"])
def tutor_registration():

    if request.method == "POST":

        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        subjects = request.form.get("subjects", "").strip()
        qualification = request.form.get("qualification", "").strip()
        experience = request.form.get("experience", "").strip()
        password = request.form.get("password", "")

        bank_name = request.form.get("bank_name", "").strip()
        account_name = request.form.get("account_name", "").strip()
        account_number = request.form.get("account_number", "").strip()

        agree_rules = request.form.get("agree_rules", "")

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not all([
            full_name, email, phone, subjects,
            qualification, experience, password,
            bank_name, account_name, account_number
        ]):
            flash("Please complete all required fields.")
            return redirect(url_for("tutor_registration"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.")
            return redirect(url_for("tutor_registration"))

        if not account_number.isdigit() or len(account_number) != 10:
            flash("Please enter a valid 10-digit bank account number.")
            return redirect(url_for("tutor_registration"))

        if agree_rules != "yes":
            flash(
                "You must read and accept the Tutor "
                "Responsibilities & Employment Rules."
            )
            return redirect(url_for("tutor_registration"))

        conn = get_db()

        try:
            # ------------------------------------------------
            # SAFE DATABASE MIGRATION
            # Adds missing columns without deleting old data.
            # ------------------------------------------------

            existing_columns = {
                row[1]
                for row in conn.execute(
                    "PRAGMA table_info(tutor_applications)"
                ).fetchall()
            }

            required_columns = {
                "bank_name": "TEXT NOT NULL DEFAULT ''",
                "account_name": "TEXT NOT NULL DEFAULT ''",
                "account_number": "TEXT NOT NULL DEFAULT ''"
            }

            for column, definition in required_columns.items():
                if column not in existing_columns:
                    conn.execute(
                        f"ALTER TABLE tutor_applications "
                        f"ADD COLUMN {column} {definition}"
                    )

            # -----------------------------------------------
            # CHECK EXISTING USER
            # -----------------------------------------------

            existing_user = conn.execute("""
                SELECT id
                FROM users
                WHERE email = ?
            """, (email,)).fetchone()

            if existing_user:
                flash("This email already has an account.")
                return redirect(url_for("tutor_registration"))

            # -----------------------------------------------
            # CHECK EXISTING APPLICATION
            # -----------------------------------------------

            existing_application = conn.execute("""
                SELECT id
                FROM tutor_applications
                WHERE email = ?
            """, (email,)).fetchone()

            if existing_application:
                flash(
                    "An application with this email already exists."
                )
                return redirect(url_for("tutor_registration"))

            # -----------------------------------------------
            # SAVE APPLICATION
            # New applicants remain PENDING until admin approval.
            # -----------------------------------------------

            conn.execute("""
                INSERT INTO tutor_applications (
                    full_name,
                    email,
                    phone,
                    subjects,
                    qualification,
                    experience,
                    password_hash,
                    bank_name,
                    account_name,
                    account_number,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """, (
                full_name,
                email,
                phone,
                subjects,
                qualification,
                experience,
                generate_password_hash(password),
                bank_name,
                account_name,
                account_number
            ))

            conn.commit()

            flash(
                "Application submitted successfully. "
                "Please wait for admin approval."
            )

        except sqlite3.IntegrityError:
            conn.rollback()
            flash(
                "An application or account with this email "
                "already exists."
            )

        except sqlite3.Error:
            conn.rollback()
            app.logger.exception("Tutor registration database error")
            flash(
                "Unable to submit your application right now. "
                "Please try again later."
            )

        finally:
            conn.close()

        return redirect(url_for("tutor_registration"))

    
    # ========================================================
    # TUTOR REGISTRATION PAGE
    # ========================================================

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport"
              content="width=device-width, initial-scale=1">

        <title>Tutor Registration - Alhikam Learning Center</title>

        <style>
            * {
                box-sizing: border-box;
            }

            body {
                font-family: Arial, sans-serif;
                background: #101810;
                color: #ffffff;
                padding: 15px;
                margin: 0;
                line-height: 1.6;
            }

            .card {
                max-width: 560px;
                margin: 20px auto;
                padding: 22px;
                background: #1b281e;
                border: 1px solid #354936;
                border-radius: 14px;
            }

            h2, h3, h4 {
                color: #d4af37;
            }

            h2 {
                text-align: center;
            }

            .subtitle {
                text-align: center;
                color: #d7dfd5;
            }

            input, textarea, button {
                font: inherit;
            }

            input:not([type="checkbox"]),
            textarea {
                display: block;
                width: 100%;
                padding: 12px;
                margin: 10px 0;
                border-radius: 7px;
                border: 1px solid #53634f;
                background: #111a13;
                color: white;
            }

            textarea {
                min-height: 100px;
                resize: vertical;
            }

            .rules {
                background: #111a13;
                border: 1px solid #53634f;
                border-radius: 10px;
                padding: 15px;
                margin: 18px 0;
            }

            .rules li {
                margin-bottom: 10px;
            }

            .agreement {
                display: flex;
                align-items: flex-start;
                gap: 10px;
                padding: 14px 0;
            }

            .agreement input {
                width: 20px;
                height: 20px;
                flex-shrink: 0;
                margin-top: 4px;
                accent-color: #d4af37;
            }

            button {
                width: 100%;
                padding: 13px;
                margin-top: 10px;
                border: 0;
                border-radius: 7px;
                background: #d4af37;
                color: #101810;
                font-weight: bold;
                cursor: pointer;
            }

            a {
                color: #e6c75a;
            }

            .message {
                background: #283c2b;
                padding: 10px;
                border-radius: 7px;
                color: #f5d76e;
                overflow-wrap: anywhere;
            }

            .note {
                color: #c5d0c3;
                font-size: 13px;
            }

            .section-title {
                margin-top: 24px;
                border-bottom: 1px solid #53634f;
                padding-bottom: 6px;
            }

            .back {
                text-align: center;
                margin-top: 20px;
            }

            .salary-card {
                background: #1b281e;
                border: 1px solid #53634f;
                border-radius: 8px;
                padding: 12px;
                margin: 12px 0;
            }

            .salary-amount {
                color: #f5d76e;
                font-size: 20px;
                font-weight: bold;
            }
        </style>
    </head>

    <body>
        <div class="card">

            <h2>Tutor Registration</h2>

            <p class="subtitle">
                Apply to become a tutor at
                Alhikam Learning Center.
            </p>

            {% with messages = get_flashed_messages() %}
                {% for message in messages %}
                    <p class="message">{{ message }}</p>
                {% endfor %}
            {% endwith %}

            <form method="POST">

                <h3 class="section-title">
                    Personal Information
                </h3>

                <input
                    name="full_name"
                    placeholder="Full Name"
                    autocomplete="name"
                    required
                >

                <input
                    type="email"
                    name="email"
                    placeholder="Email Address"
                    autocomplete="email"
                    required
                >

                <input
                    name="phone"
                    placeholder="Phone Number"
                    autocomplete="tel"
                    required
                >

                <h3 class="section-title">
                    Teaching Information
                </h3>

                <input
                    name="subjects"
                    placeholder="Subject(s) You Teach"
                    required
                >

                <input
                    name="qualification"
                    placeholder="Qualification"
                    required
                >

                <textarea
                    name="experience"
                    placeholder="Describe Your Teaching Experience"
                    required
                ></textarea>

                <input
                    type="password"
                    name="password"
                    placeholder="Create Password (minimum 6 characters)"
                    minlength="6"
                    autocomplete="new-password"
                    required
                >

                <h3 class="section-title">
                    Salary Bank Account Details
                </h3>

                <p class="note">
                    Enter the bank account where your monthly
                    salary should be paid. Use an account
                    belonging to you and provide accurate
                    details. These details are for authorized
                    administrative use only.
                </p>

                <input
                    name="bank_name"
                    placeholder="Bank Name"
                    autocomplete="off"
                    required
                >

                <input
                    name="account_name"
                    placeholder="Bank Account Name"
                    autocomplete="off"
                    required
                >

                <input
                    type="text"
                    name="account_number"
                    placeholder="10-digit Bank Account Number"
                    inputmode="numeric"
                    pattern="[0-9]{10}"
                    minlength="10"
                    maxlength="10"
                    autocomplete="off"
                    required
                >

                <div class="rules">

                    <h3>
                        Tutor Responsibilities, Salary
                        & Employment Rules
                    </h3>

                    <p>
                        Please read the salary, data support,
                        teaching duties and employment rules
                        carefully before applying.
                    </p>

                    <h4>1. Monthly Salary</h4>

                    <div class="salary-card">
                        <strong>Video Tutor</strong>
                        <p class="salary-amount">
                            ₦15,000 per month
                        </p>
                        <p class="note">
                            Proposed starting monthly salary.
                        </p>
                    </div>

                    <div class="salary-card">
                        <strong>Voice-Chat Tutor</strong>
                        <p class="salary-amount">
                            ₦10,000 per month
                        </p>
                        <p class="note">
                            Proposed starting monthly salary.
                        </p>
                    </div>

                    <ul>
                        <li>
                            Final salary depends on the assigned
                            teaching method, qualification,
                            experience, workload and written
                            employment agreement.
                        </li>
                        <li>
                            Any agreed salary change must be
                            communicated in advance and confirmed
                            in writing.
                        </li>
                    </ul>

                    <h4>2. Monthly Data Support</h4>

                    <ul>
                        <li>
                            Video tutors may receive data support
                            of up to <strong>10GB per month</strong>.
                        </li>
                        <li>
                            Voice-chat tutors may receive data
                            support of up to <strong>5GB per month</strong>.
                        </li>
                        <li>
                            These are proposed maximum allowances,
                            not a guarantee that the full amount
                            will be provided every month.
                        </li>
                        <li>
                            Eligibility, amount and delivery
                            arrangements will be confirmed in
                            the written employment agreement.
                        </li>
                    </ul>

                    <h4>3. Monthly Teaching Schedule</h4>

                    <ul>
                        <li>
                            Tutors are expected to conduct
                            8–10 classes per month.
                        </li>
                        <li>
                            The normal workload is approximately
                            2–4 teaching hours per week, subject
                            to the agreed timetable.
                        </li>
                        <li>
                            The Admin or Academic Coordinator
                            assigns subjects, class dates,
                            times and teaching methods.
                        </li>
                        <li>
                            Tutors must prepare lessons and
                            attend assigned classes on time.
                        </li>
                    </ul>

                    <h4>4. Teaching Methods</h4>

                    <ul>
                        <li>
                            Video tutors should provide clear
                            explanations, readable teaching
                            materials and suitable audio and
                            video quality.
                        </li>
                        <li>
                            Voice-chat tutors should explain
                            topics clearly, interact with
                            students and allow time for questions.
                        </li>
                        <li>
                            Tutors must use the teaching method
                            assigned or approved by the
                            Academic Coordinator.
                        </li>
                    </ul>

                    <h4>5. Syllabus and Past Questions</h4>

                    <ul>
                        <li>
                            Lessons must follow the relevant
                            official JAMB, WAEC or NECO syllabus
                            for the assigned subject.
                        </li>
                        <li>
                            Tutors should use relevant past
                            questions, practice questions and
                            clear explanations to help students
                            prepare for examinations.
                        </li>
                        <li>
                            Tutors must provide accurate answers
                            and explanations and must not
                            knowingly teach incorrect information.
                        </li>
                    </ul>

                    <h4>6. Weekly Mock Questions</h4>

                    <ul>
                        <li>
                            Every tutor must prepare weekly
                            mock questions for their assigned
                            subject.
                        </li>
                        <li>
                            Questions should include correct
                            answers and explanations.
                        </li>
                        <li>
                            Questions may require approval
                            before publication.
                        </li>
                    </ul>

                    <h4>7. Absence and Substitute Tutors</h4>

                    <ul>
                        <li>
                            Tutors must notify the Academic
                            Coordinator as early as possible
                            if they cannot attend a scheduled class.
                        </li>
                        <li>
                            A substitute tutor may be assigned
                            when necessary.
                        </li>
                        <li>
                            Any related payment or salary
                            adjustment must be documented and
                            handled according to the written
                            employment agreement and applicable law.
                        </li>
                    </ul>

                    <h4>8. Unreported Absences</h4>

                    <ul>
                        <li>
                            Three classes missed without
                            notification or an acceptable
                            explanation may lead to an
                            administrative review.
                        </li>
                        <li>
                            Replacement or termination may
                            follow after review and after the
                            tutor has an opportunity to explain.
                        </li>
                    </ul>

                    <h4>9. Professional Conduct and Reports</h4>

                    <ul>
                        <li>
                            Tutors must respect students,
                            follow the approved timetable and
                            submit lesson reports when requested.
                        </li>
                        <li>
                            Student information, passwords and
                            private account details must be
                            kept confidential.
                        </li>
                        <li>
                            Tutors must not share confidential
                            information with unauthorized persons.
                        </li>
                    </ul>

                    <h4>10. Application and Approval</h4>

                    <ul>
                        <li>
                            Submitting this form does not
                            automatically make the applicant
                            an approved tutor.
                        </li>
                        <li>
                            All applications are subject to
                            Admin review and approval.
                        </li>
                        <li>
                            Final salary, data support, workload,
                            payment arrangements and other
                            employment terms must be confirmed
                            in writing before work begins.
                        </li>
                    </ul>

                    <p class="note">
                        Salary and data figures shown here are
                        proposed starting terms. Final agreed
                        terms will be confirmed in writing and
                        will be subject to applicable
                        employment laws.
                    </p>

                </div>

                <label class="agreement">
                    <input
                        type="checkbox"
                        name="agree_rules"
                        value="yes"
                        required
                    >

                    <span>
                        I have read and understood the Tutor
                        Responsibilities, Salary & Employment
                        Rules of Alhikam Learning Center, and
                        I agree to comply with them if my
                        application is approved.
                    </span>
                </label>

                <button type="submit">
                    Submit Application
                </button>

            </form>

            <p class="back">
                <a href="{{ url_for('login') }}">
                    Back to Login
                </a>
            </p>

        </div>
    </body>
    </html>
    """)



# ============================================================
# ADMIN - TUTOR APPLICATIONS
# ============================================================

@app.route("/admin/tutor-applications")
@role_required("admin")
def admin_tutor_applications():

    conn = get_db()

    try:
        # Read existing database columns
        columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(tutor_applications)"
            ).fetchall()
        }

        # Add missing bank fields safely
        if "bank_name" not in columns:
            conn.execute("""
                ALTER TABLE tutor_applications
                ADD COLUMN bank_name TEXT DEFAULT ''
            """)

        if "account_name" not in columns:
            conn.execute("""
                ALTER TABLE tutor_applications
                ADD COLUMN account_name TEXT DEFAULT ''
            """)

        if "account_number" not in columns:
            conn.execute("""
                ALTER TABLE tutor_applications
                ADD COLUMN account_number TEXT DEFAULT ''
            """)

        if "salary_amount" not in columns:
            conn.execute("""
                ALTER TABLE tutor_applications
                ADD COLUMN salary_amount INTEGER DEFAULT 0
            """)

        if "data_allowance_gb" not in columns:
            conn.execute("""
                ALTER TABLE tutor_applications
                ADD COLUMN data_allowance_gb INTEGER DEFAULT 0
            """)

        conn.commit()

        # Get applications after ensuring columns exist
        applications = conn.execute("""
            SELECT *
            FROM tutor_applications
            ORDER BY
                CASE
                    WHEN status = 'pending' THEN 0
                    WHEN status = 'approved' THEN 1
                    ELSE 2
                END,
                id DESC
        """).fetchall()

    finally:
        conn.close()

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport"
              content="width=device-width, initial-scale=1">

        <title>Tutor Applications - Alhikam Learning Center</title>

        <style>
            * {
                box-sizing: border-box;
            }

            body {
                margin: 0;
                padding: 15px;
                font-family: Arial, sans-serif;
                background: #101810;
                color: #f5f5f5;
            }

            .container {
                max-width: 850px;
                margin: auto;
            }

            .card {
                background: #1b281e;
                border: 1px solid #354936;
                padding: 18px;
                margin: 16px 0;
                border-radius: 12px;
                overflow-wrap: anywhere;
            }

            h2, h3 {
                color: #d4af37;
            }

            .section {
                background: #121c14;
                padding: 14px;
                margin-top: 16px;
                border-radius: 9px;
                border: 1px solid #354936;
            }

            .pending {
                color: #ffd166;
            }

            .approved {
                color: #70e090;
            }

            .rejected {
                color: #ff8585;
            }

            label {
                display: block;
                margin-top: 12px;
                margin-bottom: 6px;
                color: #e6c75a;
                font-weight: bold;
            }

            input {
                display: block;
                width: 100%;
                padding: 12px;
                border-radius: 7px;
                border: 1px solid #536553;
                background: #0d140f;
                color: white;
                font-size: 16px;
            }

            button {
                padding: 12px;
                margin: 8px 5px 0 0;
                border: 0;
                border-radius: 7px;
                font-weight: bold;
                cursor: pointer;
            }

            .save {
                width: 100%;
                background: #d4af37;
                color: #101810;
                margin-top: 15px;
            }

            .approve {
                background: #16834a;
                color: white;
            }

            .reject {
                background: #b52b35;
                color: white;
            }

            a {
                color: #e6c75a;
            }

            .muted {
                color: #b8c4b8;
            }
        </style>
    </head>

    <body>
    <div class="container">

        <h2>Alhikam Learning Center</h2>
        <h3>Tutor Applications Dashboard</h3>

        <p class="muted">
            Review tutor applications, bank details, monthly salary
            and data support before approving tutors.
        </p>

        {% for application in applications %}
        <div class="card">

            <h3>{{ application["full_name"] }}</h3>

            <p>Email: {{ application["email"] }}</p>
            <p>Phone: {{ application["phone"] }}</p>
            <p>Subjects: {{ application["subjects"] }}</p>
            <p>Qualification: {{ application["qualification"] }}</p>
            <p>Experience: {{ application["experience"] }}</p>
            <p>Applied: {{ application["created_at"] }}</p>

            <p>
                Status:
                <strong class="{{ application['status'] }}">
                    {{ application["status"]|upper }}
                </strong>
            </p>

            <!-- BANK DETAILS -->
            <div class="section">
                <h3>Bank Account Details</h3>

                <p>
                    Bank Name:
                    {{ application["bank_name"] or "Not provided" }}
                </p>

                <p>
                    Account Name:
                    {{ application["account_name"] or "Not provided" }}
                </p>

                <p>
                    Account Number:
                    {{ application["account_number"] or "Not provided" }}
                </p>
            </div>

            <!-- SALARY SETTINGS -->
            <div class="section">
                <h3>Manage Tutor Salary</h3>

                <p>
                    Current Monthly Salary:
                    <strong>
                        ₦{{ "{:,}".format(
                            application["salary_amount"] or 0
                        ) }}
                    </strong>
                </p>

                <p>
                    Current Data Support:
                    <strong>
                        {{ application["data_allowance_gb"] or 0 }} GB
                    </strong>
                </p>

                <form method="POST"
                      action="{{ url_for(
                          'update_tutor_salary',
                          application_id=application['id']
                      ) }}">

                    <label>Monthly Salary (₦)</label>
                    <input
                        type="number"
                        name="salary_amount"
                        min="0"
                        max="10000000"
                        step="1"
                        value="{{ application['salary_amount'] or 0 }}"
                        required>

                    <label>Monthly Data Support (GB)</label>
                    <input
                        type="number"
                        name="data_allowance_gb"
                        min="0"
                        max="1000"
                        step="1"
                        value="{{ application['data_allowance_gb'] or 0 }}"
                        required>

                    <button class="save" type="submit">
                        Save Salary & Data Support
                    </button>
                </form>
            </div>

            <!-- APPROVE OR REJECT -->
            {% if application["status"] == "pending" %}
            <div class="section">
                <h3>Application Decision</h3>

                <form method="POST"
                      action="{{ url_for(
                          'review_tutor_application',
                          application_id=application['id']
                      ) }}">

                    <button class="approve"
                            type="submit"
                            name="decision"
                            value="approve">
                        Approve Tutor
                    </button>

                    <button class="reject"
                            type="submit"
                            name="decision"
                            value="reject">
                        Reject Application
                    </button>
                </form>
            </div>
            {% endif %}

        </div>

        {% else %}
            <p>No tutor applications yet.</p>
        {% endfor %}

        <p>
            <a href="{{ url_for('admin_dashboard') }}">
                Back to Admin Dashboard
            </a>
        </p>

    </div>
    </body>
    </html>
    """, applications=applications)


# ============================================================
# ADMIN - UPDATE TUTOR SALARY AND DATA SUPPORT
# Add this route BEFORE review_tutor_application
# ============================================================

@app.route(
    "/admin/tutor-applications/<int:application_id>/salary",
    methods=["POST"]
)
@role_required("admin")
def update_tutor_salary(application_id):

    try:
        salary_amount = int(
            request.form.get("salary_amount", "")
        )

        data_allowance_gb = int(
            request.form.get("data_allowance_gb", "")
        )

        if not 0 <= salary_amount <= 10000000:
            flash("Invalid salary amount.")
            return redirect(url_for("admin_tutor_applications"))

        if not 0 <= data_allowance_gb <= 1000:
            flash("Invalid data support amount.")
            return redirect(url_for("admin_tutor_applications"))

    except (ValueError, TypeError):
        flash("Please enter valid numbers.")
        return redirect(url_for("admin_tutor_applications"))

    conn = get_db()

    try:
        # Confirm that this tutor application exists
        application = conn.execute("""
            SELECT id
            FROM tutor_applications
            WHERE id = ?
        """, (application_id,)).fetchone()

        if application is None:
            flash("Tutor application not found.")
            return redirect(url_for("admin_tutor_applications"))

        conn.execute("""
            UPDATE tutor_applications
            SET salary_amount = ?,
                data_allowance_gb = ?
            WHERE id = ?
        """, (
            salary_amount,
            data_allowance_gb,
            application_id
        ))

        conn.commit()
        flash("Tutor salary and data support updated successfully.")

    except sqlite3.Error:
        conn.rollback()
        flash("Could not update salary. Please try again.")

    finally:
        conn.close()

    return redirect(url_for("admin_tutor_applications"))


# ============================================================
# ADMIN - APPROVE OR REJECT TUTOR
# Keep your existing review_tutor_application route below
# ============================================================

@app.route(
    "/admin/tutor-applications/<int:application_id>/review",
    methods=["POST"]
)
@role_required("admin")
def review_tutor_application(application_id):

    decision = request.form.get("decision", "")

    if decision not in {"approve", "reject"}:
        return "Invalid decision.", 400

    conn = get_db()

    try:
        application = conn.execute("""
            SELECT *
            FROM tutor_applications
            WHERE id = ?
              AND status = 'pending'
        """, (application_id,)).fetchone()

        if not application:
            flash("Application not found or already reviewed.")
            return redirect(url_for("admin_tutor_applications"))

        if decision == "approve":

            existing_user = conn.execute("""
                SELECT id, role
                FROM users
                WHERE email = ?
            """, (application["email"],)).fetchone()

            if existing_user:
                flash(
                    "This email already belongs to an account. "
                    "No account role was changed."
                )
                return redirect(url_for("admin_tutor_applications"))

            conn.execute("""
                INSERT INTO users (
                    full_name,
                    email,
                    password_hash,
                    role
                )
                VALUES (?, ?, ?, 'tutor')
            """, (
                application["full_name"],
                application["email"],
                application["password_hash"],
            ))

            conn.execute("""
                UPDATE tutor_applications
                SET status = 'approved'
                WHERE id = ?
            """, (application_id,))

            conn.commit()
            flash("Tutor approved. The tutor can now log in.")

        else:
            conn.execute("""
                UPDATE tutor_applications
                SET status = 'rejected'
                WHERE id = ?
            """, (application_id,))

            conn.commit()
            flash("Tutor application rejected.")

    except sqlite3.IntegrityError:
        conn.rollback()
        flash("Could not process this application. Please check the account.")

    finally:
        conn.close()

    return redirect(url_for("admin_tutor_applications"))



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