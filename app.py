from flask import Flask, render_template, request, redirect
import sqlite3
import csv
from flask import Response
from datetime import date
from flask import session

app = Flask(__name__)
app.secret_key = "worker_management_secret"

# Create Database
def init_db():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS workers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id TEXT UNIQUE,
    name TEXT NOT NULL,
    age INTEGER,
    department TEXT,
    salary REAL,
    status TEXT,
    join_date TEXT
)
""")

    conn.commit()
    conn.close()

init_db()


# Home Page
@app.route('/')
def index():

    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM workers")
    workers = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM workers")
    total_workers = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT department) FROM workers")
    total_departments = cur.fetchone()[0]

    cur.execute("SELECT AVG(salary) FROM workers")
    avg_salary = cur.fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        workers=workers,
        total_workers=total_workers,
        total_departments=total_departments,
        avg_salary=avg_salary
    )

# Add Worker
@app.route('/add', methods=['GET', 'POST'])
def add_worker():

    if 'user' not in session:
      return redirect('/login')

    if request.method == "POST":

        worker_id = request.form['worker_id']
        name = request.form['name']
        age = request.form['age']
        department = request.form['department']
        salary = request.form['salary']
        status = request.form['status']
        join_date = date.today().strftime("%d-%m-%Y")

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO workers
        (worker_id, name, age, department, salary, status, join_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (worker_id, name, age, department, salary, status, join_date))

        conn.commit()
        conn.close()

        return redirect('/')

    return render_template("add_worker.html")

# Edit Worker
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_worker(id):

    if 'user' not in session:
      return redirect('/login')

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    if request.method == "POST":

        worker_id = request.form['worker_id']
        name = request.form['name']
        age = request.form['age']
        department = request.form['department']
        salary = request.form['salary']
        status = request.form['status']

        cur.execute("""
        UPDATE workers
        SET worker_id=?, name=?, age=?, department=?, salary=?, status=?
        WHERE id=?
        """,
        (worker_id, name, age, department, salary, status, id))

        conn.commit()
        conn.close()

        return redirect('/')

    cur.execute("SELECT * FROM workers WHERE id=?", (id,))
    worker = cur.fetchone()

    conn.close()

    return render_template("edit_worker.html", worker=worker)
# Search Workers

@app.route('/search')
def search():

    keyword = request.args.get('keyword')

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM workers
        WHERE worker_id LIKE ?
        OR name LIKE ?
        OR department LIKE ?
    """,
    (f'%{keyword}%',
     f'%{keyword}%',
     f'%{keyword}%'))

    workers = cur.fetchall()

    # Dashboard statistics for search results
    total_workers = len(workers)

    departments = set()
    salaries = []

    for worker in workers:
        departments.add(worker[4])  # department column
        salaries.append(worker[5])  # salary column

    total_departments = len(departments)

    avg_salary = (
        round(sum(salaries) / len(salaries), 2)
        if salaries else 0
    )

    conn.close()

    return render_template(
        "index.html",
        workers=workers,
        total_workers=total_workers,
        total_departments=total_departments,
        avg_salary=avg_salary
    )

# Export Workers as CSV
@app.route('/export')
def export():

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM workers")
    workers = cur.fetchall()

    conn.close()

    def generate():

        yield "ID,Worker ID,Name,Age,Department,Salary\n"

        for worker in workers:
            yield ",".join(map(str, worker)) + "\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=workers.csv"
        }
    )

# Login

@app.route('/login', methods=['GET', 'POST'])
def login():

    error = None

    if request.method == "POST":

        username = request.form['username']
        password = request.form['password']

        if username == "admin" and password == "admin123":

            session['user'] = username

            return redirect('/')

        else:
            error = "Invalid Username or Password"

    return render_template('login.html', error=error)

# Logout
@app.route('/logout')
def logout():

    session.clear()

    return redirect('/login')

# Delete Worker
@app.route('/delete/<int:id>')
def delete_worker(id):

    if 'user' not in session:
      return redirect('/login')

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("DELETE FROM workers WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect('/')


init_db()

if __name__ == "__main__":
    app.run(debug=True)