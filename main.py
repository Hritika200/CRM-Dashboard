import streamlit as st
import mysql.connector
from mysql.connector import Error
import pandas as pd
from datetime import datetime, timedelta
import requests
import logging
from contextlib import contextmanager
from typing import Optional, List, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Page Configuration ---
st.set_page_config(
    page_title="CRM Dashboard",
    page_icon="💼",
    layout="wide"
)

# --- Custom CSS for Navbar ---
st.markdown("""
    <style>
        .navbar-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background-color: #0077b6;
            padding: 15px 50px;
            border-radius: 10px;
        }
        .navbar-title {
            font-size: 26px;
            font-weight: bold;
            color: white;
            font-family: Arial, sans-serif;
        }
        .navbar-links {
            display: flex;
            gap: 20px;
        }
        .navbar-links a {
            font-size: 18px;
            font-weight: bold;
            color: white;
            text-decoration: none;
            padding: 10px 15px;
            border-radius: 5px;
            transition: background 0.3s ease;
        }
        .navbar-links a:hover {
            background-color: #90e0ef;
            color: black;
        }
        .error-message {
            background-color: #ffebee;
            color: #c62828;
            padding: 10px;
            border-radius: 5px;
            border-left: 5px solid #c62828;
            margin: 10px 0;
        }
        .success-message {
            background-color: #e8f5e8;
            color: #2e7d32;
            padding: 10px;
            border-radius: 5px;
            border-left: 5px solid #2e7d32;
            margin: 10px 0;
        }
    </style>
""", unsafe_allow_html=True)

# --- Custom Exception Classes ---
class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass

class ValidationError(Exception):
    """Custom exception for data validation"""
    pass

# --- Database Connection with Error Handling ---
@contextmanager
def get_db_connection():
    """Context manager for database connections with automatic cleanup"""
    connection = None
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="CRMDB",
            autocommit=False
        )
        if connection.is_connected():
            yield connection
    except Error as e:
        logger.error(f"Database connection error: {e}")
        st.error(f"Database connection failed: {e}")
        raise DatabaseError(f"Failed to connect to database: {e}")
    finally:
        if connection and connection.is_connected():
            connection.close()

# --- Validation Functions ---
def validate_customer_data(name: str, email: str, phone: str) -> List[str]:
    """Validate customer input data and return list of errors"""
    errors = []
    
    if not name or len(name.strip()) < 2:
        errors.append("Name must be at least 2 characters long")
    
    if not email or '@' not in email or '.' not in email:
        errors.append("Valid email address is required")
    
    if not phone or not phone.isdigit() or len(phone) < 10:
        errors.append("Phone number must be at least 10 digits and contain only numbers")
    
    return errors

def validate_phone_uniqueness(phone: str, exclude_customer_id: Optional[int] = None) -> bool:
    """Check if phone number is unique in database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if exclude_customer_id:
                cursor.execute(
                    "SELECT customer_id FROM Customer WHERE phone_number = %s AND customer_id != %s", 
                    (phone, exclude_customer_id)
                )
            else:
                cursor.execute("SELECT customer_id FROM Customer WHERE phone_number = %s", (phone,))
            
            return cursor.fetchone() is None
    except Exception as e:
        logger.error(f"Error checking phone uniqueness: {e}")
        return False

# --- Vehicle Management Functions ---
def get_available_vehicles() -> List[Tuple[int, str, float]]:
    """Fetch available vehicles from database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT vehicle_id, CONCAT(manufacturer, ' ', model, ' (', year, ')') as display_name, price
                FROM Vehicle 
                WHERE status = 'Available' 
                ORDER BY manufacturer, model, year
            """
            cursor.execute(query)
            vehicles = cursor.fetchall()
            return vehicles
    except Exception as e:
        logger.error(f"Error fetching vehicles: {e}")
        st.error(f"Failed to fetch available vehicles: {e}")
        return []

def check_vehicle_availability(vehicle_id: int) -> bool:
    """Check if a vehicle is still available"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM Vehicle WHERE vehicle_id = %s", (vehicle_id,))
            result = cursor.fetchone()
            return result and result[0] == 'Available'
    except Exception as e:
        logger.error(f"Error checking vehicle availability: {e}")
        return False

# --- Customer Management Functions ---
def add_customer_to_db(name: str, email: str, phone: str, vehicle_id: Optional[int] = None) -> bool:
    """Add customer to database with proper error handling"""
    try:
        # Validate input
        errors = validate_customer_data(name, email, phone)
        if errors:
            for error in errors:
                st.error(error)
            return False
        
        # Check phone uniqueness
        if not validate_phone_uniqueness(phone):
            st.error("Phone number already exists in database")
            return False
        
        # Check vehicle availability if selected
        if vehicle_id and not check_vehicle_availability(vehicle_id):
            st.error("Selected vehicle is no longer available")
            return False
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if vehicle_id column exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = 'CRMDB' 
                AND TABLE_NAME = 'Customer' 
                AND COLUMN_NAME = 'vehicle_id'
            """)
            
            has_vehicle_id = cursor.fetchone()[0] > 0
            
            if has_vehicle_id and vehicle_id:
                # New schema with vehicle_id
                query = """
                    INSERT INTO Customer (name, email_id, phone_number, vehicle_id, created_at) 
                    VALUES (%s, %s, %s, %s, NOW())
                """
                cursor.execute(query, (name.strip(), email.strip(), phone.strip(), vehicle_id))
                
                # Update vehicle status
                cursor.execute("UPDATE Vehicle SET status = 'Sold' WHERE vehicle_id = %s", (vehicle_id,))
            else:
                # Old schema or no vehicle selected
                if vehicle_id:
                    # Get vehicle name for old model_purchased field
                    cursor.execute(
                        "SELECT CONCAT(manufacturer, ' ', model, ' (', year, ')') FROM Vehicle WHERE vehicle_id = %s", 
                        (vehicle_id,)
                    )
                    vehicle_result = cursor.fetchone()
                    model_purchased = vehicle_result[0] if vehicle_result else "Unknown Vehicle"
                    
                    if has_vehicle_id:
                        query = """
                            INSERT INTO Customer (name, email_id, phone_number, vehicle_id, model_purchased, created_at) 
                            VALUES (%s, %s, %s, %s, %s, NOW())
                        """
                        cursor.execute(query, (name.strip(), email.strip(), phone.strip(), vehicle_id, model_purchased))
                    else:
                        query = """
                            INSERT INTO Customer (name, email_id, phone_number, model_purchased, created_at) 
                            VALUES (%s, %s, %s, %s, NOW())
                        """
                        cursor.execute(query, (name.strip(), email.strip(), phone.strip(), model_purchased))
                    
                    # Update vehicle status
                    cursor.execute("UPDATE Vehicle SET status = 'Sold' WHERE vehicle_id = %s", (vehicle_id,))
                else:
                    # No vehicle selected
                    query = """
                        INSERT INTO Customer (name, email_id, phone_number, created_at) 
                        VALUES (%s, %s, %s, NOW())
                    """
                    cursor.execute(query, (name.strip(), email.strip(), phone.strip()))
            
            conn.commit()
            st.success("Customer added successfully!")
            logger.info(f"Customer added: {name}, Phone: {phone}")
            return True
            
    except Exception as e:
        logger.error(f"Error adding customer: {e}")
        st.error(f"Failed to add customer: {e}")
        return False

def get_customers_with_vehicles() -> pd.DataFrame:
    """Retrieve all customers with their vehicle information"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if vehicle_id column exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = 'CRMDB' 
                AND TABLE_NAME = 'Customer' 
                AND COLUMN_NAME = 'vehicle_id'
            """)
            
            has_vehicle_id = cursor.fetchone()[0] > 0
            
            if has_vehicle_id:
                # New query with vehicle_id column
                query = """
                    SELECT 
                        c.customer_id,
                        c.name,
                        c.email_id,
                        c.phone_number,
                        CASE 
                            WHEN v.vehicle_id IS NOT NULL 
                            THEN CONCAT(v.manufacturer, ' ', v.model, ' (', v.year, ')')
                            ELSE COALESCE(c.model_purchased, 'No vehicle assigned')
                        END as vehicle_purchased,
                        v.price as vehicle_price,
                        c.created_at
                    FROM Customer c
                    LEFT JOIN Vehicle v ON c.vehicle_id = v.vehicle_id
                    ORDER BY c.created_at DESC
                """
            else:
                # Fallback query for old schema
                query = """
                    SELECT 
                        c.customer_id,
                        c.name,
                        c.email_id,
                        c.phone_number,
                        COALESCE(c.model_purchased, 'No vehicle assigned') as vehicle_purchased,
                        NULL as vehicle_price,
                        c.created_at
                    FROM Customer c
                    ORDER BY c.created_at DESC
                """
            
            df = pd.read_sql(query, conn)
            return df
    except Exception as e:
        logger.error(f"Error fetching customers: {e}")
        st.error(f"Failed to fetch customer data: {e}")
        return pd.DataFrame()

# --- Database Migration Functions ---
def migrate_database():
    """Safely migrate existing database to new schema"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if vehicle_id column exists in Customer table
            cursor.execute("""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = 'CRMDB' 
                AND TABLE_NAME = 'Customer' 
                AND COLUMN_NAME = 'vehicle_id'
            """)
            
            vehicle_id_exists = cursor.fetchone()[0] > 0
            
            if not vehicle_id_exists:
                st.info("🔄 Upgrading database schema...")
                
                # Add vehicle_id column to existing Customer table
                cursor.execute("""
                    ALTER TABLE Customer 
                    ADD COLUMN vehicle_id BIGINT NULL
                """)
                
                # Add updated_at column if it doesn't exist
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = 'CRMDB' 
                    AND TABLE_NAME = 'Customer' 
                    AND COLUMN_NAME = 'updated_at'
                """)
                
                if cursor.fetchone()[0] == 0:
                    cursor.execute("""
                        ALTER TABLE Customer 
                        ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    """)
                
                # Add indexes for better performance
                try:
                    cursor.execute("CREATE INDEX idx_vehicle ON Customer(vehicle_id)")
                except Error:
                    pass  # Index might already exist
                
                conn.commit()
                st.success("✅ Database schema updated successfully!")
                logger.info("Database migration completed successfully")
            
    except Exception as e:
        logger.error(f"Error during database migration: {e}")
        st.error(f"Database migration failed: {e}")


# --- Database Initialization ---
def initialize_tables():
    """Clear and reinitialize database tables with improved schema"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Disable foreign key checks temporarily to avoid constraint issues during truncation
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

            # Truncate tables in the correct order (children first due to FK constraints)
            # cursor.execute("TRUNCATE TABLE Sales")
            # cursor.execute("TRUNCATE TABLE Follow_ups")
            # cursor.execute("TRUNCATE TABLE Interactions")
            # cursor.execute("TRUNCATE TABLE Vehicle")
            # cursor.execute("TRUNCATE TABLE Customer")

            # Re-enable foreign key checks
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

            # Now recreate and repopulate tables
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS Customer (
                customer_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email_id VARCHAR(100),
                phone_number VARCHAR(15) UNIQUE NOT NULL,
                model_purchased VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            cursor.execute("""
           
            CREATE TABLE IF NOT EXISTS Vehicle (
                vehicle_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                manufacturer VARCHAR(50) NOT NULL,
                model VARCHAR(50) NOT NULL,
                year INT NOT NULL,
                price DECIMAL(12,2) NOT NULL,
                status ENUM('Available', 'Sold', 'Reserved') DEFAULT 'Available',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_status (status),
                INDEX idx_model (manufacturer, model)
            )
            """)

            #Insert sample vehicle data again
            vehicle_data = [
                ("Ford", "Mustang", 2020, 2750000.00, "Available"),
                ("Tata", "Altroz", 2023, 1200000.00, "Available"),
                ("Tata", "Nexon", 2023, 1350000.00, "Available"),
                ("Tata", "Tiago", 2023, 1100000.00, "Available"),
                ("Toyota", "Urban Cruiser Taisor", 2023, 1700000.00, "Available"),
                ("Toyota", "Glanza", 2023, 1600000.00, "Available"),
                ("Hyundai", "Creta", 2022, 2100000.00, "Available"),
                ("Mahindra", "XUV700", 2023, 2600000.00, "Available"),
                ("Kia", "Seltos", 2020, 1950000.00, "Available"),
                ("Nissan", "Magnite", 2022, 1650000.00, "Available"),
                ("Toyota", "Vellfire", 2023, 3500000.00, "Available"),
                ("Renault", "Triber", 2023, 1250000.00, "Available"),
                ("Kia", "EV9", 2023, 4000000.00, "Available")
            ]
            # vehicle_data = []

            insert_query = """
                INSERT INTO Vehicle (manufacturer, model, year, price, status) 
                VALUES (%s, %s, %s, %s, %s)
            """
            # Insert query with ON DUPLICATE KEY UPDATE
            insert_query = """INSERT INTO Vehicle (manufacturer, model, year, price, status) VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE price=VALUES(price), status=VALUES(status)
"""
            cursor.executemany(insert_query, vehicle_data)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS Interactions (
                interaction_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                customer_id BIGINT,
                vehicle_id BIGINT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                type TEXT,
                notes TEXT,
                FOREIGN KEY (customer_id) REFERENCES Customer(customer_id) ON DELETE CASCADE,
                FOREIGN KEY (vehicle_id) REFERENCES Vehicle(vehicle_id) ON DELETE SET NULL
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS Follow_ups (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                customer_id BIGINT NOT NULL,
                follow_up_date TIMESTAMP NOT NULL,
                reason TEXT NOT NULL,
                completed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES Customer(customer_id) ON DELETE CASCADE
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS Sales (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                customer_id BIGINT NOT NULL,
                vehicle_id BIGINT NOT NULL,
                sale_date DATE NOT NULL,
                payment_status ENUM('Pending', 'Partial', 'Completed') DEFAULT 'Pending',
                vin VARCHAR(50) UNIQUE,
                sale_amount DECIMAL(12,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES Customer(customer_id) ON DELETE CASCADE,
                FOREIGN KEY (vehicle_id) REFERENCES Vehicle(vehicle_id) ON DELETE CASCADE
            )
            """)

            conn.commit()
            logger.info("Database reset and tables initialized successfully")

    except Exception as e:
        logger.error(f"Error initializing tables: {e}")
        st.error(f"Failed to initialize database: {e}")

# --- Navbar ---
st.markdown("""
    <div class="navbar-container">
        <div class="navbar-title">CRM Dashboard</div>
        <div class="navbar-links">
            <a href="?nav=home">Home</a>
            <a href="?nav=add">Add Customer</a>
            <a href="?nav=view">View Customers</a>
            <a href="?nav=vehicles">Manage Vehicles</a>
            <a href="?nav=query">Query Tables</a>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- Initialize Database ---
initialize_tables()
migrate_database()  # Add this line to run migration

# --- Navigation ---
query_params = st.query_params
selected_page = query_params.get("nav", "home")

# --- Pages ---
if selected_page == "home":
    st.markdown("<h1 style='color:#0077b6;text-align:center;'>Welcome to CRM Dashboard</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <div style='text-align: center;'>
                <p style='font-size: 20px; font-family: Georgia;'>
                    A central system to manage customer relationships efficiently.
                    You can add new customer data, view existing records, manage vehicles, and query the CRM database.
                </p>
            </div>
        """, unsafe_allow_html=True)

        if st.button("Get Started", use_container_width=True):
            st.query_params.update(nav="add")
            st.rerun()

elif selected_page == "add":
    st.header("📝 Add New Customer")
    
    with st.form("add_customer_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Customer Name *", placeholder="Enter full name")
            email = st.text_input("Email Address *", placeholder="customer@example.com")
        
        with col2:
            phone = st.text_input("Phone Number *", placeholder="10-digit phone number")
            
            # Vehicle selection dropdown
            vehicles = get_available_vehicles()
            if vehicles:
                vehicle_options = {0: "No vehicle (Lead only)"} | {v[0]: f"{v[1]} - ₹{v[2]:,.0f}" for v in vehicles}
                selected_vehicle = st.selectbox(
                    "Select Vehicle (Optional)",
                    options=list(vehicle_options.keys()),
                    format_func=lambda x: vehicle_options[x],
                    index=0
                )
            else:
                selected_vehicle = 0
                st.warning("No vehicles available in inventory")
        
        st.markdown("*Required fields")
        
        submitted = st.form_submit_button("Add Customer", use_container_width=True)
        
        if submitted:
            if name and email and phone:
                vehicle_id = selected_vehicle if selected_vehicle > 0 else None
                if add_customer_to_db(name, email, phone, vehicle_id):
                    st.balloons()
            else:
                st.error("Please fill in all required fields")

elif selected_page == "view":
    st.header("👥 Customer Records")
    
    # Add refresh button
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("🔄 Refresh Data"):
            st.rerun()
    
    # Fetch and display customers
    df = get_customers_with_vehicles()
    if not df.empty:
        # Add search functionality
        search_term = st.text_input("🔍 Search customers...", placeholder="Search by name, email, or phone")
        if search_term:
            mask = df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
            df = df[mask]
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Customers", len(df))
        with col2:
            customers_with_vehicles = len(df[df['vehicle_purchased'] != 'No vehicle assigned'])
            st.metric("Customers with Vehicles", customers_with_vehicles)
        with col3:
            if 'vehicle_price' in df.columns:
                total_sales = df['vehicle_price'].fillna(0).sum()
                st.metric("Total Sales Value", f"₹{total_sales:,.0f}")
        with col4:
            leads_only = len(df[df['vehicle_purchased'] == 'No vehicle assigned'])
            st.metric("Leads Only", leads_only)
        
        # Display data
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "customer_id": "ID",
                "name": "Name",
                "email_id": "Email",
                "phone_number": "Phone",
                "vehicle_purchased": "Vehicle",
                "vehicle_price": st.column_config.NumberColumn(
                    "Price (₹)",
                    format="₹%.0f"
                ),
                "created_at": st.column_config.DatetimeColumn(
                    "Created",
                    format="DD/MM/YYYY HH:mm"
                )
            }
        )
    else:
        st.info("No customer records found. Add some customers to get started!")

elif selected_page == "vehicles":
    st.header("🚗 Vehicle Management")
    
    try:
        with get_db_connection() as conn:
            # Display vehicle inventory
            query = """
                SELECT 
                    vehicle_id,
                    manufacturer,
                    model,
                    year,
                    price,
                    status,
                    (SELECT COUNT(*) FROM Customer WHERE vehicle_id = Vehicle.vehicle_id) as customers_assigned
                FROM Vehicle 
                ORDER BY manufacturer, model, year
            """
            df = pd.read_sql(query, conn)
            
            if not df.empty:
                # Vehicle statistics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Vehicles", len(df))
                with col2:
                    available_count = len(df[df['status'] == 'Available'])
                    st.metric("Available", available_count)
                with col3:
                    sold_count = len(df[df['status'] == 'Sold'])
                    st.metric("Sold", sold_count)
                with col4:
                    avg_price = df['price'].mean()
                    st.metric("Avg Price", f"₹{avg_price:,.0f}")
                
                # Display vehicles
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "vehicle_id": "ID",
                        "manufacturer": "Make",
                        "model": "Model",
                        "year": "Year",
                        "price": st.column_config.NumberColumn(
                            "Price (₹)",
                            format="₹%.0f"
                        ),
                        "status": st.column_config.SelectboxColumn(
                            "Status",
                            options=["Available", "Sold", "Reserved"]
                        ),
                        "customers_assigned": "Customers"
                    }
                )
            else:
                st.info("No vehicles in inventory")
                
    except Exception as e:
        st.error(f"Error loading vehicle data: {e}")

elif selected_page == "query":
    st.header("🔍 Custom Database Query")
    
    # Predefined safe queries
    st.subheader("Quick Queries")
    query_options = {
        "All Customers": "SELECT * FROM Customer ORDER BY created_at DESC",
        "Available Vehicles": "SELECT * FROM Vehicle WHERE status = 'Available'",
        "Sales Summary": """
            SELECT 
                CONCAT(v.manufacturer, ' ', v.model) as vehicle,
                COUNT(c.customer_id) as customers_count,
                SUM(v.price) as total_value
            FROM Vehicle v
            LEFT JOIN Customer c ON v.vehicle_id = c.vehicle_id
            WHERE v.status = 'Sold'
            GROUP BY v.vehicle_id, v.manufacturer, v.model
        """,
        "Customer Vehicle Report": """
            SELECT 
                c.name,
                c.email_id,
                c.phone_number,
                CONCAT(v.manufacturer, ' ', v.model, ' (', v.year, ')') as vehicle,
                v.price
            FROM Customer c
            LEFT JOIN Vehicle v ON c.vehicle_id = v.vehicle_id
            ORDER BY c.name
        """
    }
    
    selected_query = st.selectbox("Select a predefined query:", list(query_options.keys()))
    
    if st.button(f"Run Query: {selected_query}"):
        try:
            with get_db_connection() as conn:
                df = pd.read_sql(query_options[selected_query], conn)
                st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Query error: {e}")
    
    # Custom query section
    st.subheader("Custom Query")
    st.warning("⚠️ Only SELECT statements are allowed for security")
    
    custom_query = st.text_area(
        "Enter your SQL query:",
        placeholder="SELECT * FROM Customer WHERE name LIKE '%John%'"
    )
    
    if st.button("Execute Custom Query") and custom_query.strip():
        # Basic security check
        if not custom_query.strip().upper().startswith('SELECT'):
            st.error("Only SELECT queries are allowed")
        else:
            try:
                with get_db_connection() as conn:
                    df = pd.read_sql(custom_query, conn)
                    st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"Query error: {e}")

# --- Footer ---
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>CRM Dashboard v2.0 - Enhanced with Vehicle Management & Error Handling</div>",
    unsafe_allow_html=True
)

# def initialize_tables():
#     """Initialize database tables with improved schema"""
#     try:
#         with get_db_connection() as conn:
#             cursor = conn.cursor()

#             # Create Customer table (original structure maintained)
#             cursor.execute("""
#             CREATE TABLE IF NOT EXISTS Customer (
#                 customer_id BIGINT AUTO_INCREMENT PRIMARY KEY,
#                 name VARCHAR(100) NOT NULL,
#                 email_id VARCHAR(100),
#                 phone_number VARCHAR(15) UNIQUE NOT NULL,
#                 model_purchased VARCHAR(100),
#                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#             )
#             """)

#             cursor.execute("""
#             CREATE TABLE IF NOT EXISTS Vehicle (
#                 vehicle_id BIGINT AUTO_INCREMENT PRIMARY KEY,
#                 manufacturer VARCHAR(50) NOT NULL,
#                 model VARCHAR(50) NOT NULL,
#                 year INT NOT NULL,
#                 price DECIMAL(12,2) NOT NULL,
#                 status ENUM('Available', 'Sold', 'Reserved') DEFAULT 'Available',
#                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                 INDEX idx_status (status),
#                 INDEX idx_model (manufacturer, model)
#             )
#             """)

#             # Insert sample vehicle data if table is empty
#             cursor.execute("SELECT COUNT(*) FROM Vehicle")
#             if cursor.fetchone()[0] == 0:
#                 vehicle_data = [
#                     ("Ford", "Mustang", 2020, 2750000.00, "Available"),
#                     ("Tata", "Altroz", 2023, 1200000.00, "Available"),
#                     ("Tata", "Nexon", 2023, 1350000.00, "Available"),
#                     ("Tata", "Tiago", 2023, 1100000.00, "Available"),
#                     ("Toyota", "Urban Cruiser Taisor", 2023, 1700000.00, "Available"),
#                     ("Toyota", "Glanza", 2023, 1600000.00, "Available"),
#                     ("Hyundai", "Creta", 2022, 2100000.00, "Available"),
#                     ("Mahindra", "XUV700", 2023, 2600000.00, "Available"),
#                     ("Kia", "Seltos", 2020, 1950000.00, "Available"),
#                     ("Nissan", "Magnite", 2022, 1650000.00, "Available"),
#                     ("Toyota", "Vellfire", 2023, 3500000.00, "Available"),
#                     ("Renault", "Triber", 2023, 1250000.00, "Available"),
#                     ("Kia", "EV9", 2023, 4000000.00, "Available")
#                 ]
                
#                 insert_query = """
#                     INSERT INTO Vehicle (manufacturer, model, year, price, status) 
#                     VALUES (%s, %s, %s, %s, %s)
#                 """
#                 cursor.executemany(insert_query, vehicle_data)

#             # Other tables remain the same but with proper foreign key constraints
#             cursor.execute("""
#             CREATE TABLE IF NOT EXISTS Interactions (
#                 interaction_id BIGINT AUTO_INCREMENT PRIMARY KEY,
#                 customer_id BIGINT,
#                 vehicle_id BIGINT,
#                 date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                 type TEXT,
#                 notes TEXT,
#                 FOREIGN KEY (customer_id) REFERENCES Customer(customer_id) ON DELETE CASCADE,
#                 FOREIGN KEY (vehicle_id) REFERENCES Vehicle(vehicle_id) ON DELETE SET NULL
#             )
#             """)

#             cursor.execute("""
#             CREATE TABLE IF NOT EXISTS Follow_ups (
#                 id BIGINT AUTO_INCREMENT PRIMARY KEY,
#                 customer_id BIGINT NOT NULL,
#                 follow_up_date TIMESTAMP NOT NULL,
#                 reason TEXT NOT NULL,
#                 completed BOOLEAN DEFAULT FALSE,
#                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                 FOREIGN KEY (customer_id) REFERENCES Customer(customer_id) ON DELETE CASCADE
#             )
#             """)

#             cursor.execute("""
#             CREATE TABLE IF NOT EXISTS Sales (
#                 id BIGINT AUTO_INCREMENT PRIMARY KEY,
#                 customer_id BIGINT NOT NULL,
#                 vehicle_id BIGINT NOT NULL,
#                 sale_date DATE NOT NULL,
#                 payment_status ENUM('Pending', 'Partial', 'Completed') DEFAULT 'Pending',
#                 vin VARCHAR(50) UNIQUE,
#                 sale_amount DECIMAL(12,2),
#                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                 FOREIGN KEY (customer_id) REFERENCES Customer(customer_id) ON DELETE CASCADE,
#                 FOREIGN KEY (vehicle_id) REFERENCES Vehicle(vehicle_id) ON DELETE CASCADE
#             )
#             """)

#             conn.commit()
#             logger.info("Database tables initialized successfully")
            
#     except Exception as e:
#         logger.error(f"Error initializing tables: {e}")
#         st.error(f"Failed to initialize database: {e}")

