from odoo import api, fields, models, _
from datetime import date, datetime
from ...tools.ERR import RequestException
from ...tools.db_connector import GatewayConnector
from ...tools import ERR
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
import logging,json,traceback,time,pytz
from ...tools import util

LEDGER_TYPE = [
    (0, 'Opening Balance'),
    (1, 'Top Up / Agent Payment'),
    (2, 'Order'),
    (3, 'Commission'),
    (4, 'Refund'),
    (5, 'Adjustment'),
    (6, 'Admin fee'),
    (7, 'Reschedule'),
    (8, 'Addons'),
    (9, 'Statement Balance'),
    (10, 'Point Reward'),
    (11, 'Point Used'),
    (99, 'Others')
]

SOURCE_OF_FUNDS_TYPE = [
    ('balance', 'Balance'),
    ('point', 'Point Reward'),
    ('credit_limit', 'Credit Limit')
]

_logger = logging.getLogger(__name__)

class Ledger(models.Model):
    _name = 'tt.ledger'
    _inherit = 'tt.history'
    _order = 'id DESC'
    _description = 'Ledger'
    # _order = 'date, id'

    name = fields.Char('Name', copy=False)
    date = fields.Date('Date', default=fields.Date.context_today)
    debit = fields.Monetary('Debit', default=0)
    credit = fields.Monetary('Credit', default=0)
    balance = fields.Monetary('Balance',
                              default=0,
                              help='Current Agent Balance after this ledger')

    currency_id = fields.Many2one('res.currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)

    ref = fields.Char('Reference', readonly=True, copy=False)

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id)
    agent_id = fields.Many2one('tt.agent', 'Agent', index=True)
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id',
                                    store=True)

    customer_parent_id = fields.Many2one('tt.customer.parent','Customer Parent')
    customer_parent_type_id = fields.Many2one('tt.customer.parent.type','Customer Parent Type', related='customer_parent_id.customer_parent_type_id')

    transaction_type = fields.Selection(LEDGER_TYPE, string='Type')

    description = fields.Text('Description')
    pnr = fields.Char('PNR')
    issued_uid = fields.Many2one('res.users', 'Issued UID')
    display_provider_name = fields.Char('Provider', help='Display Provider Name')

    adjustment_id = fields.Many2one('tt.adjustment','Adjustment')
    refund_id = fields.Many2one('tt.refund','Refund')
    reverse_id = fields.Many2one('tt.ledger', 'Reverse')
    is_reversed = fields.Boolean('Already Reversed', default=False)

    res_model = fields.Char(
        'Related Reservation Name', index=True)
    res_id = fields.Integer(
        'Related Reservation ID', index=True, help='ID of the followed resource')

    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')

    source_of_funds_type = fields.Selection(SOURCE_OF_FUNDS_TYPE, string='Source of Funds', default='balance')

    def calc_balance(self, vals):
        # Pertimbangkan Multi Currency Ledgers
        balance = 0
        # self.env['tt.agent'].invalidate_cache(ids=vals['agent_id'])
        # self.env['tt.agent'].clear_caches()
        # self.env.cr.commit()
        if vals.get('agent_id'):
            owner_id = vals['agent_id']
            param_search = 'agent_id'
            # balance = self.env['tt.agent'].browse(vals['agent_id']).balance
        elif vals.get('customer_parent_id'):
            owner_id = vals['customer_parent_id']
            param_search = 'customer_parent_id'
            
        sql_query = "select balance from tt_ledger where %s = %s and source_of_funds_type = '%s' order by id desc limit 1;" % (param_search,owner_id, vals['source_of_funds_type'])
        self.env.cr.execute(sql_query)
        balance = self.env.cr.dictfetchall()
        if balance:
            current_balance = balance[0]['balance']
        else:
            current_balance = 0
        current_balance += vals['debit'] - vals['credit']
        return current_balance

    def prepare_vals(self, res_model,res_id,name, ref, ledger_type, currency_id, issued_uid, debit=0, credit=0,description='', source_of_funds_type='balance'):
        return {
            'name': name,
            'debit': debit,
            'credit': credit,
            'ref': ref,
            'currency_id': currency_id,
            'transaction_type': ledger_type,
            'res_model': res_model,
            'res_id': res_id,
            'description': description,
            'issued_uid': issued_uid,
            'source_of_funds_type': source_of_funds_type
        }

    def create_ledger_vanilla(self, res_model,res_id,name, ref, ledger_type, currency_id, issued_uid,agent_id,customer_parent_id, debit=0, credit=0,description='',source_of_funds_type='balance',**kwargs):
        vals = self.prepare_vals(res_model,
                                 res_id,name, ref,
                                 ledger_type,
                                 currency_id, issued_uid,
                                 debit, credit,description, source_of_funds_type and source_of_funds_type or 'balance')
        if customer_parent_id:
            vals['customer_parent_id'] = customer_parent_id
            customer_parent_obj = self.env['tt.customer.parent'].browse(int(customer_parent_id))
            agent_obj = customer_parent_obj.parent_agent_id
        else:
            vals['agent_id'] = agent_id
            agent_obj = self.env['tt.agent'].browse(int(agent_id))

        ho_obj = agent_obj and agent_obj.ho_id or False
        if ho_obj:
            vals['ho_id'] = ho_obj.id

        if kwargs:
            vals.update(kwargs)

        #bersihkan default context, bikin bug jika approve payment dari UI Invoice COR langsung. Ledger akan ter isi agent_id dan cor_id
        wash_keys = ['agent_id','customer_parent_id']
        for wash_key in wash_keys:
            default_context_key = 'default_%s' % (wash_key)
            if not vals.get(wash_key) and self.env.context.get(default_context_key):
                new_context = dict(self.env.context).copy()
                new_context.pop(default_context_key)
                self.env.context = new_context

        do_ledger_queue_ho = eval(self.env['ir.config_parameter'].sudo().get_param('do_ledger_queue_ho'))
        # harus ada ( ) nya di ho_id == agent_id
        if do_ledger_queue_ho and (agent_obj.ho_id.id == agent_id):
            self.create_ledger_queue(vals,agent_obj.ho_id.id)
            return True
        else:
            new_ledger = self.create(vals)
            return new_ledger

    def reverse_ledger_from_button(self):
        if not self.env.user.has_group('tt_base.group_ledger_level_5'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 1')
        self.reverse_ledger()
        try:
            data = {
                'code': 9901,
                'title': 'REVERSE LEDGER',
                'message': 'Ledger reversed from button: %s\nUser: %s\n' % (self.name, self.env.user.name)
            }
            context = {
                "co_ho_id": self.ho_id.id
            }
            GatewayConnector().telegram_notif_api(data, context)
        except Exception as e:
            _logger.info('Failed to send "reverse ledger" telegram notification: ' + str(e))

    def reverse_ledger(self):
        if not self.env.user.has_group('tt_base.group_ledger_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 1')

        reverse_ledger_values = {
            'name': 'Reverse:' + self.name,
            'debit': self.credit,
            'credit': self.debit,
            'ref': self.ref,
            'currency_id': self.currency_id.id,
            'transaction_type': self.transaction_type,
            'reverse_id': self.id,
            'ho_id': self.ho_id.id,
            'agent_id': self.agent_id.id,
            'customer_parent_id': self.customer_parent_id.id,
            'pnr': self.pnr,
            'issued_uid': self.issued_uid.id,
            'display_provider_name': self.display_provider_name,
            'res_model': self.res_model,
            'res_id': self.res_id,
            'is_reversed': True,
            'description': 'Reverse for %s' % (self.name),
            'adjustment_id': self.adjustment_id and self.adjustment_id.id or False,
            'refund_id': self.refund_id and self.refund_id.id or False,
            'reschedule_id': hasattr(self,'reschedule_id') and self.reschedule_id or False,
            'reschedule_model': hasattr(self,'reschedule_model') and self.reschedule_model or False,
            'provider_type_id': self.provider_type_id and self.provider_type_id.id or False,
            'source_of_funds_type': self.source_of_funds_type and self.source_of_funds_type or 'balance' ## default balance
        }

        do_ledger_queue_ho = eval(self.env['ir.config_parameter'].sudo().get_param('do_ledger_queue_ho'))
        # harus ada ( ) nya di ho_id == agent_id
        if do_ledger_queue_ho and (self.ho_id.id == self.agent_id.id):
            self.create_ledger_queue(reverse_ledger_values,self.ho_id.id)
        else:
            self.env['tt.ledger'].create(reverse_ledger_values)

        #Void Ledger queue when reversing, but ledger queue is not created yet
        if do_ledger_queue_ho:
            can_be_voided_queue_objs = self.env['tt.ledger.queue'].search([('res_model','=', self.res_model),
                                                                      ('res_id','=', self.res_id)])
            if can_be_voided_queue_objs and datetime.now() < self.env.ref('tt_accounting.cron_process_ledger_queue').nextcall:
                can_be_voided_queue_objs.write({
                    'active': False
                })
                _logger.info("### Voiding %s ledger(s), for %s %s ###" % (len(can_be_voided_queue_objs),self.res_model,self.res_id))
            else:
                _logger.info("### There are can be voided ledger queue, but skipped because queue cron is running. ###")

    @api.model
    def create(self, vals_list):
        try:
            vals_list['balance'] = self.calc_balance(vals_list)
            vals_list['date'] = datetime.now(pytz.timezone('Asia/Jakarta'))
            ledger_obj = super(Ledger, self).create(vals_list)

            ## Reverse Ledger Stuff
            if ledger_obj.reverse_id:
                ledger_obj.reverse_id.write({
                    'reverse_id': ledger_obj.id,
                    'is_reversed': True,
                })

        except Exception as e:
            # raise Exception(traceback.format_exc())
            _logger.error(traceback.format_exc())
            # raise Exception("Sigh... Concurrent Update. %s" % (vals_list['debit']))
            # 29 Des 2020, Joshua ; kalau gagal create ledger langsung di anggap concurrent update
            raise RequestException(1028)
        _logger.info('Created Ledger Succesfully %s' % (ledger_obj.id))
        return ledger_obj

    def open_reference(self):
        try:
            form_id = self.env[self.res_model].get_form_id()
        except:
            form_id = self.env['ir.ui.view'].search([('type', '=', 'form'), ('model', '=', self.res_model)], limit=1)
            form_id = form_id[0] if form_id else False

        return {
            'type': 'ir.actions.act_window',
            'name': 'Reservation',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'current',
        }

    def get_allowed_rule(self):
        return {
            'is_reversed': (##Field yang mau di check
                False,## boleh tumpuk atau tidak, False = hanya bisa edit jika field yg mau di check valuenya False, True boleh replace
                ('is_reversed', 'reverse_id')##yang boleh di edit
            ),
            'description': (
                True,
                ('description',)## koma jangan di hapus nanti error tidak loop tupple tetapi string
            ),
            'balance':(
                True,
                ('balance',)
            )
        }

    @api.multi
    def write(self, vals):
        allowed_list = []
        allowed_replace_list = []
        for rules, values in self.get_allowed_rule().items():
            if values[0]:
                allowed_replace_list += values[1]
            allowed_list += values[1]
        allowed_list = set(allowed_list)
        allowed_replace_list = set(allowed_replace_list)

        for key, value in vals.items():
            if key not in allowed_list:
                raise Exception('Cannot Write Ledger, new.')
            if getattr(self, key):
                if key not in allowed_replace_list:
                    raise Exception('Cannot Write Ledger, replace.')
        return super(Ledger, self).write(vals)

    @api.multi
    def unlink(self):
        raise UserError(_('You cannot delete a Ledger which is not draft or cancelled.'))



    # API START #####################################################################
    def create_ledger(self, provider_obj,issued_uid, use_point, payment_method_use_to_ho):
        amount = 0
        used_sc_list = []
        for sc in provider_obj.cost_service_charge_ids:
            if sc.charge_type != 'RAC' and not sc.is_ledger_created:
                amount += sc.get_total_for_payment()
                used_sc_list.append(sc)

        if amount == 0:
            return

        booking_obj = provider_obj.booking_id

        website_use_point_reward = self.env['ir.config_parameter'].sudo().get_param('use_point_reward')
        if use_point and website_use_point_reward == 'True':
            amount -= self.use_point_reward(booking_obj, use_point, amount, issued_uid)

        ledger_values = self.prepare_vals(booking_obj._name,booking_obj.id,'Order : ' + booking_obj.name, booking_obj.name,
                                          2, booking_obj.currency_id.id, issued_uid, 0, amount, '', payment_method_use_to_ho and payment_method_use_to_ho or 'balance')

        pnr_text = provider_obj.pnr if provider_obj.pnr else str(provider_obj.sequence)
        ledger_values = self.prepare_vals_for_resv(booking_obj,pnr_text,ledger_values,provider_obj.provider_id.code)
        self.create(ledger_values)

        ### 23 JUN 2023 ####
        #### update estimated currency
        agent_rate_objs = self.env['tt.agent.rate'].search([('ho_id', '=', booking_obj.ho_id.id), ('base_currency_id', '=', booking_obj.currency_id.id)])
        if agent_rate_objs:
            estimated_currency = {"total_price": 0, "currency": booking_obj.currency_id.name, "other_currency": []}
            if booking_obj.estimated_currency:
                estimated_currency = json.loads(booking_obj.estimated_currency)
            estimated_currency['total_price'] += amount
            estimated_currency['other_currency'] = []
            for agent_rate_obj in agent_rate_objs:
                estimated_currency['other_currency'].append({
                    "amount": round(estimated_currency['total_price'] / agent_rate_obj.rate, 2),
                    "currency": agent_rate_obj.to_currency_id.name,
                    "rate": agent_rate_obj.rate
                })
            booking_obj.estimated_currency = json.dumps(estimated_currency)
        for sc in used_sc_list:
            sc.change_ledger_created(True)
        return True ## return berhasil create ledger

    def create_ledger_queue(self,values, ho_id):
        self.env['tt.ledger.queue'].create({
            'ho_id': ho_id,
            'name': values['description'],
            'ledger_values_data': json.dumps(values),
            'res_model': values['res_model'],
            'res_id': values['res_id'],
        })

    def use_point_reward(self, booking_obj, use_point, amount, issued_uid):
        website_use_point_reward = self.env['ir.config_parameter'].sudo().get_param('use_point_reward')
        total_use_point = 0
        if use_point and website_use_point_reward == 'True':
            payment_method = self.env['payment.acquirer'].search([('seq_id', '=', booking_obj.payment_method)])
            if payment_method.type == 'cash':
                point_reward = booking_obj.agent_id.actual_point_reward
                if point_reward > amount:
                    total_use_point = amount - 1
                else:
                    total_use_point = point_reward
            elif payment_method.type == 'payment_gateway':
                point_reward = booking_obj.agent_id.actual_point_reward
                if point_reward - payment_method.minimum_amount > amount:
                    total_use_point = amount - payment_method.minimum_amount
                else:
                    total_use_point = point_reward
            amount -= total_use_point
            self.env['tt.point.reward'].minus_points("Used", booking_obj, total_use_point, issued_uid)
            booking_obj.is_using_point_reward = True
        return total_use_point

    def create_commission_ledger(self, provider_obj,issued_uid):
        booking_obj = provider_obj.booking_id
        agent_commission = {}
        used_sc_list = []
        for sc in provider_obj.cost_service_charge_ids:
            # Pada lionair ada r.ac positif
            # if 'RAC' in sc.charge_type and not sc.is_ledger_created:
            # 19 Jan 2024: ganti pengecekan ke exact 'RAC' karena kalo breakdown nyala ada RAC lain yang bukan commission
            if sc.charge_type == 'RAC' and not sc.is_ledger_created:
                ## FIXME TAMBAL DOWNSELL
                if sc.charge_code == 'csc':
                    amount = sc.get_total_for_payment() * -1
                ## FIXME DEFAULT AWAL
                else:
                    amount = abs(sc.get_total_for_payment())
                if amount == 0:
                    continue
                agent_id = sc.commission_agent_id.id if sc.commission_agent_id else booking_obj.agent_id.id
                if sc.charge_code == 'hoc':
                    agent_id *= -1
                if not agent_commission.get(agent_id, False):
                    agent_commission[agent_id] = 0
                agent_commission[agent_id] += amount
                used_sc_list.append(sc)

        do_ledger_queue_ho = eval(self.env['ir.config_parameter'].sudo().get_param('do_ledger_queue_ho'))
        for agent_id, amount in agent_commission.items():
            ## FIXME DEFAULT AWAL
            if amount > 0:
                ledger_values = self.prepare_vals(booking_obj._name,booking_obj.id,'Commission : ' + booking_obj.name, booking_obj.name,
                                                  3, booking_obj.currency_id.id,issued_uid, amount, 0)
            ## FIXME TAMBAL DOWNSELL
            else:
                ledger_values = self.prepare_vals(booking_obj._name, booking_obj.id, 'Commission : ' + booking_obj.name,
                                                  booking_obj.name,
                                                  3, booking_obj.currency_id.id, issued_uid, 0, amount*-1)
            ledger_values.update({
                'agent_id': abs(agent_id),
            })
            agent_obj = self.env['tt.agent'].browse(int(agent_id))
            ho_obj = agent_obj and agent_obj.ho_id or False
            if ho_obj:
                ledger_values.update({
                    'ho_id': ho_obj.id
                })
            pnr_text = provider_obj.pnr if provider_obj.pnr else str(provider_obj.sequence)
            values = self.prepare_vals_for_resv(booking_obj,pnr_text,ledger_values,provider_obj.provider_id.code)

            ## Delay HO Ledger, to minimize concurrent update on HO Balance
            #harus ada ( ) nya di ho_id == agent_id
            if do_ledger_queue_ho and (agent_id == ho_obj.id):
                #jika ternyata ledger yg mau di buaat adalah punya HO, delay dan masukkan ke queue saja
                self.create_ledger_queue(values,ho_obj.id)
            else:
                self.sudo().create(values)

        for sc in used_sc_list:
            sc.change_ledger_created(True)

        return True #return berhasil create ledger

    def action_create_ledger(self, provider_obj,issued_uid, use_point=False, payment_method_use_to_ho=False):
        if payment_method_use_to_ho != 'credit_limit':
            commission_created = self.create_commission_ledger(provider_obj,issued_uid)
            ledger_created = self.create_ledger(provider_obj,issued_uid, use_point, payment_method_use_to_ho)
            return commission_created or ledger_created
        if use_point:
            provider_obj.booking_id.is_using_point_reward = True
        return True

    # May 12, 2020 - SAM
    def action_adjustment_ledger(self, provider, provider_obj, issued_uid):
        agent_id = provider_obj.booking_id.agent_id.id
        pnr = provider['pnr']
        provider_sequence = str(provider_obj.sequence)

        # Calculate Vendor Amount
        provider_total_price = 0.0
        provider_total_commission_parent_dict = {}
        provider_total_commission_agent = 0.0
        for journey in provider['journeys']:
            for seg in journey['segments']:
                for fare in seg['fares']:
                    for sc in fare['service_charges']:
                        if sc['charge_type'] == 'RAC':
                            if not sc.get('commission_agent_id') or sc['commission_agent_id'] != agent_id:
                                commission_agent_id = sc['commission_agent_id']
                                if not provider_total_commission_parent_dict.get(commission_agent_id):
                                    provider_total_commission_parent_dict[commission_agent_id] = 0.0
                                provider_total_commission_parent_dict[commission_agent_id] += sc['total']
                            else:
                                provider_total_commission_agent += sc['total']
                        else:
                            provider_total_price += sc['total']

        for psg in provider['passengers']:
            for fee in psg['fees']:
                for sc in fee['service_charges']:
                    if sc['charge_type'] == 'RAC':
                        if not sc.get('commission_agent_id') or sc['commission_agent_id'] != agent_id:
                            commission_agent_id = sc['commission_agent_id']
                            if not provider_total_commission_parent_dict.get(commission_agent_id):
                                provider_total_commission_parent_dict[commission_agent_id] = 0.0
                            provider_total_commission_parent_dict[commission_agent_id] += sc['total']
                        else:
                            provider_total_commission_agent += sc['total']
                    else:
                        provider_total_price += sc['total']

        # Calculate Reservation Amount
        for led in provider_obj.booking_id.ledger_ids:
            ledger_pnr = led.pnr
    # END

    # def re_compute_ledger_balance(self):
    #     if not self.customer_parent_id:
    #         ledger_objs = self.search([('agent_id','=',self.agent_id.id),('id','>=',self.id)],order='id')
    #     else:
    #         ledger_objs = self.search([('customer_parent_id','=',self.customer_parent_id.id),('id','>=',self.id)],order='id')
    #
    #     cur_balance = 0
    #     for idx, rec in enumerate(ledger_objs):
    #         if idx > 0:
    #             rec.balance = cur_balance+rec.debit-rec.credit
    #         cur_balance = rec.balance
    def fixing_description_ledger_adjustment(self):
        for rec in self.search([('adjustment_id','!=',False)]):
            rec.description = '%s%s' % (rec.description,rec.adjustment_id.description and '\nReason : %s' % (rec.adjustment_id.description) or '')
            _logger.info(rec.name)

    def history_transaction_ledger_api(self, data, context):
        page = data['page'] - 1
        dom = []
        dom.append(('date','>=', data['start_date']))
        dom.append(('date','<=', data['end_date']))

        if util.get_without_empty(context, 'co_customer_parent_id'):
            dom.append(('customer_parent_id', '=', context['co_customer_parent_id']))
        else:
            dom.append(('agent_id', '=', context['co_agent_id']))
        ledger_obj = self.search(dom, offset=page * data['limit'],limit=(page+1) * data['limit'])
        res = []
        for rec_ledger in ledger_obj:
            book_obj = None
            try:
                book_obj = self.env[rec_ledger.res_model].browse(rec_ledger.res_id)
                if book_obj:
                    info = book_obj.get_transaction_additional_info()
                    booker = book_obj.booker_id.to_dict()
                else:
                    info = ''
                    booker = {}
            except:
                info = ''
                booker = {}
            provider_type = ''
            if book_obj:
                if hasattr(book_obj, 'provider_type_id'):
                    provider_type = book_obj.provider_type_id.name
            res.append({
                "name": rec_ledger.name if rec_ledger.name else '',
                "debit": rec_ledger.debit,
                "credit": rec_ledger.credit,
                "currency": rec_ledger.currency_id.name if rec_ledger.currency_id else '',
                "ref": rec_ledger.ref if rec_ledger.ref else '',
                "transaction_type": rec_ledger.transaction_type if rec_ledger.transaction_type else '',
                "description": rec_ledger.description if rec_ledger.description else '',
                "pnr": rec_ledger.pnr if rec_ledger.pnr else '',
                "info": info,
                "date": rec_ledger.date.strftime('%Y-%m-%d') if rec_ledger.date else '',
                "booker": booker,
                "create_date": rec_ledger.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                "provider_type_name": provider_type,
                "source_of_funds_type": rec_ledger.source_of_funds_type

            })

        return ERR.get_no_error(res)

    def force_domain_agent_ledger(self):
        return {
            'name': 'Ledger',
            'type': 'ir.actions.act_window',
            'res_model': 'tt.ledger',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain': [('agent_id', '=', self.env.user.agent_id.id)],
            'view_id': False,
            'views': [
                (self.env.ref('tt_accounting.tt_ledger_tree_view').id, 'tree'),
                (self.env.ref('tt_accounting.tt_ledger_form_view').id, 'form'),
            ],
            'target': 'current'
        }