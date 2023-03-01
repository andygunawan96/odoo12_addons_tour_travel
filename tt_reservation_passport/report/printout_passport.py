from odoo import models, api


class PrintoutPassportHO(models.AbstractModel):
    _name = 'report.tt_reservation_passport.printout_passport_ho'
    _description = 'Report Printout Passport HO'

    """Abstract Model for report template.

        for `_name` model, please use `report.` as prefix then add `module_name.report_name`.
        """

    def get_values(self, ids):
        passport_obj = self.env['tt.reservation.passport'].browse(ids)
        vals = {
            'booked_name': passport_obj.sudo().booked_uid.name,
            'validate_name': passport_obj.sudo().validate_uid.name
        }
        return vals

    @api.model
    def _get_report_values(self, docids, data=None):
        # print('docids : ' + str(self.env['tt.reservation.passport'].browse(data['ids'])))
        vals = {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'vals': self.get_values(data['ids']),
            'docs': self.env['tt.reservation.passport'].browse(data['ids']),
        }
        return vals


class PrintoutPassportCustomer(models.AbstractModel):
    _name = 'report.tt_reservation_passport.printout_passport_cust'
    _description = 'Report Printout Passport Customer'
    """Abstract Model for report template.

        for `_name` model, please use `report.` as prefix then add `module_name.report_name`.
        """

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'docs': self.env['tt.reservation.passport'].browse(data['ids']),
        }
