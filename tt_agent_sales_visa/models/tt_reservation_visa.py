from odoo import models, fields, api, _
from datetime import datetime, timedelta
import base64


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
            desc_text += (psg.first_name if psg.first_name else '') + ' ' + \
                         (psg.last_name if psg.last_name else '') + ', ' + \
                         (psg.title if psg.title else '') + \
                         ' (' + (psg.passenger_type if psg.passenger_type else '') + ') ' + \
                         (psg.pricelist_id.entry_type.capitalize() if psg.pricelist_id.entry_type else '') + ' ' + \
                         (psg.pricelist_id.visa_type.capitalize() if psg.pricelist_id.visa_type else '') + ' ' + \
                         (psg.pricelist_id.process_type.capitalize() if psg.pricelist_id.process_type else '') + \
                         ' (' + str(psg.pricelist_id.duration if psg.pricelist_id.duration else '-') + ' days)' + '\n'
        return desc_text

    def get_visa_summary(self):
        desc_text = ''
        for rec in self:
            desc_text = 'Reservation Visa Country : ' + (self.country_id.name if self.country_id else '') + ' ' + \
                        'Consulate : ' + (rec.immigration_consulate if rec.immigration_consulate else '') + ' ' + \
                        'Journey Date : ' + str(rec.departure_date if rec.departure_date else '')
        return desc_text

    def action_create_invoice(self, data, context):
        invoice_id = False
        book_obj = self.env['tt.reservation.visa'].search([('name', '=', data['order_number'])])
        if not invoice_id:
            invoice_id = self.env['tt.agent.invoice'].create({
                'booker_id': book_obj.booker_id.id,
                'agent_id': book_obj.agent_id.id,
                'customer_parent_id': book_obj.customer_parent_id.id,
                'customer_parent_type_id': book_obj.customer_parent_type_id.id,
                'state': 'confirm',
                'confirmed_uid': book_obj.confirmed_uid.id,
                'confirmed_date': datetime.now()
            })

        inv_line_obj = self.env['tt.agent.invoice.line'].create({
            'res_model_resv': book_obj._name,
            'res_id_resv': book_obj.id,
            'invoice_id': invoice_id.id,
            'reference': book_obj.name,
            'desc': book_obj.get_visa_summary(),
            'admin_fee': self.payment_acquirer_number_id.fee_amount
        })

        invoice_line_id = inv_line_obj.id

        discount = 0

        for psg in book_obj.passenger_ids:
            desc_text = (psg.first_name if psg.first_name else '') + ' ' + \
                        (psg.last_name if psg.last_name else '') + ', ' + \
                        (psg.title if psg.title else '') + \
                        ' (' + (psg.passenger_type if psg.passenger_type else '') + ') ' + \
                        (psg.pricelist_id.entry_type.capitalize() if psg.pricelist_id.entry_type else '') + ' ' + \
                        (psg.pricelist_id.visa_type.capitalize() if psg.pricelist_id.visa_type else '') + ' ' + \
                        (psg.pricelist_id.process_type.capitalize() if psg.pricelist_id.process_type else '') + \
                        ' (' + str(psg.pricelist_id.duration if psg.pricelist_id.duration else '-') + ' days)'
            price = 0
            for srvc in psg.cost_service_charge_ids:
                if srvc.charge_type not in ['RAC', 'DISC']:
                    price += srvc.amount
                elif srvc.charge_type == 'DISC':
                    discount += srvc.amount
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

        inv_line_obj.discount = abs(discount)

        payref_id_list = []
        if data.get('payment_ref_attachment'):
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
            'agent_id': book_obj.agent_id.id,
            'real_total_amount': invoice_id.grand_total,
            'customer_parent_id': book_obj.customer_parent_id.id
        }

        if payref_id_list:
            payment_vals.update({
                'reference': data.get('payment_reference', ''),
                'payment_image_ids': [(6, 0, payref_id_list)]
            })
        if 'seq_id' in data:
            if data['seq_id']:
                payment_vals.update({
                    'acquirer_id': self.env['payment.check_provider_acquirer'].search([('seq_id', '=', data['seq_id'])], limit=1).id,
                })

        ##membuat payment dalam draft
        payment_obj = self.env['tt.payment'].create(payment_vals)

        self.env['tt.payment.invoice.rel'].create({
            'invoice_id': invoice_id.id,
            'payment_id': payment_obj.id,
            'pay_amount': invoice_id.grand_total
        })

    def action_issued_visa_api(self, data, context):
        res = super(ReservationVisa, self).action_issued_visa_api(data, context)
        self.action_create_invoice(data, context)
        return res
