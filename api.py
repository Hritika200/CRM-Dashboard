from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# --- Database Connection ---
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="CRMDB"
    )

# --- Root Route: Show All Tables ---
@app.route('/', methods=['GET'])
def view_all_tables():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        tables = ['Customer', 'Vehicle', 'Interactions', 'Follow_ups', 'Sales']
        data = {}

        for table in tables:
            cursor.execute(f"SELECT * FROM {table}")
            data[table] = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(data), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- Add Customer API ---
@app.route('/add_customer', methods=['POST'])
def add_customer():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email_id')
    phone = data.get('phone_number')
    vehicle_id = data.get('vehicle_id')  # New: expects int or None
    vin = data.get('vin')
    payment_status = data.get('payment_status', 'Pending')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Validate vehicle_id if provided
        if vehicle_id:
            cursor.execute("SELECT status FROM Vehicle WHERE vehicle_id = %s", (vehicle_id,))
            vehicle_status = cursor.fetchone()
            if not vehicle_status or vehicle_status[0].lower() == 'sold':
                return jsonify({"status": "error", "message": "Vehicle not available or sold."}), 400

        # Insert customer with vehicle_id (nullable)
        cursor.execute(
            "INSERT INTO Customer (name, email_id, phone_number, vehicle_id) VALUES (%s, %s, %s, %s)",
            (name, email, phone, vehicle_id)
        )
        customer_id = cursor.lastrowid

        # Log interaction
        cursor.execute(
            "INSERT INTO Interactions (customer_id, vehicle_id, type, date, notes) VALUES (%s, %s, %s, NOW(), %s)",
            (customer_id, vehicle_id, 'Sale' if vehicle_id else 'New Customer',
             'Vehicle sold at time of registration' if vehicle_id else 'Initial interaction on registration')
        )

        # Schedule follow-up
        follow_up_date = datetime.now() + timedelta(days=3)
        cursor.execute(
            "INSERT INTO Follow_ups (customer_id, follow_up_date, reason, completed) VALUES (%s, %s, %s, %s)",
            (customer_id, follow_up_date, "Initial follow-up", False)
        )

        # Insert Sale record if applicable
        if vehicle_id and vin:
            cursor.execute(
                "INSERT INTO Sales (customer_id, vehicle_id, sale_date, payment_status, vin) VALUES (%s, %s, CURDATE(), %s, %s)",
                (customer_id, vehicle_id, payment_status, vin)
            )
            cursor.execute(
                "UPDATE Vehicle SET status = 'Sold' WHERE vehicle_id = %s",
                (vehicle_id,)
            )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "success", "message": "Customer, interaction, follow-up, and sales data added"}), 200

    except mysql.connector.IntegrityError as ie:
        return jsonify({"status": "error", "message": "Duplicate VIN or constraint issue"}), 409
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    # deepcode ignore RunWithDebugTrue: <please specify a reason of ignoring this>
    app.run(debug=False)
