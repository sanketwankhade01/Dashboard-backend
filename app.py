from flask import Flask, jsonify, request
from flask_cors import CORS
from collections import Counter
import os
import logging
import pyodbc
import datetime
import jwt
from functools import wraps

# If a .env file is present, load it so environment variables work locally.
try:
    # python-dotenv is optional; app continues to work if not installed and env vars are set externally
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*", "allow_headers": ["Authorization", "Content-Type", "x-access-token"]}})
app.config['SECRET_KEY'] = '123sadasdasd'  # Change this to a random secret key


# DB_PATH = 'dashboard1.db'

#New Changes done by Ashish 07-09-2025
#Read SQL Database Configration.
DB_DRIVER = os.getenv("DB_DRIVER")
SERVER = os.getenv("SERVER")
DATABASE = os.getenv("DATABASE")
UID = os.getenv("UID")
PASSWORDD = os.getenv("PASSWORDD")

# Basic validation/logging for missing DB config so users know what to set.
missing = [k for k, v in {
    'DB_DRIVER': DB_DRIVER,
    'SERVER': SERVER,
    'DATABASE': DATABASE,
    'UID': UID,
    'PASSWORDD': PASSWORDD
}.items() if not v]
if missing:
    logging.warning(f"Missing environment variables for DB connection: {missing}.\n"
                    "You can create a .env file (already present in this repo) or set env vars externally.")

#Define SQL Connection (Function 1)
def get_db_connection():
    """Create and return a database connection using environment variables."""
    try:
        connection = pyodbc.connect(
            f"DRIVER={DB_DRIVER};"
            f"SERVER={SERVER};"
            f"DATABASE={DATABASE};"
            f"UID={UID};"
            f"PWD={PASSWORDD};"
        )
        return connection
    except pyodbc.Error as e:        
        raise Exception(f"Database connection failed: {str(e)}")
    except Exception as e:        
        raise Exception(f"Unexpected error connecting to database: {str(e)}")
    

#Validate API Running or not (Function 2)
@app.route('/')
def home():
    return jsonify({"message": "Helpdesk Dashboard API is running!"})


#Fetch data based on where condition (Function 3)
def fetch_Chatbot_Transaction(date_filter=None, product="None", company=None):
    """Fetch tickets from Chatbot_Transaction table with optional date, product, and company filters."""
    connection = get_db_connection()
    cursor = connection.cursor()

    query = """
        SELECT Ticket_Creation_Date,Ticket_No,Ticket_Status,Company_Work_Feedback,
               Ticket_Priority,Ticket_Category,Ticket_Day_Open,
               Product_Name, Company_Name
        FROM Chatbot_Transaction
        WHERE 1=1
    """
    params = []

    # Add optional filters
    if date_filter:

        #  query += " AND CAST(Ticket_Creation_Date AS DATE) = CAST(? AS DATE)"
        #  params.append(date_filter)
        try:
            startdate, enddate = date_filter.split(" AND ")
            query += " AND CAST(Ticket_Creation_Date AS DATE) BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)"
            params.extend([startdate.strip(), enddate.strip()])
        except ValueError:
            raise ValueError("Invalid date_filter format. Expected 'startdate AND enddate'.")

    if product:
        query += " AND Product_Name LIKE ?"
        params.append(f"%{product}%")

    if company:
        query += " AND Company_Name LIKE ?"
        params.append(f"%{company}%")

    print("📌 Executing SQL:", query)
    print("📌 Params:", params)

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()    
    print(f"📊 Rows fetched from DB: {len(rows)}")  # Debug log
    cursor.close()
    connection.close()
    return rows
         

# All Get Function (Section 4)
@app.route('/api/dates', methods=['GET'])
def get_dates():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT CAST(Ticket_Creation_Date AS DATE) FROM Chatbot_Transaction")
    dates = [str(row[0]) for row in cursor.fetchall()]
    conn.close()
    return jsonify(dates)

# NEW ENDPOINT: Return list of Product_Name for dropdown
@app.route('/api/Product_Name', methods=['GET'])
def get_Product_Name():
    """Return unique Product_Name for employee dropdown"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Product_Name FROM Chatbot_Transaction ORDER BY Product_Name")
    employees = [{"id": i+1, "name": row[0]} for i, row in enumerate(cursor.fetchall())]
    conn.close()
    return jsonify(employees)

# NEW ENDPOINT: Return list of Company_Name for dropdown
@app.route('/api/companies', methods=['GET'])
def get_companies():
    """Return unique Company_Name for company dropdown"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Company_Name FROM Chatbot_Transaction ORDER BY Company_Name")
    companies = [{"id": i+1, "name": row[0]} for i, row in enumerate(cursor.fetchall())]
    conn.close()
    return jsonify(companies)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    date = request.args.get('date')
    product = request.args.get('product')
    company = request.args.get('company')
    print(f"📌 /api/stats requested for date={date}, product={product}, company={company}")  # Debug log

    rows = fetch_Chatbot_Transaction(date, product, company)

    if not rows:
        print("⚠️ No rows found for stats")
        return jsonify([])

    total_tickets = len(rows)

    # FIX: Ticket_Status is column index 2
    status_counts = Counter([r[2] for r in rows])

    # FIX: Ticket_Day_Open is column index 6
    avg_days_open = int(
        sum(r[6] for r in rows if r[2] == 'Open') /
        max(status_counts.get('Open', 1), 1)
    )

    stats = [
        {"label": "Tickets", "value": total_tickets, "color": "#6f42c1",
         "graphwidth": min(total_tickets, 100)},

        {"label": "Open", "value": status_counts.get('Open', 0), "color": "#dc3545",
         "graphwidth": min(int((status_counts.get('Open', 0) / total_tickets) * 100), 100)},

        {"label": "Resolved", "value": status_counts.get('Resolved', 0), "color": "#17a2b8",
         "graphwidth": min(int((status_counts.get('Resolved', 0) / total_tickets) * 100), 100)},

        {"label": "Closed", "value": status_counts.get('Closed', 0), "color": "#28a745",
         "graphwidth": min(int((status_counts.get('Closed', 0) / total_tickets) * 100), 100)},

        {"label": "Pending", "value": status_counts.get('Pending', 0), "color": "#CA279B",
         "graphwidth": min(int((status_counts.get('Pending', 0) / total_tickets) * 100), 100)},

        {"label": "Avg Days Open", "value": avg_days_open, "color": "#ffc107",
         "graphwidth": min(avg_days_open * 5, 100)}
    ]
    return jsonify(stats)

@app.route('/api/charts', methods=['GET'])
def get_charts():
    date = request.args.get('date')
    product = request.args.get('product')
    company = request.args.get('company')
    print(f"📌 /api/charts requested for date={date}, product={product}, company={company}")  # Debug log

    rows = fetch_Chatbot_Transaction(date, product, company)

    if not rows:
        print("⚠️ No rows found for charts")
        return jsonify([])

    # FIX: Corrected indexes
    status_counts = Counter([r[2] for r in rows])
    feedback_counts = Counter([r[3] for r in rows])
    severity_counts = Counter([r[4] for r in rows])
    category_counts = Counter([r[5] for r in rows])

    open_days_ranges = {
        '0-5 Days': 0, '6-10 Days': 0, '11-15 Days': 0,
        '16-20 Days': 0, '21-25 Days': 0, '> 25 Days': 0
    }

    for r in rows:
        days = r[6]  # Ticket_Day_Open
        if days <= 5:
            open_days_ranges['0-5 Days'] += 1
        elif days <= 10:
            open_days_ranges['6-10 Days'] += 1
        elif days <= 15:
            open_days_ranges['11-15 Days'] += 1
        elif days <= 20:
            open_days_ranges['16-20 Days'] += 1
        elif days <= 25:
            open_days_ranges['21-25 Days'] += 1
        else:
            open_days_ranges['> 25 Days'] += 1

    charts = [
        {
            "title": "Ticket Status",
            "type": "doughnut",
            "data": {
                "labels": list(status_counts.keys()),
                "datasets": [ {
                    "data": list(status_counts.values()),
                    "backgroundColor": ["orange", "skyblue", "red", "green", "purple"]
                }]
            }
        },
        {
            "title": "Satisfaction",
            "type": "bar",
            "data": {
                "labels": list(feedback_counts.keys()),
                "datasets": [ {
                    "data": list(feedback_counts.values()),
                    "backgroundColor": ["green", "blue", "gray", "red"]
                }]
            }
        },
        {
            "title": "Severity",
            "type": "bar",
            "data": {
                "labels": list(severity_counts.keys()),
                "datasets": [ {
                    "data": list(severity_counts.values()),
                    "backgroundColor": ["red", "orange", "yellow", "gray"]
                }]
            }
        },
        {
            "title": "Issue Category",
            "type": "bar",
            "data": {
                "labels": list(category_counts.keys()),
                "datasets": [ {
                    "data": list(category_counts.values()),
                    "backgroundColor": ["purple", "blue", "green", "gray"]
                }]
            }
        },
        {
            "title": "Open Days",
            "type": "bar",
            "data": {
                "labels": list(open_days_ranges.keys()),
                "datasets": [ {
                    "data": list(open_days_ranges.values()),
                    "backgroundColor": ["teal"]
                }]
            }
        }
    ]
    return jsonify(charts)

@app.route('/api/monthly-trends', methods=['GET'])
def get_monthly_trends():
    conn = get_db_connection()
    cursor = conn.cursor()
  
    cursor.execute("SELECT Ticket_Creation_Date, Ticket_Status FROM Chatbot_Transaction")
    rows = cursor.fetchall()
    conn.close()

    trend_data = {}
    for Ticket_Creation_Date, Ticket_Status in rows:
        if Ticket_Status not in trend_data:
            trend_data[Ticket_Status] = {}
        trend_data[Ticket_Status][Ticket_Creation_Date] = trend_data[Ticket_Status].get(Ticket_Creation_Date, 0) + 1

    labels = sorted(list(set([date.strftime('%a, %d %b %Y') for date, _ in rows])))

    datasets = []
    colors = {"Open": "red", "Resolved": "green", "Pending": "orange", "Closed": "blue"}

    for status, date_counts in trend_data.items():
        data = [date_counts.get(label, 0) for label in labels]
        datasets.append({
            "label": status,
            "data": data,
            "borderColor": colors.get(status, "gray"),
            "backgroundColor": colors.get(status, "gray"),
            "fill": False
        })

    return jsonify({"labels": labels, "datasets": datasets})

# CREATE - Add New Employee
@app.route('/api/employees', methods=['POST'])
def create_employee():
    data = request.get_json()

    required_fields = ['Emp_ID', 'Emp_Name', 'Email_Id', 'Company_ID', 'Role']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Chatbot_Emp (Emp_ID, Emp_Name, Email_Id, Company_ID, Role)
            VALUES (?, ?, ?, ?, ?)
        """, tuple(data[field] for field in required_fields))
        conn.commit()
        return jsonify({"message": "✅ Employee added successfully!"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()








# READ - Get All Employees
@app.route('/api/getemployees', methods=['GET'])
def get_all_employees():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Chatbot_Emp")
        columns = [column[0] for column in cursor.description]
        employees = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(employees), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# UPDATE - Modify Employee by Emp_ID
@app.route('/employees/<string:emp_id>', methods=['PUT'])
def update_employee(emp_id):
    data = request.get_json()
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Chatbot_Emp
            SET Emp_Name = ?, Email_Id = ?, Company_ID = ?, Department_ID = ?, 
                Role = ?, Other = ?, App_Role = ?
            WHERE Emp_ID = ?
        """, (
            data.get('Emp_Name'),
            data.get('Email_Id'),
            data.get('Company_ID'),
            data.get('Department_ID'),
            data.get('Role'),
            data.get('Other'),
            data.get('App_Role'),
            emp_id
        ))

        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"message": f"No employee found with Emp_ID {emp_id}"}), 404
        return jsonify({"message": "✅ Employee updated successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


#  DELETE - Remove Employee by Emp_ID
@app.route('/employees/<string:emp_id>', methods=['DELETE'])
def delete_employee(emp_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Chatbot_Emp WHERE Emp_ID = ?", emp_id)
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"message": f"No employee found with Emp_ID {emp_id}"}), 404
        return jsonify({"message": "🗑️ Employee deleted successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()



def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = {'Emp_ID': data['Emp_ID'], 'Role': data['Role']}
        except:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/api/protected')
@token_required
def protected_route(current_user):
    return jsonify({'message': f'Hello {current_user["Emp_ID"]}, you have access to this route with role {current_user["Role"]}.'})

# READ - Get Employee by Email and Password
@app.route('/api/auth/login', methods=['POST'])
def login():
    # --- Enhanced Debugging ---
    print(f"--- Login Request Received ---")
    print(f"Request Headers: {request.headers}")
    
    if not request.is_json:
        logging.warning("Request is not JSON. Body might be empty or have wrong Content-Type.")
        return jsonify({"message": "Invalid request: Content-Type must be application/json"}), 400

    data = request.get_json()
    print(f"Request JSON Body: {data}")

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        logging.error("Missing 'email' or 'password' in request body.")
        return jsonify({'message': 'Email and password are required'}), 400
    
    print(f"Login attempt for user: {email}")

    conn = get_db_connection()
    if conn is None:
        logging.critical("Database connection failed.")
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Chatbot_Emp WHERE Email_Id = ?", (email,))
        row = cursor.fetchone()
        
        if not row:
            logging.warning(f"User not found for email: {email}")
            return jsonify({'message': 'User not found'}), 401

        # Assuming the password in the database is plain text. 
        # In a real application, you should hash passwords.
        db_password = row.Password.strip() # Use .strip() to remove leading/trailing whitespace
        password_match = (password == db_password)
        
        print(f"Password check for '{email}': Provided='{password}', DB='{db_password}', Match={password_match}")

        if password_match:
            print(f"Password match successful for {email}.")
            token = jwt.encode({
                'Emp_ID': row.Emp_ID,
                'Role': row.Role,
                'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)
            }, app.config['SECRET_KEY'], algorithm="HS256")
            
            columns = [column[0] for column in cursor.description]
            employee = dict(zip(columns, row))
            
            return jsonify({'token': token, 'user': employee})

        logging.warning(f"Invalid password for user: {email}")
        return jsonify({'message': 'Invalid password'}), 401
    except Exception as e:
        logging.error(f"An exception occurred during login: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    app.run(debug=True)
