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

DATABASE = os.getenv(
    "DATABASE_PATH",
    "mock_exam.db",
)


# ============================================================
# DATABASE
# ============================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
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

    # Default subjects
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
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()

            if not user:
                return redirect(url_for("login"))

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
        return redirect(url_for("dashboard"))

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

        <h1>Alhikam Learning Center</h1>

        <h2>Mock Examination Portal</h2>

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
# REGISTER
# ============================================================

@app.route("/register", methods=["GET", "POST"])
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
            flash("Please fill all fields.")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.")
            return redirect(url_for("register"))

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

            flash("Registration successful. Please login.")

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:

            flash("Email already exists.")

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
            cursor: pointer;
        }

        a {
            color: #087f5b;
        }

    </style>
</head>

<body>

<div class="box">

<h2>Student Registration</h2>

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

@app.route("/login", methods=["GET", "POST"])
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

        flash("Invalid email or password.")

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

</style>

</head>

<body>

<div class="box">

<h2>Alhikam Mock Portal</h2>

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

<p>
Your examination results will appear here.
</p>

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
""", user=user)


# ============================================================
# AVAILABLE EXAMS
# ============================================================

@app.route("/exams")
@login_required
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
}

</style>

</head>

<body>

<div class="container">

<h2>Available Mock Exams</h2>

{% if exams %}

{% for exam in exams %}

<div class="exam">

<h3>
{{ exam["title"] }}
</h3>

<p>
Subject: {{ exam["subject_name"] }}
</p>

<p>
Questions: {{ exam["total_questions"] }}
</p>

<p>
Duration: {{ exam["duration_minutes"] }} minutes
</p>

<a class="btn"
   href="#">
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
""", exams=exams)


# ============================================================
# MY RESULTS
# ============================================================

@app.route("/results")
@login_required
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
    """, (user["id"],)).fetchall()

    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>

<title>My Results</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

</head>

<body>

<h2>My Results</h2>

{% if results %}

{% for result in results %}

<div>

<h3>{{ result["title"] }}</h3>

<p>
Subject: {{ result["subject_name"] }}
</p>

<p>
Score:
{{ result["score"] }}/{{ result["total_questions"] }}
</p>

<p>
Percentage:
{{ "%.2f"|format(result["percentage"]) }}%
</p>

<hr>

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
""", results=results)


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
    """, (user["id"],)).fetchall()

    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>

<title>Tutor Dashboard</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

</head>

<body>

<h2>Tutor Dashboard</h2>

<p>
Welcome, {{ user["full_name"] }}
</p>

<h3>My Questions</h3>

{% for question in questions %}

<div>

<strong>
{{ question["question_text"] }}
</strong>

<p>
Subject: {{ question["subject_name"] }}
</p>

<p>
Status: {{ question["status"] }}
</p>

<hr>

</div>

{% else %}

<p>
You have not submitted any questions.
</p>

{% endfor %}

<a href="{{ url_for('logout') }}">
Logout
</a>

</body>

</html>
""",
        user=user,
        questions=questions,
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

    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>

<title>Admin Dashboard</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

</head>

<body>

<h2>Admin Dashboard</h2>

<h3>Statistics</h3>

<ul>

<li>
Students: {{ students }}
</li>

<li>
Tutors: {{ tutors }}
</li>

<li>
Questions: {{ questions }}
</li>

<li>
Mock Exams: {{ exams }}
</li>

</ul>

<a href="{{ url_for('logout') }}">
Logout
</a>

</body>

</html>
""",
        students=students,
        tutors=tutors,
        questions=questions,
        exams=exams,
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