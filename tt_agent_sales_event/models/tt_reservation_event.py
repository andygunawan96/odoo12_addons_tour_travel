from odoo import models,api,fields
from datetime import datetime, timedelta
import base64


class ReservationEvent(models.Model):
    _inherit = 'tt.reservation.event'

    invoice_line_ids = fields.One2many('tt.agent.invoice.line', 'res_id_resv', 'Invoice', domain=[('res_model_resv','=', 'tt.reservation.event')])
    state_invoice = fields.Selection([('wait', 'Waiting'), ('partial', 'Partial'), ('full', 'Full')],
                                     'Invoice Status', help="Agent Invoice status", default='wait',
                                     readonly=True, compute='set_agent_invoice_state')

    ho_invoice_line_ids = fields.One2many('tt.ho.invoice.line', 'res_id_resv', 'HO Invoice',
                                          domain=[('res_model_resv', '=', 'tt.reservation.event')])

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

    def action_create_invoice(self, data, payment_method_to_ho):
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
                'customer_parent_id': self.customer_parent_id.id,
                'customer_parent_type_id': self.customer_parent_type_id.id,
                'currency_id': temp_ho_obj.currency_id.id,
                'state': state,
                'additional_information': add_info,
                'confirmed_uid': data['co_uid'],
                'confirmed_date': datetime.now()
            })

        inv_line_obj = self.env['tt.agent.invoice.line'].create({
            'res_model_resv': self._name,
            'res_id_resv': self.id,
            'ho_id': temp_ho_obj and temp_ho_obj.id or False,
            'invoice_id': invoice_id.id,
            'reference': self.name,
            'desc': self.get_segment_description(),
            'admin_fee': self.payment_acquirer_number_id.fee_amount,
            'customer_parent_id': self.customer_parent_id.id
        })

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
                'confirmed_uid': data['co_uid'],
                'confirmed_date': datetime.now(),
                'is_use_credit_limit': is_use_credit_limit
            })

        ho_inv_line_obj = self.env['tt.ho.invoice.line'].create({
            'res_model_resv': self._name,
            'res_id_resv': self.id,
            'ho_id': temp_ho_obj and temp_ho_obj.id or False,
            'invoice_id': ho_invoice_id.id,
            'reference': self.name,
            'desc': self.get_segment_description(),
            'admin_fee': 0
        })

        ho_invoice_line_id = ho_inv_line_obj.id

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

        ## HO INVOICE ABAIKAN SERVICE CHARGES DISC KARENA DISCOUNT DARI HO TIDAK MEMPENGARUHI NTA##
        total_price = 0
        commission_list = {}
        for psg in self.passenger_ids:
            desc_text = '%s, %s' % (' '.join((psg.first_name or '', psg.last_name or '')), psg.title or '')
            price_unit = 0
            for cost_charge in psg.cost_service_charge_ids:
                if cost_charge.charge_type not in ['DISC', 'RAC'] and cost_charge.charge_code != 'csc':
                    price_unit += cost_charge.amount
                # elif cost_charge.charge_type == 'DISC':
                #     discount += cost_charge.amount
                elif cost_charge.charge_type == 'RAC' and cost_charge.charge_code != 'csc':
                    if is_use_credit_limit:
                        if not cost_charge.commission_agent_id:
                            agent_id = self.agent_id.id
                        else:
                            agent_id = cost_charge.commission_agent_id.id
                        if self.agent_id.id != agent_id:
                            if agent_id not in commission_list:
                                commission_list[agent_id] = 0
                            commission_list[agent_id] += cost_charge.amount * -1
                        else:
                            price_unit += cost_charge.amount
                    elif cost_charge.commission_agent_id != (temp_ho_obj and temp_ho_obj or False):
                        price_unit += cost_charge.amount
            ### FARE
            self.env['tt.ho.invoice.line.detail'].create({
                'desc': desc_text,
                'price_unit': price_unit,
                'quantity': 1,
                'invoice_line_id': ho_invoice_line_id,
                'ho_id': temp_ho_obj and temp_ho_obj.id or False,
                'commission_agent_id': self.agent_id.id
            })
            total_price += price_unit
        ## RAC
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

        inv_line_obj.discount = abs(discount)
        ho_inv_line_obj.discount = abs(discount)

        if not is_use_ext_credit_limit:
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
                'ho_id': temp_ho_obj and temp_ho_obj.id or False,
                'agent_id': self.agent_id.id,
                'currency_id': temp_ho_obj.currency_id.id,
                'acquirer_id': data['acquirer_id'].id,
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

        ## payment HO
        acq_obj = False
        if payment_method_to_ho == 'credit_limit':
            ho_payment_vals = {
                'ho_id': temp_ho_obj and temp_ho_obj.id or False,
                'agent_id': self.agent_id.id,
                'currency_id': temp_ho_obj.currency_id.id,
                'acquirer_id': acq_obj,
                'real_total_amount': ho_invoice_id.grand_total,
                'confirm_uid': data['co_uid'],
                'confirm_date': datetime.now()
            }
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

    def action_issued_event(self,data):
        super(ReservationEvent, self).action_issued_event(data)
        if not self.is_invoice_created:
            self.action_create_invoice(data, self.payment_method_to_ho)

    def check_approve_refund_eligibility(self):
        if self.customer_parent_id.customer_parent_type_id.id in [self.env.ref('tt_base.customer_type_cor').id, self.env.ref('tt_base.customer_type_por').id] and self.payment_method == self.customer_parent_id.seq_id:
            if all(rec.invoice_id.state == 'paid' for rec in self.invoice_line_ids):
                return True
            else:
                return False
        else:
            return True
