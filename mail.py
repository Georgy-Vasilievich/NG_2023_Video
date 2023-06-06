import configparser, email, os, smtplib, ssl

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

config = configparser.ConfigParser()
config.read('config.ini')

def send_email(destination, attachment):
    subject = 'Your modified video'
    body = 'You have recently used our service to modify a video. The result is attached.'
    sender_email = config.get('Mail', 'Username')
    receiver_email = destination
    password = config.get('Mail', 'Password')
    
    # Create a multipart message and set headers
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = receiver_email
    message['Subject'] = subject
    
    # Add body to email
    message.attach(MIMEText(body, 'plain'))

    with open(attachment, 'rb') as file:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(file.read())
    
    # Encode file in ASCII characters to send by email
    encoders.encode_base64(part)
    
    # Add header as key/value pair to attachment part
    part.add_header(
        'Content-Disposition',
        f'attachment; filename= {os.path.normpath(attachment)}',
    )
    
    # Add attachment to message and convert message to string
    message.attach(part)
    text = message.as_string()
    
    # Log in to server using secure context and send email
    if config.getboolean('Mail', 'SSL'):
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(config.get('Mail', 'Server'), config.get('Mail', 'Port'), context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, text)
    else:
        with smtplib.SMTP(config.get('Mail', 'Server'), config.get('Mail', 'Port')) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, text)
