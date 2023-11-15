from odoo import models, fields, api, _
from datetime import datetime, timedelta
import base64


class ReservationOffline(models.Model):

    _inherit = 'tt.reservation.offline'

    state_invoice = fields.Selection([('wait', 'Waiting'), ('partial', 'Partial'), ('full', 'Full')],
                                     'Invoice Status', help="Agent Invoice status", default='wait',
                                     readonly=True)  # , compute='set_agent_invoice_state'

    invoice_line_ids = fields.One2many('tt.agent.invoice.line', 'res_id_resv', 'Invoice', domain=[('res_model_resv','=', 'tt.reservation.offline')])

    ho_invoice_line_ids = fields.One2many('tt.ho.invoice.line', 'res_id_resv', 'HO Invoice',
                                          domain=[('res_model_resv', '=', 'tt.reservation.offline')])

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

    def action_create_invoice(self, payment_method_to_ho):
        invoice_id = False
        ho_invoice_id = False

        temp_ho_obj = self.agent_id.ho_id
        is_use_ext_credit_limit = self.customer_parent_id.check_use_ext_credit_limit() and self.customer_parent_type_id.id in [
            self.env.ref('tt_base.customer_type_cor').id, self.env.ref('tt_base.customer_type_por').id]
        if is_use_ext_credit_limit:
            state = 'paid'
            add_info = self.customer_parent_id.get_external_payment_acq_seq_id()
        else:
            state = 'confirm'
            add_info = ''
        if not invoice_id:
            invoice_id = self.env['tt.agent.invoice'].create({
                'booker_id': self.booker_id.id,
                'ho_id': temp_ho_obj and temp_ho_obj.id or False,
                'agent_id': self.agent_id.id,
                'state': state,
                'additional_information': add_info,
                'customer_parent_id': self.customer_parent_id.id,
                'customer_parent_type_id': self.customer_parent_type_id.id,
                'currency_id': temp_ho_obj.currency_id.id,
                'confirmed_date': datetime.now()
            })
            if self.issued_uid.agent_id.id == self.agent_id.id:
                invoice_id.write({
                    'confirmed_uid': self.issued_uid.id
                })
            else:
                invoice_id.write({
                    'confirmed_uid': self.confirm_uid.id
                })

        discount = 0

        line_desc = ''
        if self.provider_type_id_name != 'hotel':
            for line in self.line_ids:
                line_desc += line.get_line_description()
        else:
            line_desc += 'Description : ' + (self.description if self.description else '')

        inv_line_obj = self.env['tt.agent.invoice.line'].create({
            'res_model_resv': self._name,
            'res_id_resv': self.id,
            'ho_id': temp_ho_obj and temp_ho_obj.id or False,
            'invoice_id': invoice_id.id,
            'reference': self.name,
            'desc': line_desc,
            'admin_fee': self.payment_acquirer_number_id.fee_amount
        })

        model_type_id = self.env['tt.provider.type'].search([('code', '=', self.offline_provider_type)], limit=1)
        inv_line_obj.write({
            'model_type_id': model_type_id.id
        })

        invoice_line_id = inv_line_obj.id

        ### HO ####
        is_use_credit_limit = False
        if not ho_invoice_id:
            if payment_method_to_ho == 'credit_limit':
                state = 'confirm'
                is_use_credit_limit = True
            else:
                state = 'paid'
                is_use_credit_limit = False
            ho_invoice_id = self.env['tt.ho.invoice'].create({
                'booker_id': self.booker_id.id,
                'ho_id': temp_ho_obj and temp_ho_obj.id or False,
                'agent_id': self.agent_id.id,
                'customer_parent_id': self.customer_parent_id.id,
                'customer_parent_type_id': self.customer_parent_type_id.id,
                'currency_id': temp_ho_obj.currency_id.id,
                'state': state,
                'confirmed_date': datetime.now(),
                'is_use_credit_limit': is_use_credit_limit
            })

            if self.issued_uid.agent_id.id == self.agent_id.id:
                ho_invoice_id.write({
                    'confirmed_uid': self.issued_uid.id
                })
            else:
                ho_invoice_id.write({
                    'confirmed_uid': self.confirm_uid.id
                })

        ho_inv_line_obj = self.env['tt.ho.invoice.line'].create({
            'res_model_resv': self._name,
            'res_id_resv': self.id,
            'ho_id': temp_ho_obj and temp_ho_obj.id or False,
            'invoice_id': ho_invoice_id.id,
            'reference': self.name,
            'desc': line_desc,
            'admin_fee': 0
        })

        model_type_id = self.env['tt.provider.type'].search([('code', '=', self.offline_provider_type)], limit=1)
        ho_inv_line_obj.write({
            'model_type_id': model_type_id.id
        })

        ho_invoice_line_id = ho_inv_line_obj.id

        # get charge code name

        # get prices

        if self.provider_type_id_name == 'hotel':
            qty = 0
            for line in self.line_ids:
                qty += line.obj_qty
            for line in self.line_ids:
                desc_text = line.get_line_hotel_description()
                inv_line_obj.write({
                    'invoice_line_detail_ids': [(0, 0, {
                        'desc': desc_text,
                        'price_unit': self.total / qty,
                        'quantity': qty,
                        'invoice_line_id': invoice_line_id,
                    })]
                })
        else:
            for psg in self.passenger_ids:
                desc_text = psg.customer_id.name
                price_unit = 0
                for srvc in self.sale_service_charge_ids:
                    if srvc.charge_type not in ['RAC', 'DISC']:
                        price_unit += srvc.amount
                    elif srvc.charge_type == 'DISC':
                        discount += srvc.amount
                inv_line_obj.write({
                    'invoice_line_detail_ids': [(0, 0, {
                        'desc': desc_text,
                        'price_unit': self.total / len(self.passenger_ids),
                        'quantity': 1,
                        'invoice_line_id': invoice_line_id,
                    })]
                })

        ## HO INVOICE ABAIKAN SERVICE CHARGES DISC KARENA DISCOUNT DARI HO TIDAK MEMPENGARUHI NTA##
        total_price = 0
        commission_list = {}
        if self.provider_type_id_name == 'hotel':
            qty = 0
            for line in self.line_ids:
                qty += line.obj_qty
            for line in self.line_ids:
                desc_text = line.get_line_hotel_description()
                ### FARE
                self.env['tt.ho.invoice.line.detail'].create({
                    'desc': desc_text,
                    'price_unit': self.total/qty,
                    'quantity': qty,
                    'invoice_line_id': ho_invoice_line_id,
                    'ho_id': temp_ho_obj and temp_ho_obj.id or False,
                    'commission_agent_id': self.agent_id.id
                })
                total_price += self.total/qty
            ## RAC
            price_unit = 0
            for price_obj in self.sale_service_charge_ids:
                if price_obj.charge_type == 'RAC':
                    if is_use_credit_limit:
                        if not price_obj.commission_agent_id:
                            agent_id = self.agent_id.id
                        else:
                            agent_id = price_obj.commission_agent_id.id
                        if self.agent_id.id != agent_id:
                            if agent_id not in commission_list:
                                commission_list[agent_id] = 0
                            commission_list[agent_id] += price_obj.amount * -1
                        else:
                            price_unit += price_obj.amount
                    elif price_obj.commission_agent_id != (temp_ho_obj and temp_ho_obj or False):
                        price_unit += price_obj.amount

        else:
            for psg in self.passenger_ids:
                desc_text = psg.customer_id.name
                price_unit = 0
                for srvc in self.sale_service_charge_ids:
                    if srvc.charge_type not in ['RAC', 'DISC'] and srvc.charge_code != 'csc':
                        price_unit += srvc.amount
                    elif srvc.charge_type == 'RAC' and srvc.charge_code != 'csc':
                        ho_obj = self.agent_id.ho_id
                        if is_use_credit_limit:
                            if not srvc.commission_agent_id:
                                agent_id = self.agent_id.id
                            else:
                                agent_id = srvc.commission_agent_id.id
                            if self.agent_id.id != agent_id:
                                if agent_id not in commission_list:
                                    commission_list[agent_id] = 0
                                commission_list[agent_id] += srvc.amount * -1
                            else:
                                price_unit += srvc.amount
                        elif not srvc.commission_agent_id.is_ho_agent:
                            price_unit += srvc.amount
                ### FARE
                self.env['tt.ho.invoice.line.detail'].create({
                    'desc': desc_text,
                    'price_unit': self.total / len(self.passenger_ids),
                    'quantity': 1,
                    'invoice_line_id': ho_invoice_line_id,
                    'ho_id': temp_ho_obj and temp_ho_obj.id or False,
                    'commission_agent_id': self.agent_id.id
                })
                total_price += total_price

        for rec in commission_list:
            self.env['tt.ho.invoice.line.detail'].create({
                'desc': "Commission",
                'price_unit': commission_list[rec],
                'quantity': 1,
                'invoice_line_id': ho_invoice_line_id,
                'ho_id': temp_ho_obj and temp_ho_obj.id or False,
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
                    'ho_id': temp_ho_obj and temp_ho_obj.id or False,
                    'commission_agent_id': self.agent_id.id,
                    'is_point_reward': True
                })
                self.env['tt.ledger'].use_point_reward(self, True, total_use_point, self.issued_uid.id)

        if not is_use_ext_credit_limit:
            ##membuat payment dalam draft
            payment_obj = self.env['tt.payment'].create({
                'ho_id': temp_ho_obj and temp_ho_obj.id or False,
                'agent_id': self.agent_id.id,
                'currency_id': temp_ho_obj.currency_id.id,
                'real_total_amount': invoice_id.grand_total,
                'customer_parent_id': self.customer_parent_id.id,
                'confirm_uid': invoice_id.confirmed_uid.id,
                'confirm_date': datetime.now()
            })
            if self.acquirer_id:
                payment_obj.update({
                    'acquirer_id': self.acquirer_id.id,
                })

            self.env['tt.payment.invoice.rel'].create({
                'invoice_id': invoice_id.id,
                'payment_id': payment_obj.id,
                'pay_amount': invoice_id.grand_total
            })

        ## payment HO
        acq_obj = False
        if payment_method_to_ho == 'credit_limit':
            ho_payment_vals = {
                'ho_id': temp_ho_obj and temp_ho_obj.id or False,
                'agent_id': self.agent_id.id,
                'currency_id': temp_ho_obj.currency_id.id,
                'acquirer_id': acq_obj,
                'real_total_amount': ho_invoice_id.grand_total,
                'confirm_date': datetime.now()
            }
            if self.issued_uid.agent_id.id == self.agent_id.id:
                ho_payment_vals.update({
                    'confirmed_uid': self.issued_uid.id
                })
            else:
                ho_payment_vals.update({
                    'confirmed_uid': self.confirm_uid.id
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

    def action_done(self):
        super(ReservationOffline, self).action_done()
        # if not self.is_invoice_created: ## untuk offline tidak di check karena state sering maju mundur dari done ke validate
        ## check ledger bayar pakai balance / credit limit
        self.action_create_invoice(self.payment_method_to_ho)

    def check_approve_refund_eligibility(self):
        if self.customer_parent_id.customer_parent_type_id.id in [self.env.ref('tt_base.customer_type_cor').id, self.env.ref('tt_base.customer_type_por').id] and self.payment_method == self.customer_parent_id.seq_id:
            if all(rec.invoice_id.state == 'paid' for rec in self.invoice_line_ids):
                return True
            else:
                return False
        else:
            return True
