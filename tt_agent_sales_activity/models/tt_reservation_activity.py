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

    def get_segment_description(self):
        tmp = ''
        # vals = []
        for rec in self.journey_ids:
            tmp += '%s(%s) - %s(%s),' % (rec.origin_id.city, rec.origin_id.code, rec.destination_id.city, rec.destination_id.code)
            tmp += '%s - %s\n ' % (rec.departure_date[:16], rec.arrival_date[:16])
        return tmp

    def action_create_invoice(self):
        invoice_id = self.env['tt.agent.invoice'].search([('booker_id','=',self.booker_id.id), ('state','=','draft')])

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
            # 'desc': self.get_segment_description()
        })

        invoice_line_id = inv_line_obj.id

        #untuk harga fare per passenger
        for psg in self.passenger_ids:
            desc_text = '%s, %s' % (' '.join((psg.first_name or '', psg.last_name or '')), psg.title or '')
            price_unit = 0
            for cost_charge in psg.cost_service_charge_ids:
                if cost_charge.charge_type != 'RAC':
                    price_unit += cost_charge.amount
            for channel_charge in psg.channel_service_charge_ids:
                price_unit += channel_charge.amount

            inv_line_obj.write({
                'invoice_line_detail_ids': [(0,0,{
                    'desc': desc_text,
                    'price_unit': price_unit,
                    'quantity': 1,
                    'invoice_line_id': invoice_line_id,
                })]
            })

        ##membuat payment dalam draft
        payment_obj = self.env['tt.payment'].create({
            'agent_id': self.agent_id.id,
            'acquirer_id': 7,
            'total_amount': inv_line_obj.total,
            'payment_date': datetime.now()
        })

        self.env['tt.payment.invoice.rel'].create({
            'invoice_id': invoice_id.id,
            'payment_id': payment_obj.id,
            'pay_amount': inv_line_obj.total,
        })
        payment_obj.compute_available_amount()

    # def action_issued_activity(self, api_context=None):
    #     super(ReservationActivity, self).action_issued_activity(api_context)
    #     self.action_create_invoice()
