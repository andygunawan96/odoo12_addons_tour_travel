from odoo import models, api


class PrintoutVisaHO(models.AbstractModel):
    _name = 'report.tt_reservation_visa.printout_visa_ho'
    _description = 'Report Visa HO'

    """Abstract Model for report template.

        for `_name` model, please use `report.` as prefix then add `module_name.report_name`.
        """

    def get_values(self, ids):
        visa_obj = self.env['tt.reservation.visa'].browse(ids)
        vals = {
            'booked_name': visa_obj.sudo().booked_uid.name,
            'validate_name': visa_obj.sudo().validate_uid.name
        }
        return vals

    @api.model
    def _get_report_values(self, docids, data=None):
        agent_id = False
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            agent_id = rec.agent_id
        visa_ho_footer = self.env['tt.report.common.setting'].get_footer('visa_ticket_ho',agent_id)
        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'vals': self.get_values(data['ids']),
            'visa_ho_footer': visa_ho_footer and visa_ho_footer[0].html or '',
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
        agent_id = False
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            agent_id = rec.agent_id
        visa_customer_footer = self.env['tt.report.common.setting'].get_footer('visa_ticket_customer', agent_id)
        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'visa_customer_footer': visa_customer_footer and visa_customer_footer[0].html or '',
            'docs': self.env['tt.reservation.visa'].browse(data['ids']),
        }
