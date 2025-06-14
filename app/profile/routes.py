from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from . import profile_bp

@profile_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def view():
    if request.method == 'POST':
        # Allow editing name and email only
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        if first_name and first_name != current_user.first_name:
            current_user.first_name = first_name
        if last_name is not None and last_name != current_user.last_name:
            current_user.last_name = last_name
        if email and email != current_user.email:
            current_user.email = email
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('profile.view'))
    return render_template('profile/view.html')
