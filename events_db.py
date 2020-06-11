import sqlite3
import os

def pull_db():
    try:
        if check_for_DB("eventsDB.db"):
            connection = sqlite3.connect("eventsDB.db")
            crsr = connection.cursor()
            crsr.execute("SELECT event_name,event_date,event_hour,event_status FROM events")
            events = crsr.fetchall()
            connection.close()
            return events
        else:
            raise IOError

    except IOError:
        print("DB doesn't exist")


def check_for_DB(db_name):
    return os.path.isfile(db_name)


def create_DB():
        connection = sqlite3.connect("eventsDB.db")
        crsr = connection.cursor()
        query = """CREATE TABLE events (
                        event_id INTEGER AUTO_INCREMENT PRIMARY KEY, 
                       event_name INTEGER,  
                        event_date VARCHAR(30),  
                       event_hour VARCHAR(30),  
                        event_status VARCHAR(30));"""
        crsr.execute(query)
        connection.commit()
        connection.close()


def insert_to_DB(list_of_events):
    if not check_for_DB("eventsDB.db"):  # if DB doesn't exist create it
        create_DB()
    connection = sqlite3.connect("eventsDB.db")
    crsr = connection.cursor()
    #list of events is a list containing lists in the format: [course_name,date,time,status]
    for event in list_of_events:
        insret_query = """INSERT INTO events (event_name,event_date,event_hour,event_status) VALUES ("{}", "{}", "{}", "{}");""".format(event[0],event[1][0],event[1][1],event[2])
        crsr.execute(insret_query)
    # commit changes to DB
    connection.commit()
    # close the connection
    connection.close()


def fix_date_format(date):

    if len(date) != 10:  # fix date format
        event_date = "0" + date.replace("/", "-")
        lst = event_date.split("-")
        event_date = "-".join(lst[::-1]).strip()  # flip date to US format
    else:
        event_date = date.replace("/", "-")
        lst = event_date.split("-")
        event_date = "-".join(lst[::-1]).strip()
    return event_date

