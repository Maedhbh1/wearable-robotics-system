import smtplib
import socket
from email.mime.text import MIMEText
from datetime import datetime

# Configuration
GMAIL_USER = 'YOUR_GMAIL_ADDRESS@gmail.com'
GMAIL_PASSWORD = 'YOUR_GOOGLE_APP_PASSWORD' 
RECEIVER_EMAIL = 'YOUR_RECEIVER_EMAIL@gmail.com'

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to a public DNS to see which local IP the Pi is using
        s.connect(('8.8.8.8', 80))
        IP = s.getsockname()[0]
    except Exception:
        IP = 'Not Connected'
    finally:
        s.close()
    return IP

def send_email(ip_addr):
    msg = MIMEText(f"Your AI Camera is online!\n\nLocal IP: {ip_addr}\nTime: {datetime.now()}")
    msg['Subject'] = f"Pi IP Address: {ip_addr}"
    msg['From'] = GMAIL_USER
    msg['To'] = RECEIVER_EMAIL

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    current_ip = get_ip()
    if current_ip != 'Not Connected':
        send_email(current_ip)