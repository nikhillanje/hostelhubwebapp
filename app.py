# type: ignore
from flask import Flask
from flask_pymongo import PyMongo
from urllib.parse import quote_plus
from werkzeug.security import check_password_hash
from flask import (
    Flask, render_template, request, session,
    redirect, url_for, flash, jsonify,
    send_file, make_response
)

from flask_login import (
    LoginManager, UserMixin,
    login_user, logout_user,
    login_required, current_user
)

from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField,
    SubmitField, IntegerField, SelectField
)
from wtforms.validators import (
    InputRequired, Email, Length, ValidationError
)

from werkzeug.security import (
    check_password_hash, generate_password_hash
)
from werkzeug.utils import secure_filename

from flask_mail import Mail
from flask_bcrypt import Bcrypt
from flask_pymongo import PyMongo

from bson import ObjectId
from razorpay.errors import SignatureVerificationError
from twilio.rest import Client, Client as TwilioClient
from reportlab.pdfgen import canvas

from io import BytesIO
from functools import wraps

import requests
import razorpay
import bcrypt
import random
import string
import json
import os
import time

from datetime import datetime, date, timedelta


# =============================
# FLASK APP INIT
# =============================

app = Flask(__name__)
bcrypt = Bcrypt(app)

# =============================
# SECRET KEY & SESSION CONFIG
# =============================

app.secret_key = os.environ.get("SECRET_KEY")

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=20)

# =============================
# MAIL CONFIG (GMAIL)
# =============================

app.config.update(
    MAIL_SERVER="smtp.gmail.com",
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_USERNAME=os.environ.get("MAIL_USERNAME"),
    MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD")
)

mail = Mail(app)

# =============================
# MONGODB CONFIG (ATLAS)
# =============================

mongo_username = os.environ.get("MONGO_USERNAME")
mongo_password = quote_plus(os.environ.get("MONGO_PASSWORD"))
mongo_cluster = os.environ.get("MONGO_CLUSTER")
mongo_db = os.environ.get("MONGO_DB")

app.config["MONGO_URI"] = (
    f"mongodb+srv://{mongo_username}:{mongo_password}@"
    f"{mongo_cluster}/{mongo_db}?retryWrites=true&w=majority"
)

mongo = PyMongo(app)

attendance_col = mongo.db.attendance
users_collection = mongo.db.users
attendance_collection = mongo.db.attendance

# =============================
# FILE UPLOAD
# =============================

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# =============================
# FLASK-LOGIN
# =============================

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    return User(user) if user else None

# =============================
# USER MODEL
# =============================

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data["_id"])
        self.username = user_data["username"]
        self.password = user_data["password"]

# =============================
# FORMS
# =============================

class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[InputRequired()])
    username = StringField("Username", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])
    address = StringField("Address", validators=[InputRequired()])
    mobile_no = StringField("Mobile No", validators=[InputRequired()])
    email = StringField("Email", validators=[InputRequired(), Email()])

    academic_branch = SelectField(
        "Academic Branch",
        choices=[
            ("CSE", "Computer Science Engineering"),
            ("IT", "Information Technology"),
            ("ECE", "Electronics and Communication"),
            ("EEE", "Electrical and Electronics"),
            ("ME", "Mechanical Engineering"),
            ("CE", "Civil Engineering"),
            ("AI", "Artificial Intelligence"),
            ("DS", "Data Science"),
            ("CSBS", "Computer Science & Business Systems"),
        ],
        validators=[InputRequired()],
    )

    academic_year = SelectField(
        "Academic Year",
        choices=[
            ("1", "First Year"),
            ("2", "Second Year"),
            ("3", "Third Year"),
            ("4", "Fourth Year"),
        ],
        validators=[InputRequired()],
    )

    gender = SelectField(
        "Gender",
        choices=[("Male", "Male"), ("Female", "Female"), ("Other", "Other")]
    )

    submit = SubmitField("Register")

    def validate_username(self, username):
        if mongo.db.users.find_one({"username": username.data}):
            raise ValidationError("Username already exists.")

class LoginForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])
    captcha = StringField("Enter CAPTCHA", validators=[InputRequired()])
    submit = SubmitField("Login")

# =============================
# CAPTCHA
# =============================

def generate_captcha(length=6):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

# =============================
# RAZORPAY CONFIG
# =============================

RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET")

razorpay_client = razorpay.Client(
    auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
)

# =============================
# TWILIO CONFIG
# =============================

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

twilio_client = Client(
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN
)

@app.before_request
def session_timeout_check():
    allowed_routes = [
        'home',     
        'login',         
        'adminlogin',  
        'xHostelLogin', 
        'static',
        'register',
        'send-otp',
        'verify-otp',
        'forgot-password',
        'send-reset-otp',
        'verify-reset-otp',
        'reset-password',
        'adminsetbill',
        'samp'
    ]

    # Allow non-protected routes
    if request.endpoint in allowed_routes or request.endpoint is None:
        return

    # Require login ONLY for protected pages
    if not (
        session.get('logged_in') or
        session.get('admin_logged_in') or
        session.get('xadmin_logged_in')
    ):
        return redirect(url_for('login'))
    # ---------------------------
    # Session Timeout Logic
    # ---------------------------
    now = time.time()
    timeout_seconds = 20 * 60  # 20 minutes

    last_seen = session.get('last_active', now)

    if now - last_seen > timeout_seconds:
        session.clear()
        return redirect(url_for('login'))

    # Refresh user activity time
    session['last_active'] = now




def student_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('adminlogin'))
        return f(*args, **kwargs)
    return wrapper



def hostel_admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('xadmin_logged_in'):
            return redirect(url_for('xHostelLogin'))
        return f(*args, **kwargs)
    return wrapper




@app.after_request
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/notavl')
def notavl():
    return render_template('notavl.html')


@app.route("/samp")
def samp():
    return render_template("sample_logins.html")


#--------------------------------------------------------------------------------------------------#
# Students
@app.route("/")
def home():
    latest_helpline = mongo.db.helpline.find_one(sort=[('_id', -1)])
    helpline = latest_helpline['number'] if latest_helpline else "Not Set"
    return render_template("home.html", helpline = helpline)




@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if request.method == 'GET' or not form.validate_on_submit():
        session['captcha_text'] = generate_captcha()

    if form.validate_on_submit():

        if form.captcha.data != session.get('captcha_text'):
            flash('Incorrect CAPTCHA.', 'danger')
            session['captcha_text'] = generate_captcha()
            form.captcha.data = ''
            return render_template('login.html', form=form, captcha=session['captcha_text'])

        user_data = mongo.db.users.find_one({'username': form.username.data})
  
        password_correct = False

        if user_data:
            stored_pass = user_data['password']

            # Case 1: bcrypt
            if stored_pass.startswith("$2b$") or stored_pass.startswith("$2a$"):
                try:
                    password_correct = bcrypt.check_password_hash(stored_pass, form.password.data)
                except ValueError:
                    password_correct = False

            # Case 2: pbkdf2 (Werkzeug)
            elif stored_pass.startswith("pbkdf2:sha256"):
                try:
                    password_correct = check_password_hash(stored_pass, form.password.data)
                except:
                    password_correct = False

            # Case 3: scrypt (Werkzeug)
            elif stored_pass.startswith("scrypt:"):
                try:
                    password_correct = check_password_hash(stored_pass, form.password.data)
                except:
                    password_correct = False

            # Case 4: plain text
            else:
                password_correct = (stored_pass == form.password.data)

                if password_correct:
                    new_hash = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
                    mongo.db.users.update_one({'_id': user_data['_id']}, {'$set': {'password': new_hash}})

        if password_correct:

            if not user_data.get('confirmed', False):
                flash('Your account is not confirmed by admin yet.', 'warning')
                session['captcha_text'] = generate_captcha()
                form.captcha.data = ''
                return render_template('login.html', form=form, captcha=session['captcha_text'])

            login_user(User(user_data))
            session['_id'] = str(user_data['_id'])
            session['username'] = user_data['username']

            session['logged_in'] = True


            session.pop('captcha_text', None)
            return redirect(url_for('index'))

        else:
            flash('Invalid username or password', 'danger')
            session['captcha_text'] = generate_captcha()

    return render_template('login.html', form=form, captcha=session['captcha_text'])

@app.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.get_json()
    phone = data.get('phone', '').strip()

    # Validation
    if not phone or not phone.isdigit() or len(phone) != 10:
        return jsonify({'error': 'Invalid phone number'}), 400

    otp = str(random.randint(100000, 999999))

    # Save OTP with expiry (5 minutes)
    mongo.db.otp_store.update_one(
        {'phone': phone},
        {
            '$set': {
                'otp': otp,
                'created_at': datetime.utcnow(),
                'expires_at': datetime.utcnow() + timedelta(minutes=5)
            }
        },
        upsert=True
    )

    url = "https://www.fast2sms.com/dev/bulkV2"
    payload = {
        "route": "q",
        "numbers": phone,
        "variables_values": otp
    }

    headers = {
        "authorization": params['FAST2SMS_API_KEY'],  
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        result = response.json()

        if response.status_code == 200 and result.get("return"):
            return jsonify({'message': 'OTP sent successfully'})
        else:
            return jsonify({'error': result.get('message', 'SMS failed')}), 500

    except Exception as e:
        return jsonify({'error': 'SMS service error'}), 500



# @app.route('/send-otp', methods=['POST'])
# def send_otp():
#     data = request.get_json()
#     phone = data.get('phone', '').strip()

#     if not phone or len(phone) != 10 or not phone.isdigit():
#         return jsonify({'error': 'Invalid phone number'}), 400

#     otp = str(random.randint(100000, 999999))

#     # Store OTP
#     mongo.db.otp_store.update_one(
#         {'phone': phone},
#         {'$set': {'otp': otp, 'timestamp': datetime.utcnow()}},
#         upsert=True
#     )

#     url = "https://www.fast2sms.com/dev/bulkV2"
#     payload = {
#         "route": "q",
#         "numbers": phone,
#         "variables_values": otp
#     }

#     headers = {
#         "authorization": "cmZPgOV2wyb47pkTA3u1jRX9fNoQCBtJl5MiYanIDSxHhr0vUK1rz7ySfEwxls3RMJh8LQDATCvUPjn4",
#         "Content-Type": "application/json"
#     }

#     response = requests.post(url, json=payload, headers=headers)
#     result = response.json()

#     if response.status_code == 200 and result.get("return") is True:
#         return jsonify({'message': 'OTP sent successfully'})
#     else:
#         return jsonify({'error': result.get('message', 'OTP failed')}), 500


@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    phone = data.get('phone', '').strip()
    entered_otp = data.get('otp', '').strip()

    # Validate phone
    if not phone or len(phone) != 10:
        return jsonify({'error': 'Invalid phone number'}), 400

    otp_record = mongo.db.otp_store.find_one({'phone': phone})

    if not otp_record:
        return jsonify({'error': 'OTP not found'}), 404

    # OTP expiry (5 minutes)
    time_diff = datetime.utcnow() - otp_record['timestamp']
    if time_diff.total_seconds() > 300:
        mongo.db.otp_store.delete_one({'phone': phone})
        return jsonify({'error': 'OTP expired'}), 400

    if otp_record['otp'] != entered_otp:
        return jsonify({'error': 'Invalid OTP'}), 401

    # Success
    session['otp_verified'] = True
    session['verified_phone'] = phone
    mongo.db.otp_store.delete_one({'phone': phone})

    return jsonify({'message': 'OTP verified successfully'})



@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)

        new_user = {
            "name": form.name.data,
            "username": form.username.data,
            "password": hashed_password,
            "address": form.address.data,
            "mobile_no": form.mobile_no.data,
            "email": form.email.data,
            "academic_branch": form.academic_branch.data,
            "academic_year": form.academic_year.data,
            "gender": form.gender.data,
            "status": "Pending"
        }

        mongo.db.users.insert_one(new_user)

        flash('Registered successfully. Wait For Approval then login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)




otp_store = {}  # Temporary OTP store

@app.route('/forgot-password', methods=['GET', 'POST'])     
def forgot_password():
    return render_template('forgot_password.html')




@app.route('/send-reset-otp', methods=['POST'])
def send_reset_otp():
    data = request.json
    phone = data.get('phone')

    user = mongo.db.users.find_one({'mobile_no': phone})
    if not user:
        return jsonify({'error': 'Mobile number not found'}), 404

    otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    otp_store[phone] = otp

    try:
        client.messages.create(
            body=f"Your HostelHub OTP is: {otp}",
            from_=twilio_number,
            to=f"+91{phone}"
        )
        return jsonify({'message': 'OTP sent successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/verify-reset-otp', methods=['POST'])
def verify_reset_otp():
    data = request.json
    phone = data.get('phone')
    entered_otp = data.get('otp')

    if phone not in otp_store:
        return jsonify({'error': 'No OTP requested for this number'}), 400

    if otp_store.get(phone) == entered_otp:
        return jsonify({'message': 'OTP verified'})
    else:
        return jsonify({'error': 'Invalid OTP'}), 400


@app.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    phone = data.get('phone')
    new_password = data.get('new_password')

    if phone not in otp_store:
        return jsonify({'error': 'OTP not verified yet'}), 400

    hashed_pw = generate_password_hash(new_password, method='pbkdf2:sha256')
    update_result = mongo.db.users.update_one({'mobile_no': phone}, {'$set': {'password': hashed_pw}})

    if update_result.modified_count == 0:
        return jsonify({'error': 'Password update failed. Please try again.'}), 500

    otp_store.pop(phone, None)
    return jsonify({'message': 'Password updated successfully'})




@student_required
@app.route('/index')
def index():
    username = session.get('username')
    user_id = session.get('_id')  
    user_data = None
    if user_id:
        user_data = mongo.db.users.find_one({"_id": ObjectId(user_id)})


    allocated_room = None
    if user_id:
        room_data = mongo.db.rooms.find_one({"user_id": str(user_id)})
        if room_data and room_data.get("room_no"):
            allocated_room = room_data["room_no"]

    profile_data = None
    if user_id:
        profile_data = mongo.db.profile.find_one({"user_id": str(user_id)})


    return render_template(
        'index.html',
        username=username,
        user=user_data,
        profile=profile_data,    
        allocated_room=allocated_room
    )





@app.route("/feedback", methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        name = request.form['name']
        feedback_text = request.form['feedback']
        email = request.form['email']
        suggestion = request.form.get('suggestion', '')

        if not name or not feedback_text or not email:
            return render_template('feedback.html', params=params, error="Fill all fields.")

        mongo.db.feedback.insert_one({
            "name": name,
            "feedback": feedback_text,
            "email": email,
            "suggestion": suggestion
        })

        mail.send_message(
            'New Feedback from HostelHub',
            sender=email,
            recipients=[params['gmail_user']],
            body=f"Feedback from {name}:\n\n{feedback_text}\n\nSuggestion: {suggestion}\nEmail: {email}"
        )
        return render_template('thankyou.html', params=params, success=1)

    return render_template('feedback.html', params=params)



@app.route("/contact", methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        number = request.form['mobile']  # FIXED: should match input name in HTML
        query = request.form['query']

        if not name or not number or not query:
            return render_template('contact.html', params=params, error="Fill all fields.")

        mongo.db.contact.insert_one({
            "name": name,
            "number": number,
            "query": query
        })

        mail.send_message(
            'New Query from HostelHub',
            sender=number,
            recipients=[params['gmail_user']],
            body=f"Query from: {name}\n\n Query Is: {query}\n\n Sender's Mobile Number: {number}"
        )
        return render_template('thankyou.html', params=params, success=2)

    return render_template('contact.html', params=params)


@app.route("/thankyou")
def thankyou():
    return render_template("thankyou.html")

@app.route('/timetable')
def timetable():
    timetable_collection = mongo.db.timetable

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    timetable = list(timetable_collection.find())

    # If empty, initialize with default NULL values
    if not timetable:
        timetable = [{"day": day, "breakfast": "NULL", "lunch": "NULL", "dinner": "NULL"} for day in days]

    # Sort timetable by day order
    day_order = {day: i for i, day in enumerate(days)}
    timetable.sort(key=lambda x: day_order.get(x.get("day", ""), 100))

    return render_template('timetable.html', timetable=timetable)




# Render attendance page
@app.route('/attendance')
def attendance():
    if '_id' not in session:
        return redirect('/login')

    student_id = session['_id']
    today = datetime.utcnow().date().strftime("%Y-%m-%d")

    # Check if this student has marked attendance today
    record = attendance_col.find_one({
        "student_id": student_id,
        "date": today,
        "present": "yes"
    })

    attendance_status = "yes" if record else None

    return render_template('attendance.html', attendance_status=attendance_status, today_date=today)


@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    try:
        if '_id' not in session:
            print("User not in session")
            return jsonify({'status': 'unauthorized'}), 401

        data = request.get_json()

        if not data or 'date' not in data:
            return jsonify({'status': 'error', 'message': 'Missing date'}), 400

        date = data['date']
        student_id = session['_id']
        student_username = session.get('username', 'unknown')  # safer access

        existing = attendance_col.find_one({"date": date, "student_id": student_id})
        if existing:
            return jsonify({'status': 'already_marked'})

        result = attendance_col.insert_one({
            "student_id": student_id,
            "student_username": student_username,
            "date": date,
            "present": "yes",
            "timestamp": datetime.utcnow()
        })

        print("Inserted attendance with ID:", result.inserted_id)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500




@app.route('/menu')

def menu():
    return render_template('menu.html')

@app.route('/bill')
def bill():
    if '_id' not in session:
        return redirect('/login')

    student_id = ObjectId(session['_id'])  
    current_month = datetime.now().strftime("%B %Y")

    bill = mongo.db.bill.find_one({'month': current_month})
    payment = mongo.db.payments.find_one({'student_id': student_id, 'month': current_month})

    return render_template('bill.html',
                           amount=bill['amount'] if bill else 0,
                           current_month=current_month,
                           is_paid=bool(payment))



@app.route('/pay', methods=['GET', 'POST'])
def pay():
    if '_id' not in session:
        return redirect('/login')

    student_id = ObjectId(session['_id'])
    current_month = datetime.now().strftime("%B %Y")

    if request.method == 'POST':
        mongo.db.payments.insert_one({
            'student_id': student_id,
            'month': current_month,
            'status': 'success',
            'timestamp': datetime.now()
        })
        return redirect('/index')

    bill = mongo.db.bill.find_one({'month': current_month})
    return render_template(
        'pay.html',
        amount=bill['amount'] if bill else 0,
        current_month=current_month,
        key=RAZORPAY_KEY_ID  
    )



@app.route("/create_order", methods=["POST"])
def create_order():
    data = request.get_json()
    amount = data.get("amount", 50000)

    try:
        order = razorpay_client.orders.create({
            "amount": amount,
            "currency": "INR",
            "payment_capture": 1
        })
        return jsonify(order)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route("/verify_payment", methods=["POST"])
def verify_payment():
    data = request.get_json()
    payment_id = data.get('razorpay_payment_id')

    if not payment_id:
        return jsonify({"status": "failed", "error": "Missing razorpay_payment_id"}), 400

    try:
        payment = razorpay_client.payment.fetch(payment_id)
        app.logger.info(f"Payment fetched: {payment}")

        if payment['status'] != 'captured':
            # Attempt to capture payment if not yet captured
            amount = payment['amount']  # amount in paise
            capture = razorpay_client.payment.capture(payment_id, amount)
            app.logger.info(f"Payment capture response: {capture}")
            if capture['status'] != 'captured':
                raise ValueError("Payment capture failed")
            return jsonify({"status": "success"})
        
        return jsonify({"status": "success"})

    except Exception as e:
        app.logger.error(f"Payment verification failed: {str(e)}")
        return jsonify({"status": "failed", "error": str(e)}), 400







@app.route("/payment_success")
def payment_success():
    if '_id' not in session:
        return redirect('/login')

    student_id = ObjectId(session['_id'])
    current_month = datetime.now().strftime("%B %Y")

    # Avoid duplicate entries
    existing = mongo.db.payments.find_one({'student_id': student_id, 'month': current_month})
    if not existing:
        mongo.db.payments.insert_one({
            'student_id': student_id,
            'month': current_month,
            'status': 'success',
            'timestamp': datetime.now()
        })

    return redirect('/index')





@app.route('/notification')
def notification():
    notifications = mongo.db.notification.find().sort('datetime', -1)
    return render_template('notifications.html', notifications=notifications)

@app.route('/leave', methods=['GET', 'POST'])
def leave():
    if request.method == 'POST':
        leave_data = {
            "date": date.today().strftime("%d-%m-%Y"),
            "student_name": request.form.get('student_name'),
            "student_class": request.form.get('student_class'),
            "room_no": request.form.get('room_no'),
            "no_of_days": int(request.form.get('no_of_days')),
            "from_date": request.form.get('from_date'),
            "to_date": request.form.get('to_date'),
            "return_date": request.form.get('return_date'),
            "student_contact": request.form.get('student_contact'),
            "parent_contact": request.form.get('parent_contact'),
            "parent_consent": request.form.get('parent_consent'),
        }

        mongo.db.leave.insert_one(leave_data)
        return redirect(url_for('leavesuccess'))

    return render_template("leave.html", current_date=date.today().strftime("%d-%m-%Y"),
                           student_name='', student_class='', room_no='',
                           student_contact='', parent_contact='')
@app.route('/leavesuccess')
def leavesuccess():
    return render_template('leavesuccess.html')



@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/studentprofile')
def studentprofile():
    # Logged-in user ID from session
    user_id = session.get('_id')

    if not user_id:
        flash("Please log in first.", "danger")
        return redirect(url_for('login'))

    user_data = mongo.db.users.find_one({"_id": ObjectId(user_id)})

    if not user_data:
        flash("User not found.", "danger")
        return redirect(url_for('index'))


    profile_data = mongo.db.profile.find_one({"user_id": user_id})


    allocated_room = mongo.db.rooms.find_one({"user_id": user_id})

    return render_template(
        'studentprofile.html',
        user=user_data,
        profile=profile_data, 
        room=allocated_room
    )



@app.route('/editprofile')
def editprofile():
    user_id = session.get('_id')

    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    profile = mongo.db.profile.find_one({"user_id": user_id})

    return render_template("editprofile.html", user=user, profile=profile)



@app.route('/updateprofile', methods=['POST'])
def updateprofile():
    user_id = session.get('_id')

    # Read form fields
    address = request.form.get("address")
    mobile = request.form.get("mobile")
    gender = request.form.get("gender")
    branch = request.form.get("branch")
    year = request.form.get("year")

    # Handle profile picture upload
    file = request.files.get("profile_pic")
    filename = None

    if file and file.filename != "":
        filename = secure_filename(file.filename)
        filepath = os.path.join("static/profile_pics", filename)
        file.save(filepath)

    # Main data object
    updated_fields = {
        "address": address,
        "mobile_no": mobile,    # for users
        "mobile": mobile,       # for profile
        "gender": gender,
        "academic_branch": branch,
        "academic_year": year
    }

    # Add profile picture if uploaded
    if filename:
        updated_fields["profile_photo"] = filename

    profile_data = {
        "user_id": user_id,
        "address": address,
        "mobile": mobile,
        "gender": gender,
        "academic_branch": branch,
        "academic_year": year
    }

    if filename:
        profile_data["profile_photo"] = filename

    mongo.db.profile.update_one(
        {"user_id": user_id},
        {"$set": profile_data},
        upsert=True
    )

    mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {
            "address": address,
            "mobile_no": mobile,
            "gender": gender,
            "academic_branch": branch,
            "academic_year": year
        }}
    )


    collections_to_update = [
        "rooms",
        "mess_feedback",
        "mess_attendance",
        "complaints",
        "studentlist",
        "registrations",
        "hostel_forms"
    ]

    for col in collections_to_update:
        try:
            mongo.db[col].update_many(
                {"user_id": user_id},
                {"$set": {
                    k: v for k, v in updated_fields.items()
                    if v is not None  
                }}
            )
        except:
            pass 

    return redirect(url_for('studentprofile'))




# Render mess leave page
@app.route('/messleave')
def messleave():
    if '_id' not in session:
        return redirect('/login')

    return render_template('messleave.html')

@app.route('/mark-mess-leave', methods=['POST'])
def mark_mess_leave():
    try:
        if '_id' not in session:
            return jsonify({'status': 'unauthorized'}), 401

        data = request.get_json()
        if not data or 'date' not in data:
            return jsonify({'status': 'error', 'message': 'Missing date'}), 400

        date = data['date']
        student_id = session['_id']            # ✅ STRING
        student_username = session['username']

        selected_date = datetime.strptime(date, "%Y-%m-%d").date()
        today = datetime.utcnow().date()

        # ❌ No today or past
        if selected_date <= today:
            return jsonify({'status': 'error', 'message': 'Only future dates allowed'}), 400

        # ✅ CHECK ONLY THIS STUDENT
        existing = mongo.db.messleave.find_one({
            "student_id": student_id,
            "date": date
        })

        if existing:
            return jsonify({'status': 'already_marked'})

        mongo.db.messleave.insert_one({
            "student_id": student_id,          # ✅ STRING
            "student_username": student_username,
            "date": date,
            "month": selected_date.strftime("%B %Y"),
            "status": "Absent",
            "created_at": datetime.utcnow()
        })

        return jsonify({'status': 'success'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/get-mess-leave')
def get_mess_leave():
    if '_id' not in session:
        return jsonify([])

    student_id = session['_id']   # ✅ STRING

    leaves = mongo.db.messleave.find(
        {"student_id": student_id},   # ✅ FILTER BY STUDENT
        {"_id": 0, "date": 1}
    ).sort("date", 1)

    return jsonify(list(leaves))



@app.route('/remove-mess-leave', methods=['POST'])
def remove_mess_leave():
    if '_id' not in session:
        return jsonify({'status': 'unauthorized'}), 401

    data = request.get_json()
    if not data or 'date' not in data:
        return jsonify({'status': 'error'}), 400

    mongo.db.messleave.delete_one({
        "student_id": session['_id'],   # ✅ STRING
        "date": data['date']
    })

    return jsonify({'status': 'removed'})


#-------------------------------------------------------------------------------------------#
#Admin
@app.route('/adminlogin', methods=['GET', 'POST'])
def adminlogin():
    if request.method == 'GET':
        session['captcha_text'] = generate_captcha()
        return render_template("adminlogin.html", captcha=session['captcha_text'])

    # POST request handling (form submission)
    email = request.form['email']
    password = request.form['password']
    captcha_input = request.form.get('captcha', '').strip()

    # Check CAPTCHA first
    if captcha_input.upper() != session.get('captcha_text', '').upper():
        flash("Incorrect CAPTCHA.", "danger")
        session['captcha_text'] = generate_captcha()  # Regenerate CAPTCHA if failure
        return render_template("adminlogin.html", captcha=session['captcha_text'])

    # CAPTCHA correct, check admin credentials
    admin = mongo.db.adminlogin.find_one({"email": email})
    if admin and check_password_hash(admin['password'], password):
        session.clear()  # Clear previous session data
        session['admin_logged_in'] = True
        session['admin_email'] = email
        return redirect(url_for('adminindex'))
    else:
        flash("Invalid email or password", "danger")
        session['captcha_text'] = generate_captcha()  # Regenerate CAPTCHA on failure
        return render_template("adminlogin.html", captcha=session['captcha_text'])


@app.route('/refresh_captcha')
def refresh_captcha():
    new_captcha = generate_captcha()
    session['captcha_text'] = new_captcha
    return new_captcha


@app.route('/adminindex')
def adminindex():
    pending_count = mongo.db.users.count_documents({"status": "Pending"})
    has_pending_requests = pending_count > 0
    return render_template('adminindex.html', has_pending_requests=has_pending_requests)



@app.route('/adminlogout')
def adminlogout():
    session.pop('admin_logged_in', None)
    session.pop('admin_email', None)
    return redirect(url_for('home'))





timetable_collection = mongo.db.timetable
@app.route('/admintimetable', methods=['GET', 'POST'])
def admintimetable():
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    if request.method == 'POST':
        for i, day in enumerate(days):
            updated = {
                "day": day,
                "breakfast": request.form.get(f"breakfast_{i}", ""),
                "breakfast_time": request.form.get(f"breakfast_time_{i}", ""),
                "lunch": request.form.get(f"lunch_{i}", ""),
                "lunch_time": request.form.get(f"lunch_time_{i}", ""),
                "dinner": request.form.get(f"dinner_{i}", ""),
                "dinner_time": request.form.get(f"dinner_time_{i}", "")
            }
            timetable_collection.update_one({"day": day}, {"$set": updated}, upsert=True)
        return redirect('/adminindex')

    # Fetch or initialize if empty
    timetable = list(timetable_collection.find())
    if not timetable:
        timetable = [{"day": day, "breakfast": "", "breakfast_time": "", 
                      "lunch": "", "lunch_time": "", 
                      "dinner": "", "dinner_time": ""} for day in days]

    return render_template('admintimetable.html', timetable=timetable)


@app.route('/adminfeedback')
def adminfeedback():
    feedback_data = list(mongo.db.feedback.find({}, {"_id": 0}))
    return render_template("adminfeedback.html", feedbacks=feedback_data)

@app.route("/admincontact")
def admincontact():
    contact_data = list(mongo.db.contact.find({}, {"_id": 0}))
    return render_template("admincontact.html", contacts=contact_data)


@app.route('/adminallusers')
def adminallusers():
    users = mongo.db.users.find()
    return render_template('adminallusers.html', users=users)


@app.route("/adminhelpline", methods=["GET", "POST"])
def adminhelpline():
    if request.method == "POST":
        number = request.form.get("helpline")  # <-- use "helpline" here
        if number and len(number) == 10 and number.isdigit():
            mongo.db.helpline.insert_one({"number": number})
            return render_template("adminhelpline.html", message="Helpline number saved successfully!")
        else:
            return render_template("adminhelpline.html", message="Invalid number. Enter 10 digits only.")
    return render_template("adminhelpline.html")




@app.route('/delete_user/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    result = mongo.db.users.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 1:
        return jsonify({"success": True}), 200
    else:
        return jsonify({"error": "User not found"}), 404




@app.route('/adminapproval', methods=['GET', 'POST'])
def adminapproval():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        action = request.form.get('action')

        if action == 'approve':
            mongo.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"status": "Approved", "confirmed": True}}
            )
        elif action == 'decline':
            mongo.db.users.delete_one({"_id": ObjectId(user_id)})
    

    users = mongo.db.users.find({"status": "Pending"})
    return render_template('adminapproval.html', users=users)





@app.route('/adminattendance')
def adminattendance():
    selected_date = request.args.get('date')  # Get date from query string
    students_data = []
    present_count = 0
    absent_count = 0

    if selected_date:
        # Fetch all present attendance for selected date
        attendance_records = list(attendance_collection.find({
            'date': selected_date,
            'present': 'yes'
        }))
        present_ids = {record['student_id'] for record in attendance_records}

        # Fetch all users
        users = list(users_collection.find())
        for user in users:
            user_id = str(user['_id'])
            is_present = user_id in present_ids
            status = 'Present' if is_present else 'Absent'
            students_data.append({
                'name': user.get('name', ''),
                'mobile_no': user.get('mobile_no', ''),
                'email': user.get('email', ''),
                'status': status
            })

        # Count present and absent students
        present_count = sum(1 for s in students_data if s['status'] == 'Present')
        absent_count = sum(1 for s in students_data if s['status'] == 'Absent')

    return render_template('adminattendance.html',
                           students=students_data,
                           selected_date=selected_date,
                           present_count=present_count,
                           absent_count=absent_count)



# Admin Notification Route
@app.route('/adminnotification', methods=['GET', 'POST'])
def adminnotification():
    if request.method == 'POST':
        message = request.form['message']
        if message.strip():
            now = datetime.now()
            notification = {
                'message': message,
                'datetime': now.strftime('%Y-%m-%d %H:%M:%S')
            }
            mongo.db.notification.insert_one(notification)
            return redirect(url_for('adminnotification'))
    return render_template('adminnotification.html')





# Admin route: List all leave applications
@app.route('/adminleave')
def adminleave():
    leave_applications = list(mongo.db.leave.find().sort("date", -1))  # sorted by date descending
    return render_template("adminleave.html", leave_applications=leave_applications)
    

# Admin route: View single leave application details
@app.route('/adminleaveapplications/<application_id>')
def adminleaveapplications(application_id):
    leave_application = mongo.db.leave.find_one({"_id": ObjectId(application_id)})
    if not leave_application:
        return "<h3>Application not found</h3><p><a href='/adminleave'>Back to list</a></p>"
    return render_template("adminleaveapplications.html", leave_application=leave_application)




@app.route('/adminbill')
def adminbill():
    # Check session from new login
    admin_email = session.get('xadmin_email')

    # Validate admin from xadminlogin
    admin = mongo.db.xadminlogin.find_one({"email": admin_email})

    if not admin:
        return redirect('/xHostelLogin')

    users = mongo.db.users.find()
    current_month = datetime.now().strftime("%B %Y")
    payments = list(mongo.db.payments.find({'month': current_month}))

    paid_ids = [str(p['student_id']) for p in payments]

    student_data = []
    for user in users:
        # Prevent admin record from appearing
        if user.get('email') == admin_email:
            continue

        is_paid = str(user['_id']) in paid_ids

        student_data.append({
            'name': user.get('name', ''),
            'contact': user.get('mobile_no', ''),
            'status': 'Paid' if is_paid else 'Not Paid',
            'month': current_month
        })

    return render_template('adminbill.html', students=student_data, month=current_month)






@app.route('/adminsetbill', methods=['GET', 'POST'])
def adminsetbill():
    # Check session from new login
    admin_email = session.get('xadmin_email')

    # Validate admin
    admin = mongo.db.xadminlogin.find_one({"email": admin_email})

    if not admin:
        return redirect('/xHostelLogin')

    current_month = datetime.now().strftime("%B %Y")

    if request.method == 'POST':
        amount = request.form.get('amount')

        if not amount or not amount.isdigit():
            flash("Please enter a valid numeric amount.", "danger")
            return redirect('/adminsetbill')

        mongo.db.bill.update_one(
            {"month": current_month},
            {"$set": {"amount": int(amount)}},
            upsert=True
        )

        flash(f"Monthly bill set to ₹{amount} for {current_month}", "success")
        return redirect('/adminsetbill')

    existing = mongo.db.bill.find_one({"month": current_month})
    current_amount = existing['amount'] if existing else ''

    return render_template(
        'adminsetbill.html',
        current_month=current_month,
        current_amount=current_amount
    )



@app.route('/send_complaint_page')
def send_complaint_page():
    return render_template('send_complaint.html')


@app.route('/send_complaint', methods=['POST'])
def send_complaint():
    message = request.form.get('message')
    media_file = request.files.get('media')
    media_filename = None

    if media_file and media_file.filename != '':
        filename = secure_filename(media_file.filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        media_filename = f"{timestamp}_{filename}"
        media_file.save(os.path.join(app.config['UPLOAD_FOLDER'], media_filename))

    complaint_data = {
        "message": message,
        "media": media_filename,
        "timestamp": datetime.now()
    }

    try:
        mongo.db.complaints.insert_one(complaint_data)
        return jsonify({"status": "success"})
    except Exception as e:
        print("Error:", e)
        return jsonify({"status": "fail"})


@app.route('/complaints')
def complaints():
    # Fetch all complaints sorted by latest first
    all_complaints = list(mongo.db.complaints.find().sort("timestamp", -1))
    return render_template('complaints.html', complaints=all_complaints)




@app.route('/mess-admin-dashboard')
def mess_admin_dashboard():

    # 🔐 Allow only mess admin
    if not session.get('admin_logged_in'):
        return redirect(url_for('adminlogin'))

    # 📅 Tomorrow date
    tomorrow = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')

    # 👥 Total students
    total_students = mongo.db.users.count_documents({})

    # ❌ Total absent students for tomorrow
    total_absent = mongo.db.messleave.count_documents({
        "date": tomorrow
    })

    # ✅ Total present
    total_present = total_students - total_absent

    return render_template(
        'mess_admin_dashboard.html',
        total_students=total_students,
        total_absent=total_absent,
        total_present=total_present,
        date=tomorrow
    )






# <--------------------------------------- Hostel Administration -------------------------------------------------->
@app.route('/xHostelLogin', methods=['GET', 'POST'])
def xHostelLogin():
    if request.method == 'GET':
        # Generate and store a new CAPTCHA
        session['captcha_text'] = generate_captcha()
        return render_template("xHostelLogin.html", captcha=session['captcha_text'])

    # POST request — form submission
    email = request.form.get('email')
    password = request.form.get('password')
    captcha_input = request.form.get('captcha', '').strip()

    # CAPTCHA validation
    if captcha_input.upper() != session.get('captcha_text', '').upper():
        flash("Incorrect CAPTCHA.", "danger")
        session['captcha_text'] = generate_captcha()
        return render_template("xHostelLogin.html", captcha=session['captcha_text'])

    # Check credentials from MongoDB (collection: xadminlogin)
    xadmin = mongo.db.xadminlogin.find_one({"email": email})
    if xadmin:
        # Verify hashed password
        if check_password_hash(xadmin['password'], password):
            session['xadmin_logged_in'] = True
            session['xadmin_email'] = email
            return redirect(url_for('xHostelIndex'))  # change to your actual dashboard route
        else:
            flash("Invalid password", "danger")
    else:
        flash("Email not found", "danger")

    # Regenerate CAPTCHA on failure
    session['captcha_text'] = generate_captcha()
    return render_template("xHostelLogin.html", captcha=session['captcha_text'])





@app.route('/xHostelIndex')
def xHostelIndex():
    return render_template('xHostelIndex.html')


@app.route('/xOverview')
def xOverview():
    return render_template('xOverview.html')



@app.route("/room-allocation")
def room_allocation():
    users = list(mongo.db.users.find({"status": "Approved"}))

    # Fetch all room allocations
    room_data = {r["user_id"]: r for r in mongo.db.rooms.find()}

    # Attach room info for each user
    for u in users:
        uid = str(u["_id"])
        u["allocated_room"] = room_data.get(uid, None)

    return render_template("room_allocation.html", users=users)



@app.route("/allocate-room", methods=["POST"])
def allocate_room():
    user_id = request.form.get("user_id")
    room_no = request.form.get("room_no")

    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        return jsonify({"error": "User not found"}), 404

    # Optional: Prevent duplicate allocation
    existing = mongo.db.rooms.find_one({"user_id": user_id})
    if existing:
        mongo.db.rooms.update_one(
            {"user_id": user_id},
            {"$set": {"room_no": room_no}}
        )
        return jsonify({"message": "Room updated successfully!"})

    # Save new allocation
    mongo.db.rooms.insert_one({
        "user_id": user_id,
        "name": user["name"],
        "academic_branch": user["academic_branch"],
        "academic_year": user["academic_year"],
        "room_no": room_no,
        "allocated_on": datetime.now().strftime("%Y-%m-%d %H:%M")
    })

    return jsonify({"message": "Room allocated successfully!"})





# @app.route('/rooms-overview')
# def rooms_overview():
#     rooms = []

#     # Generate F-01 to F-200
#     for i in range(1, 201):
#         room_no = f"F-{i:02d}"
#         count = mongo.db.rooms.count_documents({"room_no": room_no})
#         rooms.append({"room_no": room_no, "count": count})

#     # Generate G-01 to G-300
#     for i in range(1, 301):
#         room_no = f"G-{i:02d}"
#         count = mongo.db.rooms.count_documents({"room_no": room_no})
#         rooms.append({"room_no": room_no, "count": count})

#     return render_template("rooms_overview.html", rooms=rooms)


@app.route('/rooms-overview')
def rooms_overview():

    rooms = []

    # Get all room counts at once
    room_counts = mongo.db.rooms.aggregate([
        {"$group": {"_id": "$room_no", "count": {"$sum": 1}}}
    ])

    count_map = {r["_id"]: r["count"] for r in room_counts}

    # F-01 to F-200
    for i in range(1, 201):
        room_no = f"F-{i:02d}"
        rooms.append({
            "room_no": room_no,
            "count": count_map.get(room_no, 0)
        })

    # G-01 to G-300
    for i in range(1, 301):
        room_no = f"G-{i:02d}"
        rooms.append({
            "room_no": room_no,
            "count": count_map.get(room_no, 0)
        })

    return render_template("rooms_overview.html", rooms=rooms)





@app.route('/allocate-room-new', methods=['POST'])
def allocate_room_new():
    user_id = request.form.get('user_id')
    room_no = request.form.get('room_no').strip().upper()

    if not user_id or not room_no:
        return jsonify({"message": "Invalid request"}), 400

    # Remove previous allocation if exists
    mongo.db.rooms.delete_many({"user_id": str(user_id)})

    # Insert new allocation
    mongo.db.rooms.insert_one({
        "user_id": str(user_id),
        "room_no": room_no
    })

    return jsonify({"message": f"Room {room_no} allocated successfully!"})



@app.route('/hostel-fees')
def hostel_fees():
    user_id = session.get('_id')
    if not user_id:
        return redirect(url_for('login'))

    user_id = str(user_id)

    # Check if student has already paid
    payment = mongo.db.hostel_payments.find_one({
        "user_id": user_id,
        "status": "paid"
    })

    # Load admin-set fee
    settings = mongo.db.hostel_settings.find_one({})
    HOSTEL_FEE_AMOUNT = settings.get("fee_amount", 3000)

    return render_template(
        'hostel_fees.html',
        paid=(payment is not None),
        amount=HOSTEL_FEE_AMOUNT,
        payment=payment
    )



@app.route('/hostel-fees-admin')
def hostel_fees_admin():
    fees = list(mongo.db.hostel_fees.find().sort([("user_id", 1)]))

    for f in fees:
        f['_id'] = str(f['_id'])
        if f.get("paid_at"):
            f["paid_at"] = f["paid_at"].strftime("%Y-%m-%d")

    # Fetch payments log
    payments = list(mongo.db.hostel_payments.find().sort([("created_at", -1)]))

    for p in payments:
        p['_id'] = str(p['_id'])
        if p.get("created_at"):
            p["created_at"] = p["created_at"].strftime("%Y-%m-%d %H:%M:%S")

    return render_template(
        'hostel_fees_admin.html',
        fees=fees,
        payments=payments
    )

@app.route('/create-hostel-order', methods=['POST'])
def create_hostel_order():
    data = request.json
    user_id = str(session.get('_id'))
    amount_rupees = float(data.get('amount'))
    amount_paisa = int(round(amount_rupees * 100))

    # --- Build a short receipt (<= 40 chars) ---
    # Use first 8 chars of user_id + timestamp to keep it short and unique
    short_uid = user_id.replace(" ", "")[:8]
    receipt = f"hostel_{short_uid}_{int(time.time())}"

    # Ensure final safety: cut to 40 chars just in case
    receipt = receipt[:40]

    order_payload = {
        "amount": amount_paisa,
        "currency": "INR",
        "receipt": receipt,
        "payment_capture": 1
    }

    try:
        order = razorpay_client.order.create(order_payload)
    except BadRequestError as e:
        # Razorpay returned a 400 — surface a helpful message to client
        return jsonify({"error": "Razorpay rejected order", "details": str(e)}), 400
    except Exception as e:
        # Generic fallback
        return jsonify({"error": "Failed to create order", "details": str(e)}), 500

    # store a tentative payment record in DB
    payment_doc = {
        "user_id": user_id,
        "razorpay_order_id": order['id'],
        "amount_rupees": amount_rupees,
        "amount_paisa": amount_paisa,
        "status": "created",
        "created_at": datetime.utcnow()
    }
    inserted = mongo.db.hostel_payments.insert_one(payment_doc)

    return jsonify({
        "order_id": order['id'],
        "amount": amount_paisa,
        "currency": "INR",
        "razorpay_key": RAZORPAY_KEY_ID,
        "payment_doc_id": str(inserted.inserted_id)
    })

@app.route('/verify-hostel-payment', methods=['POST'])
def verify_hostel_payment():
    data = request.json
    payment_id = data["razorpay_payment_id"]
    order_id = data["razorpay_order_id"]
    signature = data["razorpay_signature"]
    payment_doc_id = data["payment_doc_id"]

    try:
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        })
    except:
        return jsonify({"status": "failed"}), 400

    mongo.db.hostel_payments.update_one(
        {"_id": ObjectId(payment_doc_id)},
        {"$set": {
            "status": "paid",
            "razorpay_payment_id": payment_id,
            "paid_at": datetime.utcnow()
        }}
    )

    return jsonify({"status": "success"})

@app.route('/set-hostel-fees', methods=['GET', 'POST'])
def set_hostel_fee():
    if request.method == 'POST':
        fee = float(request.form.get("fee"))

        # Update or insert fee amount
        mongo.db.hostel_settings.update_one(
            {},
            {"$set": {"fee_amount": fee}},
            upsert=True
        )

       
        return redirect(url_for('set_hostel_fee'))

    # Load current fee
    settings = mongo.db.hostel_settings.find_one({})
    current_fee = settings.get("fee_amount", 3000) if settings else 3000

    return render_template("set_hostel_fee.html", current_fee=current_fee)




#<---------------------------------------- Degugger ------------------------------------------------------------------->
if __name__ == "__main__":
    app.run(debug=True)