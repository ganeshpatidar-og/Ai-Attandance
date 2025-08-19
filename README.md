# AI Attendance System 🎓

An AI-powered face recognition attendance management system built with Flask.
It allows administrators to register students, approve them, and mark attendance automatically using face recognition.

🚀 Features

👨‍🎓 Student registration with face image

✅ Admin approval system

🤖 Face recognition–based attendance marking

📊 View and manage student attendance

🗄️ Database integration (SQL scripts included)

🎨 Web interface with HTML/CSS templates

📂 Project Structure
AI_attendance/
│── app.py               # Main Flask application
│── connection.py        # Database connection logic
│── requirements.txt     # Python dependencies
│── SqlQuery.txt         # SQL queries for DB setup
│── static/              # CSS, images, and static files
│   ├── styles.css
│   └── faces/           # Student face images
│── templates/           # HTML templates (Flask Jinja2)
    ├── home.html
    ├── admin_login.html
    ├── admin_dashboard.html
    ├── register_student.html
    ├── take_attendance.html
    ├── view_attendance.html
    └── ...

⚙️ Installation & Setup

Clone the repository

git clone <your-repo-url>
cd "AI attendance/AI attendance"


Create virtual environment

python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows


Install dependencies

pip install -r requirements.txt


Setup Database

Open SqlQuery.txt and execute queries in your SQL database.

Update connection.py with your DB credentials.

Run the app

python app.py


Open browser at http://127.0.0.1:5000/

🖥️ Tech Stack
Python (Flask)
OpenCV / Face Recognition (if used in backend)
MySQL / SQLite
HTML, CSS (Bootstrap for frontend)

🤝 Contributing

Fork the project

Create your feature branch (git checkout -b feature/YourFeature)

Commit changes (git commit -m 'Add YourFeature')

Push to branch (git push origin feature/YourFeature)

Open a Pull Request

📜 License

This project is licensed under the MIT License.
