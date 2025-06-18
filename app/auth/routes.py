from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from app.extensions import db, login_manager
from app.models import User, PendingUser
from app.models import apply_skills
from app.utils import send_email, generate_token, confirm_token

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
        first_name = request.form['first_name']
        last_name = request.form.get('last_name')
        email = request.form['email']
        password = request.form['password']
        password2 = request.form['password2']
        # Basic validation (expand as needed)
        if User.query.filter_by(first_name=first_name, last_name=last_name).first():
            flash('User with that name already exists.')
            return redirect(url_for('auth.register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered.')
            return redirect(url_for('auth.register'))
        if password != password2:
            flash('Passwords do not match.')
            return redirect(url_for('auth.register'))
        hashed_pw = generate_password_hash(password)
        pending = PendingUser(first_name=first_name, last_name=last_name, email=email, password=hashed_pw)
        db.session.add(pending)
        db.session.commit()
        token = generate_token(email, 'email-confirm')
        confirm_url = url_for('auth.confirm_email', token=token, _external=True)
        send_email(email, 'Confirm your registration', f'Click the link to confirm your account: {confirm_url}')
        flash('Registration successful! Please check your email to confirm your account.')
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


# Forgot password
@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            token = generate_token(email, 'password-reset')
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            send_email(email, 'Password Reset', f'Reset your password here: {reset_url}')
        flash('If that email exists in our system, a reset link has been sent.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = confirm_token(token, 'password-reset')
    if not email:
        flash('The reset link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.login'))
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        password = request.form['password']
        password2 = request.form['password2']
        if password != password2:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/reset_password.html')
        user.password = generate_password_hash(password)
        db.session.commit()
        flash('Password updated. You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html')

# Email confirmation
@auth_bp.route('/confirm/<token>')
def confirm_email(token):
    email = confirm_token(token, 'email-confirm')
    if not email:
        flash('The confirmation link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.login'))
    pending = PendingUser.query.filter_by(email=email).first()
    if not pending:
        flash('Account already confirmed or does not exist.', 'warning')
        return redirect(url_for('auth.login'))
    user = User(first_name=pending.first_name, last_name=pending.last_name, email=pending.email, password=pending.password)
    db.session.add(user)
    db.session.delete(pending)
    db.session.commit()
    flash('Account confirmed. You can now log in.', 'success')
    return redirect(url_for('auth.login'))

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
        languages = request.form.getlist('languages')
        chair_conf = request.form.get('chair_confidence')
        wing_conf = request.form.get('wing_confidence')
        if not date_joined_choice or not chair_conf or not wing_conf:
            flash('Please answer all questions!', 'danger')
            return render_template('auth/survey.html')

        if chair_conf in ('very', 'rather'):
            judge_choice = 'chair'
        elif wing_conf in ('very', 'rather'):
            judge_choice = 'wing'
        else:
            judge_choice = 'no'

        current_user.date_joined_choice = date_joined_choice
        current_user.judge_choice = judge_choice
        current_user.languages = ','.join(languages)
        apply_skills(current_user)
        db.session.commit()
        flash('Thanks for your answers! Your skills have been set.', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('auth/survey.html')