import smtplib, time, os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from pathlib import Path

# firebase
import firebase_admin
from firebase_admin import db, credentials

# firebase initialization
cred = credentials.Certificate('private/coronanotifier-firebase-adminsdk.json')
firebase = firebase_admin.initialize_app(cred)

# enviornment variables
env = Path('secrets.env')
load_dotenv(dotenv_path=env)

emails = list(db.reference(url='https://coronanotifier.firebaseio.com/').child('emails').get())

def add_subscriber(email: str):
    fromaddr = os.getenv('EMAIL')
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.login(fromaddr, os.getenv('EMAIL_APP_KEY'))

    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = email
    msg['Subject'] = "IMPORTANT: Subscribed to updates on COVID-19 Cases in India"
    EMAIL_BODY = "Hi,\r\nThank you so much for subscribing to receiving notifications on updates of cases reported in India. Whenever there is a change in the data you will receive an email. We don't spam!!\r\nStay Indoors and avoid any social contact. Stay safe!!\r\nRegards."
    msg.attach(MIMEText(EMAIL_BODY))
    text = msg.as_string()
    server.sendmail(fromaddr, email, text)

    emails.append(email)
    _update = {'emails': list(set(emails))}
    db.reference(url='https://coronanotifier.firebaseio.com/').update(_update)

add_subscriber('debdutgoswami@gmail.com')

