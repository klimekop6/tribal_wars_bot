import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

# Email Account
EMAIL_SENDER_ACCOUNT = "***REMOVED***"
EMAIL_SENDER_USERNAME = "TribalWarsNotification"
EMAIL_SENDER_PASSWORD = "TribalWars2077"
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_SMTP_PORT = 587 

def send_email(email_recepients: str|list[str], email_subject: str, email_body: str) -> None:
    """ send email to provided emails with custom email subject and email message """

    if isinstance(email_recepients, str):
        email_recepients = [email_recepients]
    
    # login to email server
    server = smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT)
    server.starttls()
    server.login(EMAIL_SENDER_USERNAME, EMAIL_SENDER_PASSWORD)
    # For loop, sending emails to all email recipients
    for recipient in email_recepients:
        message = MIMEMultipart('alternative')
        message['From'] = formataddr(('Tribal Wars Notification', EMAIL_SENDER_ACCOUNT))
        message['To'] = recipient
        message['Subject'] = email_subject
        message.attach(MIMEText(email_body, 'plain'))
        text = message.as_string()
        server.sendmail(EMAIL_SENDER_ACCOUNT, recipient, text)
    # All emails sent, log out.
    server.quit()