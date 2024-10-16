import sqlite3
import traceback
from datetime import timedelta


def first_start():
    with DB() as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, chat_id BIGINTEGER)""")
        c.execute(
            """CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY, 
            datetime DATETIME, 
            user_id INTEGER, 
            event_handler TEXT, 
            event_data TEXT, 
            is_first_alert BOOL DEFAULT false,
            is_last_alert BOOL DEFAULT false,
            FOREIGN KEY(user_id) REFERENCES users(id))""")


class DB:

    def __init__(self):
        self.conn = sqlite3.connect('example.db')

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc_value, traceback):
        self.conn.commit()
        self.conn.close()


class User:

    def __init__(self, username, chat_id=-1):
        self.username = username
        self.chat_id = chat_id

    def add_user(self):
        try:
            with DB() as conn:
                c = conn.cursor()
                user = self.get_user()
                if not user:
                    c.execute(
                        "INSERT INTO users (username, chat_id) VALUES ('%s', %s)" % (self.username, self.chat_id,))
                    return True, "Зарегистрирован!"
                return False, "Вы уже зарегистрированные!"
        except Exception as e:
            print(traceback.format_exc())
            return False, e

    def get_user(self):
        with DB() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE username = '%s'" % (self.username,))
            return c.fetchone()


class Event:

    def __init__(self):
        pass

    @staticmethod
    def add_event(datetime_event, event_handler, event_data, username):
        try:
            with DB() as conn:
                c = conn.cursor()
                user_id = User(username).get_user()
                if user_id:
                    c.execute(
                        "INSERT INTO events (datetime, event_handler, event_data, user_id) VALUES ('%s', '%s', '%s', %s)" % (
                            datetime_event, event_handler, event_data, user_id[0]))
                    return True, "Событие добавлено!"
                else:
                    return False, "Вы не зарегистрированы! Пропишите /reg"
        except Exception as e:
            print(traceback.format_exc())
            return False, e

    @staticmethod
    def get_all_events(username):
        try:
            with DB() as conn:
                c = conn.cursor()
                user_id = User(username).get_user()
                if user_id:
                    c.execute("SELECT * FROM events WHERE user_id = %s" % (user_id[0],))
                    return True, c.fetchall()
                else:
                    return False, "Вы не зарегистрированы! Пропишите /reg"
        except Exception as e:
            print(traceback.format_exc())
            return False, e

    @staticmethod
    def get_events_by_id(event_id):
        try:
            with DB() as conn:
                c = conn.cursor()
                c.execute("""SELECT * FROM events WHERE id = %s""" % (event_id,))
                return True, c.fetchone()
        except Exception as e:
            print(traceback.format_exc())
            return False, e

    @staticmethod
    def delete_event(event_id):
        try:
            with DB() as conn:
                c = conn.cursor()
                c.execute("""DELETE FROM events WHERE id = %s""" % (event_id,))
                return True, "Событие удалено!"
        except Exception as e:
            print(traceback.format_exc())
            return False, e

    @staticmethod
    def get_all_events_by_date(date, time_delta):
        try:
            with DB() as conn:
                c = conn.cursor()
                date_next = date + timedelta(hours=time_delta)
                c.execute("""SELECT e.id, event_handler, event_data, chat_id 
                             FROM events e 
                             INNER JOIN users u ON u.id = e.user_id  
                             WHERE datetime <= ? AND datetime > ? AND is_first_alert=0;""",
                          (date, date_next))
                events = c.fetchall()
                ids = [id[0] for id in events]
                if time_delta == 2:
                    c.execute(
                        """UPDATE events SET is_last_alert = 1 WHERE id IN ({});""".format(','.join('?' * len(ids))),
                        ids)
                elif time_delta == 24:
                    c.execute(
                        """UPDATE events SET is_first_alert = 1 WHERE id IN ({});""".format(','.join('?' * len(ids))),
                        ids)
                conn.commit()
                return True, events
        except Exception as e:
            print(traceback.format_exc())
            return False, e
