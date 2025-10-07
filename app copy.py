from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
from collections import Counter
import os
import logging
import pyodbc
import datetime

app = Flask(__name__)
CORS(app)


# DB_PATH = 'dashboard1.db'

#New Changes done by Ashish 07-09-2025
#Read SQL Database Configration.
DB_DRIVER = os.getenv("DB_DRIVER")
SERVER = os.getenv("SERVER")
DATABASE = os.getenv("DATABASE")
UID = os.getenv("UID")
PASSWORDD = os.getenv("PASSWORDD")

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
    
    #New Changes done by Ashish 07-09-2025

def fetch_Chatbot_Transaction(date_filter=None):
        
    # conn = sqlite3.connect(DB_PATH)
    # cursor = conn.cursor()
    # if date_filter:
    #     cursor.execute("SELECT * FROM Chatbot_Transaction WHERE date = ?", (date_filter,))
    # else:
    #     cursor.execute("SELECT * FROM Chatbot_Transaction")
    # rows = cursor.fetchall()
    # conn.close()
    # return rows
        connection = get_db_connection()
        cursor = connection.cursor()
        #target_date = datetime.date(date_filter)
        if date_filter:
          cursor.execute("SELECT Ticket_Creation_Date,Ticket_No,Ticket_Status,Company_Work_Feedback,Ticket_Priority,Ticket_Category,Ticket_Day_Open FROM Chatbot_Transaction WHERE Ticket_Creation_Date = ?", (date_filter,))
         #cursor.execute("""SELECT Ticket_Creation_Date, Ticket_No, Ticket_Status, Company_Work_Feedback,Ticket_Priority, Ticket_Category, Ticket_Day_Open FROM Chatbot_Transaction  WHERE Ticket_Creation_Date = ? """, (target_date,))
        else:
         cursor.execute("SELECT Ticket_Creation_Date,Ticket_No,Ticket_Status,Company_Work_Feedback,Ticket_Priority,Ticket_Category,Ticket_Day_Open FROM Chatbot_Transaction")
         rows = cursor.fetchall()    
         cursor.close()
         connection.close()
         return rows
         


@app.route('/')
def home():
    return jsonify({"message": "Helpdesk Dashboard API is running!"})


@app.route('/api/dates', methods=['GET'])
def get_dates():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Ticket_Creation_Date FROM Chatbot_Transaction")
    dates = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(dates)


@app.route('/api/stats', methods=['GET'])
def get_stats():
    date = request.args.get('date')
    rows = fetch_Chatbot_Transaction(date)
    total_tickets = len(rows)
    status_counts = Counter([r[3] for r in rows])

    avg_days_open = int(
        sum(r[7] for r in rows if r[3] == 'Open') /
        max(status_counts.get('Open', 1), 1)
    )

    stats = [
        {"label": "Tickets", "value": total_tickets, "color": "#6f42c1",
         "graphwidth": min(int((total_tickets / 100) * 10), 100)},

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
    print(date)
    rows = fetch_Chatbot_Transaction(date)

    print("Hello Ashish")
    status_counts = Counter([r[3] for r in rows])
    print("100")
    feedback_counts = Counter([r[4] for r in rows])
    print("200")
    severity_counts = Counter([r[5] for r in rows])
    print("300")
    category_counts = Counter([r[6] for r in rows])
    print("400")

    open_days_ranges = {
        '0-5 Days': 0, '6-10 Days': 0, '11-15 Days': 0,
        '16-20 Days': 0, '21-25 Days': 0, '> 25 Days': 0
    }
    print("500")
    for r in rows:
        days = r[7]
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
    print("Hello 100")
    charts = [
        {
            "title": "Ticket Status",
            "type": "doughnut",
            "data": {
                "labels": list(status_counts.keys()),
                "datasets": [{
                    "data": list(status_counts.values()),
                    "backgroundColor": ["orange", "skyblue", "red", "green"]
                }]
            }
        },
        {
            "title": "Satisfaction",
            "type": "radar",
            "data": {
                "labels": list(feedback_counts.keys()),
                "datasets": [{
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
                "datasets": [{
                    "data": list(severity_counts.values()),
                    "backgroundColor": ["red", "orange", "yellow", "gray"]
                }]
            }
        },
        {
            "title": "Issue Category",
            "type": "line",
            "data": {
                "labels": list(category_counts.keys()),
                "datasets": [{
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
                "datasets": [{
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

    labels = sorted(list(set([date for date, _ in rows])))

    datasets = []
    colors = {"Open": "red", "Resolved": "green", "Pending": "orange", "Closed": "blue"}

    for status, date_counts in trend_data.items():
        data = [date_counts.get(label, 0) for label in labels]
        datasets.append({
            "label": status,
            "data": data,
            "borderColor": colors.get(status, "gray"),
            "fill": False
        })

    return jsonify({"labels": labels, "datasets": datasets})


if __name__ == '__main__':
    app.run(debug=True)
