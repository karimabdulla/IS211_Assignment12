from flask import Flask, render_template, request, session, redirect, abort
from db import init_db, query, insert, delete, close_connection
from sqlite3 import IntegrityError
import datetime

app = Flask(__name__)
app.secret_key = "5c8fce510fa3c5f9bb251cd1b13fd6eb"


def check_auth():
    if "auth" in session:
        return True
    return False


# Index route
@app.route('/')
def index():
    init_db()

    # Check if authenticated, if not, redirect to login page
    if not check_auth():
        return redirect("/login")
    # Otherwise redirect to the dashboard
    return redirect("/dashboard")


# Login route - GET
@app.route('/login')
def get_login():
    if not check_auth():
        return render_template("auth/login.html",
                               alert=session.pop("alert", None)
                               )
    # Otherwise redirect to the dashboard
    else:
        return redirect("/dashboard")


# Login route - POST
@app.route('/login', methods=['POST'])
def post_login():
    def authenticate(username, password):
        auth = query("select first_name,\
                            last_name,\
                            username\
                            from users\
                            where username = ? and pw = ?",
                     (username, password),
                     True
                     )
        # Returns the result, type None or dict
        return auth

    auth = authenticate(request.form["username"], request.form["password"])
    if auth:
        session['auth'] = auth
        session["alert"] = {
            "level": "success",
            "message": "Successfully logged in!"
        }
        return redirect("/dashboard")
    else:
        session["alert"] = {
            "level": "danger",
            "message": "Could not validate the provided credentials. Please try again!"
        }
        return redirect("/login")


# Logout route
@app.route('/logout')
def logout():
    if check_auth():
        session.pop("auth", None)
    # Redirect to the application root
    return redirect("/")


# Dashboard route
@app.route('/dashboard')
def dashboard():
    if not check_auth():
        return redirect("/login")
    breadcrumbs = [{"title": "Dashboard", "url": "/"}]
    # Query the database to return students and quizzes
    students = query("select * from students\
                         order by last_name, first_name asc")
    quizzes = query("select * from quizzes\
                        order by quiz_date asc")
    return render_template("teacher/dashboard.html",
                           breadcrumbs=breadcrumbs,
                           students=students,
                           quizzes=quizzes,
                           alert=session.pop("alert", None)
                           )


# Add student route - GET
@app.route('/student/add')
def get_add_student():
    """
    Function to render the add_student template and pass errors and alerts.
    """

    # Check if authenticated, if not, redirect to login page
    if not check_auth():
        return redirect("/login")

    # Set the breadcrumbs for the route
    breadcrumbs = [
        {"title": "Dashboard", "url": "/dashboard"},
        {"title": "Add Student", "url": "/student/add"}
    ]
    return render_template("teacher/add_student.html",
                           breadcrumbs=breadcrumbs,
                           errors=session.pop("errors", None),
                           alert=session.pop("alert", None)
                           )


# Add student route - POST
@app.route('/student/add', methods=['POST'])
def post_add_student():
    if not check_auth():
        return redirect("/login")

    def validate(form):
        validation_errors = {"messages": {}, "input": {}}

        # Validate first_name input field
        if (form["first_name"].strip() == ""):
            validation_errors["messages"].update(
                {"first_name": "First name is a required field."})

        # Validate last_name input field
        if (form["last_name"].strip() == ""):
            validation_errors["messages"].update(
                {"last_name": "Last name is a required field."})

        # If there are messages in the dictionary, add the original input
        if validation_errors["messages"]:
            validation_errors.update({"input": dict(form)})
        # Otherwise reset the dictionary to empty
        else:
            validation_errors = {}

        # Return the dictionary
        return validation_errors

    # Call the validate function and store the return value in a variable
    validation = validate(request.form)
    # If the dictionary is empty, insert the student in the database
    if not validation:
        row_id = insert("Insert into students\
                    (first_name, last_name)\
                    values (?, ?)",
                        (request.form["first_name"], request.form["last_name"]))

        # Add an alert message to the session to be displayed on the page
        session["alert"] = {
            "level": "success",
            "message": "Student added successfully!"
        }

        # Redirect back to the dashboard and scroll to the new student row
        return redirect("/dashboard#student-"+str(row_id))
    # Otherwise redirect back and display the error messages
    else:
        # Add the errors to be displayed to the session
        session["errors"] = validation
        # Redirect back to /student/add
        return redirect("/student/add")


# View student route
@app.route('/student/<id>')
def get_student(id):
    if not check_auth():
        return redirect("/login")

    # Query the database to find the student with the
    # id number passed in
    student = query("select * from students\
                      where id = ?", (id, ), True)

    if not student:
        # Add an alert message to the session
        session["alert"] = {
            "level": "danger",
            "message": "Could not find a student with ID # {}.".
            format(str(id))
        }
        return redirect("/dashboard")

    quizzes = query("select q.*, sq.score from quizzes q\
                    inner join student_quiz sq\
                    on sq.student_id = ?\
                    and sq.quiz_id = q.id\
                    order by quiz_date asc", (id, ))

    # Set the breadcrumbs for the route
    breadcrumbs = [
        {"title": "Dashboard", "url": "/dashboard"},
        {"title": "Student", "url": "/student/"+id}
    ]
    # Render the view_student template, passing in
    # breadcrumbs, student, quizzes, and alerts
    return render_template("teacher/view_student.html",
                           breadcrumbs=breadcrumbs,
                           student=student,
                           quizzes=quizzes,
                           alert=session.pop("alert", None)
                           )


# Delete student route - POST
@app.route('/student/<id>/delete', methods=['POST'])
def post_delete_student(id):
    if not check_auth():
        return redirect("/login")

    student = query("select * from students\
                      where id = ?", (id, ), True)

    if not student:
        # Add an alert message to the session
        session["alert"] = {
            "level": "danger",
            "message": "Could not find a student with ID # {}."
            .format(str(id))
        }
        return redirect("/dashboard")

    # Execute the delete statements
    delete("delete from student_quiz where student_id = ?", (id, ))
    delete("delete from students where id = ?", (id, ))

    # Add an alert message to the session
    session["alert"] = {
        "level": "success",
        "message": "Deleted student and quiz results \
                    for student ID # {} successfully."
        .format(str(id))
    }
    return redirect("/dashboard")


# Add quiz route - GET
@app.route('/quiz/add')
def get_add_quiz():
    if not check_auth():
        return redirect("/login")

    # Set the breadcrumbs for the route
    breadcrumbs = [
        {"title": "Dashboard", "url": "/dashboard"},
        {"title": "Add Quiz", "url": "/quiz/add"}
    ]
    return render_template("teacher/add_quiz.html",
                           breadcrumbs=breadcrumbs,
                           errors=session.pop("errors", None),
                           alert=session.pop("alert", None)
                           )


# Add quiz route - POST
@app.route('/quiz/add', methods=['POST'])
def post_add_quiz():
    if not check_auth():
        return redirect("/login")

    def validate(form):

        # Dictionary to store error messages and original input in
        validation_errors = {"messages": {}, "input": {}}

        # Validate quiz_subject input field
        if (form["quiz_subject"].strip() == ""):
            validation_errors["messages"].update(
                {"quiz_subject": "Quiz Subject is a required field."})

        # Validate question_count input field
        if (form["question_count"].strip() == ""):
            validation_errors["messages"].update(
                {"question_count": "# of Questions is a required field."})
        else:
            try:
               if int(form["question_count"]) < 0:
                   raise ValueError
            except ValueError:
                validation_errors["messages"].update(
                    {"question_count": "Please enter a valid number."})

        # Validate quiz_date input field
        if (form["quiz_date"].strip() == ""):
            validation_errors["messages"].update(
                {"quiz_date": "Quiz Date is a required field."})
        else:
            try:
                datetime.datetime.strptime(form["quiz_date"], '%Y-%m-%d')
            except ValueError:
                validation_errors["messages"].update(
                    {"quiz_date": "A date in YYYY-MM-DD format is required."})

        # If there are messages in the dictionary, add the original input
        if validation_errors["messages"]:
            validation_errors.update({"input": dict(form)})
        # Otherwise reset the dictionary to empty
        else:
            validation_errors = {}

        # Return the dictionary
        return validation_errors

    # Call the validate function and store the return value in a variable
    validation = validate(request.form)
    # If the dictionary is empty, insert the quiz in the database
    if not validation:
        row_id = insert("Insert into quizzes\
                        (quiz_subject, question_count, quiz_date)\
                        values (?, ?, ?)", (
                        request.form["quiz_subject"],
                        request.form["question_count"],
                        request.form["quiz_date"]
                        ))

        # Add an alert message to the session to be displayed on the page
        session["alert"] = {
            "level": "success",
            "message": "Quiz added successfully!"
        }

        # Redirect back to the dashboard and scroll to the new student row
        return redirect("/dashboard#quiz-"+str(row_id))
    # Otherwise redirect back and display the error messages
    else:
        # Add the errors to be displayed to the session
        session["errors"] = validation
        # Redirect back to /quiz/add
        return redirect("/quiz/add")


# Delete quiz route - POST
@app.route('/quiz/<id>/delete', methods=['POST'])
def post_delete_quiz(id):
    if not check_auth():
        return redirect("/login")

    quiz = query("select * from quizzes\
                      where id = ?", (id, ), True)

    if not quiz:
        # Add an alert message to the session
        session["alert"] = {
            "level": "danger",
            "message": "Could not find a quiz with ID # {}."
            .format(str(id))
        }
        return redirect("/dashboard")

    # Execute the delete statements
    delete("delete from student_quiz where quiz_id = ?", (id, ))
    delete("delete from quizzes where id = ?", (id, ))

    # Add an alert message to the session
    session["alert"] = {
        "level": "success",
        "message": "Deleted quiz and results \
                    for quiz ID # {} successfully."
        .format(str(id))
    }
    return redirect("/dashboard")


# View quiz results route
@app.route('/quiz/<id>/results')
def get_quiz_results(id):
    authed = check_auth()
    quiz = query("select * from quizzes\
                      where id = ?", (id, ), True)
    if not quiz:
        if authed:
            session["alert"] = {
                "level": "danger",
                "message": "Could not find a quiz with ID # {}.".
                format(str(id))
            }
            return redirect("/dashboard")
        # Otherwise return an HTTP 404 error
        else:
            abort(404)

    # Get the results for the quiz
    results = query("select s.*, sq.score from students s\
                    inner join student_quiz sq\
                    on sq.quiz_id = ?\
                    and sq.student_id = s.id\
                    order by last_name, first_name asc", (id, ))

    # Set the breadcrumbs for the route if authenticated
    breadcrumbs = [
        {"title": "Dashboard", "url": "/dashboard"},
        {"title": "Quiz Results", "url": "/quiz/"+id+"/results"}
    ] if authed else []
    # Render the view_results template, passing in
    # breadcrumbs, quiz, results, and alerts
    return render_template("shared/view_results.html",
                           breadcrumbs=breadcrumbs,
                           quiz=quiz,
                           results=results,
                           authed=authed,
                           alert=session.pop("alert", None)
                           )


# Delete quiz result route - POST
@app.route('/quiz/<quiz_id>/results/<student_id>/delete', methods=['POST'])
def get_delete_quiz_result(quiz_id, student_id):
    result = query("select * from student_quiz\
                      where quiz_id = ? and student_id = ?",
                   (quiz_id, student_id), True)

    if not result:
        session["alert"] = {
            "level": "danger",
            "message": "Could not find a result for quiz ID # {} \
                        and student ID # {}."
            .format(str(quiz_id), str(student_id))
        }
        return redirect("/dashboard")

    delete("delete from student_quiz where\
            quiz_id = ? and student_id = ?", (quiz_id, student_id))

    # Add an alert message to the session
    session["alert"] = {
        "level": "success",
        "message": "Deleted quiz result successfully."
    }
    return redirect("/dashboard")


@app.route('/results/add')
def get_add_result():
    breadcrumbs = [
        {"title": "Dashboard", "url": "/dashboard"},
        {"title": "Add Quiz Result", "url": "/results/add"}
    ]
    # Query the database to return students and quizzes
    students = query("select * from students\
                         order by last_name, first_name asc")
    quizzes = query("select * from quizzes\
                        order by quiz_date asc")

    return render_template("teacher/add_result.html",
                           breadcrumbs=breadcrumbs,
                           students=students,
                           quizzes=quizzes,
                           errors=session.pop("errors", None),
                           alert=session.pop("alert", None)
                           )


@app.route('/results/add', methods=['POST'])
def post_add_result():

    def validate(form):
        validation_errors = {"messages": {}, "input": {}}

        if (form["student_id"].strip() == ""):
            validation_errors["messages"].update(
                {"student_id": "Please select a student from the list."})
        else:
            try:
               int(form["student_id"])
            except ValueError:
                validation_errors["messages"].update(
                    {"student_id": "Please select a student from the list."})

        # Validate quiz_id input field
        if (form["quiz_id"].strip() == ""):
            validation_errors["messages"].update(
                {"quiz_id": "Please select a quiz from the list."})
        else:
            try:
               int(form["quiz_id"])
            except ValueError:
                validation_errors["messages"].update(
                    {"quiz_id": "Please select a quiz from the list."})

        # Validate score input field
        if (form["score"].strip() == ""):
            validation_errors["messages"].update(
                {"score": "Grade is a required field."})
        else:
            try:
               score = int(form["score"])
               if score < 0 or score > 100:
                   raise ValueError
            except ValueError:
                validation_errors["messages"].update(
                    {"score": "Please enter a number between 0 and 100."})

        # If there are messages in the dictionary, add the original input
        if validation_errors["messages"]:
            validation_errors.update({"input": dict(form)})
        # Otherwise reset the dictionary to empty
        else:
            validation_errors = {}

        # Return the dictionary
        return validation_errors

    # Call the validate function and store the return value in a variable
    validation = validate(request.form)
    # If the dictionary is empty, insert the student in the database
    if not validation:
        try:
            insert("Insert into student_quiz\
                    (student_id, quiz_id, score)\
                    values (?, ?, ?)",
                   (request.form["student_id"], request.form["quiz_id"], request.form["score"]))

            # Add an alert message to the session to be displayed on the page
            session["alert"] = {
                "level": "success",
                "message": "Quiz result added for student ID # {} successfully!"
                .format(request.form["student_id"])
            }

            # Redirect back to the dashboard
            return redirect("/dashboard")

        except IntegrityError:
            # Add an alert message to the session to be displayed on the page
            session["alert"] = {
                "level": "danger",
                "message": "Quiz result could not be added for \
                            quiz ID # {} and student ID # {} because \
                            an entry already exists. Delete the current \
                            quiz result for the student first."
                .format(request.form["quiz_id"],
                        request.form["student_id"])
            }

            # Redirect back to the dashboard
            return redirect("/dashboard")

    # Otherwise redirect back and display the error messages
    else:
        # Add the errors to be displayed to the session
        session["errors"] = validation
        # Redirect back to /student/add
        return redirect("/results/add")


@app.teardown_appcontext
def teardown(exception):
    close_connection(exception)


if __name__ == '__main__':
    app.run()