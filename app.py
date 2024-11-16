# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import json
import os
from datetime import datetime
import matplotlib
from datetime import datetime

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Clients.db'
app.config['SQLALCHEMY_BINDS'] = {
    'admin': 'sqlite:///Admin.db'
}

# Add this new context processor
@app.context_processor
def utility_processor():
    return {
        'now': datetime.now
    }

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    uuid = db.Column(db.String(36), unique=True, nullable=False)


class Admin(UserMixin, db.Model):
    __bind_key__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    uuid = db.Column(db.String(36), unique=True, nullable=False)


@login_manager.user_loader
def load_user(user_id):
    if session.get('user_type') == 'admin':
        return Admin.query.get(int(user_id))
    return User.query.get(int(user_id))


def initialize_admin():
    if not Admin.query.filter_by(email='admin1@gmail.com').first():
        admin = Admin(
            name='Admin1.0',
            email='admin1@gmail.com',
            password=generate_password_hash('y*c!0Ob4fwaV'),
            uuid=str(uuid.uuid4())
        )
        db.session.add(admin)
        db.session.commit()


def create_user_json(user):
    data = {
        'transactions': [],
        'total_in': 0,
        'total_out': 0,
        'current_balance': 0
    }
    with open(f'user_data/{user.uuid}.json', 'w') as f:
        json.dump(data, f)


@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        admin = Admin.query.filter_by(email=email).first()
        if admin and check_password_hash(admin.password, password):
            login_user(admin)
            session['user_type'] = 'admin'
            return redirect(url_for('admin_dashboard'))

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            session['user_type'] = 'user'
            return redirect(url_for('dashboard'))

        flash('Invalid email or password')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        currency = request.form.get('currency')

        if password != confirm_password:
            flash('Passwords do not match')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))

        user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            currency=currency,
            uuid=str(uuid.uuid4())
        )
        db.session.add(user)
        db.session.commit()

        os.makedirs('user_data', exist_ok=True)
        create_user_json(user)
        flash('Registration successful')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/dashboard')
@login_required
def dashboard():
    if session.get('user_type') != 'user':
        return redirect(url_for('admin_dashboard'))

    with open(f'user_data/{current_user.uuid}.json', 'r') as f:
        data = json.load(f)

    # Create matplotlib chart
    plt.figure(figsize=(10, 6))
    transactions = data['transactions'][-10:]  # Last 10 transactions
    dates = [t['date'] for t in transactions]
    amounts = [t['amount'] if t['type'] == 'in' else -t['amount'] for t in transactions]
    plt.plot(dates, amounts)
    plt.title('Recent Transactions')
    plt.xticks(rotation=45)

    # Convert plot to base64 string
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()
    plt.close()

    return render_template('dashboard.html',
                           balance=data['current_balance'],
                           total_in=data['total_in'],
                           total_out=data['total_out'],
                           plot_url=plot_url,
                           currency=current_user.currency)


@app.route('/add_transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        transaction_type = request.form.get('type')
        amount = float(request.form.get('amount'))
        name = request.form.get('name')
        description = request.form.get('description')

        with open(f'user_data/{current_user.uuid}.json', 'r+') as f:
            data = json.load(f)

            transaction = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'type': transaction_type,
                'amount': amount,
                'name': name,
                'description': description
            }

            data['transactions'].append(transaction)
            if transaction_type == 'in':
                data['total_in'] += amount
                data['current_balance'] += amount
            else:
                data['total_out'] += amount
                data['current_balance'] -= amount

            f.seek(0)
            json.dump(data, f)
            f.truncate()

        flash('Transaction added successfully')
        return redirect(url_for('transactions'))

    return render_template('add_transaction.html', currency=current_user.currency)


@app.route('/transactions')
@login_required
def transactions():
    with open(f'user_data/{current_user.uuid}.json', 'r') as f:
        data = json.load(f)
    return render_template('transactions.html',
                           transactions=data['transactions'],
                           currency=current_user.currency)


@app.route('/edit_transaction/<int:index>', methods=['POST'])
@login_required
def edit_transaction(index):
    with open(f'user_data/{current_user.uuid}.json', 'r+') as f:
        data = json.load(f)

        old_transaction = data['transactions'][index]
        new_amount = float(request.form.get('amount'))

        # Update totals
        if old_transaction['type'] == 'in':
            data['total_in'] -= old_transaction['amount']
            data['current_balance'] -= old_transaction['amount']
            data['total_in'] += new_amount
            data['current_balance'] += new_amount
        else:
            data['total_out'] -= old_transaction['amount']
            data['current_balance'] += old_transaction['amount']
            data['total_out'] += new_amount
            data['current_balance'] -= new_amount

        # Update transaction
        data['transactions'][index].update({
            'amount': new_amount,
            'name': request.form.get('name'),
            'description': request.form.get('description')
        })

        f.seek(0)
        json.dump(data, f)
        f.truncate()

    return redirect(url_for('transactions'))


@app.route('/delete_transaction/<int:index>')
@login_required
def delete_transaction(index):
    with open(f'user_data/{current_user.uuid}.json', 'r+') as f:
        data = json.load(f)
        transaction = data['transactions'].pop(index)

        if transaction['type'] == 'in':
            data['total_in'] -= transaction['amount']
            data['current_balance'] -= transaction['amount']
        else:
            data['total_out'] -= transaction['amount']
            data['current_balance'] += transaction['amount']

        f.seek(0)
        json.dump(data, f)
        f.truncate()

    return redirect(url_for('transactions'))


# Admin routes
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if session.get('user_type') != 'admin':
        return redirect(url_for('dashboard'))

    users_count = User.query.count()
    admins_count = Admin.query.count()

    return render_template('admin/dashboard.html', users=users_count, admins=admins_count)


@app.route('/admin/users')
@login_required
def admin_users():
    if session.get('user_type') != 'admin':
        return redirect(url_for('dashboard'))
    users = User.query.all()
    return render_template('admin/users.html', users=users)


@app.route('/admin/add_admin', methods=['GET', 'POST'])
@login_required
def admin_add_admin():
    if session.get('user_type') != 'admin':
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        if Admin.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('admin_add_admin'))

        admin = Admin(
            name=name,
            email=email,
            password=generate_password_hash(password),
            uuid=str(uuid.uuid4())
        )
        db.session.add(admin)
        db.session.commit()
        flash('Admin added successfully')
        return redirect(url_for('admin_admins'))

    return render_template('admin/add_admin.html')


@app.route('/admin/admins')
@login_required
def admin_admins():
    if session.get('user_type') != 'admin':
        return redirect(url_for('dashboard'))
    admins = Admin.query.all()
    return render_template('admin/admins.html', admins=admins)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('user_type', None)
    return redirect(url_for('login'))



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        initialize_admin()
    app.run(debug=True)