from flask import Flask, render_template, request, redirect, Response, session
import sqlite3
from datetime import date

app = Flask(__name__)
app.secret_key = "worker_management_secret"

DB_NAME = "database.db"

# ---------------- DATABASE INIT ----------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Workers table
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

    # Users table (LOGIN + ROLES)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    # Default admin
    cur.execute("SELECT * FROM users WHERE username=?", ("admin",))
    if not cur.fetchone():
        cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    ("admin", "admin123", "admin"))

    # Default viewer
    cur.execute("SELECT * FROM users WHERE username=?", ("viewer",))
    if not cur.fetchone():
        cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    ("viewer", "viewer123", "viewer"))

    conn.commit()
    conn.close()


# ---------------- HOME (DASHBOARD) ----------------
@app.route('/')
def index():

    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("SELECT * FROM workers")
    workers = cur.fetchall()

    # Dashboard stats
    cur.execute("SELECT COUNT(*) FROM workers")
    total_workers = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT department) FROM workers")
    total_departments = cur.fetchone()[0]

    cur.execute("SELECT AVG(salary) FROM workers")
    avg_salary = cur.fetchone()[0] or 0

    # 📊 CHART 1: Department distribution
    cur.execute("SELECT department, COUNT(*) FROM workers GROUP BY department")
    dept_data = cur.fetchall()

    departments = [row[0] for row in dept_data]
    dept_counts = [row[1] for row in dept_data]

    # 📊 CHART 2: Salary per worker
    cur.execute("SELECT name, salary FROM workers")
    salary_data = cur.fetchall()

    names = [row[0] for row in salary_data]
    salaries = [row[1] for row in salary_data]

    conn.close()

    return render_template(
        "index.html",
        workers=workers,
        total_workers=total_workers,
        total_departments=total_departments,
        avg_salary=avg_salary,
        departments=departments,
        dept_counts=dept_counts,
        names=names,
        salaries=salaries
    )


# ---------------- ADD WORKER ----------------
@app.route('/add', methods=['GET', 'POST'])
def add_worker():

    if 'user' not in session:
        return redirect('/login')

    if session.get('role') != 'admin':
        return "Access Denied (Admin Only)"

    if request.method == "POST":

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO workers
        (worker_id, name, age, department, salary, status, join_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            request.form['worker_id'],
            request.form['name'],
            request.form['age'],
            request.form['department'],
            request.form['salary'],
            request.form['status'],
            date.today().strftime("%d-%m-%Y")
        ))

        conn.commit()
        conn.close()

        return redirect('/')

    return render_template("add_worker.html")


# ---------------- EDIT WORKER ----------------
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_worker(id):

    if 'user' not in session:
        return redirect('/login')

    if session.get('role') != 'admin':
        return "Access Denied (Admin Only)"

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    if request.method == "POST":

        cur.execute("""
        UPDATE workers
        SET worker_id=?, name=?, age=?, department=?, salary=?, status=?
        WHERE id=?
        """,
        (
            request.form['worker_id'],
            request.form['name'],
            request.form['age'],
            request.form['department'],
            request.form['salary'],
            request.form['status'],
            id
        ))

        conn.commit()
        conn.close()
        return redirect('/')

    cur.execute("SELECT * FROM workers WHERE id=?", (id,))
    worker = cur.fetchone()
    conn.close()

    return render_template("edit_worker.html", worker=worker)


# ---------------- DELETE WORKER ----------------
@app.route('/delete/<int:id>')
def delete_worker(id):

    if 'user' not in session:
        return redirect('/login')

    if session.get('role') != 'admin':
        return "Access Denied (Admin Only)"

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("DELETE FROM workers WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect('/')


# ---------------- SEARCH ----------------
@app.route('/search')
def search():

    if 'user' not in session:
        return redirect('/login')

    keyword = request.args.get('keyword')

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM workers
        WHERE worker_id LIKE ?
        OR name LIKE ?
        OR department LIKE ?
    """,
    (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))

    workers = cur.fetchall()

    conn.close()

    return render_template("index.html", workers=workers)


# ---------------- EXPORT CSV ----------------
@app.route('/export')
def export():

    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("SELECT * FROM workers")
    workers = cur.fetchall()

    conn.close()

    def generate():
        yield "ID,Worker ID,Name,Age,Department,Salary,Status,Join Date\n"
        for w in workers:
            yield ",".join(map(str, w)) + "\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=workers.csv"}
    )


# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():

    error = None

    if request.method == "POST":

        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        cur.execute("""
            SELECT username, role 
            FROM users 
            WHERE username=? AND password=?
        """, (username, password))

        user = cur.fetchone()
        conn.close()

        if user:
            session['user'] = user[0]
            session['role'] = user[1]
            return redirect('/')
        else:
            error = "Invalid Username or Password"

    return render_template('login.html', error=error)


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ---------------- INIT ----------------
init_db()

if __name__ == "__main__":
    app.run(debug=True)