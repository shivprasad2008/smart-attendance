# Smart Attendance System

This is a simple attendance tracking project built for demonstration purposes.
It is designed to work reliably during presentations without depending on QR scanning or complex setups.

The system uses a code-based approach where teachers generate a session code and students use that code to mark their attendance.

---

## Project Overview

The system has three types of users:

* Admin
* Teacher
* Student

Each role has a specific purpose in the system.

---

## Admin

The admin manages all users in the system.

Default admin account:

* Username: shiv
* Password: 1234

Admin responsibilities:

* Create student accounts
* Create teacher accounts
* Control who can access the system

There is no public signup. Only admin-created users can log in.

---

## Teacher

Teachers are responsible for conducting attendance sessions.

What a teacher can do:

* Start a session
* Generate a unique session code (for example: ATT-92KF)
* Show the code to students
* End the session
* View basic attendance information

---

## Student

Students use the system to mark their attendance.

What a student can do:

* Log in using credentials provided by admin
* Enter the session code
* Mark attendance
* View their attendance summary

---

## How Attendance Works

1. Teacher starts a session
2. System generates a session code
3. Students enter the code
4. Attendance is recorded

The system checks:

* Whether the session is active
* Whether the code is valid
* Whether the student has already marked attendance

---

## Attendance Calculation

Attendance is calculated using the formula:

Attendance % = (Attended Classes / Total Classes) × 100

This is used to show:

* Total classes
* Attended classes
* Missed classes
* Overall percentage

---

## Technology Used

Backend:

* Python (Flask)

Frontend:

* HTML
* CSS
* JavaScript

Storage:

* In-memory data (no database used)

---

## Notes

* This project is built for demonstration and learning purposes
* Data is not stored permanently (resets when server restarts)
* The system is kept simple to ensure it works smoothly during presentations

---

## Future Improvements (Optional)

* Add database for permanent storage
* Improve authentication system
* Add detailed analytics and reports
* Add mobile responsiveness

---

## Conclusion

This project demonstrates a basic attendance management system using a simple and reliable approach.
It focuses on functionality and clarity rather than complexity.
