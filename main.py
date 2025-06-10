
uSEFUL CODE

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

