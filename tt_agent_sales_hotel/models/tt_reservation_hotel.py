from odoo import models,api,fields
from datetime import datetime, timedelta
import base64


class ReservationHotel(models.Model):
    _inherit = 'tt.reservation.hotel'

    invoice_line_ids = fields.One2many('tt.agent.invoice.line', 'res_id_resv', 'Invoice', domain=[('res_model_resv','=', 'tt.reservation.hotel')])
    state_invoice = fields.Selection([('wait', 'Waiting'), ('partial', 'Partial'), ('full', 'Full')],
                                     'Invoice Status', help="Agent Invoice status", default='wait',
                                     readonly=True, compute='set_agent_invoice_state')

    ho_invoice_line_ids = fields.One2many('tt.ho.invoice.line', 'res_id_resv', 'HO Invoice',
                                          domain=[('res_model_resv', '=', 'tt.reservation.hotel')])

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
        tmp = 'Hotel : %s\n' % (self.hotel_name, )
        for idx, rec in enumerate(self.room_detail_ids):
            tmp += 'Room %s: %s %s(%s),\n' % (str(idx+1), rec.room_name, rec.room_type, rec.meal_type if rec.meal_type else 'Room Only')
        tmp += 'Date  : %s - %s\n' % (str(self.checkin_date)[:10], str(self.checkout_date)[:10])
        tmp += 'Guest :\n'
        for idx, guest in enumerate(self.passenger_ids):
            tmp += str(idx+1) + '. ' + guest['customer_id'].name + '\n'
        tmp += 'Special Request: %s\n'  % (self.special_req or '-', )
        return tmp

    def action_create_invoice(self, data, payment_method_to_ho):
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

        inv_line_obj = self.env['tt.agent.invoice.line'].create({
            'res_model_resv': self._name,
            'res_id_resv': self.id,
            'invoice_id': invoice_id.id,
            'reference': self.name,
            'desc': self.get_segment_description(),
            'admin_fee': self.payment_acquirer_number_id.fee_amount,
            'discount': self.total_discount,
        })

        ### HO ####
        is_use_credit_limit = False
        if not ho_invoice_id:
            if payment_method_to_ho == 'balance':
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

        ho_inv_line_obj = self.env['tt.ho.invoice.line'].create({
            'res_model_resv': self._name,
            'res_id_resv': self.id,
            'invoice_id': ho_invoice_id.id,
            'reference': self.name,
            'desc': self.get_segment_description(),
            'admin_fee': 0,
            'discount': self.total_discount,
        })

        ho_invoice_line_id = ho_inv_line_obj.id

        for room_obj in self.room_detail_ids:
            meal = room_obj.meal_type or 'Room Only'
            self.env['tt.agent.invoice.line.detail'].create({
                'desc': room_obj.room_name + ' (' + meal + ') ',
                'invoice_line_id': inv_line_obj.id,
                'price_unit': room_obj.sale_price,
                'quantity': 1,
            })

        discount = 0
        for price_obj in self.sale_service_charge_ids:
            if price_obj.charge_type == 'DISC':
                discount += price_obj.total

        ## HO
        total_price = 0
        commission_list = {}
        for idx, room_obj in enumerate(self.room_detail_ids):
            meal = room_obj.meal_type or 'Room Only'
            price_unit = room_obj.sale_price
            for price_obj in self.sale_service_charge_ids:
                if price_obj.charge_type == 'RAC':
                    if is_use_credit_limit:
                        if not price_obj.commission_agent_id:
                            agent_id = self.agent_id.id
                        else:
                            agent_id = price_obj.commission_agent_id.id
                        if agent_id not in commission_list:
                            commission_list[agent_id] = 0
                        commission_list[agent_id] += price_obj.amount * -1
                    elif price_obj.commission_agent_id != self.env.ref('tt_base.rodex_ho'):
                        price_unit += price_obj.amount
            ## FARE
            self.env['tt.ho.invoice.line.detail'].create({
                'desc': room_obj.room_name + ' (' + meal + ') ',
                'invoice_line_id': ho_inv_line_obj.id,
                'price_unit': price_unit,
                'quantity': 1,
            })
            total_price += price_unit

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
        if self.is_using_point_reward and is_use_credit_limit:
            ## CREATE LEDGER UNTUK POTONG POINT REWARD
            total_use_point = 0
            total_price -= abs(discount)
            payment_method = self.env['payment.acquirer'].search([('seq_id', '=', self.payment_method)])
            if payment_method.type == 'cash':
                point_reward = self.agent_id.actual_point_reward
                if point_reward > total_price:
                    total_use_point = total_price - 1
                else:
                    total_use_point = point_reward
            elif payment_method.type == 'payment_gateway':
                point_reward = self.agent_id.actual_point_reward
                if point_reward - payment_method.minimum_amount > total_price:
                    total_use_point = total_price - payment_method.minimum_amount
                else:
                    total_use_point = point_reward

            if total_use_point:
                self.env['tt.ho.invoice.line.detail'].create({
                    'desc': "Use Point Reward",
                    'price_unit': total_use_point,
                    'quantity': 1,
                    'invoice_line_id': ho_invoice_line_id,
                    'commission_agent_id': self.agent_id.id,
                    'is_point_reward': True
                })
                self.use_point_reward(self, True, total_use_point, self.issued_uid)

        inv_line_obj.discount = abs(discount)
        ho_inv_line_obj.discount = abs(discount)

        upsell_sc = 0
        for psg in self.passenger_ids:
            upsell_sc += sum(channel_charge.amount for channel_charge in psg.channel_service_charge_ids)
        inv_line_obj.invoice_line_detail_ids[0]['price_unit'] += upsell_sc

        ##membuat payment dalam draft
        if data.get('acquirer_id'):
            # B2B
            if isinstance(data['acquirer_id'], dict):
                acquirer_obj = self.env['payment.acquirer'].search([('seq_id', '=', data['acquirer_id'].get('seq_id') or data['acquirer_id'].get('acquirer_seq_id') )], limit=1)
            else:
                acquirer_obj = self.env['payment.acquirer'].browse(data['acquirer_id'])
        else:
            # B2C
            acquirer_obj = self.payment_acquirer_number_id.payment_acquirer_id

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
            'acquirer_id': acquirer_obj.id,
            'real_total_amount': invoice_id.grand_total,
            'customer_parent_id': self.customer_parent_id.id,
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

        ## payment HO
        acq_obj = False
        if payment_method_to_ho != 'credit_limit':
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

        if ho_payref_id_list:
            ho_payment_vals.update({
                'reference': data.get('payment_reference', ''),
                'payment_image_ids': [(6, 0, ho_payref_id_list)]
            })

        ho_payment_obj = self.env['tt.payment'].create(ho_payment_vals)

        self.env['tt.payment.invoice.rel'].create({
            'ho_invoice_id': ho_invoice_id.id,
            'payment_id': ho_payment_obj.id,
            'pay_amount': ho_invoice_id.grand_total
        })
        ## payment HO

        self.write({
            'is_invoice_created': True
        })

    def action_done(self, issued_response={}):
        a = super(ReservationHotel, self).action_done(issued_response)
        # Calc PNR untuk agent_invoice + agent_invoice_line
        for rec in self.invoice_line_ids:
            rec._compute_invoice_line_pnr()
            rec.invoice_id._compute_invoice_pnr()
        return a

    def action_issued(self, data, kwargs=False):
        super(ReservationHotel, self).action_issued(data, kwargs)
        # if not self.is_invoice_created:
        ## check ledger bayar pakai balance / credit limit
        payment_method_to_ho = ''
        for ledger_obj in self.ledger_ids:
            if ledger_obj.transaction_type == 2:  ## order
                if ledger_obj.source_of_funds_type in ['balance', 'credit_limit']:
                    payment_method_to_ho = ledger_obj.source_of_funds_type
                    break
            pass
        self.action_create_invoice(data, payment_method_to_ho)
