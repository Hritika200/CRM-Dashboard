💼 CRM Dashboard
A basic Customer Relationship Management (CRM) dashboard built using:

 💠Python

 💠Flask API (backend)

 💠Streamlit (frontend UI)

 💠MySQL (database)

This website allows you to manage customer data, record vehicle sales, schedule follow-ups, and track interactions in a centralized interface.

📌 Features

✅ Add new customers via a friendly Streamlit form

✅ Automatically log customer interactions

✅ Schedule a follow-up 3 days after a new customer is added

✅ View all customer records and query any table from the CRMDB

✅ API built with Flask, accessible for backend integrations

🧱 Project Structure
bash

Copy

Edit

crm-dashboard/
│
├── app.py              # Flask backend API
├── dashboard.py        # Streamlit frontend
├── requirements.txt    # Python dependencies
└── README.md           # Project documentation

🛠️ Setup Instructions
Python 3.8+,
MySQL installed and running,
CRMDB database created in MySQL

📝 Since a local database is used in this project the application will have issues in being deployed for that use cloud based databases and migrate the local database from MySQL, PostGRESQL to that cloud database platforms like Railway, Amazon RDS Free Tier, Aiven,etc.
