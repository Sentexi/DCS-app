from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db, login_manager
from app.models import User
from app.models import apply_skills

from . import auth_bp 

# For Flask-Login: user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register route
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        # Basic validation (expand as needed)
        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('auth.register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered.')
            return redirect(url_for('auth.register'))
        hashed_pw = generate_password_hash(password)
        user = User(username=username, email=email, password=hashed_pw)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html')

# Login route
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully.')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid email or password.')
    return render_template('auth/login.html')

# Logout route
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('auth.login'))

@auth_bp.route('/survey', methods=['GET', 'POST'])
@login_required
def survey():
    # If survey already done, redirect to dashboard
    if current_user.date_joined_choice:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        date_joined_choice = request.form.get('date_joined_choice')
        judge_choice = request.form.get('judge_choice')
        if not date_joined_choice or not judge_choice:
            flash('Please answer all questions!', 'danger')
            return render_template('auth/survey.html')

        current_user.date_joined_choice = date_joined_choice
        current_user.judge_choice = judge_choice
        apply_skills(current_user)
        db.session.commit()
        flash('Thanks for your answers! Your skills have been set.', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('auth/survey.html')