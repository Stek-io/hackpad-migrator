import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

smtp_host = os.environ.get('HACKPAD_SMPT_HOST') or 'localhost'
smtp_port = os.environ.get('HACKPAD_SMPT_PORT') or 1025
smtp_user = os.environ.get('HACKPAD_SMPT_USER') or ''
smtp_password = os.environ.get('HACKPAD_SMPT_PASSWORD') or ''

def send_html_email(me, you, bcc, subject, html, text):

    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = me
    msg['To'] = you
    msg['Bcc'] = bcc
    
    # Record the MIME types of both parts - text/plain and text/html.
    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')

    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    msg.attach(part1)
    msg.attach(part2)

    # Send the message via local SMTP server.
    s = smtplib.SMTP(smtp_host, smtp_port)
    if smtp_user and smtp_password:
        s.ehlo()
        s.starttls()
        s.login(smtp_user, smtp_password)
    # sendmail function takes 3 arguments: sender's address, recipient's address
    # and message to send - here it is sent as one string.
    s.sendmail(me, you, msg.as_string())
    s.quit()


    
def send_text_email(me, you, bcc, subject, text):

    msg = MIMEText(text)
    msg['Subject'] = subject
    msg['From'] = me
    msg['To'] = you
    msg['Bcc'] = bcc
    
    # Send the message via our own SMTP server.
    s = smtplib.SMTP(smtp_host, smtp_port)
    if smtp_user and smtp_password:
        s.ehlo()
        s.starttls()
        s.login(smtp_user, smtp_password)

    s.send_message(msg)
    s.quit()



