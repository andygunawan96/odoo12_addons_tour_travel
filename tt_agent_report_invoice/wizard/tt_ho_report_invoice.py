from odoo import fields, models, api

STATE = [
    ('all', 'All'),
    ('draft', 'Draft'),
    ('paid', 'Paid'),
    ('bill', 'Bill'),
    ('bill2', 'Bill by System'),
    ('cancel', 'Canceled')
]


class HOReportInvoice(models.TransientModel):
    _name = 'tt.ho.report.invoice.wizard'
    _inherit = "tt.agent.report.common.wizard"

    state = fields.Selection(selection=STATE, string="State", default='all')

    # customer = fields.Selection(selection=lambda self: self._compute_customer_selection(), string='Customer', default='all')

    def _compute_customer_selection(self):
        value = [('all', 'ALL')]
        customer = self.env['tt.customer.parent'].search(['agent_id', '=', self.res.user_id])
        for i in customer:
            temp_tuple = (customer.name, customer.name)
            if temp_tuple not in value:
                value.append(temp_tuple)

    def _print_report(self, data):
        records = {
            'ids': self.ids,
            'model': self._name,
            'data_form': data['form']
        }
        return self.env.ref('tt_agent_report_invoice.action_ho_report_invoice').report_action(self, data=records)

    def returning_index(self, lst, params):
        for i, dic in enumerate(lst):
            if dic['payment_acquirer'] == params['payment_acquirer'] and dic['payment_account'] == params['payment_account']:
                return i
        return -1
