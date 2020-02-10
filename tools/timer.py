from datetime import datetime, timedelta
import json


class Timer:
    def __init__(self, service_name=''):
        self.sequence = 1
        self.service_name = service_name
        self.date_start = datetime.now()
        self.date_end = ''
        self.results = []

    def start(self):
        self.date_start = datetime.now()

    def stop(self):
        self.lap()
        self.date_end = datetime.now()

    def lap(self):
        delta = datetime.now() - self.date_start
        mins, secs = divmod(delta.seconds, 60)
        hours, mins = divmod(mins, 60)
        days, hours = divmod(hours, 24)
        param = {
            'service_name': self.service_name,
            'days': days,
            'hours': hours,
            'minutes': mins,
            'seconds': secs,
            'microseconds': delta.microseconds,
        }
        res = 'Service : {service_name}, {days} day(s) {hours} hour(s) {minutes} minute(s) {seconds} second(s) {microseconds} microsecond(s)'.format(**param)
        print(res)
        self.results.append(res)
        self.date_start = datetime.now()
        self.sequence += 1

    def show(self):
        for rec in self.results:
            print(rec)
