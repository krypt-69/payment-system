from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.core.window import Window
from kivy.logger import Logger
import requests
import re
from datetime import datetime
import random

# Set window background color
Window.clearcolor = (0.95, 0.95, 0.95, 1)

class MpesaSMSForwarder(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Server configuration - user will input IP
        self.server_ip = ""
        self.server_url = ""
        
        # SMS tracking
        self.received_sms = []
        self.is_monitoring = False
        self.processed_ids = set()
        
        # Test mode - set to True for testing without real SMS
        self.test_mode = True
        
        # Track the initial message widget
        self.initial_message_widget = None
        
    def build(self):
        """Build the main application interface"""
        # Main container
        main_layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        # Add background color
        with main_layout.canvas.before:
            Color(0.1, 0.1, 0.2, 1)  # Dark blue background
            self.rect = Rectangle(size=Window.size, pos=main_layout.pos)
        
        # Header Section
        header_layout = self.create_header()
        main_layout.add_widget(header_layout)
        
        # Server Configuration Section
        server_layout = self.create_server_section()
        main_layout.add_widget(server_layout)
        
        # Control Section
        control_layout = self.create_control_section()
        main_layout.add_widget(control_layout)
        
        # Transactions Display Section
        transactions_layout = self.create_transactions_section()
        main_layout.add_widget(transactions_layout)
        
        # Testing Section (can be commented out)
        test_layout = self.create_test_section()
        main_layout.add_widget(test_layout)
        
        return main_layout
    
    def create_header(self):
        """Create the app header with title and description"""
        header_layout = BoxLayout(orientation='vertical', size_hint=(1, 0.15))
        
        # App title
        title = Label(
            text="💰 M-Pesa SMS Auto-Forwarder",
            font_size='24sp',
            bold=True,
            color=(1, 1, 1, 1),
            size_hint=(1, 0.6)
        )
        header_layout.add_widget(title)
        
        # App description
        desc = Label(
            text="Automatically detects M-Pesa SMS and forwards to your server",
            font_size='14sp',
            color=(0.8, 0.8, 1, 1),
            size_hint=(1, 0.4)
        )
        header_layout.add_widget(desc)
        
        return header_layout
    
    def create_server_section(self):
        """Create server configuration section"""
        server_layout = BoxLayout(orientation='vertical', size_hint=(1, 0.15))
        
        # Section title
        server_title = Label(
            text="🔧 Server Configuration",
            font_size='16sp',
            bold=True,
            color=(1, 1, 1, 1),
            size_hint=(1, 0.4)
        )
        server_layout.add_widget(server_title)
        
        # IP input layout
        ip_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.6))
        
        ip_label = Label(
            text="Server IP:",
            size_hint=(0.3, 1),
            color=(1, 1, 1, 1)
        )
        ip_layout.add_widget(ip_label)
        
        self.ip_input = TextInput(
            hint_text="192.168.1.100",
            multiline=False,
            size_hint=(0.5, 1),
            background_color=(1, 1, 1, 0.8),
            foreground_color=(0, 0, 0, 1)
        )
        ip_layout.add_widget(self.ip_input)
        
        self.save_btn = Button(
            text="💾 Save",
            size_hint=(0.2, 1),
            background_color=(0.2, 0.6, 0.2, 1)
        )
        self.save_btn.bind(on_press=self.save_server_ip)
        ip_layout.add_widget(self.save_btn)
        
        server_layout.add_widget(ip_layout)
        
        # Server status
        self.server_status = Label(
            text="❌ Server not configured",
            font_size='12sp',
            color=(1, 0.5, 0.5, 1),
            size_hint=(1, 0.3)
        )
        server_layout.add_widget(self.server_status)
        
        return server_layout
    
    def create_control_section(self):
        """Create monitoring control section"""
        control_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.1))
        
        # Monitor button
        self.monitor_btn = Button(
            text="🚀 START MONITORING",
            size_hint=(0.6, 1),
            background_color=(0.2, 0.7, 0.2, 1),
            font_size='16sp',
            bold=True
        )
        self.monitor_btn.bind(on_press=self.toggle_monitoring)
        control_layout.add_widget(self.monitor_btn)
        
        # Status indicator
        self.status_indicator = Label(
            text="⏸️ READY",
            size_hint=(0.4, 1),
            font_size='14sp',
            color=(1, 1, 1, 1)
        )
        control_layout.add_widget(self.status_indicator)
        
        return control_layout
    
    def create_transactions_section(self):
        """Create transactions display section"""
        trans_layout = BoxLayout(orientation='vertical', size_hint=(1, 0.5))
        
        # Section title
        trans_title = Label(
            text="📱 Recent M-Pesa Transactions",
            font_size='16sp',
            bold=True,
            color=(1, 1, 1, 1),
            size_hint=(1, 0.1)
        )
        trans_layout.add_widget(trans_title)
        
        # Scrollable transactions area
        scroll = ScrollView(size_hint=(1, 0.9))
        
        # Grid layout for transactions
        self.transactions_grid = GridLayout(
            cols=1,
            spacing=10,
            size_hint_y=None
        )
        self.transactions_grid.bind(minimum_height=self.transactions_grid.setter('height'))
        
        # Initial message - store reference to this widget
        self.initial_message_widget = Label(
            text="No transactions yet.\nStart monitoring to see M-Pesa transactions here.",
            size_hint_y=None,
            height=100,
            color=(0.8, 0.8, 0.8, 1),
            text_size=(400, None)
        )
        self.transactions_grid.add_widget(self.initial_message_widget)
        
        scroll.add_widget(self.transactions_grid)
        trans_layout.add_widget(scroll)
        
        return trans_layout
    
    def create_test_section(self):
        """Create testing section (can be commented out for production)"""
        test_layout = BoxLayout(orientation='vertical', size_hint=(1, 0.1))
        
        # Test buttons layout
        test_buttons = BoxLayout(orientation='horizontal', size_hint=(1, 1))
        
        # Test connection button
        test_conn_btn = Button(
            text="🧪 Test Connection",
            size_hint=(0.5, 1),
            background_color=(0.2, 0.5, 0.8, 1)
        )
        test_conn_btn.bind(on_press=self.test_server_connection)
        test_buttons.add_widget(test_conn_btn)
        
        # Simulate SMS button
        simulate_btn = Button(
            text="📨 Simulate M-Pesa SMS",
            size_hint=(0.5, 1),
            background_color=(0.8, 0.5, 0.2, 1)
        )
        simulate_btn.bind(on_press=self.simulate_mpesa_sms)
        test_buttons.add_widget(simulate_btn)
        
        test_layout.add_widget(test_buttons)
        
        return test_layout
    
    def save_server_ip(self, instance):
        """Save the server IP and construct the full API URL"""
        ip = self.ip_input.text.strip()
        
        if not ip:
            self.server_status.text = "❌ Please enter server IP"
            self.server_status.color = (1, 0.5, 0.5, 1)
            return
        
        # Construct full API URL
        self.server_ip = ip
        self.server_url = f"http://{ip}/api/add_transaction"
        
        self.server_status.text = f"✅ Server: {self.server_url}"
        self.server_status.color = (0.5, 1, 0.5, 1)
        
        Logger.info(f"Server URL set to: {self.server_url}")
    
    def toggle_monitoring(self, instance):
        """Start or stop SMS monitoring"""
        if not self.is_monitoring:
            self.start_monitoring()
        else:
            self.stop_monitoring()
    
    def start_monitoring(self):
        """Start automatic SMS monitoring"""
        if not self.server_url:
            self.status_indicator.text = "❌ SET SERVER FIRST"
            self.status_indicator.color = (1, 0.5, 0.5, 1)
            return
        
        self.is_monitoring = True
        self.monitor_btn.text = "🛑 STOP MONITORING"
        self.monitor_btn.background_color = (0.8, 0.2, 0.2, 1)
        self.status_indicator.text = "🔍 SCANNING..."
        self.status_indicator.color = (1, 1, 0.5, 1)
        
        # Start checking for SMS every 2 seconds
        self.monitor_event = Clock.schedule_interval(self.check_for_sms, 2)
        
        Logger.info("M-Pesa SMS monitoring started")
    
    def stop_monitoring(self):
        """Stop automatic monitoring"""
        self.is_monitoring = False
        self.monitor_btn.text = "🚀 START MONITORING"
        self.monitor_btn.background_color = (0.2, 0.7, 0.2, 1)
        self.status_indicator.text = "⏸️ READY"
        self.status_indicator.color = (1, 1, 1, 1)
        
        if hasattr(self, 'monitor_event'):
            self.monitor_event.cancel()
        
        Logger.info("M-Pesa SMS monitoring stopped")
    
    def check_for_sms(self, dt):
        """
        Main SMS checking function
        This runs every 2 seconds when monitoring is active
        """
        try:
            # Update status with current time
            current_time = datetime.now().strftime("%H:%M:%S")
            self.status_indicator.text = f"🔍 Scanning... {current_time}"
            
            # Get new SMS messages
            new_sms_list = self.get_new_sms_messages()
            
            # Process each new SMS
            for sms_data in new_sms_list:
                self.process_sms_message(sms_data)
                
        except Exception as e:
            Logger.error(f"Error in SMS check: {e}")
            self.status_indicator.text = f"❌ Error: {str(e)[:20]}..."
    
    def get_new_sms_messages(self):
        """
        Get new SMS messages from the device
        In production, this would read from Android SMS content provider
        """
        new_sms = []
        
        if self.test_mode:
            # TEST MODE: Simulate occasional M-Pesa messages
            # Comment out this entire if block in production
            if random.random() < 0.05:  # 5% chance to generate test message
                test_messages = [
                    "Ksh1,230 from JOHN KAMAU on 15/12/24 RefORD001",
                    "Ksh4,560 from MARY WANJIKU on 15/12/24 RefORD002",
                    "Ksh3,210 from PETER NJOROGE on 15/12/24 RefORD003",
                    "Confirmed. Ksh8,900 paid to BUSINESS. RefORD004",
                    "DAVID KIPTOO sent you Ksh2,340. Reference: ORD005"
                ]
                test_msg = random.choice(test_messages)
                if test_msg not in self.processed_ids:
                    new_sms.append({
                        'id': test_msg,  # Using message as ID for simulation
                        'text': test_msg,
                        'timestamp': datetime.now()
                    })
                    self.processed_ids.add(test_msg)
        
        # TODO: REPLACE WITH ACTUAL SMS READING CODE FOR PRODUCTION
        # This is where you would implement reading real SMS from Android
        # Example implementation would use Android's SMS content provider
        
        return new_sms
    
    def process_sms_message(self, sms_data):
        """
        Process an SMS message: parse, display, and forward to server
        """
        try:
            sms_text = sms_data['text']
            Logger.info(f"Processing SMS: {sms_text}")
            
            # Parse M-Pesa transaction details
            parsed_data = self.parse_mpesa_transaction(sms_text)
            
            if parsed_data:
                # Display the transaction in the UI
                self.display_transaction(parsed_data, sms_text)
                
                # Forward to server
                self.forward_to_server(sms_text, parsed_data)
                
                return True
            else:
                Logger.warning(f"Not a valid M-Pesa SMS: {sms_text}")
                return False
                
        except Exception as e:
            Logger.error(f"Error processing SMS: {e}")
            # Display error transaction
            error_data = {
                'sender_name': 'ERROR',
                'amount': 0,
                'reference': 'PARSE_ERROR',
                'timestamp': datetime.now().strftime("%H:%M:%S")
            }
            self.display_transaction(error_data, f"Error: {str(e)}")
            return False
    
    def parse_mpesa_transaction(self, sms_text):
        """
        Parse M-Pesa SMS to extract transaction details
        Returns: dict with 'sender_name', 'amount', 'reference', 'timestamp'
        """
        patterns = [
            # Pattern 1: "Ksh1,000 from JOHN DOE on 12/12/24 RefABC123"
            r"Ksh([\d,]+)\.?\s*from\s*(.*?)\s*on\s*\d+/\d+/\d+.*?Ref(\w+)",
            
            # Pattern 2: "Confirmed. Ksh500.00 paid to BUSINESS. RefXYZ789"  
            r"Confirmed\.\s*Ksh([\d,]+)\.\d+\s*paid to.*?Ref(\w+)",
            
            # Pattern 3: "JOHN DOE sent you Ksh1,500. Reference: REF456"
            r"(.*?)\s*sent you\s*Ksh([\d,]+).*?Reference:\s*(\w+)",
            
            # Pattern 4: Generic M-Pesa format
            r"Ksh([\d,]+)\.?\s*received from\s*(.*?)\s*.*?Ref(\w+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, sms_text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    # Extract data based on pattern type
                    if 'sent you' in sms_text:
                        # Format: "JOHN DOE sent you Ksh1,500"
                        sender_name = groups[0].strip().title()
                        amount = int(groups[1].replace(',', ''))
                        reference = groups[2].strip()
                    else:
                        # Format: "Ksh1,000 from JOHN DOE"
                        sender_name = groups[1].strip().title()
                        amount = int(groups[0].replace(',', ''))
                        reference = groups[2].strip()
                    
                    return {
                        'sender_name': sender_name,
                        'amount': amount,
                        'reference': reference,
                        'timestamp': datetime.now().strftime("%H:%M:%S")
                    }
        
        # No pattern matched
        return None
    
    def display_transaction(self, transaction_data, raw_sms):
        """
        Display a transaction in the transactions grid
        """
        # Remove initial message if it exists
        if (self.initial_message_widget and 
            self.initial_message_widget in self.transactions_grid.children):
            self.transactions_grid.remove_widget(self.initial_message_widget)
            self.initial_message_widget = None
        
        # Create transaction card
        card = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=120,
            padding=10,
            spacing=5
        )
        
        # Add background color based on status
        with card.canvas.before:
            Color(0.2, 0.2, 0.3, 1)  # Dark blue card
            Rectangle(pos=card.pos, size=card.size)
        
        # Transaction details
        details_layout = BoxLayout(orientation='horizontal', size_hint_y=0.7)
        
        # Left side: Basic info
        left_info = BoxLayout(orientation='vertical', size_hint_x=0.6)
        
        name_label = Label(
            text=f"👤 {transaction_data['sender_name']}",
            size_hint_y=0.4,
            color=(1, 1, 1, 1),
            text_size=(200, None)
        )
        left_info.add_widget(name_label)
        
        amount_label = Label(
            text=f"💰 KSh {transaction_data['amount']:,}",
            size_hint_y=0.3,
            color=(0.5, 1, 0.5, 1),
            bold=True
        )
        left_info.add_widget(amount_label)
        
        ref_label = Label(
            text=f"🔖 {transaction_data['reference']}",
            size_hint_y=0.3,
            color=(0.8, 0.8, 1, 1),
            font_size='12sp'
        )
        left_info.add_widget(ref_label)
        
        details_layout.add_widget(left_info)
        
        # Right side: Timestamp
        time_label = Label(
            text=f"🕒 {transaction_data['timestamp']}",
            size_hint_x=0.4,
            color=(1, 1, 1, 0.8),
            font_size='12sp'
        )
        details_layout.add_widget(time_label)
        
        card.add_widget(details_layout)
        
        # Status bar
        status_bar = Label(
            text="📤 Forwarding to server...",
            size_hint_y=0.3,
            color=(1, 1, 0.5, 1),
            font_size='11sp'
        )
        card.add_widget(status_bar)
        
        # Add to transactions grid (at the top)
        self.transactions_grid.add_widget(card, index=0)
        
        # Store for reference
        self.received_sms.append({
            'card': card,
            'status_bar': status_bar,
            'data': transaction_data
        })
    
    def forward_to_server(self, sms_text, parsed_data):
        """
        Forward transaction data to the server API
        """
        try:
            payload = {
                'sms_text': sms_text,
                'parsed_data': parsed_data,
                'timestamp': datetime.now().isoformat(),
                'device': 'kivy_auto_app'
            }
            
            Logger.info(f"Sending to server: {parsed_data}")
            
            # Send HTTP POST request
            response = requests.post(
                self.server_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            
            # Update status based on response
            if self.received_sms:
                status_bar = self.received_sms[-1]['status_bar']
                
                if response.status_code == 200:
                    status_bar.text = "✅ Successfully sent to server!"
                    status_bar.color = (0.5, 1, 0.5, 1)
                    Logger.info("Transaction successfully forwarded to server")
                else:
                    status_bar.text = f"❌ Server error: {response.status_code}"
                    status_bar.color = (1, 0.5, 0.5, 1)
                    Logger.error(f"Server returned error: {response.status_code}")
                    
        except requests.exceptions.ConnectionError:
            self.update_transaction_status("❌ Cannot connect to server")
            Logger.error("Connection error - check server IP and network")
        except Exception as e:
            self.update_transaction_status(f"❌ Error: {str(e)[:30]}...")
            Logger.error(f"Error sending to server: {e}")
    
    def update_transaction_status(self, status_text):
        """Update the status of the most recent transaction"""
        if self.received_sms:
            status_bar = self.received_sms[-1]['status_bar']
            status_bar.text = status_text
            status_bar.color = (1, 0.5, 0.5, 1)
    
    # =========================================================================
    # TESTING FUNCTIONS - CAN BE COMMENTED OUT IN PRODUCTION
    # =========================================================================
    
    def test_server_connection(self, instance):
        """Test connection to the server"""
        if not self.server_url:
            self.status_indicator.text = "❌ SET SERVER FIRST"
            return
        
        self.status_indicator.text = "🧪 Testing connection..."
        
        try:
            # Simple GET request to check if server is reachable
            response = requests.get(f"http://{self.server_ip}/", timeout=5)
            
            if response.status_code == 200:
                self.status_indicator.text = "✅ Server is reachable!"
                self.status_indicator.color = (0.5, 1, 0.5, 1)
            else:
                self.status_indicator.text = f"⚠️ Server responded with {response.status_code}"
                self.status_indicator.color = (1, 1, 0.5, 1)
                
        except requests.exceptions.ConnectionError:
            self.status_indicator.text = "❌ Cannot reach server"
            self.status_indicator.color = (1, 0.5, 0.5, 1)
        except Exception as e:
            self.status_indicator.text = f"❌ Test failed: {str(e)[:20]}..."
            self.status_indicator.color = (1, 0.5, 0.5, 1)
    
    def simulate_mpesa_sms(self, instance):
        """Simulate receiving an M-Pesa SMS for testing"""
        if not self.server_url:
            self.status_indicator.text = "❌ SET SERVER FIRST"
            return
        
        test_messages = [
            "Ksh2,500 from TEST USER on 15/12/24 RefTEST001",
            "Ksh1,800 from DEMO CUSTOMER on 15/12/24 RefTEST002",
            "Confirmed. Ksh3,200 paid to RESTAURANT. RefTEST003"
        ]
        
        test_sms = random.choice(test_messages)
        Logger.info(f"Simulating SMS: {test_sms}")
        
        # Process the simulated SMS
        self.process_sms_message({
            'id': f"test_{datetime.now().timestamp()}",
            'text': test_sms,
            'timestamp': datetime.now()
        })
        
        self.status_indicator.text = "📨 Test SMS processed!"

if __name__ == '__main__':
    MpesaSMSForwarder().run()
