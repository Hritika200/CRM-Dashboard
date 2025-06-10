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
✅ Record vehicle purchases and update vehicle status to "Sold"
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

🚀 How It Works
1. Backend (Flask API)
The app.py defines API endpoints such as:
POST /add_customer — adds a customer, logs an interaction, schedules a follow-up
GET / — fetches all CRM table data

Includes logic to:
Match vehicles using CONCAT(manufacturer, model)
Record sales in the Sales table with VIN and payment status
Update Vehicle.status to "Sold"

2. Frontend (Streamlit UI)
Clean navigation bar with custom CSS

Pages:
Home: Welcome message and "Get Started" button
Add Customer: Form for submitting new customer info
View Customers:See all customers in a table
Query Tables: Enter a table name to view contents dynamically

🛠️ Setup Instructions
✅ Prerequisites
Python 3.8+
MySQL installed and running
CRMDB database created in MySQL
