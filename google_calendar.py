from __future__ import print_function
import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar', "https://www.googleapis.com/auth/calendar.events"]


def get_events():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)

    # Call the Calendar API
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time

    print('Getting the upcoming 500 events')
    events_result = service.events().list(calendarId='primary', timeMin=now,
                                          maxResults=500, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        print('No upcoming events found.')
    events_dic = {}  # group all events in the same date to date:[(event1,hour),(event2,hour)]
    for event in events:
        event_id = event["id"]
        start = event['start'].get('dateTime', event['start'].get('date'))
        s = start.split("T")  # s[0] is date, s[1] is time
        summary = event['summary']
        if 'description' in event:
            desc = event['description']
        else:
            desc = None
        if len(s) >= 2:  # we have time for event
            date, time = s[0], s[1]
        else:  # no time for event
            date, time = s[0], None
        if date in events_dic:
            events_dic[date].append((summary, time, desc, event_id))  # add tuple of (summary,time)
        else:
            events_dic[date] = [(summary, time, desc, event_id)]
    return events_dic, service, now


def winter_summer_format(date):
    year = date.split("-")[0]
    if year + "-10-27" < date < str(int(year) + 1) + "-03-27":  # winter - tested on summer clock working! 24/10/20
        return '{}T{}:00.000+03:00', '{}T{}:00.000+02:00'
    else:
        return '{}T{}:00.000+04:00', '{}T{}:00.000+03:00'  # summer


def create_event(event):
    start_format, end_format = winter_summer_format((event.date))
    my_event = {
        'summary': '{}'.format(event.name),
        'location': "",
        'description': '{}'.format(event.status),
        'start': {
            'dateTime': start_format.format(event.date, event.time),
            'timeZone': 'Asia/Jerusalem',
        },
        'end': {
            'dateTime': end_format.format(event.date, event.time),
            # So that's year, month, day,
            # the letter T, hours, minutes, seconds, miliseconds, + or -, timezoneoffset in hours and minutes
            'timeZone': 'Asia/Jerusalem',
        },
        'recurrence': [
            # 'RRULE:FREQ=DAILY;COUNT=1'
        ],
        'attendees': [
            # {'email': 'lpage@example.com'},
            # {'email': 'sbrin@example.com'},
        ],

        'reminders': {
            'useDefault': False,
            'overrides': [
                # {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 24 * 60},
            ],
        },
        'colorId': [2]
    }
    return my_event


if __name__ == '__main__':
    print(get_events())
