from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from . import profile_bp

@profile_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def view():
    if request.method == 'POST':
        # Allow editing username and email only
        username = request.form.get('username')
        email = request.form.get('email')
        if username and username != current_user.username:
            current_user.username = username
        if email and email != current_user.email:
            current_user.email = email
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('profile.view'))
    return render_template('profile/view.html')
