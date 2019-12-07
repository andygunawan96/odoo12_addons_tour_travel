from odoo import models, api


class PrintoutVisaHO(models.AbstractModel):
    _name = 'report.tt_reservation_visa.printout_visa_ho'
    _description = 'Report Visa HO'

    """Abstract Model for report template.

        for `_name` model, please use `report.` as prefix then add `module_name.report_name`.
        """

    def get_values(self, ids):
        print(ids)
        visa_obj = self.env['tt.reservation.visa'].browse(ids)
        vals = {
            'booked_name': visa_obj.sudo().booked_uid.name,
            'validate_name': visa_obj.sudo().validate_uid.name
        }
        return vals

    @api.model
    def _get_report_values(self, docids, data=None):
        print('docids : ' + str(self.env['tt.reservation.visa'].browse(data['ids'])))
        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'vals': self.get_values(data['ids']),
            'docs': self.env['tt.reservation.visa'].browse(data['ids']),
        }


class PrintoutVisaCustomer(models.AbstractModel):
    _name = 'report.tt_reservation_visa.printout_visa_cust'
    _description = 'Report Visa Customer'

    """Abstract Model for report template.

        for `_name` model, please use `report.` as prefix then add `module_name.report_name`.
        """

    @api.model
    def _get_report_values(self, docids, data=None):
        print('docids : ' + str(self.env['tt.reservation.visa'].browse(data['ids'])))
        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'docs': self.env['tt.reservation.visa'].browse(data['ids']),
        }
