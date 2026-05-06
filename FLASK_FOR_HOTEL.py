from flask import Flask, render_template, request, redirect, session
import subprocess
import os
from datetime import datetime
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = "secret123"

# BASE DIR
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.txt")
RESERVATIONS_FILE = os.path.join(BASE_DIR, "reservations.txt")
BACKEND_EXE = os.path.join(BASE_DIR, "backend.exe")

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'myhotelapp1407@gmail.com'
app.config['MAIL_PASSWORD'] = 'htcq djja sgzz eype' 
app.config['MANAGER_EMAIL'] = 'hotelmanager3217@gmail.com'
app.config['MANAGER_USERNAME'] = 'manager'
app.config['MANAGER_PASSWORD'] = 'admin123'

mail = Mail(app)

TIME_SLOTS = [
    "10:00 - 12:00",
    "12:00 - 14:00",
    "14:00 - 16:00",
    "16:00 - 18:00",
    "18:00 - 20:00",
    "20:00 - 22:00"
]

def run_backend(args):
    """Helper to run the C backend and return output"""
    try:
        # Ensure all args are strings
        str_args = [str(arg) for arg in args]
        result = subprocess.run(
            [BACKEND_EXE] + str_args,
            capture_output=True,
            text=True,
            cwd=BASE_DIR
        )
        return result.stdout.strip()
    except Exception as e:
        return f"ERROR: {str(e)}"

def send_booking_email(user_email, manager_email, booking_details):
    # 1. Email to User
    user_msg = Message("Table Reservation Confirmation", 
                       sender=("Ember & Ivory", app.config['MAIL_USERNAME']), 
                       recipients=[user_email])
    user_msg.body = f"Hello {booking_details['name']},\n\nYour table has been reserved!\n\nID: {booking_details['booking_id']}\nTables: {booking_details['table']}\nDate: {booking_details['date']}\nTime: {booking_details['slot']}\n\nThank you for choosing Ember & Ivory!"
    
    # 2. Email to Manager
    manager_msg = Message("NEW RESERVATION: Action Required", 
                          sender=("Ember & Ivory", app.config['MAIL_USERNAME']), 
                          recipients=[manager_email])
    manager_msg.body = f"Hello Manager,\n\nA new reservation has been placed.\n\nCustomer: {booking_details['name']} ({user_email})\nBooking ID: {booking_details['booking_id']}\nTables: {booking_details['table']}\nGuests: {booking_details['guests']}\nDate: {booking_details['date']}\nSlot: {booking_details['slot']}\n\nPlease ensure the venue is prepared."
    
    try:
        mail.send(user_msg)
        mail.send(manager_msg)
    except Exception as e:
        print(f"Mail Error: {e}")
        pass

@app.route("/")
def home():
    return render_template("home_page.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # AUTH via C
        res = run_backend(["login", email, password])
        if res != "FAILURE" and not res.startswith("ERROR"):
            session["user"] = email
            session["name"] = res
            return redirect("/bookings")

        return render_template("login_page.html", error="Invalid credentials")

    return render_template("login_page.html")

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        confirm = request.form["confirm"]

        if password != confirm:
            return render_template("signup.html", error="Passwords mismatch")

        phone = request.form["phone"]
        # SIGNUP via C (name, phone, email, password)
        res = run_backend(["signup", name, phone, email, password])
        if res == "EXISTS":
            return render_template("signup.html", error="Email already registered")
        elif res == "SUCCESS":
            return redirect("/login")
        else:
            return render_template("signup.html", error="Signup failed")

    return render_template("signup.html")

@app.route("/bookings")
def bookings():
    if "user" not in session:
        return redirect("/login")

    # Listing bookings is still in Python as it's just 'reading' the connection
    bookings_list = []
    if os.path.exists(RESERVATIONS_FILE):
        with open(RESERVATIONS_FILE) as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) > 0 and parts[0] == session["user"]:
                    bookings_list.append(parts)

    return render_template("bookings.html", bookings=bookings_list)

@app.route("/reserve", methods=["GET", "POST"])
def reserve():
    if "user" not in session:
        return redirect("/login")

    today = datetime.now().strftime("%Y-%m-%d")

    if request.method == "POST":
        date = request.form["date"]
        guests = int(request.form["guests"])
        slot = request.form["slot"]

        if date < today:
            return render_template("reservation.html", error="Invalid date", today=today)

        # FIND TABLES via C
        res = run_backend(["find", guests, date, slot])
        if res == "NONE" or res.startswith("ERROR"):
            return render_template("reservation.html", error="No tables available", today=today)

        session["pending_booking"] = {
            "tables": res,
            "guests": guests,
            "date": date,
            "slot": slot
        }
        return redirect("/payment")

    date = request.args.get("date", today)
    available_slots = []
    for s in TIME_SLOTS:
        # Check if any tables available for this slot (guests=1 is enough to see if ANY table is free)
        res = run_backend(["find", "1", date, s])
        if res != "NONE" and not res.startswith("ERROR"):
            available_slots.append(s)

    return render_template("reservation.html", 
                           today=today, 
                           slots=TIME_SLOTS, 
                           available_slots=available_slots)


@app.route("/payment", methods=["GET","POST"])
def payment():
    if "pending_booking" not in session:
        return redirect("/reserve")

    booking = session["pending_booking"]

    if request.method == "POST":
        # RESERVE via C
        booking_id = run_backend([
            "reserve", 
            session["user"], 
            booking["tables"], 
            booking["guests"], 
            booking["date"], 
            booking["slot"]
        ])

        booking_details = {
            "name": session["name"],
            "booking_id": booking_id,
            "table": booking["tables"].replace('|', ', '),
            "guests": booking["guests"],
            "date": booking["date"],
            "slot": booking["slot"]
        }

        send_booking_email(session["user"], app.config['MANAGER_EMAIL'], booking_details)
        session.pop("pending_booking")

        return render_template("payment.html", success="Payment Successful!", booking_id=booking_id, booking=booking_details)

    return render_template("payment.html", booking={
        "table": booking["tables"].replace('|', ', '),
        "guests": booking["guests"],
        "date": booking["date"],
        "slot": booking["slot"]
    })


def send_cancel_email(user_email, manager_email, details):
    # 1. Email to User
    user_msg = Message("Table Reservation Cancelled", 
                       sender=("Ember & Ivory", app.config['MAIL_USERNAME']), 
                       recipients=[user_email])
    user_msg.body = f"Hello {details['name']},\n\nYour reservation (ID: {details['booking_id']}) has been cancelled as per your request.\n\nDate: {details['date']}\nTime: {details['time']}\n\nWe hope to see you again soon!"
    
    # 2. Email to Manager
    manager_msg = Message(f"CANCELLATION: Booking {details['booking_id']}", 
                          sender=("Ember & Ivory", app.config['MAIL_USERNAME']), 
                          recipients=[manager_email])
    manager_msg.body = f"ALERT: A reservation has been cancelled.\n\nCustomer: {details['name']} ({user_email})\nBooking ID: {details['booking_id']}\nDate: {details['date']}\nTime: {details['time']}\n\nThe tables have been released back into the available inventory."

    try:
        mail.send(user_msg)
        mail.send(manager_msg)
    except Exception as e:
        print(f"Mail Error: {e}")
        pass

@app.route("/cancel/<int:id>")
def cancel(id):
    if "user" not in session:
        return redirect("/login")

    # Get details before cancelling to send email
    cancel_details = None
    if os.path.exists(RESERVATIONS_FILE):
        with open(RESERVATIONS_FILE) as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) > 1 and int(parts[1]) == id:
                    cancel_details = {
                        "name": session.get("name", "Guest"),
                        "booking_id": id,
                        "date": parts[4],
                        "time": parts[5]
                    }
                    break

    # CANCEL via C
    run_backend(["cancel", str(id)])

    if cancel_details:
        send_cancel_email(session["user"], app.config['MANAGER_EMAIL'], cancel_details)

    return redirect("/bookings")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/manager/login", methods=["GET", "POST"])
def manager_login():
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")
        if u == app.config['MANAGER_USERNAME'] and p == app.config['MANAGER_PASSWORD']:
            session["manager"] = u
            return redirect("/manager/dashboard")
        return render_template("manager_login.html", error="Invalid Manager Credentials")
    return render_template("manager_login.html")

@app.route("/manager/dashboard")
def manager_dashboard():
    if "manager" not in session:
        return redirect("/manager/login")
    
    all_bookings = []
    if os.path.exists(RESERVATIONS_FILE):
        with open(RESERVATIONS_FILE) as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) >= 7:
                    # status: 0=Unpaid, 1=Cancelled, 2=Paid
                    all_bookings.append(parts)
    
    return render_template("manager_dashboard.html", bookings=all_bookings[::-1])

@app.route("/manager/pay/<int:id>")
def manager_mark_paid(id):
    if "manager" not in session:
        return redirect("/manager/login")
    
    # Update via C
    run_backend(["pay", str(id)])
    return redirect("/manager/dashboard")

if __name__ == "__main__":
    app.run(debug=True)
