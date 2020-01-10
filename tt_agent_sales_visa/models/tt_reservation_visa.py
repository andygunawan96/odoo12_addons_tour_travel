from odoo import models, fields, api, _
from datetime import datetime


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
                'confirmed_uid': context['co_uid'],
                'confirmed_date': datetime.now()
            })

        inv_line_obj = self.env['tt.agent.invoice.line'].create({
            'res_model_resv': book_obj._name,
            'res_id_resv': book_obj.id,
            'invoice_id': invoice_id.id,
            'desc': book_obj.get_visa_summary()
        })

        invoice_line_id = inv_line_obj.id

        for psg in book_obj.passenger_ids:
            desc_text = psg.first_name + ' ' + psg.last_name + ', ' + psg.title + ' (' + psg.passenger_type + ') ' + \
                        psg.pricelist_id.entry_type.capitalize() + ' ' + psg.pricelist_id.visa_type.capitalize() + ' ' \
                        + psg.pricelist_id.process_type.capitalize() + ' (' + str(psg.pricelist_id.duration) + ' days)'
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
            'real_total_amount': inv_line_obj.total_after_tax,
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
            'pay_amount': inv_line_obj.total_after_tax,
        })

    def get_visa_summary_expenses(self, data):
        desc_text = ''
        for rec in self:
            desc_text += 'Expenses - Reservation Visa Order Number : ' + self.name + '\n'
            desc_text += 'Date : ' + str(data[0][0]['create_date'].strftime('%d-%m-%Y'))
        return desc_text

    def action_create_invoice_expenses(self, data):
        invoice_id = False
        # book_obj = self.env['tt.reservation.visa'].search([('name', '=', data['order_number'])])
        if not invoice_id:
            invoice_id = self.env['tt.agent.invoice'].create({
                'booker_id': self.booker_id.id,
                'agent_id': self.agent_id.id,
                'customer_parent_id': self.customer_parent_id.id,
                'customer_parent_type_id': self.customer_parent_type_id.id,
                'state': 'confirm',
                'confirmed_uid': self.env.user.id,  # context['co_uid']
                'confirmed_date': datetime.now()
            })

        inv_line_obj = self.env['tt.agent.invoice.line'].create({
            'res_model_resv': self._name,
            'res_id_resv': self.id,
            'invoice_id': invoice_id.id,
            'desc': self.get_visa_summary_expenses(data)
        })

        invoice_line_id = inv_line_obj.id

        for data1 in data:
            for data2 in data1:
                vendor_id = self.env['tt.reservation.visa.vendor.lines'].search([('id', '=', data2['id'])])
                desc_text = ''
                desc_text += vendor_id.vendor_id.name if vendor_id.vendor_id.name else ' '
                desc_text += ' - '
                desc_text += vendor_id.reference_number if vendor_id.reference_number else ' '

                price = vendor_id.amount

                inv_line_obj.write({
                    'invoice_line_detail_ids': [(0, 0, {
                        'desc': desc_text,
                        'price_unit': price,
                        'quantity': 1,
                        'invoice_line_id': invoice_line_id,
                    })]
                })
                vendor_id.is_invoice_created = True

        # for vendor in self.provider_booking_ids.vendor_ids:
        #     if not vendor.is_invoice_created:
        #         if vendor.amount - vendor.nta_amount != 0:
        #             desc_text = ''
        #             desc_text += vendor.vendor_id.name if vendor.vendor_id.name else ' '
        #             desc_text += ' - '
        #             desc_text += vendor.reference_number if vendor.reference_number else ' '
        #
        #             price = vendor.amount
        #
        #             inv_line_obj.write({
        #                 'invoice_line_detail_ids': [(0, 0, {
        #                     'desc': desc_text,
        #                     'price_unit': price,
        #                     'quantity': 1,
        #                     'invoice_line_id': invoice_line_id,
        #                 })]
        #             })
        #             vendor.is_invoice_created = True
        #             print(price)

        ##membuat payment dalam draft
        payment_obj = self.env['tt.payment'].create({
            'agent_id': self.agent_id.id,
            'real_total_amount': inv_line_obj.total_after_tax,
            'customer_parent_id': self.customer_parent_id.id
        })
        if self.payment_method:
            payment_obj.update({
                'acquirer_id': self.env['payment.acquirer'].search([('seq_id', '=', self.payment_method)], limit=1).id,
            })

        self.env['tt.payment.invoice.rel'].create({
            'invoice_id': invoice_id.id,
            'payment_id': payment_obj.id,
            'pay_amount': inv_line_obj.total_after_tax,
        })

            # if 'seq_id' in data:
            #     if data['seq_id']:
            #         payment_obj.update({
            #             'acquirer_id': self.env['payment.acquirer'].search([('seq_id', '=', data['seq_id'])],limit=1).id,
            #         })

    # def action_issued_visa(self, api_context=None):
    #     super(ReservationVisa, self).action_issued_visa(api_context)
    #     self.action_create_invoice()

    def action_issued_visa_api(self, data, context):
        res = super(ReservationVisa, self).action_issued_visa_api(data, context)
        self.action_create_invoice(data, context)
        return res

    def action_calc_expenses_visa(self):
        super(ReservationVisa, self).action_calc_expenses_visa()
        datas = {}
        for provider in self.provider_booking_ids:
            for vendor in provider.vendor_ids:
                if not vendor.is_invoice_created:
                    create_date = vendor.create_date
                    if not datas.get(create_date.strftime('%d-%m-%Y')):
                        datas[create_date.strftime('%d-%m-%Y')] = []
                    datas[create_date.strftime('%d-%m-%Y')].append(vendor.read())
        for data in datas:
            self.action_create_invoice_expenses(datas[data])
