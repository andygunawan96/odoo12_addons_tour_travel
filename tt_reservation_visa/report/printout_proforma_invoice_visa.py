from odoo import models, api


class PrintoutProformaInvoiceVisa(models.AbstractModel):
    _name = 'report.tt_reservation_visa.printout_proforma_invoice_visa'

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