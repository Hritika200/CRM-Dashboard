from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# @app.route('/')
# def home():
#     return 'Hello, Render!'
# --- Database Connection ---
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="CRMDB"
    )

# --- Add Customer API ---
@app.route('/add_customer', methods=['POST'])
def add_customer():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email_id')
    phone = data.get('phone_number')
    vehicle_id = data.get('vehicle_id')
    payment_status = data.get('payment_status', 'Pending')
    sale_amount = data.get('sale_amount')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Validate phone
        cursor.execute("SELECT customer_id FROM Customer WHERE phone_number = %s", (phone,))
        if cursor.fetchone():
            return jsonify({"status": "error", "message": "Phone number already exists"}), 409

        # Vehicle logic
        if vehicle_id:
            cursor.execute("SELECT manufacturer, model, year, stock FROM Vehicle WHERE vehicle_id = %s", (vehicle_id,))
            vehicle = cursor.fetchone()
            if not vehicle:
                return jsonify({"status": "error", "message": "Vehicle not found"}), 404

            manufacturer, model, year, stock = vehicle
            if stock <= 0:
                return jsonify({"status": "error", "message": "Vehicle is out of stock"}), 400

            model_purchased = f"{manufacturer} {model} ({year})"

            # Decrease stock
            cursor.execute("UPDATE Vehicle SET stock = stock - 1 WHERE vehicle_id = %s AND stock > 0", (vehicle_id,))

            # Update status if total stock of that model-year is zero
            cursor.execute("""
                UPDATE Vehicle v
                JOIN (
                    SELECT manufacturer, model, year
                    FROM Vehicle
                    GROUP BY manufacturer, model, year
                    HAVING SUM(stock) <= 0
                ) AS depleted
                ON v.manufacturer = depleted.manufacturer AND v.model = depleted.model AND v.year = depleted.year
                SET v.status = 'Sold'
            """)
        else:
            model_purchased = None

        # Insert Customer
        if vehicle_id:
            cursor.execute("""
                INSERT INTO Customer (name, email_id, phone_number, vehicle_id, model_purchased, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (name.strip(), email.strip(), phone.strip(), vehicle_id, model_purchased))
        else:
            cursor.execute("""
                INSERT INTO Customer (name, email_id, phone_number, created_at)
                VALUES (%s, %s, %s, NOW())
            """, (name.strip(), email.strip(), phone.strip()))

        customer_id = cursor.lastrowid
        print("✅ Customer inserted with ID:", customer_id)

        # Insert Follow-Up
        follow_up_reason = "Post-sale vehicle service follow-up" if vehicle_id else "Initial lead follow-up"
        follow_up_days = 30 if vehicle_id else 3
        cursor.execute("""
            INSERT INTO Follow_ups (customer_id, follow_up_date, reason, completed)
            VALUES (%s, NOW() + INTERVAL %s DAY, %s, FALSE)
        """, (customer_id, follow_up_days, follow_up_reason))

        # Insert into Sales
        cursor.execute("""INSERT INTO Sales (customer_id, vehicle_id, sale_date, payment_status, sale_amount)
                       VALUES (%s, %s, NOW(), %s, %s""", (customer_id, vehicle_id, payment_status, sale_amount))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "success", "message": "Customer, follow-up and sales recorded"}), 200

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# --- View All Tables API (for frontend debugging) ---
@app.route('/', methods=['GET'])
def view_all_tables():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        tables = ['Customer', 'Vehicle', 'Follow_ups', 'Sales']
        data = {}

        for table in tables:
            cursor.execute(f"SELECT * FROM {table}")
            data[table] = cursor.fetchall()

        cursor.close()
        conn.close()
        return jsonify(data), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False)
