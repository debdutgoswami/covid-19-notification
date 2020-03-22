import requests, json, smtplib, os, time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from bs4 import BeautifulSoup
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

# base url for the data
_url = 'https://www.mohfw.gov.in/'

def check(_json) -> str:
    """Performs check for any update in the official database of India.

    Returns:
        str -- The message which is to be sent as email.
    """
    change = False
    _update, _msg = dict(), ""
    req = requests.get(_url).content
    soup = BeautifulSoup(req, 'html.parser')
    rows = soup.find_all('tr')

    for row in rows[1:len(rows)-1]:
        col = row.find_all('td')
        if len(col)<6:
            continue
        state = col[1].text
        try:
            # current data from the website
            _update.update({
                state: {
                    "In": col[2].text,
                    "Fr": col[3].text,
                    "Cur": col[4].text,
                    "Dth": col[5].text
                }
            })
        except IndexError:
            change = True
            break

        # looking for changes in data
        try:
            _cur = _update[state]
            _prev = _json[state]
            cur_msg = ""
            if _prev["In"] != _cur["In"]:
                cur_msg += f"Indian case has changed from {_prev['In'].strip()} to {_cur['In'].strip()}\t"
            if _prev["Fr"] != _cur["Fr"]:
                cur_msg += f"Foreign case has changed from {_prev['Fr'].strip()} to {_cur['Fr'].strip()}\t"
            if _prev["Cur"] != _cur["Cur"]:
                cur_msg += f"Cured case has changed from {_prev['Cur'].strip()} to {_cur['Cur'].strip()}\t"
            if _prev["Dth"] != _cur["Dth"]:
                cur_msg += f"Death case has changed from {_prev['In'].strip()} to {_cur['In'].strip()}\t"
            if len(cur_msg):
                _msg += f"\r\nIn {state},\nNo. of " + cur_msg
        except KeyError:
            #  for addition of new state
            _msg += f"\nNew state {state} have {_update[state]['In'].strip()} Indian case, {_update[state]['Fr'].strip()} Foreign case, {_update[state]['Cur']} cured and {_update[state]['Dth']} death.\n"

    if change==False:
        try:
            # count of the total cases in India
            _total = rows[len(rows)-1].find_all('td')
            _totIN, _totFR = _total[1].text, _total[2].text
            total_msg = f"\r\nThe total no. of cases in India are {int(_totIN.strip())+int(_totFR.strip())} (including Foreign Nationality) having {_total[3].text.strip()} cured and {_total[4].text.strip()} deaths."
        except ValueError:
            # count of the total cases in India
            _total = rows[len(rows)-2].find_all('td')
            _totIN, _totFR = _total[1].text, _total[2].text
            total_msg = f"\r\nThe total no. of cases in India are {int(_totIN[:len(_totIN)-2].strip())+int(_totFR[:len(_totFR)-2].strip())} (including Foreign Nationality) having {_total[3].text.strip()} cured and {_total[4].text.strip()} deaths."
    else:
        # count of the total cases in India
        _total = rows[len(rows)-2].find_all('td')
        _totIN, _totFR = _total[1].text, _total[2].text
        total_msg = f"\r\nThe total no. of cases in India are {int(_totIN[:len(_totIN)-2].strip())+int(_totFR[:len(_totFR)-2].strip())} (including Foreign Nationality) having {_total[3].text.strip()} cured and {_total[4].text.strip()} deaths."

    # if there is no change then there is no point in sending notification
    if len(_msg):
        with open('stats.json', 'w') as f:
            json.dump(_update, f)

        _msg += total_msg
        _msg = "Hi,\r\nThere has been an update in the number of cases reported for COVID-19.\r\n" + _msg

        return _msg

    return None

def send_notification(emails: list, EMAIL_BODY: str):
    """Used to send  emails to the subscribers.

    Arguments:
        emails {list} -- list of subscribers
        EMAIL_BODY {str} -- the body of the EMAIL
    """
    fromaddr = os.getenv('EMAIL')
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.login(fromaddr, os.getenv('EMAIL_APP_KEY'))

    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = fromaddr
    msg['Subject'] = "IMPORTANT: Updates on COVID-19 Cases in India"
    msg.attach(MIMEText(EMAIL_BODY))

    # didn't add masg['To'] because anything we put in msg is visible to everyone so the everyones' email will be visible
    for toaddr in emails:
        text = msg.as_string()
        server.sendmail(fromaddr, toaddr, text)


if __name__ == "__main__":
    global emails

    while True:
        _json = None
        with open('stats.json', 'r') as f:
            _json = json.load(f)

        emails = list(db.reference(url=os.getenv('FIREBASE')).child('emails').get())

        EMAIL_BODY = check(_json)

        if EMAIL_BODY:
            send_notification(emails, EMAIL_BODY)

        time.sleep(300)