from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from models import db, User, Subject, Result, ResultItem
from utils import newPassword, verifyPassword, save_image
import os
from datetime import date
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.before_request
def before_request():
    db.connect(reuse_if_open=True)

@app.after_request
def after_request(response):
    db.close()
    return response


@app.context_processor
def inject_user():
    user = None
    if 'user_id' in session:
        try:
            user = User.get_by_id(session['user_id'])
        except User.DoesNotExist:
            user = None
    return dict(user=user)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first.', 'warning')
            return redirect(url_for('login'))
        user = User.get_by_id(session['user_id'])
        if user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        roll_no = request.form['roll_no']
        password = request.form['password']
        image = request.files.get('image')

        if not all([name, email, roll_no, password]):
            flash('Please fill all required fields.', 'danger')
            return redirect(url_for('register'))

        if User.select().where((User.email == email) | (User.roll_no == roll_no)).exists():
            flash('Email or Roll Number already registered.', 'danger')
            return redirect(url_for('register'))

        filename = None
        if image and image.filename != '':
            filename = save_image(image, app.config['UPLOAD_FOLDER'])

        hashed_password = newPassword(password)
        user = User.create(
            name=name,
            email=email,
            roll_no=roll_no,
            password=hashed_password,
            image=filename,
            role='student' 
        )
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            user = User.get(User.email == email)
            if verifyPassword(user.password, password):
                session['user_id'] = user.id
                session['user_name'] = user.name
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Incorrect password.', 'danger')
        except User.DoesNotExist:
            flash('User not found.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))

    user = User.get_by_id(session['user_id'])
    subjects = Subject.select()
    results = Result.select().where(Result.student == user).order_by(Result.declaration_date.desc()) if user.role == 'student' else None

    return render_template('dashboard.html', subjects=subjects, results=results)


@app.route('/subjects/edit/<int:subject_id>', methods=['GET', 'POST'])
def edit_subject(subject_id):
    subject = Subject.get_or_none(Subject.id == subject_id)
    if not subject:
        flash('Subject not found.', 'danger')
        return redirect(url_for('manage_subjects'))
    if request.method == 'POST':
        subject.sub_code = request.form['sub_code']
        subject.name = request.form['sub_name']
        subject.save()
        flash('Subject updated successfully!', 'success')
        return redirect(url_for('manage_subjects'))
    return render_template('edit_subject.html', subject=subject)

@app.route('/subjects/delete/<int:subject_id>', methods=['POST'])
def delete_subject(subject_id):
    subject = Subject.get_or_none(Subject.id == subject_id)
    if not subject:
        flash('Subject not found.', 'danger')
    else:
        subject.delete_instance()
        flash('Subject deleted successfully!', 'success')
    return redirect(url_for('manage_subjects'))



@app.route('/admin/subjects', methods=['GET', 'POST'])
@admin_required
def manage_subjects():
    if request.method == 'POST':
        sub_code = request.form['sub_code'].strip()
        sub_name = request.form['sub_name'].strip()
        if not sub_code or not sub_name:
            flash('Subject code and name are required.', 'danger')
        elif Subject.select().where(Subject.sub_code == sub_code).exists():
            flash('Subject code already exists.', 'danger')
        else:
            Subject.create(sub_code=sub_code, name=sub_name)
            flash('Subject added successfully.', 'success')
        return redirect(url_for('manage_subjects'))

    subjects = Subject.select()
    return render_template('manage_subjects.html', subjects=subjects)


@app.route('/admin/declare_result', methods=['GET', 'POST'])
@admin_required
def declare_result():
    subjects = Subject.select()
    if request.method == 'POST':
        student_roll = request.form['student_roll'].strip()
        try:
            student = User.get(User.roll_no == student_roll)
        except User.DoesNotExist:
            flash('Student not found.', 'danger')
            return redirect(url_for('declare_result'))

        result = Result.create(student=student, declaration_date=date.today())

        for subject in subjects:
            marks = request.form.get(f'marks_{subject.sub_code}')
            total = request.form.get(f'total_{subject.sub_code}')
            if marks is None or total is None:
                continue
            try:
                marks = int(marks)
                total = int(total)
            except ValueError:
                flash(f'Invalid marks for subject {subject.sub_code}', 'danger')
                result.delete_instance(recursive=True)
                return redirect(url_for('declare_result'))

            ResultItem.create(result=result, subject=subject, marks_obtained=marks, total_marks=total)

        flash('Result declared successfully.', 'success')
        return redirect(url_for('declare_result'))

    return render_template('declare_result.html', subjects=subjects)


@app.route('/results/<int:result_id>')
def results(result_id):
    result = Result.get_or_none(Result.id == result_id)
    if not result:
        flash('Result not found.', 'danger')
        return redirect(url_for('dashboard'))

    items = ResultItem.select().where(ResultItem.result == result)

    
    total_obtained = sum(item.marks_obtained for item in items)
    total_possible = sum(item.total_marks for item in items)
    percentage = (total_obtained / total_possible) * 100 if total_possible > 0 else 0

    return render_template(
        'results.html',
        result=result,
        items=items,
        total_obtained=total_obtained,
        total_possible=total_possible,
        percentage=percentage
    )



@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
