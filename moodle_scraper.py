import requests
from bs4 import BeautifulSoup
import events_db as db
import google_calendar as gc


class MoodleEvent:
    def __init__(self, name, date, time, status):
        self.name = name
        self.date = date
        self.time = time
        self.status = status

    def __repr__(self):
        return "({}, {}, {}, {})".format(self.name,self.date,self.time,self.status)


def moodle_tlv(username, user_id, password):
        print("Fetching assignments from moodle..")
        url = "https://moodle.tau.ac.il/login/index.php"
        session = requests.session()
        p = session.get(url)
        p1 = session.get("https://moodle.tau.ac.il/auth/saml2/login.php")
        soup = BeautifulSoup(p1.text,"html.parser")
        token = str(soup.find('input', {'name': 'SAMLRequest'})["value"])
        header = {"Content-Type": "application/x-www-form-urlencoded",
                  "Referrer": "https://moodle.tau.ac.il/auth/saml2/login.php", "Origin": "https://moodle.tau.ac.il"}
        payload = {'SAMLResponse': token, "RelayState": "https://moodle.tau.ac.il/auth/saml2/login.php"}
        p2 = "https://nidp.tau.ac.il/nidp/saml2/sso"
        a = session.post(p2, cookies=session.cookies, headers=header, data=payload)
        p3 = "https://nidp.tau.ac.il/nidp/saml2/sso?sid=0&sid=0"
        header = {"Content-Type": "application/x-www-form-urlencoded",
                  "Origin": "https://nidp.tau.ac.il",
                  "Referer": "https://nidp.tau.ac.il/nidp/saml2/sso?id=10&sid=0&option=credential&sid=0"}
        payload = {"option": "credential", "Ecom_User_ID": username, "Ecom_User_Pid": user_id,
                    "Ecom_Password": password}
        b = session.post(p3, cookies=session.cookies, headers=header, data=payload)
        c= session.get("https://nidp.tau.ac.il/nidp/saml2/sso?sid=0")
        soup = BeautifulSoup(c.text,"html.parser")
        token = str(soup.find('input', {'name': 'SAMLResponse'})["value"])
        header = {"Content-Type": "application/x-www-form-urlencoded",
                  "Origin": "https://nidp.tau.ac.il","Referer": "https://nidp.tau.ac.il/nidp/saml2/sso?sid=0"}
        payload = {'SAMLResponse': token, "RelayState": "https://moodle.tau.ac.il/auth/saml2/login.php"}
        d=session.post("https://moodle.tau.ac.il/auth/saml2/sp/saml2-acs.php/moodle.tau.ac.il", cookies=session.cookies, headers=header, data=payload)
        # passed authentication
        main = session.get("https://moodle.tau.ac.il/")
        soup = BeautifulSoup(main.text,"html.parser")
        elements = soup.select(".courselink a") # finds all elements with class courselink in HTML file
        links = [elements[i].get("href") for i in range(len(elements))]  # all the course links

        pages = [BeautifulSoup(session.get(link).text,"html.parser") for link in links]  # actual course pages
        activities = [(pages[i].find("title").string, pages[i].select(".activityinstance a")) for i in range(len(pages))]  # all rows of specific course
        assignments = []
        for activity in activities:
                title = activity[0]
                course_assignments = [task.get("href") for task in activity[1] if "https://moodle.tau.ac.il/mod/assign" in task.get("href")]  # adds to assignments if has /assign suffix
                pages = [BeautifulSoup(session.get(assignment).text, "html.parser") for assignment in course_assignments]
                assignments.append((title,pages))
        moodle_events = []
        for course in assignments:
                for page in course[1]:  # course[1] is the assignment list for this course
                        status = page.find("td",class_="submissionstatussubmitted cell c1 lastcol")
                        tags = page.find_all("tr")
                        for date in tags:
                                if "עד לתאריך" in str(date):
                                        nd = date.text.strip().split(",")
                                        nd[0] = nd[0][9:].strip()  # date
                                        nd[1] = nd[1][1:].strip()  # time
                                        new_date = db.fix_date_format(nd[0])
                                        # create MoodleEvent object and add to moodle_events list
                                        if status:  # status is None if assignments hasn't been submitted yet
                                                moodle_events.append(MoodleEvent(course[0].strip(), new_date,nd[1].strip(),status.text))
                                        else:
                                                moodle_events.append(MoodleEvent(course[0].strip(), new_date,nd[1].strip(),status))

                                        break
        return moodle_events


def create_events(moodle_events):
    try:
        print("Creating Events..")
        events_dic, service, now = gc.get_events()
        for event in moodle_events:  # event is MoodleEvent object with attrs: name,date,time,status
                if event.date > now:
                        # events dic from Google Calendar
                        if event.date in events_dic:
                                found_event = False
                                for tuple in events_dic[event.date]:  # iterates over events on a specific date
                                        if event.name == tuple[0]:  # if current event summary exists in calendar
                                                found_event = True
                                                status = tuple[2] # status from calendar
                                                if status == "None":
                                                    status = None  # set to None value instead of None string
                                                if event.status != status:  # status changed 
                                                    service.events().delete(calendarId='primary',
                                                                            eventId=tuple[3]).execute()
                                                    print("Event status changed -", event.name, event.date)
                                                    # event deleted, set flag to false create a new one
                                                    found_event = False
                                                break  # event already exists, exit loop

                                if not found_event:
                                        my_event = gc.create_event(event)
                                        service.events().insert(calendarId='primary', body=my_event).execute()
                                        print("New event created - ", event.name, event.date)

                        else:  # date not in events dictionary
                                if event.date > now:
                                        my_event = gc.create_event(event)
                                        service.events().insert(calendarId='primary', body=my_event).execute()
                                        print("Created out of scope event", event.name, event.date)  # prints course name and date
    except HttpError:
        print("Failed to delete event")



if __name__ == "__main__":
        # DB for testing
        data = db.pull_db()
        events = [MoodleEvent(event[0],event[1],event[2], event[3]) for event in data]
        create_events( moodle_tlv("user","id","password"))


