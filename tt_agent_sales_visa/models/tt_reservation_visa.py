from odoo import models, fields, api, _


class ReservationVisa(models.Model):

    _inherit = 'tt.reservation.visa'

    state_invoice = fields.Selection([('wait', 'Waiting'), ('partial', 'Partial'), ('full', 'Full')],
                                     'Invoice Status', help="Agent Invoice status", default='wait',
                                     readonly=True, compute='set_agent_invoice_state')

    invoice_line_ids = fields.One2many('tt.agent.invoice.line', 'res_id_resv', 'Invoice', domain=[('res_model_resv','=', 'tt.reservation.visa')])

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

    def get_all_passengers_desc(self):
        desc_text = ''
        for psg in self.passenger_ids:
            desc_text += psg.first_name + ' ' + psg.last_name + ', ' + psg.title + ' (' + psg.passenger_type + ') ' + \
                        psg.pricelist_id.entry_type.capitalize() + ' ' + psg.pricelist_id.visa_type.capitalize() + ' ' \
                        + psg.pricelist_id.process_type.capitalize() + ' (' + str(psg.pricelist_id.duration) + ' days)'\
                        + '\n'
        return desc_text

    def get_visa_summary(self):
        desc_text = ''
        for rec in self:
            desc_text = 'Reservation Visa Country : ' + self.country_id.name + ' ' + 'Consulate : ' + \
                        rec.immigration_consulate + ' ' + 'Journey Date : ' + str(rec.departure_date)
        return desc_text

    def action_create_invoice(self):
        invoice_id = False

        if not invoice_id:
            invoice_id = self.env['tt.agent.invoice'].create({
                'booker_id': self.booker_id.id,
                'agent_id': self.agent_id.id,
                'customer_parent_id': self.customer_parent_id.id,
                'customer_parent_type_id': self.customer_parent_type_id.id
            })

        inv_line_obj = self.env['tt.agent.invoice.line'].create({
            'res_model_resv': self._name,
            'res_id_resv': self.id,
            'invoice_id': invoice_id.id,
            'desc': self.get_visa_summary()
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
                'invoice_line_detail_ids': [(0, 0, {
                    'desc': desc_text,
                    'price_unit': price,
                    'quantity': 1,
                    'invoice_line_id': invoice_line_id,
                })]
            })

        ##membuat payment dalam draft
        payment_obj = self.env['tt.payment'].create({
            'agent_id': self.agent_id.id,
            'real_total_amount': inv_line_obj.total,
            'customer_parent_id': self.customer_parent_id.id
        })
        if self.acquirer_id:
            payment_obj.update({
                'acquirer_id': self.acquirer_id.id,
            })

        self.env['tt.payment.invoice.rel'].create({
            'invoice_id': invoice_id.id,
            'payment_id': payment_obj.id,
            'pay_amount': inv_line_obj.total,
        })

    def action_issued_visa(self, api_context=None):
        super(ReservationVisa, self).action_issued_visa(api_context)
        self.action_create_invoice()
