from odoo import models,api,fields
from datetime import datetime


class ReservationActivity(models.Model):

    _inherit = 'tt.reservation.activity'

    # invoice_line_ids = fields.One2many('tt.agent.invoice.line.','res_id_resv', 'Invoice',
    #                               domain="[('res_model_resv','=','self._name'),('res_id_resv','=','self.id')]")

    state_invoice = fields.Selection([('wait', 'Waiting'), ('partial', 'Partial'), ('full', 'Full')],
                                     'Invoice Status', help="Agent Invoice status", default='wait',
                                     readonly=True, compute='set_agent_invoice_state')

    invoice_line_ids = fields.One2many('tt.agent.invoice.line', 'res_id_resv', 'Invoice', domain=[('res_model_resv','=', 'tt.reservation.activity')])


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

    def get_activity_description(self):
        tmp = ''
        for rec in self.provider_booking_ids:
            for rec2 in rec.activity_detail_ids:
                tmp += '%s (%s), ' % (rec2.activity_id.name, rec2.activity_product_id.name,)
                tmp += '%s ' % (rec2.visit_date,)
                if rec2.timeslot:
                    tmp += '(%s) ' % (rec2.timeslot,)
                tmp += '\n'
            tmp += '\n'
        return tmp

    def action_create_invoice(self, acquirer_id,co_uid,customer_parent_id):
        invoice_id = False

        if not invoice_id:
            invoice_id = self.env['tt.agent.invoice'].create({
                'booker_id': self.booker_id.id,
                'agent_id': self.agent_id.id,
                'customer_parent_id': self.customer_parent_id.id,
                'customer_parent_type_id': self.customer_parent_type_id.id,
                'state': 'confirm',
                'confirmed_uid': co_uid,
                'confirmed_date': datetime.now()
            })

        inv_line_obj = self.env['tt.agent.invoice.line'].create({
            'res_model_resv': self._name,
            'res_id_resv': self.id,
            'invoice_id': invoice_id.id,
            'reference': self.name,
            'desc': self.get_activity_description(),
            'admin_fee': self.payment_acquirer_number_id.fee_amount
        })

        invoice_line_id = inv_line_obj.id

        # untuk harga fare per passenger
        for psg in self.passenger_ids:
            desc_text = '%s, %s' % (' '.join((psg.first_name or '', psg.last_name or '')), psg.title or '')
            price_unit = 0
            for cost_charge in psg.cost_service_charge_ids:
                if cost_charge.charge_type not in ['RAC', 'DISC']:
                    price_unit += cost_charge.amount
            for channel_charge in psg.channel_service_charge_ids:
                price_unit += channel_charge.amount

            inv_line_obj.write({
                'invoice_line_detail_ids': [(0, 0, {
                    'desc': desc_text,
                    'price_unit': price_unit,
                    'quantity': 1,
                    'invoice_line_id': invoice_line_id,
                })]
            })

        ##membuat payment dalam draft
        payment_obj = self.env['tt.payment'].create({
            'agent_id': self.agent_id.id,
            'acquirer_id': acquirer_id,
            'real_total_amount': invoice_id.grand_total,
            'customer_parent_id': customer_parent_id,
            'confirm_uid': co_uid,
            'confirm_date': datetime.now()
        })

        self.env['tt.payment.invoice.rel'].create({
            'invoice_id': invoice_id.id,
            'payment_id': payment_obj.id,
            'pay_amount': invoice_id.grand_total
        })

    def action_reverse_activity(self, context):
        super(ReservationActivity, self).action_reverse_activity(context)
        for rec in self.invoice_line_ids:
            try:
                rec.invoice_id.action_cancel_invoice()
            except Exception as e:
                print(str(e))

    def action_issued_activity(self, co_uid, customer_parent_id, acquirer_id):
        super(ReservationActivity, self).action_issued_activity(co_uid, customer_parent_id)
        self.action_create_invoice(acquirer_id, co_uid, customer_parent_id)

