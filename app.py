import sqlite3
from datetime import date

from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "quran-school-secret-key"
DATABASE = "database.db"

# Куран жатташтын статустары
STATUS_MEMORIZED = "Өтүлдү"
QURAN_STATUSES = [STATUS_MEMORIZED, "Өтүлгөн жок", "Кайталоо"]





# =========================
# DATABASE
# =========================
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def password_ok(stored, entered):
    """Сырсөз хэштелген болсо хэш менен, ачык текст болсо түз салыштырат."""
    if not stored:
        return False
    if stored.startswith(("pbkdf2:", "scrypt:")):
        return check_password_hash(stored, entered)
    return stored == entered


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS teacher_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL,
            lesson_number INTEGER NOT NULL,
            topic TEXT NOT NULL,
            lesson_date TEXT NOT NULL,
            status TEXT NOT NULL,
            note TEXT,
            semester INTEGER DEFAULT 1
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            birth_year INTEGER,
            course_id INTEGER NOT NULL,
            parent_name TEXT,
            phone TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS student_attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            assignment_id INTEGER NOT NULL,
            lesson_date TEXT NOT NULL,
            attendance TEXT NOT NULL,
            grade TEXT,
            note TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS parents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            student_id INTEGER NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS quran_sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            juz_number INTEGER NOT NULL UNIQUE,
            section_name TEXT,
            start_reference TEXT,
            end_reference TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS quran_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            juz_number INTEGER NOT NULL,
            surah_name TEXT,
            start_ayah INTEGER,
            end_ayah INTEGER,
            lesson_number INTEGER,
            status TEXT NOT NULL,
            progress_date TEXT NOT NULL,
            grade TEXT,
            note TEXT,
            teacher_id INTEGER,
            semester INTEGER DEFAULT 1
        )
    """)

    try:
        conn.execute("ALTER TABLE lessons ADD COLUMN semester INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE quran_progress ADD COLUMN semester INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE quran_progress ADD COLUMN lesson_number INTEGER")
    except sqlite3.OperationalError:
        pass

    courses = [
        "1-а", "1-б", "1-в",
        "2-а", "2-б",
        "3-а", "3-б"
    ]
    for course in courses:
        existing = conn.execute("SELECT id FROM courses WHERE name = ?", (course,)).fetchone()
        if not existing:
            conn.execute("INSERT INTO courses (name) VALUES (?)", (course,))

    subjects = ["Куран жаттоо", "Фикх", "Акыйда", "Хадис", "Тафсир", "Тажвид", "Сийра", "Араб тили"]
    for subject in subjects:
        existing = conn.execute("SELECT id FROM subjects WHERE name = ?", (subject,)).fetchone()
        if not existing:
            conn.execute("INSERT INTO subjects (name) VALUES (?)", (subject,))

    quran_sections = [
        (1, "الم", "الفاتحة 1", "البقرة 141"),
        (2, "سيقول", "البقرة 142", "البقرة 252"),
        (3, "تلك الرسل", "البقرة 253", "آل عمران 92"),
        (4, "لن تنالوا", "آل عمران 93", "النساء 23"),
        (5, "والمحصنات", "النساء 24", "النساء 147"),
        (6, "لا يحب الله", "النساء 148", "المائدة 81"),
        (7, "وإذا سمعوا", "المائدة 82", "الأنعام 110"),
        (8, "ولو أننا", "الأنعام 111", "الأعراف 87"),
        (9, "قال الملأ", "الأعراف 88", "الأنفال 40"),
        (10, "واعلموا", "الأنفال 41", "التوبة 92"),
        (11, "يعتذرون", "التوبة 93", "هود 5"),
        (12, "وما من دابة", "هود 6", "يوسف 52"),
        (13, "وما أبرئ", "يوسف 53", "إبراهيم 52"),
        (14, "ربما", "الحجر 1", "النحل 128"),
        (15, "سبحان الذي", "الإسراء 1", "الكهف 74"),
        (16, "قال ألم", "الكهف 75", "طه 135"),
        (17, "اقترب للناس", "الأنبياء 1", "الحج 78"),
        (18, "قد أفلح", "المؤمنون 1", "الفرقان 20"),
        (19, "وقال الذين", "الفرقان 21", "النمل 55"),
        (20, "فما كان جواب", "النمل 56", "العنكبوت 45"),
        (21, "اتل ما أوحي", "العنكبوت 46", "الأحزاب 30"),
        (22, "ومن يقنت", "الأحزاب 31", "يس 27"),
        (23, "وما أنزلنا", "يس 28", "الزمر 31"),
        (24, "فمن أظلم", "الزمر 32", "فصلت 46"),
        (25, "إليه يرد", "فصلت 47", "الجاثية 37"),
        (26, "حم", "الأحقاف 1", "الذاريات 30"),
        (27, "قال فما خطبكم", "الذاريات 31", "الحديد 29"),
        (28, "قد سمع الله", "المجادلة 1", "التحريم 12"),
        (29, "تبارك الذي", "الملك 1", "المرسلات 50"),
        (30, "عم يتساءلون", "النبأ 1", "الناس 6")
    ]

    for item in quran_sections:
        existing = conn.execute("SELECT id FROM quran_sections WHERE juz_number = ?", (item[0],)).fetchone()
        if not existing:
            conn.execute("""
                INSERT INTO quran_sections
                (juz_number, section_name, start_reference, end_reference)
                VALUES (?, ?, ?, ?)
            """, item)

    admin_teacher = conn.execute("SELECT id FROM teachers WHERE username = ?", ("admin",)).fetchone()
    if not admin_teacher:
        conn.execute("""
            INSERT INTO teachers (name, username, password)
            VALUES (?, ?, ?)
        """, ("Администратор", "admin", "1234"))

    conn.commit()
    conn.close()


# =========================
# LOGIN & LOGOUT
# =========================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username == "admin" and password == "1234":
            session.clear()
            session["user_id"] = 0
            session["username"] = "admin"
            session["role"] = "admin"
            return redirect(url_for("admin"))

        conn = get_db()

        parent = conn.execute("SELECT * FROM parents WHERE username = ?", (username,)).fetchone()
        if parent and password_ok(parent["password"], password):
            session.clear()
            session["user_id"] = parent["id"]
            session["student_id"] = parent["student_id"]
            session["username"] = parent["username"]
            session["role"] = "parent"
            conn.close()
            return redirect(url_for("parent"))

        teacher = conn.execute("SELECT * FROM teachers WHERE username = ?", (username,)).fetchone()
        if teacher and password_ok(teacher["password"], password):
            session.clear()
            session["user_id"] = teacher["id"]
            session["username"] = teacher["username"]
            session["role"] = "teacher"
            conn.close()
            return redirect(url_for("teacher"))

        conn.close()
        return render_template("login.html", error="Логин же сырсөз туура эмес")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# =========================
# ADMIN DASHBOARD
# =========================
@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    
    conn = get_db()
    
    # 1. Жалпы статистикалык маалыматтар
    total_teachers = conn.execute("SELECT COUNT(*) AS count FROM teachers WHERE username != 'admin'").fetchone()["count"]
    total_students = conn.execute("SELECT COUNT(*) AS count FROM students").fetchone()["count"]
    total_parents = conn.execute("SELECT COUNT(*) AS count FROM parents").fetchone()["count"]
    total_courses = conn.execute("SELECT COUNT(*) AS count FROM courses").fetchone()["count"]
    total_subjects = conn.execute("SELECT COUNT(*) AS count FROM subjects").fetchone()["count"]
    total_assignments = conn.execute("SELECT COUNT(*) AS count FROM teacher_assignments").fetchone()["count"]
    total_attendance = conn.execute("SELECT COUNT(*) AS count FROM student_attendance").fetchone()["count"]
    
    # 2. Куран боюнча прогресстер
    completed_juz = conn.execute(
        "SELECT COUNT(DISTINCT student_id || '-' || juz_number) AS count FROM quran_progress WHERE status = ?",
        (STATUS_MEMORIZED,)
    ).fetchone()["count"]

    finished_row = conn.execute("""
        SELECT COUNT(*) AS count FROM (
            SELECT student_id
            FROM quran_progress
            WHERE status = ?
            GROUP BY student_id
            HAVING COUNT(DISTINCT juz_number) = 30
        )
    """, (STATUS_MEMORIZED,)).fetchone()

    quran_finished_students = finished_row["count"] if finished_row else 0
    finish_percent = round((quran_finished_students / total_students * 100), 1) if total_students > 0 else 0

    # 3. Катышуу статистикасы
    present_count = conn.execute("SELECT COUNT(*) AS count FROM student_attendance WHERE attendance = 'Келди'").fetchone()["count"]
    absent_count = conn.execute("SELECT COUNT(*) AS count FROM student_attendance WHERE attendance = 'Келген жок'").fetchone()["count"]
    total_att_records = present_count + absent_count
    attendance_percent = round(present_count / total_att_records * 100, 1) if total_att_records > 0 else 0

    # 4. Тизмелер
    courses = conn.execute("SELECT * FROM courses ORDER BY id").fetchall()
    teachers = conn.execute("SELECT * FROM teachers WHERE username != 'admin' ORDER BY id DESC").fetchall()
    assignments = conn.execute("""
        SELECT ta.id, t.name AS teacher_name, c.name AS course_name, s.name AS subject_name
        FROM teacher_assignments ta
        JOIN teachers t ON ta.teacher_id = t.id
        JOIN courses c ON ta.course_id = c.id
        JOIN subjects s ON ta.subject_id = s.id
        ORDER BY ta.id DESC
    """).fetchall()

    # 5. 6 Семестр боюнча статистика
    quran_semester_stats = []
    semester_goals = {1: 3, 2: 8, 3: 13, 4: 21, 5: 30, 6: 30}
    for semester in range(1, 7):
        completed = conn.execute(
            "SELECT COUNT(DISTINCT student_id || '-' || juz_number) AS count FROM quran_progress WHERE semester = ? AND status = ?",
            (semester, STATUS_MEMORIZED)
        ).fetchone()["count"]
        goal = semester_goals[semester]
        percent = round(completed / goal * 100, 1) if goal > 0 else 0
        quran_semester_stats.append({
            "semester": semester,
            "goal": goal,
            "completed": completed,
            "percent": min(percent, 100)
        })

    conn.close()
    
    # 6. Бардык маалыматтарды шаблонго жиберүү
    return render_template(
        "admin.html",
        total_teachers=total_teachers,
        total_students=total_students,
        total_parents=total_parents,
        total_courses=total_courses,
        total_subjects=total_subjects,
        total_assignments=total_assignments,
        total_attendance=total_attendance,
        completed_juz=completed_juz,
        quran_finished_students=quran_finished_students,
        finish_percent=finish_percent,
        present_count=present_count,
        absent_count=absent_count,
        attendance_percent=attendance_percent,
        courses=courses,
        teachers=teachers,
        assignments=assignments,
        quran_semester_stats=quran_semester_stats
    )

# =========================
# ADD STUDENT
# =========================
@app.route("/add_student", methods=["GET", "POST"])
def add_student():
    if session.get("role") not in ["admin", "teacher"]:
        return redirect(url_for("login"))

    conn = get_db()
    courses = conn.execute("SELECT * FROM courses ORDER BY id").fetchall()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        birth_year_raw = request.form.get("birth_year", "").strip()
        course_id = request.form.get("course_id", type=int)
        parent_name = request.form.get("parent_name", "").strip()
        phone = request.form.get("phone", "").strip()

        if not name or not parent_name or not phone or course_id is None:
            conn.close()
            return render_template("add_student.html", courses=courses, error="Аты-жөнү, курс, ата-эненин аты жана телефон толтурулушу керек.")

        birth_year = None
        if birth_year_raw:
            try:
                birth_year = int(birth_year_raw)
            except ValueError:
                conn.close()
                return render_template("add_student.html", courses=courses, error="Туулган жылы туура эмес.")

            if not 1950 <= birth_year <= date.today().year + 1:
                conn.close()
                return render_template("add_student.html", courses=courses, error="Туулган жылы 1950дөн азыркы жылга чейин болушу керек.")

        course = conn.execute("SELECT id FROM courses WHERE id = ?", (course_id,)).fetchone()
        if not course:
            conn.close()
            return render_template("add_student.html", courses=courses, error="Тандалган курс табылган жок.")

        conn.execute("""
            INSERT INTO students (name, birth_year, course_id, parent_name, phone)
            VALUES (?, ?, ?, ?, ?)
        """, (name, birth_year, course_id, parent_name, phone))
        conn.commit()
        conn.close()
        return redirect(url_for("students"))

    conn.close()
    return render_template("add_student.html", courses=courses)


# =========================
# STUDENTS
# =========================
@app.route("/students")
def students():
    if session.get("role") not in ["admin", "teacher"]:
        return redirect(url_for("login"))

    selected_group = request.args.get("group")
    conn = get_db()

    if selected_group:
        students_list = conn.execute("""
            SELECT st.*, c.name AS course_name
            FROM students st
            JOIN courses c ON st.course_id = c.id
            WHERE c.name = ?
            ORDER BY st.id DESC
        """, (selected_group,)).fetchall()
    else:
        students_list = conn.execute("""
            SELECT st.*, c.name AS course_name
            FROM students st
            JOIN courses c ON st.course_id = c.id
            ORDER BY st.id DESC
        """).fetchall()

    courses = conn.execute("SELECT * FROM courses ORDER BY id").fetchall()
    conn.close()

    return render_template("students.html", students=students_list, courses=courses, selected_group=selected_group)


# =========================
# TEACHER
# =========================
@app.route("/teacher")
def teacher():
    if session.get("role") != "teacher":
        return redirect(url_for("login"))

    teacher_id = session.get("user_id")
    conn = get_db()
    teacher_info = conn.execute("SELECT * FROM teachers WHERE id = ?", (teacher_id,)).fetchone()
    assignments = conn.execute("""
        SELECT ta.id, c.name AS course_name, s.name AS subject_name
        FROM teacher_assignments ta
        JOIN courses c ON ta.course_id = c.id
        JOIN subjects s ON ta.subject_id = s.id
        WHERE ta.teacher_id = ?
        ORDER BY ta.id
    """, (teacher_id,)).fetchall()
    conn.close()

    return render_template("teacher.html", teacher=teacher_info, assignments=assignments)


@app.route("/teacher-students/<int:assignment_id>")
def teacher_students(assignment_id):
    if session.get("role") not in ["admin", "teacher"]:
        return redirect(url_for("login"))

    conn = get_db()
    assignment = conn.execute("""
        SELECT
            ta.id,
            ta.teacher_id,
            ta.course_id,
            ta.subject_id,
            t.name AS teacher_name,
            c.name AS course_name,
            s.name AS subject_name
        FROM teacher_assignments ta
        JOIN teachers t ON ta.teacher_id = t.id
        JOIN courses c ON ta.course_id = c.id
        JOIN subjects s ON ta.subject_id = s.id
        WHERE ta.id = ?
    """, (assignment_id,)).fetchone()

    if not assignment:
        conn.close()
        return redirect(url_for("teacher"))

    if session.get("role") == "teacher" and assignment["teacher_id"] != session.get("user_id"):
        conn.close()
        return redirect(url_for("teacher"))

    students = conn.execute("""
        SELECT st.*, c.name AS course_name
        FROM students st
        JOIN courses c ON st.course_id = c.id
        WHERE st.course_id = ?
        ORDER BY st.name
    """, (assignment["course_id"],)).fetchall()

    conn.close()

    return render_template(
        "teacher_students.html",
        assignment=assignment,
        students=students,
        teacher_name=assignment["teacher_name"]
    )


@app.route("/teachers")
def teachers_list():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    try:
        teachers = conn.execute("""
            SELECT id, name, username
            FROM teachers
            WHERE username != 'admin'
            ORDER BY name
        """).fetchall()
        return render_template("teachers_list.html", teachers=teachers)
    finally:
        conn.close()


# =========================
# ADD TEACHER
# =========================
@app.route("/add-teacher", methods=["GET", "POST"])
def add_teacher():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not name or not username or not password:
            return render_template("add_teacher.html", error="Бардык талааларды толтуруңуз")

        conn = get_db()
        try:
            conn.execute("INSERT INTO teachers (name, username, password) VALUES (?, ?, ?)", (name, username, password))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template("add_teacher.html", error="Бул логин мурда катталган")

        conn.close()
        return redirect(url_for("admin"))

    return render_template("add_teacher.html")


# =========================
# ASSIGN TEACHER
# =========================
@app.route("/assign-teacher", methods=["GET", "POST"])
def assign_teacher():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    teachers = conn.execute("SELECT * FROM teachers WHERE username != 'admin' ORDER BY name").fetchall()
    courses = conn.execute("SELECT * FROM courses ORDER BY id").fetchall()
    subjects = conn.execute("SELECT * FROM subjects ORDER BY id").fetchall()

    if request.method == "POST":
        teacher_id = request.form.get("teacher_id", type=int)
        course_id = request.form.get("course_id", type=int)
        subject_id = request.form.get("subject_id", type=int)

        existing = conn.execute("""
            SELECT id FROM teacher_assignments
            WHERE teacher_id = ? AND course_id = ? AND subject_id = ?
        """, (teacher_id, course_id, subject_id)).fetchone()

        if existing:
            conn.close()
            return render_template("assign_teacher.html", teachers=teachers, courses=courses, subjects=subjects, error="Бул сабак мурда бекитилген")

        conn.execute("INSERT INTO teacher_assignments (teacher_id, course_id, subject_id) VALUES (?, ?, ?)", (teacher_id, course_id, subject_id))
        conn.commit()
        conn.close()
        return redirect(url_for("admin"))

    conn.close()
    return render_template("assign_teacher.html", teachers=teachers, courses=courses, subjects=subjects)


@app.route("/assigned-lessons")
def assigned_lessons():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    try:
        assignments = conn.execute("""
            SELECT
                ta.id,
                COALESCE(t.name, '—') AS teacher_name,
                COALESCE(c.name, '—') AS course_name,
                COALESCE(s.name, '—') AS subject_name
            FROM teacher_assignments ta
            LEFT JOIN teachers t ON ta.teacher_id = t.id
            LEFT JOIN courses c ON ta.course_id = c.id
            LEFT JOIN subjects s ON ta.subject_id = s.id
            ORDER BY c.name, t.name, s.name
        """).fetchall()
        return render_template("assigned_lessons.html", assignments=assignments)
    finally:
        conn.close()


# =========================
# EDIT ASSIGNMENT
# =========================
@app.route("/edit-assignment/<int:assignment_id>", methods=["GET", "POST"])
def edit_assignment(assignment_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    assignment = conn.execute("SELECT * FROM teacher_assignments WHERE id = ?", (assignment_id,)).fetchone()

    if not assignment:
        conn.close()
        return redirect(url_for("admin"))

    teachers = conn.execute("SELECT * FROM teachers WHERE username != 'admin' ORDER BY name").fetchall()
    courses = conn.execute("SELECT * FROM courses ORDER BY id").fetchall()
    subjects = conn.execute("SELECT * FROM subjects ORDER BY id").fetchall()

    if request.method == "POST":
        teacher_id = request.form.get("teacher_id", type=int)
        course_id = request.form.get("course_id", type=int)
        subject_id = request.form.get("subject_id", type=int)

        conn.execute("""
            UPDATE teacher_assignments
            SET teacher_id = ?, course_id = ?, subject_id = ?
            WHERE id = ?
        """, (teacher_id, course_id, subject_id, assignment_id))
        conn.commit()
        conn.close()
        return redirect(url_for("admin"))

    conn.close()
    return render_template("edit_assignment.html", assignment=assignment, teachers=teachers, courses=courses, subjects=subjects)


# =========================
# DELETE ASSIGNMENT
# =========================
@app.route("/delete-assignment/<int:assignment_id>")
def delete_assignment(assignment_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    conn.execute("DELETE FROM student_attendance WHERE assignment_id = ?", (assignment_id,))
    conn.execute("DELETE FROM lessons WHERE assignment_id = ?", (assignment_id,))
    conn.execute("DELETE FROM teacher_assignments WHERE id = ?", (assignment_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


# =========================
# QURAN SECTIONS
# =========================
@app.route("/quran-sections")
def quran_sections():
    if session.get("role") not in ["admin", "teacher"]:
        return redirect(url_for("login"))
    
    conn = get_db()
    
    # 1. 30 жүздүн тизмеси (маалыматтары)
    sections = [
        {"juz_number": 1, "section_name": "1-жүз (Алиф Лам Мим)", "start_reference": "Аль-Фатиха 1", "end_reference": "Аль-Бакара 141"},
        {"juz_number": 2, "section_name": "2-жүз", "start_reference": "Аль-Бакара 142", "end_reference": "Аль-Бакара 252"},
        {"juz_number": 3, "section_name": "3-жүз", "start_reference": "Аль-Бакара 253", "end_reference": "Али Имран 92"},
        {"juz_number": 4, "section_name": "4-жүз", "start_reference": "Али Имран 93", "end_reference": "Ан-Ниса 23"},
        {"juz_number": 5, "section_name": "5-жүз", "start_reference": "Ан-Ниса 24", "end_reference": "Ан-Ниса 147"},
        {"juz_number": 6, "section_name": "6-жүз", "start_reference": "Ан-Ниса 148", "end_reference": "Аль-Маида 81"},
        {"juz_number": 7, "section_name": "7-жүз", "start_reference": "Аль-Маида 82", "end_reference": "Аль-Анъам 110"},
        {"juz_number": 8, "section_name": "8-жүз", "start_reference": "Аль-Анъам 111", "end_reference": "Аль-Араф 87"},
        {"juz_number": 9, "section_name": "9-жүз", "start_reference": "Аль-Араф 88", "end_reference": "Аль-Анфал 40"},
        {"juz_number": 10, "section_name": "10-жүз", "start_reference": "Аль-Анфал 41", "end_reference": "Ат-Тавба 92"},
        {"juz_number": 11, "section_name": "11-жүз", "start_reference": "Ат-Тавба 93", "end_reference": "Худ 5"},
        {"juz_number": 12, "section_name": "12-жүз", "start_reference": "Худ 6", "end_reference": "Юсуф 52"},
        {"juz_number": 13, "section_name": "13-жүз", "start_reference": "Юсуф 53", "end_reference": "Ибрахим 52"},
        {"juz_number": 14, "section_name": "14-жүз", "start_reference": "Аль-Хижр 1", "end_reference": "Ан-Нахл 128"},
        {"juz_number": 15, "section_name": "15-жүз", "start_reference": "Аль-Исра 1", "end_reference": "Аль-Кахф 74"},
        {"juz_number": 16, "section_name": "16-жүз", "start_reference": "Аль-Кахф 75", "end_reference": "Та Ха 135"},
        {"juz_number": 17, "section_name": "17-жүз", "start_reference": "Аль-Анбия 1", "end_reference": "Аль-Хажж 78"},
        {"juz_number": 18, "section_name": "18-жүз", "start_reference": "Аль-Муминун 1", "end_reference": "Аль-Фуркан 20"},
        {"juz_number": 19, "section_name": "19-жүз", "start_reference": "Аль-Фуркан 21", "end_reference": "Ан-Намль 55"},
        {"juz_number": 20, "section_name": "20-жүз", "start_reference": "Ан-Намль 56", "end_reference": "Аль-Анкабут 45"},
        {"juz_number": 21, "section_name": "21-жүз", "start_reference": "Аль-Анкабут 46", "end_reference": "Аль-Ахзаб 30"},
        {"juz_number": 22, "section_name": "22-жүз", "start_reference": "Аль-Ахзаб 31", "end_reference": "Ясин 27"},
        {"juz_number": 23, "section_name": "23-жүз", "start_reference": "Ясин 28", "end_reference": "Аз-Зумар 31"},
        {"juz_number": 24, "section_name": "24-жүз", "start_reference": "Аз-Зумар 32", "end_reference": "Фуссилат 46"},
        {"juz_number": 25, "section_name": "25-жүз", "start_reference": "Фуссилат 47", "end_reference": "Аль-Жасия 37"},
        {"juz_number": 26, "section_name": "26-жүз", "start_reference": "Аль-Ахкаф 1", "end_reference": "Ад-Зарият 30"},
        {"juz_number": 27, "section_name": "27-жүз", "start_reference": "Ад-Зарият 31", "end_reference": "Аль-Хадид 29"},
        {"juz_number": 28, "section_name": "28-жүз", "start_reference": "Аль-Мужадила 1", "end_reference": "Тахрим 12"},
        {"juz_number": 29, "section_name": "29-жүз", "start_reference": "Аль-Мулк 1", "end_reference": "Мурсалат 50"},
        {"juz_number": 30, "section_name": "30-жүз", "start_reference": "Наба 1", "end_reference": "Нас 6"}
    ]
    
    # 2. Студенттерди курстары менен кошо алуу жана алардын жаттаган жуздерүн эсептөө
    students = conn.execute("""
        SELECT s.id, s.name, c.name AS course_name,
               (SELECT COUNT(DISTINCT juz_number) FROM quran_progress qp WHERE qp.student_id = s.id AND qp.status = ?) AS memorized_count
        FROM students s
        LEFT JOIN courses c ON s.course_id = c.id
        ORDER BY c.id, s.name
    """, (STATUS_MEMORIZED,)).fetchall()
    
    # 3. Системага жалпы киргизилген (жатталган) жуздердин санын эсептөө
    total_memorized_juza = conn.execute("""
        SELECT COUNT(DISTINCT juz_number) FROM quran_progress WHERE status = ?
    """, (STATUS_MEMORIZED,)).fetchone()[0] or 0
    
    conn.close()
    
    return render_template("quran_sections.html", 
                           sections=sections, 
                           students=students, 
                           total_memorized_juza=total_memorized_juza)
@app.route("/surahs-list")
def surahs_list():
    if session.get("role") not in ["admin", "teacher"]:
        return redirect(url_for("login"))
    
    surahs = [
        {"id": 1, "name": "Аль-Фатиха", "arabic_name": "الفاتحة", "english_name": "Al-Fatihah", "verses_count": 7, "revelation_type": "Мекке"},
        {"id": 2, "name": "Аль-Бакара", "arabic_name": "البقرة", "english_name": "Al-Baqarah", "verses_count": 286, "revelation_type": "Медина"},
        {"id": 3, "name": "Али Имран", "arabic_name": "آل عمران", "english_name": "Ali 'Imran", "verses_count": 200, "revelation_type": "Медина"},
        {"id": 4, "name": "Ан-Ниса", "arabic_name": "النساء", "english_name": "An-Nisa'", "verses_count": 176, "revelation_type": "Медина"},
        {"id": 5, "name": "Аль-Маида", "arabic_name": "المائدة", "english_name": "Al-Ma'idah", "verses_count": 120, "revelation_type": "Медина"},
        {"id": 6, "name": "Аль-Анъам", "arabic_name": "الأنعام", "english_name": "Al-An'am", "verses_count": 165, "revelation_type": "Мекке"},
        {"id": 7, "name": "Аль-Араф", "arabic_name": "الأعراف", "english_name": "Al-A'raf", "verses_count": 206, "revelation_type": "Мекке"},
        {"id": 8, "name": "Аль-Анфал", "arabic_name": "الأنفال", "english_name": "Al-Anfal", "verses_count": 75, "revelation_type": "Медина"},
        {"id": 9, "name": "Ат-Тавба", "arabic_name": "التوبة", "english_name": "At-Tawbah", "verses_count": 129, "revelation_type": "Медина"},
        {"id": 10, "name": "Юнус", "arabic_name": "يونس", "english_name": "Yunus", "verses_count": 109, "revelation_type": "Мекке"},
        {"id": 11, "name": "Худ", "arabic_name": "هود", "english_name": "Hud", "verses_count": 123, "revelation_type": "Мекке"},
        {"id": 12, "name": "Юсуф", "arabic_name": "يوسف", "english_name": "Yusuf", "verses_count": 111, "revelation_type": "Мекке"},
        {"id": 13, "name": "Ар-Рад", "arabic_name": "الرعد", "english_name": "Ar-Ra'd", "verses_count": 43, "revelation_type": "Медина"},
        {"id": 14, "name": "Ибрахим", "arabic_name": "إبراهيم", "english_name": "Ibrahim", "verses_count": 52, "revelation_type": "Мекке"},
        {"id": 15, "name": "Аль-Хижр", "arabic_name": "الحجر", "english_name": "Al-Hijr", "verses_count": 99, "revelation_type": "Мекке"},
        {"id": 16, "name": "Ан-Нахл", "arabic_name": "النحل", "english_name": "An-Nahl", "verses_count": 128, "revelation_type": "Мекке"},
        {"id": 17, "name": "Аль-Исра", "arabic_name": "الإسراء", "english_name": "Al-Isra'", "verses_count": 111, "revelation_type": "Мекке"},
        {"id": 18, "name": "Аль-Кахф", "arabic_name": "الكهف", "english_name": "Al-Kahf", "verses_count": 110, "revelation_type": "Мекке"},
        {"id": 19, "name": "Марьям", "arabic_name": "مريم", "english_name": "Maryam", "verses_count": 98, "revelation_type": "Мекке"},
        {"id": 20, "name": "Та Ха", "arabic_name": "طه", "english_name": "Ta-Ha", "verses_count": 135, "revelation_type": "Мекке"},
        {"id": 21, "name": "Аль-Анбия", "arabic_name": "الأنبياء", "english_name": "Al-Anbiya'", "verses_count": 112, "revelation_type": "Мекке"},
        {"id": 22, "name": "Аль-Хажж", "arabic_name": "الحج", "english_name": "Al-Hajj", "verses_count": 78, "revelation_type": "Медина"},
        {"id": 23, "name": "Аль-Муминун", "arabic_name": "المؤمنون", "english_name": "Al-Mu'minun", "verses_count": 118, "revelation_type": "Мекке"},
        {"id": 24, "name": "Ан-Нур", "arabic_name": "النور", "english_name": "An-Nur", "verses_count": 64, "revelation_type": "Медина"},
        {"id": 25, "name": "Аль-Фуркан", "arabic_name": "الفرقان", "english_name": "Al-Furqan", "verses_count": 77, "revelation_type": "Мекке"},
        {"id": 26, "name": "Аш-Шуара", "arabic_name": "الشعراء", "english_name": "Ash-Shu'ara'", "verses_count": 227, "revelation_type": "Мекке"},
        {"id": 27, "name": "Ан-Намль", "arabic_name": "النمل", "english_name": "An-Naml", "verses_count": 93, "revelation_type": "Мекке"},
        {"id": 28, "name": "Аль-Касас", "arabic_name": "القصص", "english_name": "Al-Qasas", "verses_count": 88, "revelation_type": "Мекке"},
        {"id": 29, "name": "Аль-Анкабут", "arabic_name": "العنكبوت", "english_name": "Al-'Ankabut", "verses_count": 69, "revelation_type": "Мекке"},
        {"id": 30, "name": "Ар-Рум", "arabic_name": "الروم", "english_name": "Ar-Rum", "verses_count": 60, "revelation_type": "Мекке"},
        {"id": 31, "name": "Лукман", "arabic_name": "لقمان", "english_name": "Luqman", "verses_count": 34, "revelation_type": "Мекке"},
        {"id": 32, "name": "Ас-Сажда", "arabic_name": "السجدة", "english_name": "As-Sajdah", "verses_count": 30, "revelation_type": "Мекке"},
        {"id": 33, "name": "Аль-Ахзаб", "arabic_name": "الأحزاب", "english_name": "Al-Ahzab", "verses_count": 73, "revelation_type": "Медина"},
        {"id": 34, "name": "Саба", "arabic_name": "سبأ", "english_name": "Saba'", "verses_count": 54, "revelation_type": "Мекке"},
        {"id": 35, "name": "Фатыр", "arabic_name": "فاطر", "english_name": "Fatir", "verses_count": 45, "revelation_type": "Мекке"},
        {"id": 36, "name": "Ясин", "arabic_name": "يس", "english_name": "Ya-Sin", "verses_count": 83, "revelation_type": "Мекке"},
        {"id": 37, "name": "Ас-Саффат", "arabic_name": "الصافات", "english_name": "As-Saffat", "verses_count": 182, "revelation_type": "Мекке"},
        {"id": 38, "name": "Сад", "arabic_name": "ص", "english_name": "Sad", "verses_count": 88, "revelation_type": "Мекке"},
        {"id": 39, "name": "Аз-Зумар", "arabic_name": "الزمر", "english_name": "Az-Zumar", "verses_count": 75, "revelation_type": "Мекке"},
        {"id": 40, "name": "Гафир", "arabic_name": "غافر", "english_name": "Ghafir", "verses_count": 85, "revelation_type": "Мекке"},
        {"id": 41, "name": "Фуссилат", "arabic_name": "فصلت", "english_name": "Fussilat", "verses_count": 54, "revelation_type": "Мекке"},
        {"id": 42, "name": "Аш-Шура", "arabic_name": "الشورى", "english_name": "Ash-Shura", "verses_count": 53, "revelation_type": "Мекке"},
        {"id": 43, "name": "Аз-Зухруф", "arabic_name": "الزخرف", "english_name": "Az-Zukhruf", "verses_count": 89, "revelation_type": "Мекке"},
        {"id": 44, "name": "Ад-Духан", "arabic_name": "الدخان", "english_name": "Ad-Dukhan", "verses_count": 59, "revelation_type": "Мекке"},
        {"id": 45, "name": "Аль-Жасия", "arabic_name": "الجاثية", "english_name": "Al-Jathiyah", "verses_count": 37, "revelation_type": "Мекке"},
        {"id": 46, "name": "Аль-Ахкаф", "arabic_name": "الأحقاف", "english_name": "Al-Ahqaf", "verses_count": 35, "revelation_type": "Мекке"},
        {"id": 47, "name": "Мухаммад", "arabic_name": "محمد", "english_name": "Muhammad", "verses_count": 38, "revelation_type": "Медина"},
        {"id": 48, "name": "Аль-Фатх", "arabic_name": "الفتح", "english_name": "Al-Fath", "verses_count": 29, "revelation_type": "Медина"},
        {"id": 49, "name": "Аль-Хужурат", "arabic_name": "الحجرات", "english_name": "Al-Hujurat", "verses_count": 18, "revelation_type": "Медина"},
        {"id": 50, "name": "Каф", "arabic_name": "ق", "english_name": "Qaf", "verses_count": 45, "revelation_type": "Мекке"},
        {"id": 51, "name": "Зарият", "arabic_name": "الذاريات", "english_name": "Adh-Dhariyat", "verses_count": 60, "revelation_type": "Мекке"},
        {"id": 52, "name": "Тур", "arabic_name": "الطور", "english_name": "At-Tur", "verses_count": 49, "revelation_type": "Мекке"},
        {"id": 53, "name": "Нажм", "arabic_name": "النجم", "english_name": "An-Najm", "verses_count": 62, "revelation_type": "Мекке"},
        {"id": 54, "name": "Камар", "arabic_name": "القمر", "english_name": "Al-Qamar", "verses_count": 55, "revelation_type": "Мекке"},
        {"id": 55, "name": "Ар-Рахман", "arabic_name": "الرحمن", "english_name": "Ar-Rahman", "verses_count": 78, "revelation_type": "Медина"},
        {"id": 56, "name": "Вакыя", "arabic_name": "واقعة", "english_name": "Al-Waqi'ah", "verses_count": 96, "revelation_type": "Мекке"},
        {"id": 57, "name": "Хадид", "arabic_name": "الحديد", "english_name": "Al-Hadid", "verses_count": 29, "revelation_type": "Медина"},
        {"id": 58, "name": "Мужадила", "arabic_name": "المجادلة", "english_name": "Al-Mujadila", "verses_count": 22, "revelation_type": "Медина"},
        {"id": 59, "name": "Хашр", "arabic_name": "الحشر", "english_name": "Al-Hashr", "verses_count": 24, "revelation_type": "Медина"},
        {"id": 60, "name": "Мумтахана", "arabic_name": "الممتحنة", "english_name": "Al-Mumtahanah", "verses_count": 13, "revelation_type": "Медина"},
        {"id": 61, "name": "Сафф", "arabic_name": "الصف", "english_name": "As-Saff", "verses_count": 14, "revelation_type": "Медина"},
        {"id": 62, "name": "Жума", "arabic_name": "الجمعة", "english_name": "Al-Jumu'ah", "verses_count": 11, "revelation_type": "Медина"},
        {"id": 63, "name": "Мунафикун", "arabic_name": "المنافقون", "english_name": "Al-Munafiqun", "verses_count": 11, "revelation_type": "Медина"},
        {"id": 64, "name": "Тагабун", "arabic_name": "التغابن", "english_name": "At-Taghabun", "verses_count": 18, "revelation_type": "Медина"},
        {"id": 65, "name": "Талак", "arabic_name": "الطلاق", "english_name": "At-Talaq", "verses_count": 12, "revelation_type": "Медина"},
        {"id": 66, "name": "Тахрим", "arabic_name": "التحريم", "english_name": "At-Tahrim", "verses_count": 12, "revelation_type": "Медина"},
        {"id": 67, "name": "Мулк", "arabic_name": "الملك", "english_name": "Al-Mulk", "verses_count": 30, "revelation_type": "Мекке"},
        {"id": 68, "name": "Калам", "arabic_name": "القلم", "english_name": "Al-Qalam", "verses_count": 52, "revelation_type": "Мекке"},
        {"id": 69, "name": "Хакка", "arabic_name": "الحاقة", "english_name": "Al-Haqqah", "verses_count": 52, "revelation_type": "Мекке"},
        {"id": 70, "name": "Маариж", "arabic_name": "المعارج", "english_name": "Al-Ma'arij", "verses_count": 44, "revelation_type": "Мекке"},
        {"id": 71, "name": "Нух", "arabic_name": "نوح", "english_name": "Nuh", "verses_count": 28, "revelation_type": "Мекке"},
        {"id": 72, "name": "Жин", "arabic_name": "الجن", "english_name": "Al-Jinn", "verses_count": 28, "revelation_type": "Мекке"},
        {"id": 73, "name": "Муззаммил", "arabic_name": "المزمل", "english_name": "Al-Muzzammil", "verses_count": 20, "revelation_type": "Мекке"},
        {"id": 74, "name": "Муддассир", "arabic_name": "المدثر", "english_name": "Al-Muddaththir", "verses_count": 56, "revelation_type": "Мекке"},
        {"id": 75, "name": "Кыямат", "arabic_name": "القيامة", "english_name": "Al-Qiyamah", "verses_count": 40, "revelation_type": "Мекке"},
        {"id": 76, "name": "Инсан", "arabic_name": "الانسان", "english_name": "Al-Insan", "verses_count": 31, "revelation_type": "Медина"},
        {"id": 77, "name": "Мурсалат", "arabic_name": "المرسلات", "english_name": "Al-Mursalat", "verses_count": 50, "revelation_type": "Мекке"},
        {"id": 78, "name": "Наба", "arabic_name": "النبأ", "english_name": "An-Naba'", "verses_count": 40, "revelation_type": "Мекке"},
        {"id": 79, "name": "Назиат", "arabic_name": "النازعات", "english_name": "An-Nazi'at", "verses_count": 46, "revelation_type": "Мекке"},
        {"id": 80, "name": "Абаса", "arabic_name": "عبس", "english_name": "'Abasa", "verses_count": 42, "revelation_type": "Мекке"},
        {"id": 81, "name": "Таквир", "arabic_name": "التكوير", "english_name": "At-Takwir", "verses_count": 29, "revelation_type": "Мекке"},
        {"id": 82, "name": "Инфитар", "arabic_name": "الانفطار", "english_name": "Al-Infitar", "verses_count": 19, "revelation_type": "Мекке"},
        {"id": 83, "name": "Мутаффифин", "arabic_name": "المطففين", "english_name": "Al-Mutaffifin", "verses_count": 36, "revelation_type": "Мекке"},
        {"id": 84, "name": "Иншикак", "arabic_name": "الانشقاق", "english_name": "Al-Inshiqaq", "verses_count": 25, "revelation_type": "Мекке"},
        {"id": 85, "name": "Буруж", "arabic_name": "البروج", "english_name": "Al-Buruj", "verses_count": 22, "revelation_type": "Мекке"},
        {"id": 86, "name": "Тарик", "arabic_name": "الطارق", "english_name": "At-Tariq", "verses_count": 17, "revelation_type": "Мекке"},
        {"id": 87, "name": "Ала", "arabic_name": "الأعلى", "english_name": "Al-A'la", "verses_count": 19, "revelation_type": "Мекке"},
        {"id": 88, "name": "Гашия", "arabic_name": "الغاشية", "english_name": "Al-Ghashiyah", "verses_count": 26, "revelation_type": "Мекке"},
        {"id": 89, "name": "Фажр", "arabic_name": "الفجر", "english_name": "Al-Fajr", "verses_count": 30, "revelation_type": "Мекке"},
        {"id": 90, "name": "Балад", "arabic_name": "البلد", "english_name": "Al-Balad", "verses_count": 20, "revelation_type": "Мекке"},
        {"id": 91, "name": "Шамс", "arabic_name": "الشمس", "english_name": "Ash-Shams", "verses_count": 15, "revelation_type": "Мекке"},
        {"id": 92, "name": "Лайл", "arabic_name": "الليل", "english_name": "Al-Lail", "verses_count": 21, "revelation_type": "Мекке"},
        {"id": 93, "name": "Духа", "arabic_name": "الضحى", "english_name": "Ad-Duha", "verses_count": 11, "revelation_type": "Мекке"},
        {"id": 94, "name": "Шарх", "arabic_name": "الشرح", "english_name": "Ash-Sharh", "verses_count": 8, "revelation_type": "Мекке"},
        {"id": 95, "name": "Тин", "arabic_name": "التين", "english_name": "At-Tin", "verses_count": 8, "revelation_type": "Мекке"},
        {"id": 96, "name": "Алак", "arabic_name": "العلق", "english_name": "Al-'Alaq", "verses_count": 19, "revelation_type": "Мекке"},
        {"id": 97, "name": "Кадр", "arabic_name": "القدر", "english_name": "Al-Qadr", "verses_count": 5, "revelation_type": "Мекке"},
        {"id": 98, "name": "Байина", "arabic_name": "البينة", "english_name": "Al-Bayyinah", "verses_count": 8, "revelation_type": "Медина"},
        {"id": 99, "name": "Залзала", "arabic_name": "الزلزلة", "english_name": "Az-Zalzalah", "verses_count": 8, "revelation_type": "Медина"},
        {"id": 100, "name": "Адият", "arabic_name": "العاديات", "english_name": "Al-'Adiyat", "verses_count": 11, "revelation_type": "Мекке"},
        {"id": 101, "name": "Кариа", "arabic_name": "القارعة", "english_name": "Al-Qari'ah", "verses_count": 11, "revelation_type": "Мекке"},
        {"id": 102, "name": "Такасур", "arabic_name": "التكاثر", "english_name": "At-Takathur", "verses_count": 8, "revelation_type": "Мекке"},
        {"id": 103, "name": "Аср", "arabic_name": "العصر", "english_name": "Al-'Asr", "verses_count": 3, "revelation_type": "Мекке"},
        {"id": 104, "name": "Хумаза", "arabic_name": "الهمزة", "english_name": "Al-Humazah", "verses_count": 9, "revelation_type": "Мекке"},
        {"id": 105, "name": "Филь", "arabic_name": "الفيل", "english_name": "Al-Fil", "verses_count": 5, "revelation_type": "Мекке"},
        {"id": 106, "name": "Курайш", "arabic_name": "قريش", "english_name": "Quraysh", "verses_count": 4, "revelation_type": "Мекке"},
        {"id": 107, "name": "Маун", "arabic_name": "الماعون", "english_name": "Al-Ma'un", "verses_count": 7, "revelation_type": "Мекке"},
        {"id": 108, "name": "Кавсар", "arabic_name": "الكوثر", "english_name": "Al-Kawthar", "verses_count": 3, "revelation_type": "Мекке"},
        {"id": 109, "name": "Кафирун", "arabic_name": "الكافرون", "english_name": "Al-Kafirun", "verses_count": 6, "revelation_type": "Мекке"},
        {"id": 110, "name": "Наср", "arabic_name": "النصر", "english_name": "An-Nasr", "verses_count": 3, "revelation_type": "Медина"},
        {"id": 111, "name": "Масад", "arabic_name": "المسد", "english_name": "Al-Masad", "verses_count": 5, "revelation_type": "Мекке"},
        {"id": 112, "name": "Ихлас", "arabic_name": "الإخلاص", "english_name": "Al-Ikhlas", "verses_count": 4, "revelation_type": "Мекке"},
        {"id": 113, "name": "Фаляк", "arabic_name": "الفلق", "english_name": "Al-Falaq", "verses_count": 5, "revelation_type": "Мекке"},
        {"id": 114, "name": "Нас", "arabic_name": "الناس", "english_name": "An-Nas", "verses_count": 6, "revelation_type": "Мекке"}
    ]
    
    return render_template("surahs_list.html", surahs=surahs)


# =========================
# LESSON PAGE
# =========================
@app.route("/lesson/<int:assignment_id>")
def lesson_page(assignment_id):
    if session.get("role") not in ["admin", "teacher"]:
        return redirect(url_for("login"))

    selected_semester = request.args.get("semester", 1, type=int)
    if selected_semester < 1 or selected_semester > 6:
        selected_semester = 1

    conn = get_db()
    assignment = conn.execute("""
        SELECT ta.*, t.name AS teacher_name, c.name AS course_name, s.name AS subject_name
        FROM teacher_assignments ta
        JOIN teachers t ON ta.teacher_id = t.id
        JOIN courses c ON ta.course_id = c.id
        JOIN subjects s ON ta.subject_id = s.id
        WHERE ta.id = ?
    """, (assignment_id,)).fetchone()

    if not assignment:
        conn.close()
        return redirect(url_for("admin"))

    lessons = conn.execute("""
        SELECT * FROM lessons
        WHERE assignment_id = ? AND semester = ?
        ORDER BY lesson_number
    """, (assignment_id, selected_semester)).fetchall()

    conn.close()
    return render_template("lesson.html", assignment=assignment, lessons=lessons, selected_semester=selected_semester)


# =========================
# PARENT CABINET
# =========================
@app.route("/parent")
def parent():
    if session.get("role") != "parent":
        return redirect(url_for("login"))

    student_id = session.get("student_id")
    conn = get_db()
    
    # 1. Студенттин маалыматы
    student = conn.execute("""
        SELECT st.*, c.name AS course_name, c.id AS course_id
        FROM students st
        JOIN courses c ON st.course_id = c.id
        WHERE st.id = ?
    """, (student_id,)).fetchone()

    # 2. Куран жаттоо прогресси
    quran_progress = conn.execute("""
        SELECT qp.*, t.name AS teacher_name
        FROM quran_progress qp
        LEFT JOIN teachers t ON t.id = qp.teacher_id
        WHERE qp.student_id = ?
        ORDER BY qp.id DESC
    """, (student_id,)).fetchall()

    # 3. Башка сабактардын жыйынтыктары (lessons аркылуу)
    lessons = []
    if student and student["course_id"]:
        # Студенттин курсуна дайындалган мугалимдин сабактарын алабыз
        lessons = conn.execute("""
            SELECT l.* FROM lessons l
            JOIN teacher_assignments ta ON ta.id = l.assignment_id
            WHERE ta.course_id = ?
            ORDER BY l.lesson_date DESC
        """, (student["course_id"],)).fetchall()

    # 4. Төлөмдөр (Эгер payments таблицасы бар болсо)
    payments = []
    try:
        payments = conn.execute("""
            SELECT * FROM payments WHERE student_id = ? ORDER BY id DESC
        """, (student_id,)).fetchall()
    except Exception:
        pass  # Эгер payments таблицасы али түзүлө элек болсо ката бербейт

    conn.close()

    return render_template(
        "parent.html",
        student=student,
        quran_progress=quran_progress,
        lessons=lessons,
        payments=payments
    )
# =========================
# PARENTS LIST
# =========================
@app.route("/parents")
def parents():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    parents_list = conn.execute("""
        SELECT p.*, st.name AS student_name
        FROM parents p
        LEFT JOIN students st ON p.student_id = st.id
        ORDER BY p.id DESC
    """).fetchall()
    conn.close()

    return render_template("parents.html", parents=parents_list)


# =========================
# EDIT STUDENT
# =========================
@app.route("/edit-student/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):
    if session.get("role") not in ["admin", "teacher"]:
        return redirect(url_for("login"))

    conn = get_db()
    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()

    if not student:
        conn.close()
        return redirect(url_for("students"))

    courses = conn.execute("SELECT * FROM courses ORDER BY id").fetchall()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        birth_year_raw = request.form.get("birth_year", "").strip()
        course_id = request.form.get("course_id", type=int)
        parent_name = request.form.get("parent_name", "").strip()
        phone = request.form.get("phone", "").strip()

        if not name or course_id is None:
            conn.close()
            return render_template("edit_student.html", student=student, courses=courses, error="Аты-жөнү жана курс толтурулушу керек.")

        birth_year = None
        if birth_year_raw:
            try:
                birth_year = int(birth_year_raw)
            except ValueError:
                conn.close()
                return render_template("edit_student.html", student=student, courses=courses, error="Туулган жылы туура эмес.")

            if not 1950 <= birth_year <= date.today().year + 1:
                conn.close()
                return render_template("edit_student.html", student=student, courses=courses, error="Туулган жылы 1950дөн азыркы жылга чейин болушу керек.")

        course = conn.execute("SELECT id FROM courses WHERE id = ?", (course_id,)).fetchone()
        if not course:
            conn.close()
            return render_template("edit_student.html", student=student, courses=courses, error="Тандалган курс табылган жок.")

        conn.execute("""
            UPDATE students
            SET name = ?, birth_year = ?, course_id = ?, parent_name = ?, phone = ?
            WHERE id = ?
        """, (name, birth_year, course_id, parent_name, phone, student_id))

        conn.commit()
        conn.close()
        return redirect(url_for("students"))

    conn.close()
    return render_template("edit_student.html", student=student, courses=courses)


# =========================
# ADD PARENT
# =========================
@app.route("/add-parent", methods=["GET", "POST"])
def add_parent():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    students_list = conn.execute("SELECT * FROM students ORDER BY name").fetchall()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        student_id = request.form.get("student_id", type=int)

        if not name or not username or not password or not student_id:
            conn.close()
            return render_template("add_parent.html", students=students_list, error="Бардык талааларды толтуруңуз")

        try:
            conn.execute("""
                INSERT INTO parents (name, username, password, student_id)
                VALUES (?, ?, ?, ?)
            """, (name, username, password, student_id))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template("add_parent.html", students=students_list, error="Бул логин мурда катталган")

        conn.close()
        return redirect(url_for("parents"))

    conn.close()
    return render_template("add_parent.html", students=students_list)


# =========================
# ADD LESSON
# =========================
@app.route("/add-lesson/<int:assignment_id>", methods=["POST"])
def add_lesson(assignment_id):
    if session.get("role") not in ["admin", "teacher"]:
        return redirect(url_for("login"))

    lesson_date = request.form.get("lesson_date", "").strip()
    topic = request.form.get("topic", "").strip()
    semester = request.form.get("semester", 1, type=int)
    if semester < 1 or semester > 6:
        semester = 1
    
    # Формадан келген статусту алабыз (эгер келбесе демейки боюнча "Өтүлдү" болот)
    status = request.form.get("status", "Өтүлдү").strip()
    note = request.form.get("note", "").strip()

    if lesson_date and topic:
        conn = get_db()
        try:
            row = conn.execute("""
                SELECT COALESCE(MAX(lesson_number), 0) + 1 AS next_number
                FROM lessons
                WHERE assignment_id = ? AND semester = ?
            """, (assignment_id, semester)).fetchone()

            conn.execute("""
                INSERT INTO lessons
                    (assignment_id, lesson_number, topic, lesson_date, status, note, semester)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (assignment_id, row["next_number"], topic, lesson_date, status, note, semester))
            conn.commit()
        finally:
            conn.close()

    return redirect(url_for("lesson_page", assignment_id=assignment_id, semester=semester))


# =========================
# PARENT GRADES
# =========================
@app.route("/parent-grades")
def parent_grades():
    if session.get("role") != "parent":
        return redirect(url_for("login"))

    parent_id = session.get("user_id")
    conn = get_db()

    try:
        parent = conn.execute("SELECT * FROM parents WHERE id = ?", (parent_id,)).fetchone()
        if not parent or not parent["student_id"]:
            return "Ата-эне же ага байланган студент табылган жок", 404

        student_id = parent["student_id"]
        student = conn.execute("""
            SELECT st.*, c.name AS course_name
            FROM students st
            LEFT JOIN courses c ON c.id = st.course_id
            WHERE st.id = ?
        """, (student_id,)).fetchone()

        if not student:
            return "Студент табылган жок", 404

        grades = conn.execute("""
            SELECT
                sa.id,
                sa.lesson_date AS lesson_date,
                COALESCE(l.topic, s.name) AS topic,
                sa.grade AS grade,
                sa.note AS comment,
                c.name AS course_name,
                s.name AS subject_name,
                sa.attendance AS attendance,
                t.name AS teacher_name
            FROM student_attendance sa
            LEFT JOIN teacher_assignments ta ON sa.assignment_id = ta.id
            LEFT JOIN courses c ON ta.course_id = c.id
            LEFT JOIN subjects s ON ta.subject_id = s.id
            LEFT JOIN teachers t ON ta.teacher_id = t.id
            LEFT JOIN lessons l ON l.assignment_id = sa.assignment_id
                                AND l.lesson_date = sa.lesson_date
            WHERE sa.student_id = ?
            GROUP BY sa.id
            ORDER BY sa.lesson_date DESC, sa.id DESC
        """, (student_id,)).fetchall()

        return render_template("parent_grades.html", student=student, grades=grades)
    finally:
        conn.close()


# =========================
# QURAN PROGRESS
# =========================
@app.route("/quran-progress")
def quran_progress():
    if session.get("role") != "parent":
        return redirect(url_for("login"))

    parent_id = session.get("user_id")
    conn = get_db()
    parent = conn.execute("SELECT * FROM parents WHERE id = ?", (parent_id,)).fetchone()
    if not parent or not parent["student_id"]:
        conn.close()
        return "Студент табылган жок", 404

    student_id = parent["student_id"]
    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    progress = conn.execute("SELECT * FROM quran_progress WHERE student_id = ? ORDER BY id DESC", (student_id,)).fetchall()
    conn.close()
    return render_template("quran_progress.html", student=student, progress=progress)


@app.route("/teacher/quran-progress/<int:student_id>", methods=["GET", "POST"])
def teacher_quran_progress(student_id):
    role = session.get("role")
    if role not in ["teacher", "admin"]:
        return redirect(url_for("login"))

    conn = get_db()
    try:
        student = conn.execute("""
            SELECT st.*, c.name AS course_name
            FROM students st
            LEFT JOIN courses c ON c.id = st.course_id
            WHERE st.id = ?
        """, (student_id,)).fetchone()

        if not student:
            return "Студент табылган жок", 404

        if role == "teacher":
            teacher_id = session.get("teacher_id", session.get("user_id"))
            assignment = conn.execute("""
                SELECT id FROM teacher_assignments
                WHERE teacher_id = ? AND course_id = ?
                LIMIT 1
            """, (teacher_id, student["course_id"])).fetchone()

            if not assignment:
                return "Бул студенттин курсу сизге дайындалган эмес.", 403

        if request.method == "POST":
            juz_number = request.form.get("juz_number", type=int)
            surah_name = request.form.get("surah_name", "").strip()
            start_ayah = request.form.get("start_ayah", type=int)
            end_ayah = request.form.get("end_ayah", type=int)
            lesson_number = request.form.get("lesson_number", type=int)
            semester = request.form.get("semester", type=int)
            status = request.form.get("status", "").strip()
            grade = request.form.get("grade", "").strip()
            note = request.form.get("note", "").strip()
            progress_date = request.form.get("progress_date", "").strip() or date.today().isoformat()

            teacher_id = session.get("user_id")

            conn.execute("""
                INSERT INTO quran_progress (
                    student_id, juz_number, surah_name, start_ayah, end_ayah,
                    lesson_number, status, progress_date, grade, note, teacher_id, semester
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                student_id, juz_number, surah_name, start_ayah, end_ayah,
                lesson_number, status, progress_date, grade, note, teacher_id, semester
            ))
            conn.commit()
            return redirect(url_for("teacher_quran_progress", student_id=student_id))

        quran_progress = conn.execute("""
            SELECT qp.*, t.name AS teacher_name, st.name AS student_name
            FROM quran_progress qp
            LEFT JOIN teachers t ON t.id = qp.teacher_id
            LEFT JOIN students st ON st.id = qp.student_id
            WHERE qp.student_id = ?
            ORDER BY qp.id DESC
        """, (student_id,)).fetchall()

        # МИЛДЕТТҮҮ ТҮРДӨ ушул файл аталышы турушу керек:
        return render_template(
            "teacher_quran_progress.html",
            student=student,
            quran_progress=quran_progress
        )
    finally:
        conn.close()
@app.route("/juz-list")
def juz_list():
    if session.get("role") not in ["admin", "teacher"]:
        return redirect(url_for("login"))
    
    # 30 жүздүн тизмеси
    sections = [
        {"juz_number": 1, "section_name": "1-жүз (Алиф Лам Мим)", "start_reference": "Аль-Фатиха 1", "end_reference": "Аль-Бакара 141"},
        {"juz_number": 2, "section_name": "2-жүз", "start_reference": "Аль-Бакара 142", "end_reference": "Аль-Бакара 252"},
        {"juz_number": 3, "section_name": "3-жүз", "start_reference": "Аль-Бакара 253", "end_reference": "Али Имран 92"},
        {"juz_number": 4, "section_name": "4-жүз", "start_reference": "Али Имран 93", "end_reference": "Ан-Ниса 23"},
        {"juz_number": 5, "section_name": "5-жүз", "start_reference": "Ан-Ниса 24", "end_reference": "Ан-Ниса 147"},
        {"juz_number": 6, "section_name": "6-жүз", "start_reference": "Ан-Ниса 148", "end_reference": "Аль-Маида 81"},
        {"juz_number": 7, "section_name": "7-жүз", "start_reference": "Аль-Маида 82", "end_reference": "Аль-Анъам 110"},
        {"juz_number": 8, "section_name": "8-жүз", "start_reference": "Аль-Анъам 111", "end_reference": "Аль-Араф 87"},
        {"juz_number": 9, "section_name": "9-жүз", "start_reference": "Аль-Араф 88", "end_reference": "Аль-Анфал 40"},
        {"juz_number": 10, "section_name": "10-жүз", "start_reference": "Аль-Анфал 41", "end_reference": "Ат-Тавба 92"},
        {"juz_number": 11, "section_name": "11-жүз", "start_reference": "Ат-Тавба 93", "end_reference": "Худ 5"},
        {"juz_number": 12, "section_name": "12-жүз", "start_reference": "Худ 6", "end_reference": "Юсуф 52"},
        {"juz_number": 13, "section_name": "13-жүз", "start_reference": "Юсуф 53", "end_reference": "Ибрахим 52"},
        {"juz_number": 14, "section_name": "14-жүз", "start_reference": "Аль-Хижр 1", "end_reference": "Ан-Нахл 128"},
        {"juz_number": 15, "section_name": "15-жүз", "start_reference": "Аль-Исра 1", "end_reference": "Аль-Кахф 74"},
        {"juz_number": 16, "section_name": "16-жүз", "start_reference": "Аль-Кахф 75", "end_reference": "Та Ха 135"},
        {"juz_number": 17, "section_name": "17-жүз", "start_reference": "Аль-Анбия 1", "end_reference": "Аль-Хажж 78"},
        {"juz_number": 18, "section_name": "18-жүз", "start_reference": "Аль-Муминун 1", "end_reference": "Аль-Фуркан 20"},
        {"juz_number": 19, "section_name": "19-жүз", "start_reference": "Аль-Фуркан 21", "end_reference": "Ан-Намль 55"},
        {"juz_number": 20, "section_name": "20-жүз", "start_reference": "Ан-Намль 56", "end_reference": "Аль-Анкабут 45"},
        {"juz_number": 21, "section_name": "21-жүз", "start_reference": "Аль-Анкабут 46", "end_reference": "Аль-Ахзаб 30"},
        {"juz_number": 22, "section_name": "22-жүз", "start_reference": "Аль-Ахзаб 31", "end_reference": "Ясин 27"},
        {"juz_number": 23, "section_name": "23-жүз", "start_reference": "Ясин 28", "end_reference": "Аз-Зумар 31"},
        {"juz_number": 24, "section_name": "24-жүз", "start_reference": "Аз-Зумар 32", "end_reference": "Фуссилат 46"},
        {"juz_number": 25, "section_name": "25-жүз", "start_reference": "Фуссилат 47", "end_reference": "Аль-Жасия 37"},
        {"juz_number": 26, "section_name": "26-жүз", "start_reference": "Аль-Ахкаф 1", "end_reference": "Ад-Зарият 30"},
        {"juz_number": 27, "section_name": "27-жүз", "start_reference": "Ад-Зарият 31", "end_reference": "Аль-Хадид 29"},
        {"juz_number": 28, "section_name": "28-жүз", "start_reference": "Аль-Мужадила 1", "end_reference": "Тахрим 12"},
        {"juz_number": 29, "section_name": "29-жүз", "start_reference": "Аль-Мулк 1", "end_reference": "Мурсалат 50"},
        {"juz_number": 30, "section_name": "30-жүз", "start_reference": "Наба 1", "end_reference": "Нас 6"}
    ]
    return render_template("juz_list.html", sections=sections)

# =========================
# LESSON 2 & STUDENT PROFILE
# =========================
@app.route("/lesson-2")
def lesson_2():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("lesson_2.html")


@app.route("/student/<int:student_id>")
def student_profile(student_id):
    if session.get("role") not in ["admin", "teacher"]:
        return redirect(url_for("login"))

    conn = get_db()
    try:
        student = conn.execute("""
            SELECT students.*, courses.name AS course_name
            FROM students
            LEFT JOIN courses ON courses.id = students.course_id
            WHERE students.id = ?
        """, (student_id,)).fetchone()

        if not student:
            return "Студент табылган жок", 404

        return render_template("student_profile.html", student=student)
    finally:
        conn.close()


# =========================
# TEACHER ATTENDANCE & GRADES
# =========================
@app.route("/teacher/attendance/<int:assignment_id>/<int:student_id>", methods=["GET", "POST"])
def teacher_attendance(assignment_id, student_id):
    if session.get("role") not in ["admin", "teacher"]:
        return redirect(url_for("login"))

    conn = get_db()
    try:
        assignment = conn.execute("""
            SELECT ta.*, t.name AS teacher_name, c.name AS course_name, s.name AS subject_name
            FROM teacher_assignments ta
            JOIN teachers t ON t.id = ta.teacher_id
            JOIN courses c ON c.id = ta.course_id
            JOIN subjects s ON s.id = ta.subject_id
            WHERE ta.id = ?
        """, (assignment_id,)).fetchone()

        if not assignment:
            return "Сабак табылган жок", 404

        if session.get("role") == "teacher" and assignment["teacher_id"] != session.get("user_id"):
            return "Бул сабакты көрүүгө уруксат жок", 403

        student = conn.execute("""
            SELECT st.*, c.name AS course_name
            FROM students st
            LEFT JOIN courses c ON c.id = st.course_id
            WHERE st.id = ? AND st.course_id = ?
        """, (student_id, assignment["course_id"])).fetchone()

        if not student:
            return "Студент табылган жок", 404

        selected_date = (
            request.form.get("lesson_date", "").strip()
            or request.args.get("lesson_date", "").strip()
            or date.today().isoformat()
        )

        if request.method == "POST":
            attendance = request.form.get("attendance", "").strip()
            grade_raw = request.form.get("grade", "").strip()
            note = request.form.get("note", "").strip()

            allowed_attendance = ["Келди", "Келген жок", "Кечикти", "Уруксат"]
            if attendance not in allowed_attendance:
                return "Катышуу түрүн туура тандаңыз", 400

            grade = grade_raw if grade_raw else None

            existing = conn.execute("""
                SELECT id FROM student_attendance
                WHERE student_id = ? AND assignment_id = ? AND lesson_date = ?
            """, (student_id, assignment_id, selected_date)).fetchone()

            if existing:
                conn.execute("""
                    UPDATE student_attendance
                    SET attendance = ?, grade = ?, note = ?
                    WHERE id = ?
                """, (attendance, grade, note, existing["id"]))
            else:
                conn.execute("""
                    INSERT INTO student_attendance
                        (student_id, assignment_id, lesson_date, attendance, grade, note)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (student_id, assignment_id, selected_date, attendance, grade, note))

            conn.commit()
            return redirect(url_for(
                "teacher_attendance",
                assignment_id=assignment_id,
                student_id=student_id,
                lesson_date=selected_date,
                saved=1
            ))

        record = conn.execute("""
            SELECT * FROM student_attendance
            WHERE student_id = ? AND assignment_id = ? AND lesson_date = ?
        """, (student_id, assignment_id, selected_date)).fetchone()

        records = conn.execute("""
            SELECT * FROM student_attendance
            WHERE student_id = ? AND assignment_id = ?
            ORDER BY lesson_date DESC, id DESC
        """, (student_id, assignment_id)).fetchall()

        return render_template(
            "teacher_attendance.html",
            student=student,
            assignment=assignment,
            record=record,
            records=records,
            selected_date=selected_date,
            saved=request.args.get("saved") == "1"
        )
    finally:
        conn.close()


# =========================
# EDIT / DELETE PARENT
# =========================
@app.route("/edit-parent/<int:parent_id>", methods=["GET", "POST"])
def edit_parent(parent_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    try:
        parent = conn.execute("SELECT * FROM parents WHERE id = ?", (parent_id,)).fetchone()
        if not parent:
            return "Ата-эне табылган жок", 404

        students_list = conn.execute("SELECT id, name FROM students ORDER BY name").fetchall()

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            student_id = request.form.get("student_id", type=int)

            if not name or not username or student_id is None:
                return "Аты-жөнү, логин жана студент тандалышы керек.", 400

            student = conn.execute("SELECT id FROM students WHERE id = ?", (student_id,)).fetchone()
            if not student:
                return "Тандалган студент табылган жок.", 400

            existing = conn.execute("SELECT id FROM parents WHERE username = ? AND id != ?", (username, parent_id)).fetchone()
            if existing:
                return "Бул логин башка аккаунтта колдонулууда.", 400

            if password:
                hashed_pw = generate_password_hash(password)
                conn.execute("""
                    UPDATE parents
                    SET name = ?, username = ?, password = ?, student_id = ?
                    WHERE id = ?
                """, (name, username, hashed_pw, student_id, parent_id))
            else:
                conn.execute("""
                    UPDATE parents
                    SET name = ?, username = ?, student_id = ?
                    WHERE id = ?
                """, (name, username, student_id, parent_id))

            conn.commit()
            return redirect(url_for("parents"))

        return render_template("edit_parent.html", parent=parent, students=students_list)
    finally:
        conn.close()


@app.route("/delete-parent/<int:parent_id>", methods=["POST"])
def delete_parent(parent_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    try:
        parent = conn.execute("SELECT id FROM parents WHERE id = ?", (parent_id,)).fetchone()
        if not parent:
            return "Ата-эне табылган жок", 404

        conn.execute("DELETE FROM parents WHERE id = ?", (parent_id,))
        conn.commit()
        return redirect(url_for("parents"))
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    app.run(debug=True)