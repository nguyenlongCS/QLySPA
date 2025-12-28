from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('pages/home.html')

@app.route('/about')
def about():
    return render_template('pages/about.html')

@app.route('/services')
def services():
    return render_template('pages/services.html')

@app.route('/feedback')
def feedback():
    return render_template('pages/feedback.html')

@app.route('/contact')
def contact():
    return render_template('pages/contact.html')

@app.route('/booking')
def booking():
    return render_template('pages/booking.html')

@app.route('/login')
def login():
    return render_template('pages/login.html')

@app.route('/register')
def register():
    return render_template('pages/register.html')

@app.route('/employee')
def employee():
    return render_template('pages/employee.html')

@app.route('/admin')
def admin():
    return render_template('pages/admin.html')

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5500,
        debug=True   # auto reload HTML + Python
    )