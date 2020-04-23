from odoo import models, fields, api, _
from datetime import datetime


class ReservationPassport(models.Model):

    _inherit = 'tt.reservation.passport'

    state_invoice = fields.Selection([('wait', 'Waiting'), ('partial', 'Partial'), ('full', 'Full')],
                                     'Invoice Status', help="Agent Invoice status", default='wait',
                                     readonly=True)  # , compute='set_agent_invoice_state'

    invoice_line_ids = fields.One2many('tt.agent.invoice.line', 'res_id_resv', 'Invoice', domain=[('res_model_resv','=', 'tt.reservation.passport')])

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
            desc_text += (psg.first_name if psg.first_name else '') + ' ' + \
                         (psg.last_name if psg.last_name else '') + ', ' + \
                         (psg.title if psg.title else '') + \
                         ' (' + (psg.passenger_type if psg.passenger_type else '') + ') ' + \
                         (psg.pricelist_id.apply_type.capitalize() if psg.pricelist_id.apply_type else '') + ' ' + \
                         (psg.pricelist_id.passport_type.capitalize() if psg.pricelist_id.passport_type else '') + ' ' + \
                         (psg.pricelist_id.process_type.capitalize() if psg.pricelist_id.process_type else '') + \
                         ' (' + str((psg.pricelist_id.duration if psg.pricelist_id.duration else '-')) + ' days)' + \
                         '\n'
        return desc_text

    def get_passport_summary(self):
        desc_text = ''
        for rec in self:
            desc_text = 'Reservation Passport Immigration : ' + (rec.immigration_consulate if rec.immigration_consulate else '')
        return desc_text

    def action_create_invoice(self, data, context):  #
        invoice_id = False
        book_obj = self.env['tt.reservation.passport'].search([('name', '=', data['order_number'])])
        if not invoice_id:
            invoice_id = self.env['tt.agent.invoice'].create({
                'booker_id': book_obj.booker_id.id,
                'contact_id': self.contact_id.id,
                'agent_id': self.agent_id.id,
                'customer_parent_id': book_obj.customer_parent_id.id,
                'customer_parent_type_id': book_obj.customer_parent_type_id.id,
                'state': 'confirm',
                'confirmed_uid': book_obj.confirmed_uid.id,
                'confirmed_date': datetime.now()
            })

        inv_line_obj = self.env['tt.agent.invoice.line'].create({
            'res_model_resv': self._name,
            'res_id_resv': self.id,
            'invoice_id': invoice_id.id,
            'reference': self.name,
            'desc': self.get_all_passengers_desc(),
            'admin_fee': self.payment_acquirer_number_id.fee_amount
        })

        invoice_line_id = inv_line_obj.id

        for psg in self.passenger_ids:
            desc_text = (psg.first_name if psg.first_name else '') + ' ' + \
                        (psg.last_name if psg.last_name else '') + ', ' + \
                        (psg.title if psg.title else '') + \
                        ' (' + (psg.passenger_type if psg.passenger_type else '') + ') ' + \
                        (psg.pricelist_id.apply_type.capitalize() if psg.pricelist_id.apply_type else '') + ' ' + \
                        (psg.pricelist_id.passport_type.capitalize() if psg.pricelist_id.passport_type else '') + ' ' + \
                        (psg.pricelist_id.process_type.capitalize() if psg.pricelist_id.process_type else '') + \
                        ' (' + str(psg.pricelist_id.duration if psg.pricelist_id.duration else '-') + ' days)'
            price = 0
            for srvc in psg.cost_service_charge_ids:
                if srvc.charge_type != 'RAC':
                    price += srvc.amount
            for srvc in psg.channel_service_charge_ids:
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
            'agent_id': book_obj.agent_id.id,
            'real_total_amount': invoice_id.grand_total,
            'customer_parent_id': book_obj.customer_parent_id.id
        })
        if 'seq_id' in data:
            if data['seq_id']:
                payment_obj.update({
                    'acquirer_id': self.env['payment.acquirer'].search([('seq_id', '=', data['seq_id'])],limit=1).id,
                })

        self.env['tt.payment.invoice.rel'].create({
            'invoice_id': invoice_id.id,
            'payment_id': payment_obj.id,
            'pay_amount': invoice_id.grand_total
        })

    def action_issued_passport_api(self, data, context):  # , context
        res = super(ReservationPassport, self).action_issued_passport_api(data, context)  # , context
        self.action_create_invoice(data, context)  # , context
        return res
