from odoo import models,api,fields
from datetime import datetime
import pytz


class ReservationPhc(models.Model):

    _inherit = 'tt.reservation.phc'

    # invoice_line_ids = fields.One2many('tt.agent.invoice.line.','res_id_resv', 'Invoice',
    #                               domain="[('res_model_resv','=','self._name'),('res_id_resv','=','self.id')]")

    state_invoice = fields.Selection([('wait', 'Waiting'), ('partial', 'Partial'), ('full', 'Full')],
                                     'Invoice Status', help="Agent Invoice status", default='wait',
                                     readonly=True, compute='set_agent_invoice_state')

    invoice_line_ids = fields.One2many('tt.agent.invoice.line', 'res_id_resv', 'Invoice',
                                       domain=[('res_model_resv', '=', 'tt.reservation.phc')])

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
        # TODO: soale mnurut ku biar ada nomor pendaftarane walo g kepake nomer e
        # Opsi 1: Jika Nama reservation dan PNR e sdah sama pakai yg ini
        tmp = '%s\n' % (self.provider_booking_ids[0].carrier_id.name)
        # Opsi 2: Jika PNR dan resv ne beda pakek yg ini
        # tmp = self.name + '\n'
        for timeslot_obj in self.timeslot_ids:
            if timeslot_obj.timeslot_type == 'drive_thru':
                tmp+= '\n%s' % (str(timeslot_obj.datetimeslot.astimezone(pytz.timezone('Asia/Jakarta')).strftime('%Y-%m-%d')) + ' (DRIVE THRU 08.00 - 15.00 WIB tergantung banyaknya antrian)')
            else:
                tmp+= '\n%s' % (str(timeslot_obj.datetimeslot.astimezone(pytz.timezone('Asia/Jakarta')).strftime('%Y-%m-%d %H:%M')))
        tmp += '\n\nAddress : %s' % (self.test_address)
        return tmp

    def action_create_invoice(self,acquirer_id,co_uid,customer_parent_id):
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
            'reference': 'Order Number:\n%s' % (self.name),
            'desc': self.get_segment_description(),
            'admin_fee': self.payment_acquirer_number_id.fee_amount
        })

        invoice_line_id = inv_line_obj.id

        discount = 0

        #untuk harga fare per passenger
        for provider in self.provider_booking_ids:
            for ticket in provider.ticket_ids:
                psg = ticket.passenger_id
                desc_text = '%s, %s (%s)' % (' '.join((psg.first_name or '', psg.last_name or '')), psg.title or '', ticket.ticket_number)
                price_unit = 0
                for cost_charge in psg.cost_service_charge_ids:
                    if cost_charge.charge_type not in ['RAC', 'DISC']:
                        price_unit += cost_charge.amount
                    elif cost_charge.charge_type == 'DISC':
                        discount += cost_charge.amount
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

        inv_line_obj.discount = abs(discount)

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


    # # ## CREATED by Samvi 2018/07/24
    # @api.multi
    # def action_check_provider_state(self, api_context=None):
    #     res = super(Reservationphc, self).action_check_provider_state(api_context)
    #     if self.provider_booking_ids:
    #         # todo membuat mekanisme untuk partial issued seperti apa
    #         # fixme sementara create agent invoice berdasarkan bookingan
    #         if any(rec.state == 'issued' for rec in self.provider_booking_ids):
    #             # if self.agent_id.agent_type_id.id in [self.env.ref('tt_base_rodex.agent_type_citra').id,
    #             #                                       self.env.ref('tt_base_rodex.agent_type_japro').id]:
    #             self.action_create_invoice()
    #
    #     return res

    def action_reverse_phc(self,context):
        super(ReservationPhc, self).action_reverse_phc(context)
        for rec in self.invoice_line_ids:
            try:
                rec.invoice_id.action_cancel_invoice()
            except Exception as e:
                print(str(e))

    def action_issued_phc(self,co_uid,customer_parent_id,acquirer_id):
        super(ReservationPhc, self).action_issued_phc(co_uid,customer_parent_id)
        self.action_create_invoice(acquirer_id,co_uid,customer_parent_id)

