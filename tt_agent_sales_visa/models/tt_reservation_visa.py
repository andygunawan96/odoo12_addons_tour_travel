from odoo import models, fields, api, _


class ReservationVisa(models.Model):

    _inherit = 'tt.reservation.visa'

    state_invoice = fields.Selection([('wait', 'Waiting'), ('partial', 'Partial'), ('full', 'Full')],
                                     'Invoice Status', help="Agent Invoice status", default='wait',
                                     readonly=True, compute='set_agent_invoice_state')

    invoice_line_ids = fields.One2many('tt.agent.invoice.line', 'res_id_resv', 'Invoice')


    @api.depends('invoice_line_ids')
    def set_agent_invoice_state(self):

        states = []

        for rec in self.invoice_line_ids:
            states.append(rec.state)

        if all(state == 'draft' for state in states) or not states:
            self.state_invoice = 'wait'
        elif all(state != 'draft' for state in states):
            self.state_invoice = 'full'
        elif any(state != 'draft' for state in states):
            self.state_invoice = 'partial'

    def action_create_invoice(self):
        invoice_id = self.env['tt.agent.invoice'].search(
            [('booker_id', '=', self.contact_id.id), ('state', '=', 'draft')])

        if not invoice_id:
            invoice_id = self.env['tt.agent.invoice'].create({
                'contact_id': self.contact_id.id,
                'agent_id': self.agent_id.id,
            })

        inv_line_obj = self.env['tt.agent.invoice.line'].create({
            'res_model_resv': self._name,
            'res_id_resv': self.id,
            'invoice_id': invoice_id.id,
            'desc': 'Testing Visa Invoice'
        })

        invoice_line_id = inv_line_obj.id

        for psg in self.passenger_ids:
            desc_text = psg.first_name + ' ' + psg.last_name + ', ' + psg.title + ' (' + psg.passenger_type + ') ' + \
                        psg.pricelist_id.entry_type.capitalize() + ' ' + psg.pricelist_id.visa_type.capitalize() + ' ' \
                        + psg.pricelist_id.process_type.capitalize() + ' (' + str(psg.pricelist_id.duration) + ' days)'
            price = 0
            for srvc in psg['cost_service_charge_ids']:
                if srvc.charge_code != 'rac':
                    price += srvc.amount
            for srvc in psg['channel_service_charge_ids']:
                price += srvc.amount
            inv_line_obj.write({
                'invoice_line_detail_ids': [(0,0,{
                    'desc': desc_text,
                    'price_unit': price,
                    'quantity': 1,
                    'invoice_line_id': invoice_line_id,
                })]
            })
