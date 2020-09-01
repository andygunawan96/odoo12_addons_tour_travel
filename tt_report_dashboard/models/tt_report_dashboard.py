from odoo import models, fields, api, _
from ...tools import variables,util,ERR
import logging, traceback,pytz

_logger = logging.getLogger(__name__)

class TtReportDashboard(models.Model):
    _name = 'tt.report.dashboard'

    def get_report_json_api(self, data, context):
        type = data['report_type']
        if type == 'overall':
            res = self.get_report_overall(data)
        elif type == 'airline':
            res = self.get_report_airline(data)
        elif type == 'event':
            res = self.get_report_event(data)
        elif type == 'train':
            res = self.get_report_train(data)
        elif type == 'passport':
            res = self.get_report_passport(data)
        elif type == 'ppob':
            res = self.get_report_ppob(data)
        elif type == 'activity':
            res = self.get_report_activity(data)
        elif type == 'hotel':
            res = self.get_report_hotel(data)
        else:
            return ERR.get_error(1001, "Cannot find action")
        return ERR.get_no_error(res)

    def get_report_xls_api(self, data,  context):
        return ERR.get_no_error()

    def get_report_overall(self, data):
        temp_dict = {
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'type': data['report_type']
        }
        values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)


        return ERR.get_no_error(values)

    def get_report_airline(self, data):
        temp_dict = {
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'type': data['report_type']
        }
        values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

        return ERR.get_no_error(values)

    def get_report_activity(self, data):
        temp_dict = {
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'type': data['report_type']
        }
        values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)
        return ERR.get_no_error(values)

    def get_report_event(self, data):
        temp_dict = {
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'type': data['report_type']
        }
        values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)
        return ERR.get_no_error(values)

    def get_report_passport(self, data):
        temp_dict = {
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'type': data['report_type']
        }
        values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)
        return ERR.get_no_error(values)

    def get_report_ppob(self, data):
        temp_dict = {
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'type': data['report_type']
        }
        values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)
        return ERR.get_no_error(values)

    def get_report_train(self, data):
        temp_dict = {
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'type': data['report_type']
        }
        values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)
        return ERR.get_no_error(values)

    def get_report_hotel(self, data):
        temp_dict = {
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'type': data['report_type']
        }
        values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)
        return ERR.get_no_error(values)