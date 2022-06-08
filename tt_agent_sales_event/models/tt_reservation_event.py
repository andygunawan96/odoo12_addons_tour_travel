from odoo import models,api,fields
from datetime import datetime, timedelta
import base64


class ReservationEvent(models.Model):
    _inherit = 'tt.reservation.event'

    invoice_line_ids = fields.One2many('tt.agent.invoice.line', 'res_id_resv', 'Invoice', domain=[('res_model_resv','=', 'tt.reservation.event')])
    state_invoice = fields.Selection([('wait', 'Waiting'), ('partial', 'Partial'), ('full', 'Full')],
                                     'Invoice Status', help="Agent Invoice status", default='wait',
                                     readonly=True, compute='set_agent_invoice_state')

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
        tmp = 'Event : %s\n' % (self.event_name,)
        if self.event_id:
            tmp += 'Location : \n'
            for rec in self.event_id.location_ids:
                tmp += ' - %s, %s, %s, %s\n' % (rec.name, rec.address, rec.city_id.name, rec.country_id.name)

        tmp += 'Booker : %s\n' % (self.booker_id.name,)
        tmp += 'Contact Person: %s\n' % (self.contact_title,)
        tmp += 'Contact Email : %s\n' % (self.contact_email,)
        tmp += 'Contact Phone : %s\n' % (self.contact_phone,)
        return tmp

    def action_create_invoice(self, data):
        invoice_id = self.invoice_line_ids.filtered(lambda x: x.state in ['bill', 'bill2', 'paid'])

        if not invoice_id:
            invoice_id = self.env['tt.agent.invoice'].create({
                'booker_id': self.booker_id.id,
                'agent_id': self.agent_id.id,
                'customer_parent_id': self.customer_parent_id.id,
                'customer_parent_type_id': self.customer_parent_type_id.id,
                'state': 'confirm',
                'confirmed_uid': data['co_uid'],
                'confirmed_date': datetime.now()
            })

        inv_line_obj = self.env['tt.agent.invoice.line'].create({
            'res_model_resv': self._name,
            'res_id_resv': self.id,
            'invoice_id': invoice_id.id,
            'reference': self.name,
            'desc': self.get_segment_description(),
            'admin_fee': self.payment_acquirer_number_id.fee_amount,
            'customer_parent_id': self.customer_parent_id.id
        })

        discount = 0

        for opt_obj in self.passenger_ids:
            price_unit = 0
            for cost_charge in opt_obj.cost_service_charge_ids:
                if cost_charge.charge_type not in ['RAC', 'DISC']:
                    price_unit += cost_charge.amount
                elif cost_charge.charge_type == 'DISC':
                    discount += cost_charge.amount
            for channel_charge in opt_obj.channel_service_charge_ids:
                price_unit += channel_charge.amount

            ticket = opt_obj.option_id.ticket_number and ' (' + opt_obj.option_id.ticket_number + ') ' or ''
            self.env['tt.agent.invoice.line.detail'].create({
                # 'desc': opt_obj.option_id.event_option_id.grade + ticket,
                'desc': opt_obj.option_id.event_option_name and opt_obj.option_id.event_option_name + ticket or ticket,
                'invoice_line_id': inv_line_obj.id,
                'price_unit': price_unit, # Channel + Cost Service Charge
                'quantity': 1,
            })

        inv_line_obj.discount = abs(discount)

        payref_id_list = []
        for idx, att in enumerate(data['payment_ref_attachment']):
            file_ext = att['name'].split(".")[-1]
            temp_filename = '%s_Payment_Ref_%s.%s' % (str(idx), invoice_id.name, file_ext)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': temp_filename,
                    'file_reference': 'Payment Reference',
                    'file': att['file']
                },
                {
                    'co_agent_id': self.agent_id.id,
                    'co_uid': data['co_uid'],
                }
            )
            upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            payref_id_list.append(upc_id.id)

        payment_vals = {
            'agent_id': self.agent_id.id,
            'acquirer_id': data['acquirer_id'],
            'real_total_amount': invoice_id.grand_total,
            'customer_parent_id': data['customer_parent_id'],
            'confirm_uid': data['co_uid'],
            'confirm_date': datetime.now()
        }

        if payref_id_list:
            payment_vals.update({
                'reference': data.get('payment_reference', ''),
                'payment_image_ids': [(6, 0, payref_id_list)]
            })

        ##membuat payment dalam draft
        payment_obj = self.env['tt.payment'].create(payment_vals)

        self.env['tt.payment.invoice.rel'].create({
            'invoice_id': invoice_id.id,
            'payment_id': payment_obj.id,
            'pay_amount': invoice_id.grand_total
        })

    def action_issued_event(self,data):
        super(ReservationEvent, self).action_issued_event(data)
        self.action_create_invoice(data)
