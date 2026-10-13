from flask import Flask, render_template, request, redirect, session
import pyodbc

app = Flask(__name__)
app.secret_key = "DAMS_SECRET_KEY_2026"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():
    return pyodbc.connect(
        "DRIVER={SQL Server};"
        "SERVER=localhost\\SQLEXPRESS;"
        "DATABASE=DAMS;"
        "Trusted_Connection=yes;"
    )


# =========================================================
# LOGIN / ROLE FUNCTIONS
# =========================================================

def get_role():
    return str(session.get("role") or "").strip().lower()


def is_logged_in():
    return bool(session.get("username"))


def is_admin():
    return get_role() == "admin"


def is_student():
    return get_role() == "student"


def is_faculty():
    return get_role() == "faculty"


# =========================================================
# HOME
# =========================================================

@app.route("/")
def index():
    return redirect("/login")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT Username, Password, Role, StudentID
            FROM Users
            WHERE Username = ? AND Password = ?
        """, (username, password))

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            session["username"] = user[0]
            session["role"] = (user[2] or "").strip().lower()

            role = session["role"]

            if role == "admin":
                return redirect("/dashboard")

            elif role == "faculty":
                return redirect("/faculty_dashboard")

            elif role == "student":
                session["student_id"] = user[3]
                session["student_username"] = username
                return redirect("/student_dashboard")

        return render_template(
            "index.html",
            error="Invalid Username or Password"
        )

    return render_template("index.html")

# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if not is_logged_in():
        return redirect("/login")

    if not is_admin():
        return "Access Denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM Students")
    total_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Faculty")
    total_faculty = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Activities")
    total_activities = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM EventRegistration")
    total_events = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Attendance")
    total_attendance = cursor.fetchone()[0]

    cursor.execute("""
        SELECT TOP 5 ActivityID, ActivityName, ActivityType, ActivityDate,
               Venue, Organizer, Description
        FROM Activities
        ORDER BY ActivityDate DESC, ActivityID DESC
    """)
    activities = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "dashboard.html",
        total_students=total_students,
        total_faculty=total_faculty,
        total_activities=total_activities,
        total_events=total_events,
        total_attendance=total_attendance,
        activities=activities
    )


# =========================================================
# FACULTY DASHBOARD
# =========================================================

@app.route("/faculty_dashboard")
def faculty_dashboard():

    if not is_logged_in():
        return redirect("/login")

    if not is_faculty():
        return "Access Denied", 403

    faculty_codes = {
        "NV": "Dr Naveen",
        "IM": "Dr Immanuvel",
        "RKP": "Dr Radhakrishnan",
        "VG": "Mrs Vasantha Rani",
        "PV": "Miss Poovarasi",
        "DD": "Mr Daniel Abishek",
        "NK": "Mr Naveen Kumar",
        "KW": "Mr Kamaleshwar"
    }

    username = session.get("username", "").strip().upper()

    faculty_name = faculty_codes.get(username, username)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT FacultyName, Department, Designation, Email, Phone
        FROM Faculty
        WHERE FacultyName = ?
    """, (faculty_name,))

    faculty = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "faculty_dashboard.html",
        faculty=faculty,
        faculty_name=faculty_name
    )


# =========================================================
# STUDENT DASHBOARD
# =========================================================

@app.route("/student_dashboard")
def student_dashboard():

    if not is_logged_in():
        return redirect("/login")

    if not is_student():
        return "Access Denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        student_id = session.get("student_id")

        cursor.execute("""
            SELECT StudentID, RegisterNo, StudentName
            FROM Students
            WHERE StudentID = ?
        """, (student_id,))

        student = cursor.fetchone()

    finally:
        cursor.close()
        conn.close()

    if student is None:
        return "Student details not found.", 404

    return render_template(
        "student_dashboard.html",
        student=student
    )


# =========================================================
# STUDENT DETAILS
# =========================================================

@app.route("/student_details")
def student_details():

    if not is_logged_in():
        return redirect("/login")

    if not is_student():
        return "Access Denied", 403

    student_id = session.get("student_id")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT StudentID,
               RegisterNo,
               StudentName,
               Department,
               YearOfStudy,
               Email,
               MobileNo
        FROM Students
        WHERE StudentID = ?
    """, (student_id,))

    student = cursor.fetchone()

    cursor.close()
    conn.close()

    if not student:
        return "Student not found", 404

    return render_template(
        "student_details.html",
        student=student
    )


# =========================================================
# STUDENT MANAGEMENT
# =========================================================

@app.route("/student")
def student():

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    return render_template("student.html")


@app.route("/add_student", methods=["POST"])
def add_student():

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    regno = request.form.get("regno", "").strip()
    name = request.form.get("name", "").strip()
    department = request.form.get("department", "").strip()
    year = request.form.get("year", "").strip()
    email = request.form.get("email", "").strip()
    mobile = request.form.get("mobile", "").strip()

    if not regno or not name or not department:
        return "Required student fields are missing", 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO Students
        (
            RegisterNo,
            StudentName,
            Department,
            YearOfStudy,
            Email,
            MobileNo
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        regno,
        name,
        department,
        year,
        email,
        mobile
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/view_students")


@app.route("/view_students")
def view_students():

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT StudentID,
               RegisterNo,
               StudentName,
               Department,
               YearOfStudy,
               Email,
               MobileNo
        FROM Students
        ORDER BY StudentID
    """)

    students = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "view_students.html",
        students=students
    )


@app.route("/edit_student/<int:id>")
def edit_student(id):

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT StudentID,
               RegisterNo,
               StudentName,
               Department,
               YearOfStudy,
               Email,
               MobileNo
        FROM Students
        WHERE StudentID = ?
    """, (id,))

    student_data = cursor.fetchone()

    cursor.close()
    conn.close()

    if not student_data:
        return "Student not found", 404

    return render_template(
        "edit_student.html",
        student=student_data
    )


@app.route("/update_student", methods=["POST"])
def update_student():

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    student_id = request.form.get("id")

    regno = request.form.get("regno", "").strip()
    name = request.form.get("name", "").strip()
    department = request.form.get("department", "").strip()
    year = request.form.get("year", "").strip()
    email = request.form.get("email", "").strip()
    mobile = request.form.get("mobile", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE Students
        SET RegisterNo = ?,
            StudentName = ?,
            Department = ?,
            YearOfStudy = ?,
            Email = ?,
            MobileNo = ?
        WHERE StudentID = ?
    """, (
        regno,
        name,
        department,
        year,
        email,
        mobile,
        student_id
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/view_students")


@app.route("/delete_student/<int:id>")
def delete_student(id):

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM Students
        WHERE StudentID = ?
    """, (id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/view_students")


# =========================================================
# FACULTY MANAGEMENT
# =========================================================

@app.route("/faculty", methods=["GET", "POST"])
def faculty():

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    # The Faculty Management page contains the add form and links to the list.
    if request.method == "GET":
        return render_template("faculty.html")

    # Keep compatibility with any form that still posts directly to /faculty.
    name = (request.form.get("name") or request.form.get("facultyname") or request.form.get("FacultyName") or "").strip()
    department = (request.form.get("department") or request.form.get("Department") or "").strip()
    designation = (request.form.get("designation") or request.form.get("Designation") or "").strip()
    email = (request.form.get("email") or request.form.get("Email") or "").strip()
    phone = (request.form.get("phone") or request.form.get("Phone") or "").strip()

    if not name or not department or not designation:
        return "Please fill in all required faculty fields.", 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO Faculty (FacultyName, Department, Designation, Email, Phone)
            VALUES (?, ?, ?, ?, ?)
        """, (name, department, designation, email, phone))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("Faculty route error:", e)
        return "Unable to add faculty. Check the VS Code terminal.", 500
    finally:
        cursor.close()
        conn.close()

    return redirect("/view_faculty")


@app.route("/add_faculty", methods=["POST"])
def add_faculty():

    # Check login
    if not is_logged_in():
        return redirect("/login")

    # Allow Admin and Faculty
    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    # Get form values
    name = (
        request.form.get("name")
        or request.form.get("facultyname")
        or request.form.get("FacultyName")
        or ""
    ).strip()

    department = (
        request.form.get("department")
        or request.form.get("Department")
        or ""
    ).strip()

    designation = (
        request.form.get("designation")
        or request.form.get("Designation")
        or ""
    ).strip()

    email = (
        request.form.get("email")
        or request.form.get("Email")
        or ""
    ).strip()

    phone = (
        request.form.get("phone")
        or request.form.get("Phone")
        or ""
    ).strip()

    # Validate required fields
    if not name or not department or not designation:
        return "Please fill in all required faculty fields.", 400

    conn = None
    cursor = None

    try:
        # Database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert faculty details
        cursor.execute("""
            INSERT INTO Faculty
                (FacultyName, Department, Designation, Email, Phone)
            VALUES (?, ?, ?, ?, ?)
        """, (
            name,
            department,
            designation,
            email,
            phone
        ))

        conn.commit()

    except Exception as e:
        if conn:
            conn.rollback()

        print("Add Faculty Error:", e)

        return (
            "Unable to add faculty. "
            "Please check the VS Code terminal for the database error."
        ), 500

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()

    # Redirect after successful insertion
    return redirect("/view_faculty")


@app.route("/view_faculty")
def view_faculty():

    if not is_logged_in():
        return redirect("/login")

    # Allow Admin and Faculty to view faculty details
    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT FacultyID,
               FacultyName,
               Department,
               Designation,
               Email,
               Phone
        FROM Faculty
        ORDER BY FacultyID
    """)

    faculty_list = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "view_faculty.html",
        faculty=faculty_list
    )


@app.route("/edit_faculty/<int:id>")
def edit_faculty(id):

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT FacultyID,
               FacultyName,
               Department,
               Designation,
               Email,
               Phone
        FROM Faculty
        WHERE FacultyID = ?
    """, (id,))

    faculty_data = cursor.fetchone()

    cursor.close()
    conn.close()

    if not faculty_data:
        return "Faculty not found", 404

    return render_template(
        "edit_faculty.html",
        faculty=faculty_data
    )


@app.route("/update_faculty", methods=["POST"])
def update_faculty():

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    faculty_id = request.form.get("id")

    name = (request.form.get("name") or request.form.get("facultyname") or request.form.get("FacultyName") or "").strip()
    department = (request.form.get("department") or request.form.get("Department") or "").strip()
    designation = (request.form.get("designation") or request.form.get("Designation") or "").strip()
    email = (request.form.get("email") or request.form.get("Email") or "").strip()
    phone = (request.form.get("phone") or request.form.get("Phone") or "").strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE Faculty
        SET FacultyName = ?,
            Department = ?,
            Designation = ?,
            Email = ?,
            Phone = ?
        WHERE FacultyID = ?
    """, (
        name,
        department,
        designation,
        email,
        phone,
        faculty_id
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/view_faculty")


@app.route("/delete_faculty/<int:id>")
def delete_faculty(id):

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM Faculty
        WHERE FacultyID = ?
    """, (id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/view_faculty")


# =========================================================
# ACTIVITY MANAGEMENT
# =========================================================

@app.route("/activities")
def activities():

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    return render_template("activity.html")


@app.route("/add_activity", methods=["POST"])
def add_activity():

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    activityname = (request.form.get("activityname") or request.form.get("activity_name") or request.form.get("name") or "").strip()
    activitytype = (request.form.get("activitytype") or request.form.get("activity_type") or request.form.get("type") or "").strip()
    activitydate = (request.form.get("activitydate") or request.form.get("activity_date") or request.form.get("date") or "").strip()
    organizer = (request.form.get("organizer") or "").strip()
    venue = (request.form.get("venue") or "").strip()
    description = (request.form.get("description") or "").strip()

    if not activityname or not activitytype or not activitydate:
        return "Required activity fields are missing", 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO Activities
        (
            ActivityName,
            ActivityType,
            ActivityDate,
            Organizer,
            Venue,
            Description
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        activityname,
        activitytype,
        activitydate,
        organizer,
        venue,
        description
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/view_activities")


@app.route("/view_activities")
def view_activities():

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ActivityID,
               ActivityName,
               ActivityType,
               ActivityDate,
               Venue,
               Organizer,
               Description
        FROM Activities
        ORDER BY ActivityID
    """)

    activities_list = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "view_activities.html",
        activities=activities_list
    )


@app.route("/edit_activity/<int:id>")
def edit_activity(id):

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ActivityID,
               ActivityName,
               ActivityType,
               ActivityDate,
               Venue,
               Organizer,
               Description
        FROM Activities
        WHERE ActivityID = ?
    """, (id,))

    activity_data = cursor.fetchone()

    cursor.close()
    conn.close()

    if not activity_data:
        return "Activity not found", 404

    return render_template(
        "edit_activity.html",
        activity=activity_data
    )


@app.route("/update_activity", methods=["POST"])
def update_activity():

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    activity_id = request.form.get("activityid") or request.form.get("activity_id") or request.form.get("id")

    name = (request.form.get("name") or request.form.get("activityname") or request.form.get("activity_name") or "").strip()
    activity_type = (request.form.get("type") or request.form.get("activitytype") or request.form.get("activity_type") or "").strip()
    activity_date = (request.form.get("date") or request.form.get("activitydate") or request.form.get("activity_date") or "").strip()
    venue = (request.form.get("venue") or "").strip()
    organizer = (request.form.get("organizer") or "").strip()
    description = (request.form.get("description") or "").strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE Activities
        SET ActivityName = ?,
            ActivityType = ?,
            ActivityDate = ?,
            Venue = ?,
            Organizer = ?,
            Description = ?
        WHERE ActivityID = ?
    """, (
        name,
        activity_type,
        activity_date,
        venue,
        organizer,
        description,
        activity_id
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/view_activities")


@app.route("/delete_activity/<int:id>")
def delete_activity(id):

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
       return "Access Denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM Activities
        WHERE ActivityID = ?
    """, (id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/view_activities")


# =========================================================
# EVENT REGISTRATION
# =========================================================

@app.route("/event_registration")
def event_registration():

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty() or is_student()):
        return "Access Denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get activities
    cursor.execute("""
        SELECT ActivityID,
               ActivityName,
               ActivityType,
               ActivityDate,
               Organizer,
               Venue
        FROM Activities
        ORDER BY ActivityDate DESC
    """)

    activities = cursor.fetchall()

    # -----------------------------------------------------
    # ADMIN AND FACULTY
    # -----------------------------------------------------

    if is_admin() or is_faculty():

        cursor.execute("""
            SELECT StudentID,
                   RegisterNo,
                   StudentName,
                   Department,
                   YearOfStudy
            FROM Students
            ORDER BY StudentName
        """)

        students = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template(
            "event_registration.html",
            student=None,
            students=students,
            activities=activities
        )

    # -----------------------------------------------------
    # STUDENT
    # -----------------------------------------------------

    student_id = session.get("student_id")

    cursor.execute("""
        SELECT StudentID,
               RegisterNo,
               StudentName,
               Department,
               YearOfStudy,
               Email,
               MobileNo
        FROM Students
        WHERE StudentID = ?
    """, (student_id,))

    student = cursor.fetchone()

    cursor.close()
    conn.close()

    if not student:
        return "Student not found", 404

    return render_template(
        "event_registration.html",
        student=student,
        students=[],
        activities=activities
    )


@app.route("/register_event", methods=["POST"])
def register_event():

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty() or is_student()):
        return "Access Denied", 403

    activity_id = request.form.get("activityid")
    registration_date = request.form.get(
        "registrationdate",
        ""
    ).strip()

    if not activity_id or not registration_date:
        return "Activity and registration date are required", 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get activity name
    cursor.execute("""
        SELECT ActivityName
        FROM Activities
        WHERE ActivityID = ?
    """, (activity_id,))

    activity = cursor.fetchone()

    if not activity:
        cursor.close()
        conn.close()
        return "Activity not found", 404

    activity_name = activity[0]

    # -----------------------------------------------------
    # STUDENT ID
    # -----------------------------------------------------

    if is_student():

        student_id = session.get("student_id")

    else:

        student_id = request.form.get("studentid")

    if not student_id:
        cursor.close()
        conn.close()
        return "Student is required", 400

    # Get student name from database
    cursor.execute("""
        SELECT StudentName
        FROM Students
        WHERE StudentID = ?
    """, (student_id,))

    student = cursor.fetchone()

    if not student:
        cursor.close()
        conn.close()
        return "Student not found", 404

    student_name = student[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM EventRegistration
        WHERE StudentID = ? AND ActivityID = ?
    """, (student_id, activity_id))
    if cursor.fetchone()[0] > 0:
        cursor.close()
        conn.close()
        return "Student is already registered for this activity", 409

    # -----------------------------------------------------
    # INSERT REGISTRATION
    # -----------------------------------------------------

    cursor.execute("""
        INSERT INTO EventRegistration
        (
            StudentID,
            StudentName,
            ActivityID,
            ActivityName,
            RegistrationDate
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        student_id,
        student_name,
        activity_id,
        activity_name,
        registration_date
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/view_event_registrations")


@app.route("/view_event_registrations")
def view_event_registrations():

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty() or is_student()):
        return "Access Denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    if is_student():

        student_id = session.get("student_id")

        cursor.execute("""
            SELECT *
            FROM EventRegistration
            WHERE StudentID = ?
            ORDER BY RegistrationDate DESC
        """, (student_id,))

    else:

        cursor.execute("""
            SELECT *
            FROM EventRegistration
            ORDER BY RegistrationDate DESC
        """)

    registrations = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "view_event_registrations.html",
        registrations=registrations
    )


@app.route("/edit_event/<int:id>")
def edit_event(id):

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty() or is_student()):
        return "Access Denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT RegistrationID,
               StudentID,
               StudentName,
               ActivityID,
               ActivityName,
               RegistrationDate
        FROM EventRegistration
        WHERE RegistrationID = ?
    """, (id,))

    registration = cursor.fetchone()

    cursor.close()
    conn.close()

    if registration is None:
        return "Event Registration not found", 404

    # Students can edit only their own registrations
    if is_student():
        student_id = session.get("student_id")

        if str(registration[1]) != str(student_id):
            return "Access Denied: You can edit only your own registration", 403

    return render_template(
        "edit_event_registration.html",
        registration=registration
    )

@app.route("/update_event", methods=["POST"])
def update_event():

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty() or is_student()):
        return "Access Denied", 403

    registration_id = request.form.get("id")
    student_id = request.form.get("studentid")
    student_name = request.form.get("studentname")
    activity_id = request.form.get("activityid")
    activity_name = request.form.get("activityname")
    registration_date = request.form.get("registrationdate")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check whether the registration exists
    cursor.execute("""
        SELECT StudentID
        FROM EventRegistration
        WHERE RegistrationID = ?
    """, (registration_id,))

    registration = cursor.fetchone()

    if registration is None:
        cursor.close()
        conn.close()
        return "Event Registration not found", 404

    # Students can update only their own registrations
    if is_student():
        logged_in_student_id = session.get("student_id")

        if str(registration[0]) != str(logged_in_student_id):
            cursor.close()
            conn.close()
            return "Access Denied: You can update only your own registration", 403

        # Do not allow students to change ownership
        student_id = logged_in_student_id

        cursor.execute("""
            SELECT StudentName
            FROM Students
            WHERE StudentID = ?
        """, (logged_in_student_id,))

        student = cursor.fetchone()

        if student:
            student_name = student[0]

    cursor.execute("""
        UPDATE EventRegistration
        SET StudentID = ?,
            StudentName = ?,
            ActivityID = ?,
            ActivityName = ?,
            RegistrationDate = ?
        WHERE RegistrationID = ?
    """, (
        student_id,
        student_name,
        activity_id,
        activity_name,
        registration_date,
        registration_id
    ))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect("/view_event_registrations")


@app.route("/delete_event/<int:id>", methods=["GET", "POST"])
def delete_event(id):

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty() or is_student()):
        return "Access Denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    # Find the registration
    cursor.execute("""
        SELECT StudentID
        FROM EventRegistration
        WHERE RegistrationID = ?
    """, (id,))

    registration = cursor.fetchone()

    if registration is None:
        cursor.close()
        conn.close()
        return "Event Registration not found", 404

    # Students can delete only their own registration
    if is_student():
        logged_in_student_id = session.get("student_id")

        if str(registration[0]) != str(logged_in_student_id):
            cursor.close()
            conn.close()
            return "Access Denied: You can delete only your own registration", 403

    # Delete registration
    cursor.execute("""
        DELETE FROM EventRegistration
        WHERE RegistrationID = ?
    """, (id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/view_event_registrations")


# =========================================================
# ATTENDANCE
# =========================================================

@app.route("/attendance", methods=["GET", "POST"])
def attendance():
    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    # Supports both POST forms and query-string links.
    activity_id = (request.values.get("activityid") or
                   request.values.get("activity_id") or "").strip()
    attendance_date = (request.values.get("attendancedate") or
                       request.values.get("attendance_date") or "").strip()

    if not attendance_date:
        from datetime import date
        attendance_date = date.today().isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Show activities that have at least one event registration.
        cursor.execute("""
            SELECT DISTINCT a.ActivityID, a.ActivityName, a.ActivityDate
            FROM Activities AS a
            INNER JOIN EventRegistration AS er
                ON er.ActivityID = a.ActivityID
            ORDER BY a.ActivityDate DESC, a.ActivityID DESC
        """)
        activities_list = cursor.fetchall()

        students = []
        existing_attendance = {}

        # Do not load every student. Only show students registered
        # for the activity selected by the user.
        if activity_id:
            cursor.execute("""
                SELECT DISTINCT s.StudentID, s.RegisterNo, s.StudentName
                FROM EventRegistration AS er
                INNER JOIN Students AS s
                    ON s.StudentID = er.StudentID
                WHERE er.ActivityID = ?
                ORDER BY s.StudentName
            """, (activity_id,))
            students = cursor.fetchall()

            cursor.execute("""
                SELECT StudentID, Status
                FROM Attendance
                WHERE ActivityID = ? AND AttendanceDate = ?
            """, (activity_id, attendance_date))
            existing_attendance = {
                row[0]: row[1] for row in cursor.fetchall()
            }

    finally:
        cursor.close()
        conn.close()

    return render_template(
        "attendance.html",
        activities=activities_list,
        students=students,
        selected_activity_id=activity_id,
        attendance_date=attendance_date,
        existing_attendance=existing_attendance
    )


@app.route("/save_attendance", methods=["POST"])
def save_attendance():
    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    activity_id = (request.form.get("activityid") or
                   request.form.get("activity_id") or "").strip()
    attendance_date = (request.form.get("attendancedate") or
                       request.form.get("attendance_date") or "").strip()

    if not activity_id or not attendance_date:
        return "Activity and attendance date are required", 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT ActivityName FROM Activities WHERE ActivityID = ?",
            (activity_id,)
        )
        activity_row = cursor.fetchone()
        if not activity_row:
            return "Activity not found", 404
        activity_name = activity_row[0]

        # Only registered students can receive attendance for this activity.
        cursor.execute("""
            SELECT DISTINCT s.StudentID, s.StudentName
            FROM EventRegistration AS er
            INNER JOIN Students AS s
                ON s.StudentID = er.StudentID
            WHERE er.ActivityID = ?
            ORDER BY s.StudentName
        """, (activity_id,))
        registered_students = cursor.fetchall()

        if not registered_students:
            conn.rollback()
            return "No students are registered for this activity. Attendance was not saved.", 400

        # Replace only attendance for this activity and date.
        cursor.execute("""
            DELETE FROM Attendance
            WHERE ActivityID = ? AND AttendanceDate = ?
        """, (activity_id, attendance_date))

        for student in registered_students:
            student_id = student[0]
            student_name = student[1]
            status = request.form.get(f"status_{student_id}", "Absent")
            if status not in ("Present", "Absent"):
                status = "Absent"

            cursor.execute("""
                INSERT INTO Attendance
                    (StudentID, StudentName, ActivityID, ActivityName,
                     AttendanceDate, Status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                student_id,
                student_name,
                activity_id,
                activity_name,
                attendance_date,
                status
            ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

    return redirect("/view_attendance")


@app.route("/view_attendance")
def view_attendance():
    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT AttendanceID, StudentID, StudentName, ActivityID,
                   ActivityName, AttendanceDate, Status
            FROM Attendance
            ORDER BY AttendanceDate DESC, ActivityName, StudentName
        """)
        attendance_data = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    return render_template("view_attendance.html", attendance=attendance_data)


@app.route("/edit_attendance/<int:id>")
def edit_attendance(id):
    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT AttendanceID, StudentID, StudentName, ActivityID,
                   ActivityName, AttendanceDate, Status
            FROM Attendance
            WHERE AttendanceID = ?
        """, (id,))
        attendance_data = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    if not attendance_data:
        return "Attendance not found", 404

    return render_template("edit_attendance.html", attendance=attendance_data)


@app.route("/update_attendance", methods=["POST"])
def update_attendance():
    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    attendance_id = request.form.get("id") or request.form.get("attendanceid")
    student_id = request.form.get("studentid")
    activity_id = request.form.get("activityid")
    attendance_date = request.form.get("attendancedate")
    status = request.form.get("status", "Absent")

    if not all((attendance_id, student_id, activity_id, attendance_date)):
        return "Attendance ID, student, activity and date are required", 400
    if status not in ("Present", "Absent"):
        status = "Absent"

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Prevent editing attendance for a student not registered for the activity.
        cursor.execute("""
            SELECT s.StudentName, a.ActivityName
            FROM EventRegistration AS er
            INNER JOIN Students AS s ON s.StudentID = er.StudentID
            INNER JOIN Activities AS a ON a.ActivityID = er.ActivityID
            WHERE er.StudentID = ? AND er.ActivityID = ?
        """, (student_id, activity_id))
        row = cursor.fetchone()
        if not row:
            return "Student is not registered for this activity", 400

        cursor.execute("""
            UPDATE Attendance
            SET StudentID = ?, StudentName = ?, ActivityID = ?,
                ActivityName = ?, AttendanceDate = ?, Status = ?
            WHERE AttendanceID = ?
        """, (
            student_id, row[0], activity_id, row[1],
            attendance_date, status, attendance_id
        ))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

    return redirect("/view_attendance")


@app.route("/delete_attendance/<int:id>", methods=["GET", "POST"])
def delete_attendance(id):
    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Attendance WHERE AttendanceID = ?", (id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

    return redirect("/view_attendance")


# =========================================================
# CERTIFICATES
# =========================================================

@app.route("/certificates")
def certificates():

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM Certificates
        ORDER BY CertificateID DESC
    """)

    certificates_data = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "certificates.html",
        certificates=certificates_data
    )


@app.route("/add_certificate", methods=["POST"])
def add_certificate():

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    student_id = request.form.get("studentid") or request.form.get("student_id")
    activity_id = request.form.get("activityid") or request.form.get("activity_id")
    certificate_type = request.form.get("certificatetype") or request.form.get("certificate_type")
    certificate_date = request.form.get("certificatedate") or request.form.get("certificate_date")

    if not student_id or not activity_id or not certificate_type or not certificate_date:
        return "Student, activity, certificate type and date are required", 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT StudentName FROM Students WHERE StudentID = ?", (student_id,))
    student_row = cursor.fetchone()
    cursor.execute("SELECT ActivityName FROM Activities WHERE ActivityID = ?", (activity_id,))
    activity_row = cursor.fetchone()
    if not student_row or not activity_row:
        cursor.close()
        conn.close()
        return "Student or activity not found", 404
    student_name = student_row[0]
    activity_name = activity_row[0]

    cursor.execute("""
        INSERT INTO Certificates
        (
            StudentID,
            StudentName,
            ActivityID,
            ActivityName,
            CertificateType,
            CertificateDate
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        student_id,
        student_name,
        activity_id,
        activity_name,
        certificate_type,
        certificate_date
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/certificates")


@app.route("/edit_certificate/<int:id>")
def edit_certificate(id):

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM Certificates
        WHERE CertificateID = ?
    """, (id,))

    certificate = cursor.fetchone()

    cursor.close()
    conn.close()

    if not certificate:
        return "Certificate not found", 404

    return render_template(
        "edit_certificate.html",
        certificate=certificate
    )


@app.route("/update_certificate", methods=["POST"])
def update_certificate():

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    certificate_id = request.form.get("certificateid") or request.form.get("certificate_id") or request.form.get("id")

    student_id = request.form.get("studentid") or request.form.get("student_id")
    activity_id = request.form.get("activityid") or request.form.get("activity_id")
    certificate_type = request.form.get("certificatetype") or request.form.get("certificate_type")
    certificate_date = request.form.get("certificatedate") or request.form.get("certificate_date")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT StudentName FROM Students WHERE StudentID = ?", (student_id,))
    student_row = cursor.fetchone()
    cursor.execute("SELECT ActivityName FROM Activities WHERE ActivityID = ?", (activity_id,))
    activity_row = cursor.fetchone()
    if not student_row or not activity_row:
        cursor.close()
        conn.close()
        return "Student or activity not found", 404

    cursor.execute("""
        UPDATE Certificates
        SET StudentID = ?,
            StudentName = ?,
            ActivityID = ?,
            ActivityName = ?,
            CertificateType = ?,
            CertificateDate = ?
        WHERE CertificateID = ?
    """, (
        student_id,
        student_row[0],
        activity_id,
        activity_row[0],
        certificate_type,
        certificate_date,
        certificate_id
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/certificates")


@app.route("/delete_certificate/<int:id>")
def delete_certificate(id):

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM Certificates
        WHERE CertificateID = ?
    """, (id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/certificates")


@app.route("/generate_certificate", defaults={"id": None})
@app.route("/generate_certificate/<int:id>")
def generate_certificate(id):
    """Show the generation form, or display a saved certificate by ID."""

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # When an ID is supplied, display that saved certificate.
        if id is not None:
            cursor.execute("""
                SELECT *
                FROM Certificates
                WHERE CertificateID = ?
            """, (id,))
            certificate = cursor.fetchone()

            if not certificate:
                return "Certificate not found", 404

            return render_template("certificate.html", certificate=certificate)

        # Without an ID, show the certificate generation form.
        cursor.execute("""
            SELECT StudentID, RegisterNo, StudentName
            FROM Students
            ORDER BY StudentName
        """)
        students = cursor.fetchall()

        cursor.execute("""
            SELECT ActivityID, ActivityName, ActivityDate
            FROM Activities
            ORDER BY ActivityDate DESC
        """)
        activities = cursor.fetchall()

        return render_template(
            "generate_certificate.html",
            students=students,
            activities=activities
        )
    finally:
        cursor.close()
        conn.close()


@app.route("/student_certificates")
def student_certificates():

    if not is_logged_in():
        return redirect("/login")

    if not is_student():
        return "Access Denied", 403

    student_id = session.get("student_id")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get logged-in student's details
    cursor.execute("""
        SELECT StudentID, RegisterNo, StudentName,
               Department, YearOfStudy, Email, MobileNo
        FROM Students
        WHERE StudentID = ?
    """, (student_id,))

    student = cursor.fetchone()

    if student is None:
        cursor.close()
        conn.close()
        return "Student details not found", 404

    # Get certificates for this student
    cursor.execute("""
        SELECT *
        FROM Certificates
        WHERE StudentID = ?
    """, (student_id,))

    certificates = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "student_certificates.html",
        student=student,
        certificates=certificates
    )


@app.route("/student_generate_certificate/<int:id>")
def student_generate_certificate(id):

    if not is_logged_in():
        return redirect("/login")

    if not is_student():
        return "Access Denied", 403

    student_id = session.get("student_id")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM Certificates
        WHERE CertificateID = ?
        AND StudentID = ?
    """, (id, student_id))

    certificate = cursor.fetchone()

    cursor.close()
    conn.close()

    if not certificate:
        return "Certificate not found", 404

    return render_template(
        "certificate.html",
        certificate=certificate
    )


# =========================================================
# REPORTS
# =========================================================

@app.route("/reports", methods=["GET", "POST"])
def reports():

    # -----------------------------------------------------
    # CHECK LOGIN AND ADMIN ACCESS
    # -----------------------------------------------------

    if not is_logged_in():
        return redirect("/login")

    if not (is_admin() or is_faculty()):
        return "Access Denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    # -----------------------------------------------------
    # SUMMARY COUNTS
    # -----------------------------------------------------

    cursor.execute("SELECT COUNT(*) FROM Students")
    total_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Faculty")
    total_faculty = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Activities")
    total_activities = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM EventRegistration")
    total_events = cursor.fetchone()[0]

    total_registrations = total_events

    cursor.execute("SELECT COUNT(*) FROM Attendance")
    total_attendance = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM Attendance
        WHERE Status = 'Present'
    """)
    total_present = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM Attendance
        WHERE Status = 'Absent'
    """)
    total_absent = cursor.fetchone()[0]

    # -----------------------------------------------------
    # OVERALL ATTENDANCE PERCENTAGE
    # -----------------------------------------------------

    if total_attendance > 0:
        overall_percentage = (
            total_present / total_attendance
        ) * 100
    else:
        overall_percentage = 0.0


    # -----------------------------------------------------
    # EVENT-WISE REPORT - LATEST ATTENDANCE STATUS
    # -----------------------------------------------------

    cursor.execute("""
        WITH LatestAttendance AS (
            SELECT
                at.AttendanceID,
                at.StudentID,
                at.ActivityID,
                at.Status,
                ROW_NUMBER() OVER (
                    PARTITION BY at.StudentID, at.ActivityID
                    ORDER BY at.AttendanceID DESC
                ) AS rn
            FROM Attendance at
        )

        SELECT
            a.ActivityID,
            a.ActivityName,

            COUNT(DISTINCT er.RegistrationID) AS Registrations,

            COUNT(DISTINCT CASE
                WHEN la.Status = 'Present'
                THEN er.StudentID
            END) AS PresentCount,

            COUNT(DISTINCT CASE
                WHEN la.Status = 'Absent'
                THEN er.StudentID
            END) AS AbsentCount,

            CAST(
                CASE
                    WHEN COUNT(DISTINCT er.StudentID) = 0
                    THEN 0
                    ELSE
                        100.0 *
                        COUNT(DISTINCT CASE
                            WHEN la.Status = 'Present'
                            THEN er.StudentID
                        END)
                        / COUNT(DISTINCT er.StudentID)
                END
                AS DECIMAL(5,2)
            ) AS AttendancePercentage

        FROM Activities a

        LEFT JOIN EventRegistration er
            ON er.ActivityID = a.ActivityID

        LEFT JOIN LatestAttendance la
            ON la.ActivityID = a.ActivityID
            AND la.StudentID = er.StudentID
            AND la.rn = 1

        GROUP BY
            a.ActivityID,
            a.ActivityName

        ORDER BY
            a.ActivityID
    """)

    event_reports = cursor.fetchall()


    # -----------------------------------------------------
    # DATE-WISE REPORT
    # -----------------------------------------------------

    selected_date = (
        request.values.get("from_date") or ""
    ).strip()

    date_report = []

    if selected_date:

        cursor.execute("""
            SELECT
                a.ActivityID,
                a.ActivityName,
                a.ActivityType,
                a.ActivityDate,
                a.Venue,
                s.Department,
                s.YearOfStudy,
                er.RegistrationID,
                s.StudentID,
                s.RegisterNo,
                s.StudentName,
                er.ActivityID,
                COALESCE(at.Status, 'Absent') AS Status

            FROM Activities a

            INNER JOIN EventRegistration er
                ON er.ActivityID = a.ActivityID

            INNER JOIN Students s
                ON s.StudentID = er.StudentID

            LEFT JOIN Attendance at
                ON at.ActivityID = a.ActivityID
                AND at.StudentID = s.StudentID
                AND CONVERT(date, at.AttendanceDate) = ?

            WHERE CONVERT(date, a.ActivityDate) = ?

            ORDER BY
                a.ActivityID,
                s.StudentName
        """, (selected_date, selected_date))

        date_report = cursor.fetchall()

    # -----------------------------------------------------
    # CLOSE DATABASE CONNECTION
    # -----------------------------------------------------

    cursor.close()
    conn.close()

    # -----------------------------------------------------
    # DISPLAY REPORTS PAGE
    # -----------------------------------------------------

    return render_template(
        "reports.html",

        # Summary values
        total_students=total_students,
        total_faculty=total_faculty,
        total_activities=total_activities,
        total_events=total_events,
        total_registrations=total_registrations,
        total_attendance=total_attendance,
        total_present=total_present,
        total_absent=total_absent,

        # Percentage
        overall_percentage=overall_percentage,

        # Event-wise report
        event_reports=event_reports,

        # Date-wise report
        from_date=selected_date,
        date_report=date_report,
        datewise_report=date_report
    )


# =========================================================
# TEST EVENT REGISTRATIONS
# =========================================================

@app.route("/test_event_registrations")
def test_event_registrations():

    if not is_logged_in():
        return redirect("/login")

    if not is_admin():
        return "Access Denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM EventRegistration
    """)

    registrations = cursor.fetchall()

    cursor.close()
    conn.close()

    return str(registrations)


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)