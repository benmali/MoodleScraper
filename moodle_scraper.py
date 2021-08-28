import requests
import google_calendar as gc
from selenium.webdriver.chrome.options import Options
import os
import re
from selenium import webdriver
import datetime
import pandas as pd
import json


class MoodleEvent:
    def __init__(self, name, date, time, status):
        self.name = name
        self.date = date
        self.time = time
        self.status = status

    def __repr__(self):
        return "({}, {}, {}, {})".format(self.name, self.date, self.time, self.status)


def export_excel(moodle_events):
    events = [[event.name, event.date, event.time, event.status] for event in moodle_events]
    df1 = pd.DataFrame(events,
                       index=[i for i in range(1, len(events) + 1)],
                       columns=['name', "date", 'time', 'status']
                       )
    with pd.ExcelWriter('moodle.xlsx') as writer:
        df1.to_excel(writer, sheet_name='Sheet_name_1')


def selenium_to_session(driver):
    """
    function takes Webdriver element, creates a Session object and returns it with the Cookies from the Webdriver
    :param driver: WebDriver object
    :return: Session object
    """
    session = requests.Session()
    cookies_browser = driver.get_cookies()
    c = [session.cookies.set(c['name'], c['value']) for c in cookies_browser]
    return session


def format_date(date):
    """
    create dd/mm/yyyy date to yyyy-mm-dd
    :param date: string - date in dd/mm/yyyy format
    :return: string  - date in yyyy-mm-dd format
    """
    new_date = date.split("/")[::-1]
    for i in range(1, 3):
        if len(new_date[i]) < 2:
            new_date[i] = "0" + new_date[i]

    return "-".join(new_date)


def moodle_tlv(username, user_id, password, driver):
    try:
        print("Fetching assignments from moodle..")
        driver.get("https://moodle.tau.ac.il/login/index.php")
        driver.implicitly_wait(5)
        unm = driver.find_element_by_name("Ecom_User_ID")
        unm.send_keys(username)
        uid = driver.find_element_by_name("Ecom_User_Pid")
        uid.send_keys(user_id)
        pw = driver.find_element_by_name("Ecom_Password")
        pw.send_keys(password)
        login = driver.find_element_by_name("loginButton2")
        login.click()
        driver.get("https://moodle.tau.ac.il/login/index.php")
        # passed authentication
        driver.get("https://moodle.tau.ac.il/")
        print("Authentication Passed!")
        session = selenium_to_session(driver)
        s1 = session.get("https://moodle.tau.ac.il/")
        print("Getting Courses..")
        course_links = re.findall(r"(https://moodle\.tau\.ac\.il/course/view\.php\?id=[0-9]+)\" data-key", s1.text)
        moodle_events = []
        for link in course_links:
            driver.get(link)
            course_page = driver.page_source
            # course_name = re.findall(r"<title>(.*)</title>", course_page)[0]
            course_assignments_links = re.findall(r"(https://moodle\.tau\.ac\.il/mod/assign/view\.php\?id=[0-9]+)\">",
                                                  course_page)
            for assignment_link in course_assignments_links:
                driver.get(assignment_link)
                assignment_page = driver.page_source
                assignment_title = re.findall(r"<title>(.*)</title>", assignment_page)[0]
                submission_full_date = re.findall("<th class=\"cell c0\" style=\"\" scope=\"row\">עד לתאריך</th>\n"
                                                  "<td class=\"cell c1 lastcol\" style=\"\">(.*)</td>", assignment_page)
                status = assignment_page.find("submissionstatussubmitted")
                if status == -1:
                    status = "Not Submitted"
                else:
                    status = "Submitted"
                if submission_full_date:
                    submission_date = format_date(submission_full_date[0].split(",")[0].strip())
                    submission_hour = submission_full_date[0].split(",")[1].strip()
                else:
                    submission_date = "2020-12-31"
                    submission_hour = "08:00"

                moodle_events.append(MoodleEvent(assignment_title,
                                                 submission_date,
                                                 submission_hour,
                                                 status))

        return moodle_events

    except:
        print("Unexpected Error")


def create_events(moodle_events):
    print("Creating Events..")
    events_dic, service, now = gc.get_events()
    date_now = datetime.datetime.strptime(now.split("T")[0], '%Y-%m-%d')
    for event in moodle_events:  # event is MoodleEvent object with attrs: name,date,time,status
        moodle_event_date = datetime.datetime.strptime(event.date, '%Y-%m-%d')
        if moodle_event_date >= date_now:
            # events dic from Google Calendar
            if event.date in events_dic and event.time[:2] != "00":
                found = False
                for tuple in events_dic[event.date]:  # iterates over events on a specific date
                    if event.name == tuple[0]:  # if current event summary exists in calendar
                        status = tuple[2]  # status from calendar
                        if event.status != status:  # status changed
                            service.events().delete(calendarId='primary',
                                                    eventId=tuple[3]).execute()
                            print("Event status changed -", event.name, event.date)

                        else:
                            found = True
                            break  # event already exists, exit loop
                if not found:
                    my_event = gc.create_event(event)
                    service.events().insert(calendarId='primary', body=my_event).execute()
                    print("New event created - ", event.name, event.date)

            else:  # date not in events dictionary
                # check for day before
                event_date = datetime.datetime.strptime(event.date, '%Y-%m-%d')
                day_before = event_date - datetime.timedelta(days=1)
                day_before = str(day_before).split()[0]
                create = True

                if event.time[:2] == "00" and day_before in events_dic:  # hour is 12am regardless of minutes
                    for tuple in events_dic[day_before]:
                        if event.name == tuple[0]:  # if current event summary exists in calendar
                            status = tuple[2]  # status from calendar
                            if event.status != status:  # status changed
                                service.events().delete(calendarId='primary',
                                                        eventId=tuple[3]).execute()
                                print("Event status changed -", event.name, event.date)
                                # event deleted, set flag to false create a new one
                            else:
                                create = False
                                break
                if create:
                    my_event = gc.create_event(event)
                    service.events().insert(calendarId='primary', body=my_event).execute()
                    print("Created out of scope event", event.name, event.date)  # prints course name and date


if __name__ == "__main__":
    current_dir = os.getcwd()
    chrome_driver_path = os.getcwd() + '\\chromedriver'

    chrome_options = Options()
    chrome_options.add_argument('--headless')

    webdriver = webdriver.Chrome(
        executable_path=chrome_driver_path, options=chrome_options
    )
    with open("user.json", "r") as file:
        user_details = json.loads(file.read())
    if user_details:
        user = user_details.get("user", None)
        user_id = user_details.get("user_id", None)
        password = user_details.get("password", None)
        create_events(moodle_tlv(user, user_id, password, webdriver))

    webdriver.close()
    print("Done")
    # event = gc.create_event(MoodleEvent("Test",'2020-10-24',"17:00","Tested!"))
    # event2 = gc.create_event(MoodleEvent("Test2", '2020-10-29', "17:00", "Tested!"))
    # events_dic, service, now = gc.get_events()
    # service.events().insert(calendarId='primary', body=event).execute()
    # service.events().insert(calendarId='primary', body=event2).execute()
    #
