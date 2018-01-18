from flask_mail import Message
from argon2 import PasswordHasher
from psycopg2 import IntegrityError
from validate_email import validate_email
from argon2.exceptions import VerifyMismatchError
from file_host.helpers import get_db_connection
from flask import (abort, Blueprint, current_app, flash, g, redirect, request,
                   session, render_template, url_for)

blueprint = Blueprint('user', __name__, template_folder='templates')


# call this to logout instead of session.pop directly just in case the
# logout procedure ever chagnes
def _logout():
    session.pop('site_user_id', None)


def _login(site_user_id):
    session['site_user_id'] = site_user_id
    # TODO: log login to database


def _is_valid_password(pass1, pass2):
    if pass1 == '':
        flash('Password may not be empty')
        return False
    if pass1 != pass2:
        flash('Passwords do not match')
        return False
    return True


@blueprint.route('/login/', methods=['GET', 'POST'])
def login():
    this_page = 'user/login.html'
    if request.method == 'POST':
        hasher = PasswordHasher()
        db_connection = get_db_connection()
        db_cursor = db_connection.cursor()
        db_cursor.execute('select site_user_id, password from site_user '
                          'where email = %s;', (request.form['email'],))
        db_user = db_cursor.fetchone()
        if db_user is not None:
            db_user_id = db_user[0]
            db_password = db_user[1]
        else:
            flash('Invalid email or password')
            return render_template(this_page)
        # TODO: prevent login when already logged in
        try:
            hasher.verify(db_password, request.form['password'])
            _login(db_user_id)
            return redirect(url_for('index.index'))
        except VerifyMismatchError:
            flash('Invalid email or password')
            render_template(this_page)
    return render_template(this_page)


@blueprint.route('/register/', methods=['GET', 'POST'])
def register():
    this_page = 'user/register.html'
    if request.method == 'POST':
        if not _is_valid_password(request.form['password'],
                                  request.form['password_confirmation']):
            return render_template(this_page)
        if not validate_email(request.form['email']):
            flash('Improperly formatted email')
            return render_template(this_page)
        # TODO: prevent registration when logged in
        with get_db_connection() as db_connection:
            db_cursor = db_connection.cursor()
            hasher = PasswordHasher()
            password_hash = hasher.hash(request.form['password'])
            try:
                db_cursor.execute('insert into site_user (email, password) '
                                  'values (%s, %s);', (request.form['email'],
                                                       password_hash))
            except IntegrityError:
                flash('This email is already associated with an account')
                return render_template(this_page)
            db_cursor.execute('select * from lastval();')
            new_site_user_id = db_cursor.fetchone()[0]
            db_cursor.callproc(
                'create_registration_confirmation_entry', [new_site_user_id])
            registration_confirmation_url = db_cursor.fetchone()[0]
            mail_msg = Message('Welcome', recipients=[request.form['email']])
            mail_msg.html = ('Please click the following link to complete '
                             'your registration: '
                             '<br><a href={0}/register/{1}/{2}>'
                             '{0}/register/{1}/{2}</a>'
                             .format(current_app.config['SERVER_NAME'],
                                     new_site_user_id,
                                     registration_confirmation_url))
            current_app.config['mail'].send(mail_msg)
            flash('A confirmation email has been sent. '
                  'Please check your inbox.')
            g.registration_confirmation_url = registration_confirmation_url
            return redirect(url_for('user.login'))
    return render_template(this_page)


@blueprint.route('/register/<site_user_id>/<confirmation_url>/')
def confirm_registration(site_user_id, confirmation_url):
    with get_db_connection() as db_connection:
        db_cursor = db_connection.cursor()
        db_cursor.callproc('confirm_registration',
                           [site_user_id, confirmation_url,
                            current_app.config['REG_CONFIRM_EXPR']])
        proc_result = db_cursor.fetchone()[0]
        if proc_result == 'failure_wrong_id':
            abort(404)
        flash('Registration confirmed. You have automatically been signed in')
        _login(site_user_id)
    return redirect(url_for('index.index'))


@blueprint.route('/password_reset/', methods=['GET', 'POST'])
def request_password_reset():
    this_page = 'user/request_password_reset.html'
    if request.method == 'POST':
        db_connection = get_db_connection()
        db_cursor = db_connection.cursor()
        db_cursor.execute('select a,b from '
                          'create_password_reset_entry(%s, %s, %s) '
                          'as (a text, b text);',
                          [request.form['email'], '127.0.0.1',
                           current_app.config['PASS_RESET_EXPR']])
        db_connection.commit()
        ret = db_cursor.fetchone()
        result_code = ret[0]
        if result_code == 'failure_not_account':
            flash('That email is not associated with any account')
        elif result_code == 'failure_existing_request':
            flash('A request to reset the given account\'s password has '
                  'already been filed. Please check your email for the '
                  'instructions to reset your password.')
        elif result_code == 'success':
            flash('Your password reset request has been sent. Please check '
                  'your email for further instructions.')
            g.password_reset_url = ret[1]
            # TODO: actually email the person the reset url
        else:
            flash('An error with the website has occured. The administrator '
                  'has automatically been notified and is working to fix the '
                  'issue. Please try again later.')
            # TODO: actually log the error and notify the administrator(s)
    return render_template(this_page)


@blueprint.route('/password_reset/<site_user_id>/<reset_url>/',
                 methods=['GET', 'POST'])
def reset_password(site_user_id, reset_url):
    this_page = 'user/reset_password.html'
    if request.method == 'POST':
        if not _is_valid_password(request.form['password'],
                                  request.form['password_confirmation']):
            return render_template(this_page)
        db_connection = get_db_connection()
        db_cursor = db_connection.cursor()
        hasher = PasswordHasher()
        password_hash = hasher.hash(request.form['password'])
        db_cursor.callproc('reset_site_user_password',
                           [site_user_id, reset_url, password_hash,
                            current_app.config['PASS_RESET_EXPR']])
        db_connection.commit()
        reset_password_code = db_cursor.fetchone()[0]
        if reset_password_code == 'failure_wrong_id':
            flash('Invalid parameters. Future invalid attempts will result in '
                  'a ban')
            # TODO: Actually log and act on fishy activity
            return render_template(this_page)
        elif reset_password_code == 'failure_expired':
            flash('This password reset URL has already expired. Please '
                  'request another reset.')
            return redirect(url_for('.request_password_reset'))
        elif reset_password_code == 'failure_redeemed':
            flash('This password reset URL has already been used to reset '
                  'your password. Please request another reset.')
            return redirect(url_for('.request_password_reset'))
        elif reset_password_code == 'failure_redeemed_exisiting_request':
            flash('This password reset URL has already been used to reset '
                  'your password. You have already filed a new request to '
                  'reset your password. Please check your email for further '
                  'instructions.')
            return render_template(this_page)
        elif reset_password_code == 'success':
            flash('Your password has been reset and you have been signed in.')
            _login(site_user_id)
            return redirect(url_for('index.index'))
        else:
            flash('An unknown error occurred. The administrator has '
                  'automatically been notified. Please try again later.')
            flash(reset_password_code)
            # TODO: Actually email the admin with an error report
            return render_template(this_page)
    return render_template(this_page)
