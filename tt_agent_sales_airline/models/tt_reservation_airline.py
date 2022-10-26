from odoo import models,api,fields
from datetime import datetime, timedelta
import base64


class ReservationAirline(models.Model):

    _inherit = 'tt.reservation.airline'

    # invoice_line_ids = fields.One2many('tt.agent.invoice.line.','res_id_resv', 'Invoice',
    #                               domain="[('res_model_resv','=','self._name'),('res_id_resv','=','self.id')]")

    state_invoice = fields.Selection([('wait', 'Waiting'), ('partial', 'Partial'), ('full', 'Full')],
                                     'Invoice Status', help="Agent Invoice status", default='wait',
                                     readonly=True, compute='set_agent_invoice_state')

    invoice_line_ids = fields.One2many('tt.agent.invoice.line', 'res_id_resv', 'Invoice',
                                       domain=[('res_model_resv','=', 'tt.reservation.airline')])

    ho_invoice_line_ids = fields.One2many('tt.ho.invoice.line', 'res_id_resv', 'HO Invoice',
                                       domain=[('res_model_resv','=', 'tt.reservation.airline')])


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
        for journey in self.journey_ids:
            tmp += '%s - %s\n' % (journey.departure_date[:16], journey.arrival_date[:16])
            for rec in journey.segment_ids:
                tmp += '%s(%s) - %s(%s), ' % (rec.origin_id.city, rec.origin_id.code, rec.destination_id.city, rec.destination_id.code)
                tmp += '%s - %s\n' % (rec.departure_date[:16], rec.arrival_date[:16])
        return tmp

    def action_create_invoice(self, data, payment_method):
        invoice_id = False
        ho_invoice_id = False

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
        is_use_credit_limit = False
        if not ho_invoice_id:
            if payment_method == 'balance':
                state = 'paid'
                is_use_credit_limit = False
            else:
                state = 'confirm'
                is_use_credit_limit = True
            ho_invoice_id = self.env['tt.ho.invoice'].create({
                'booker_id': self.booker_id.id,
                'agent_id': self.agent_id.id,
                'customer_parent_id': self.customer_parent_id.id,
                'customer_parent_type_id': self.customer_parent_type_id.id,
                'state': state,
                'confirmed_uid': data['co_uid'],
                'confirmed_date': datetime.now(),
                'is_use_credit_limit': is_use_credit_limit
            })

        inv_line_obj = self.env['tt.agent.invoice.line'].create({
            'res_model_resv': self._name,
            'res_id_resv': self.id,
            'invoice_id': invoice_id.id,
            'reference': self.name,
            'desc': self.get_segment_description(),
            'admin_fee': self.payment_acquirer_number_id.fee_amount
        })

        ho_inv_line_obj = self.env['tt.ho.invoice.line'].create({
            'res_model_resv': self._name,
            'res_id_resv': self.id,
            'invoice_id': ho_invoice_id.id,
            'reference': self.name,
            'desc': self.get_segment_description(),
            'admin_fee': 0
        })

        invoice_line_id = inv_line_obj.id
        ho_invoice_line_id = ho_inv_line_obj.id

        #untuk harga fare per passenger
        discount = 0

        for psg in self.passenger_ids:
            desc_text = '%s, %s' % (' '.join((psg.first_name or '', psg.last_name or '')), psg.title or '')
            price_unit = 0
            for cost_charge in psg.cost_service_charge_ids:
                if cost_charge.charge_type not in ['RAC', 'DISC']:
                    price_unit += cost_charge.amount
                elif cost_charge.charge_type == 'DISC':
                    discount += cost_charge.amount
            for channel_charge in psg.channel_service_charge_ids.filtered(lambda x: 'rs' not in x.charge_code.split('.')):
                price_unit += channel_charge.amount

            inv_line_obj.write({
                'invoice_line_detail_ids': [(0,0,{
                    'desc': desc_text,
                    'price_unit': price_unit,
                    'quantity': 1,
                    'invoice_line_id': invoice_line_id,
                })]
            })
        total_price_unit = 0
        ## HO INVOICE
        for psg in self.passenger_ids:
            desc_text = '%s, %s' % (' '.join((psg.first_name or '', psg.last_name or '')), psg.title or '')
            price_unit = 0
            commission_list = {}
            for cost_charge in psg.cost_service_charge_ids:
                if cost_charge.charge_type not in ['DISC','RAC']:
                    price_unit += cost_charge.amount
                elif cost_charge.charge_type == 'DISC':
                    discount += cost_charge.amount
                elif cost_charge.charge_type == 'RAC':
                    if is_use_credit_limit:
                        if not cost_charge.commission_agent_id:
                            agent_id = self.agent_id.id
                        else:
                            agent_id = cost_charge.commission_agent_id.id
                        if agent_id not in commission_list:
                            commission_list[agent_id] = 0
                        commission_list[agent_id] += cost_charge.amount * -1
                    else:
                        price_unit += cost_charge.amount
            total_price_unit += price_unit
            for channel_charge in psg.channel_service_charge_ids.filtered(lambda x: 'rs' not in x.charge_code.split('.')):
                price_unit += channel_charge.amount
            ### FARE
            self.env['tt.ho.invoice.line.detail'].create({
                'desc': desc_text,
                'price_unit': price_unit,
                'quantity': 1,
                'invoice_line_id': ho_invoice_line_id,
            })
            ## RAC
            for rec in commission_list:
                self.env['tt.ho.invoice.line.detail'].create({
                    'desc': "Commission",
                    'price_unit': commission_list[rec],
                    'quantity': 1,
                    'invoice_line_id': ho_invoice_line_id,
                    'commission_agent_id': rec,
                    'is_commission': True
                })


        inv_line_obj.discount = abs(discount)
        # ho_inv_line_obj.discount = abs(discount)

        payref_id_list = []
        ho_payref_id_list = []
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

            ## HO
            temp_filename = '%s_HO_Payment_Ref_%s.%s' % (str(idx), ho_invoice_id.name, file_ext)
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
            ho_payref_id_list.append(upc_id.id)

        payment_vals = {
            'agent_id': self.agent_id.id,
            'acquirer_id': data['acquirer_id'],
            'real_total_amount': invoice_id.grand_total,
            'customer_parent_id': data['customer_parent_id'],
            'confirm_uid': data['co_uid'],
            'confirm_date': datetime.now()
        }

        ## payment HO
        acq_obj = False
        if payment_method != 'credit_limit':
            acq_objs = self.agent_id.payment_acquirer_ids
            for payment_acq in acq_objs:
                if payment_acq.name == 'Cash':
                    acq_obj = payment_acq.id
                    break

        ho_payment_vals = {
            'agent_id': self.agent_id.id,
            'acquirer_id': acq_obj,
            'real_total_amount': ho_invoice_id.grand_total,
            'confirm_uid': data['co_uid'],
            'confirm_date': datetime.now()
        }
        ## payment HO


        if payref_id_list:
            payment_vals.update({
                'reference': data.get('payment_reference', ''),
                'payment_image_ids': [(6, 0, payref_id_list)]
            })

        if ho_payref_id_list:
            ho_payment_vals.update({
                'reference': data.get('payment_reference', ''),
                'payment_image_ids': [(6, 0, ho_payref_id_list)]
            })

        ##membuat payment dalam draft
        payment_obj = self.env['tt.payment'].create(payment_vals)
        ho_payment_obj = self.env['tt.payment'].create(ho_payment_vals)

        self.env['tt.payment.invoice.rel'].create({
            'invoice_id': invoice_id.id,
            'payment_id': payment_obj.id,
            'pay_amount': invoice_id.grand_total
        })

        self.env['tt.payment.invoice.rel'].create({
            'ho_invoice_id': ho_invoice_id.id,
            'payment_id': ho_payment_obj.id,
            'pay_amount': ho_invoice_id.grand_total
        })

        self.write({
            'is_invoice_created': True
        })


    # # ## CREATED by Samvi 2018/07/24
    # @api.multi
    # def action_check_provider_state(self, api_context=None):
    #     res = super(ReservationTrain, self).action_check_provider_state(api_context)
    #     if self.provider_booking_ids:
    #         # todo membuat mekanisme untuk partial issued seperti apa
    #         # fixme sementara create agent invoice berdasarkan bookingan
    #         if any(rec.state == 'issued' for rec in self.provider_booking_ids):
    #             # if self.agent_id.agent_type_id.id in [self.env.ref('tt_base_rodex.agent_type_citra').id,
    #             #                                       self.env.ref('tt_base_rodex.agent_type_japro').id]:
    #             self.action_create_invoice()
    #
    #     return res

    def action_reverse_airline(self,context):
        super(ReservationAirline, self).action_reverse_airline(context)
        for rec in self.invoice_line_ids:
            try:
                rec.invoice_id.action_cancel_invoice()
            except Exception as e:
                print(str(e))

    def action_issued_airline(self,data):
        super(ReservationAirline, self).action_issued_airline(data)
        if not self.is_invoice_created:
            ## check ledger bayar pakai balance / credit limit
            payment_method_to_ho =  ''
            for ledger_obj in self.ledger_ids:
                if ledger_obj.transaction_type == 2: ## order
                    if ledger_obj.source_of_funds_type in ['balance', 'credit_limit']:
                        payment_method_to_ho = ledger_obj.source_of_funds_type
                        break
                pass
            self.action_create_invoice(data, payment_method_to_ho)

    def update_pnr_provider_airline_api(self, req, context):
        resp = super(ReservationAirline, self).update_pnr_provider_airline_api(req, context)
        updated_obj = self.browse(resp['response']['book_id'])
        if updated_obj.is_invoice_created:
            for inv_obj in updated_obj.invoice_line_ids:
                inv_obj.pnr = updated_obj.pnr
        return resp