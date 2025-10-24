from flask import Flask, render_template, request, jsonify, session
import sqlite3
import json
import re
from datetime import datetime
import threading
import time

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Sample menu data
MENU_ITEMS = [
    {"id": 1, "name": "rice", "price": 1500, "category": "Main"},
    {"id": 2, "name": "ndengu", "price": 30, "category": "Main"},
    {"id": 3, "name": "ugali", "price": 40, "category": "Sides"},
    {"id": 4, "name": "fulu", "price": 30, "category": "Main"},
    {"id": 5, "name": "omena", "price": 30, "category": "Main"},
    {"id": 6, "name": "tea", "price": 20, "category": "Drinks"},
]

# Your M-Pesa PayBill details
PAYBILL_NUMBER = "8834998"
BUSINESS_NAME = "RESTAURANT"

# Initialize database
def init_db():
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  customer_name TEXT,
                  items TEXT,
                  total_amount INTEGER,
                  status TEXT DEFAULT 'pending',
                  reference TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  sender_name TEXT,
                  amount INTEGER,
                  reference TEXT,
                  order_id INTEGER,
                  sms_text TEXT,
                  received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# Customer Routes
@app.route('/')
def menu():
    return render_template('menu.html', menu_items=MENU_ITEMS)

@app.route('/order', methods=['POST'])
def create_order():
    customer_name = request.form.get('customer_name')
    selected_items = request.form.getlist('items')
    
    # Calculate total and create order summary
    order_details = []
    total = 0
    for item_id in selected_items:
        item = next((x for x in MENU_ITEMS if x['id'] == int(item_id)), None)
        if item:
            order_details.append(item['name'])
            total += item['price']
    
    # Generate unique reference
    reference = f"ORD{datetime.now().strftime('%H%M%S')}"
    
    # Save to database
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('''INSERT INTO orders (customer_name, items, total_amount, reference)
                 VALUES (?, ?, ?, ?)''',
              (customer_name, json.dumps(order_details), total, reference))
    order_id = c.lastrowid
    conn.commit()
    conn.close()
    
    # Generate M-Pesa USSD code
    ussd_code = f"*144*{PAYBILL_NUMBER}*{total}*{reference}#"
    
    return render_template('order.html',
                         customer_name=customer_name,
                         order_details=order_details,
                         total=total,
                         reference=reference,
                         ussd_code=ussd_code,
                         order_id=order_id)

# Admin Routes
@app.route('/admin')
def admin_dashboard():
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    
    # Get pending orders
    c.execute('''SELECT * FROM orders WHERE status = 'pending' ORDER BY created_at DESC''')
    pending_orders = c.fetchall()
    
    # Get completed orders
    c.execute('''SELECT * FROM orders WHERE status = 'paid' ORDER BY created_at DESC''')
    completed_orders = c.fetchall()
    
    # Get recent transactions
    c.execute('''SELECT * FROM transactions ORDER BY received_at DESC LIMIT 10''')
    transactions = c.fetchall()
    
    conn.close()
    
    return render_template('admin.html',
                         pending_orders=pending_orders,
                         completed_orders=completed_orders,
                         transactions=transactions)

# API endpoints for real-time updates
@app.route('/api/orders')
def get_orders():
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('''SELECT * FROM orders ORDER BY created_at DESC''')
    orders = c.fetchall()
    conn.close()
    
    # Convert to dict
    orders_list = []
    for order in orders:
        orders_list.append({
            'id': order[0],
            'customer_name': order[1],
            'items': json.loads(order[2]),
            'total_amount': order[3],
            'status': order[4],
            'reference': order[5],
            'created_at': order[6]
        })
    
    return jsonify(orders_list)

@app.route('/api/check_payments')
def check_payments():
    # This would be called periodically to check for new payments
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    
    # Get all pending orders
    c.execute('''SELECT * FROM orders WHERE status = 'pending'\n''')
    pending_orders = c.fetchall()
    
    # Get all transactions
    c.execute('''SELECT * FROM transactions''')
    transactions = c.fetchall()
    
    # Match transactions to orders
    for transaction in transactions:
        name = transaction[1]  # reference from transaction
        amount = transaction[2]  # amount from transaction
        
        # Find matching order
        for order in pending_orders:
            if order[1] == name and order[3] == amount:  # reference and amount match
                # Update order status
                c.execute('''UPDATE orders SET status = 'paid' WHERE id = ?''', (order[0],))
                conn.commit()
                print(f"Order {order[0]} marked as paid!")
    
    conn.close()
    return jsonify({'status': 'checked'})

# M-Pesa SMS Parser (Simulated - you'll integrate with actual SMS reading)
def parse_mpesa_sms(sms_text):
    """Parse M-Pesa SMS to extract name, amount, reference"""
    patterns = [
        # Pattern: Ksh1,000 from JOHN DOE on 12/12/24 RefABC123
        r"Ksh([\d,]+)\.?\s*from\s*(.*?)\s*on\s*\d+/\d+/\d+.*?Ref(\w+)",
        # Pattern: Confirmed. Ksh500.00 paid to BUSINESS. RefXYZ789
        r"Confirmed\.\s*Ksh([\d,]+)\.\d+\s*paid to.*?Ref(\w+)",
        # Custom pattern for your business
        r"Ksh([\d,]+).*?from\s*(.*?)\s*.*?Ref(\w+)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, sms_text, re.IGNORECASE)
        if match:
            return {
                'amount': int(match.group(1).replace(',', '')),
                'sender_name': match.group(2).strip().title(),
                'reference': match.group(3).strip()
            }
    return None

# Simulate receiving SMS (Replace this with actual SMS reading)
def simulate_sms_receiver():
    """This function simulates receiving M-Pesa SMS"""
    # In real implementation, this would read from GSM modem or Android app
    pass

@app.route('/api/add_transaction', methods=['POST'])
def add_transaction():
    """Endpoint to add transaction from SMS reader"""
    data = request.json
    sms_text = data.get('sms_text')
    
    # Parse the SMS
    transaction_data = parse_mpesa_sms(sms_text)
    
    if transaction_data:
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        
        # Save transaction
        c.execute('''INSERT INTO transactions (sender_name, amount, reference, sms_text)
                     VALUES (?, ?, ?, ?)''',
                  (transaction_data['sender_name'], transaction_data['amount'], 
                   transaction_data['reference'], sms_text))
        
        # Check if it matches any pending order
        c.execute('''SELECT * FROM orders WHERE reference = ? AND total_amount = ? AND status = 'pending'\n''',
                  (transaction_data['reference'], transaction_data['amount']))
        matching_order = c.fetchone()
        
        if matching_order:
            # Mark order as paid
            c.execute('''UPDATE orders SET status = 'paid' WHERE id = ?''', (matching_order[0],))
            print(f"✅ Order {matching_order[0]} paid by {transaction_data['sender_name']}")
        
        conn.commit()
        conn.close()
        
        return jsonify({'status': 'success', 'matched_order': bool(matching_order)})
    
    return jsonify({'status': 'failed', 'error': 'Could not parse SMS'})

if __name__ == '__main__':
    # Start background thread for payment checking
    def background_checker():
        while True:
            time.sleep(7)  # Check every 10 seconds
            try:
                with app.app_context():
                    check_payments()
            except:
                pass
    
    # Uncomment to start background checking
    # checker_thread = threading.Thread(target=background_checker)
    # checker_thread.daemon = True
    # checker_thread.start()
    
    app.run(host='0.0.0.0', port=1200, debug=True)