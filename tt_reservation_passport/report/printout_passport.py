from odoo import models, api


class PrintoutPassportHO(models.AbstractModel):
    _name = 'report.tt_reservation_passport.printout_passport_ho'

    """Abstract Model for report template.

        for `_name` model, please use `report.` as prefix then add `module_name.report_name`.
        """

    @api.model
    def _get_report_values(self, docids, data=None):
        print('docids : ' + str(self.env['tt.reservation.passport'].browse(data['ids'])))
        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'docs': self.env['tt.reservation.passport'].browse(data['ids']),
        }


class PrintoutPassportCustomer(models.AbstractModel):
    _name = 'report.tt_reservation_passport.printout_passport_cust'

    """Abstract Model for report template.

        for `_name` model, please use `report.` as prefix then add `module_name.report_name`.
        """

    @api.model
    def _get_report_values(self, docids, data=None):
        print('docids : ' + str(self.env['tt.reservation.passport'].browse(data['ids'])))
        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'docs': self.env['tt.reservation.passport'].browse(data['ids']),
        }
