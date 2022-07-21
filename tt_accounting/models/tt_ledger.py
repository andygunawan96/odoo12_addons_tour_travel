from odoo import api, fields, models, _
from datetime import date, datetime
from ...tools.ERR import RequestException
from ...tools import ERR
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
# from ...tools.telegram import TelegramInfoNotification
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
    (99, 'Others')
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

        sql_query = 'select balance from tt_ledger where %s = %s order by id desc limit 1;' % (param_search,owner_id)
        self.env.cr.execute(sql_query)
        balance = self.env.cr.dictfetchall()
        if balance:
            current_balance = balance[0]['balance']
        else:
            current_balance = 0
        current_balance += vals['debit'] - vals['credit']
        return current_balance

    def prepare_vals(self, res_model,res_id,name, ref, ledger_date, ledger_type, currency_id, issued_uid, debit=0, credit=0,description = ''):
        return {
            'name': name,
            'debit': debit,
            'credit': credit,
            'ref': ref,
            'currency_id': currency_id,
            'date': ledger_date,
            'transaction_type': ledger_type,
            'res_model': res_model,
            'res_id': res_id,
            'description': description,
            'issued_uid': issued_uid
        }

    def create_ledger_vanilla(self, res_model,res_id,name, ref, ledger_date, ledger_type, currency_id, issued_uid,agent_id,customer_parent_id, debit=0, credit=0,description = '',**kwargs):
        # self.waiting_list_process([agent_id],customer_parent_id,debit)
        vals = self.prepare_vals(res_model,
                                 res_id,name, ref,
                                 ledger_date, ledger_type,
                                 currency_id, issued_uid,
                                 debit, credit,description)
        if customer_parent_id:
            vals['customer_parent_id'] = customer_parent_id
        else:
            vals['agent_id'] = agent_id

        if kwargs:
            vals.update(kwargs)
        new_ledger = self.create(vals)
        return new_ledger

    def reverse_ledger(self):
        # 3
        # self.waiting_list_process([self.agent_id and self.agent_id.id or False],self.customer_parent_id and self.customer_parent_id.id or False,"Reverse")
        reverse_id = self.env['tt.ledger'].create({
            'name': 'Reverse:' + self.name,
            'debit': self.credit,
            'credit': self.debit,
            'ref': self.ref,
            'currency_id': self.currency_id.id,
            'transaction_type': self.transaction_type,
            'reverse_id': self.id,
            'agent_id': self.agent_id.id,
            'customer_parent_id': self.customer_parent_id.id,
            'pnr': self.pnr,
            'date': fields.datetime.now(),
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
            'provider_type_id': self.provider_type_id and self.provider_type_id.id or False
        })

        self.update({
            'reverse_id': reverse_id.id,
            'is_reversed': True,
        })
        return reverse_id

    @api.model
    def create(self, vals_list):
        # successfully_created = False
        # while(not successfully_created):
        #     try:
        try:
            vals_list['balance'] = self.calc_balance(vals_list)
            vals_list['date'] = datetime.now(pytz.timezone('Asia/Jakarta'))
            ledger_obj = super(Ledger, self).create(vals_list)
            #     successfully_created = True
            # except Exception as e:
            #     _logger.error(traceback.format_exc())
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
    def create_ledger(self, provider_obj,issued_uid):
        amount = 0
        used_sc_list = []
        for sc in provider_obj.cost_service_charge_ids:
            if sc.charge_type != 'RAC' and not sc.is_ledger_created:
                amount += sc.get_total_for_payment()
                used_sc_list.append(sc)

        if amount == 0:
            return

        booking_obj = provider_obj.booking_id
        ledger_values = self.prepare_vals(booking_obj._name,booking_obj.id,'Order : ' + booking_obj.name, booking_obj.name, datetime.now()+relativedelta(hours=7),
                                          2, booking_obj.currency_id.id, issued_uid, 0, amount)

        pnr_text = provider_obj.pnr if provider_obj.pnr else str(provider_obj.sequence)
        ledger_values = self.prepare_vals_for_resv(booking_obj,pnr_text,ledger_values,provider_obj.provider_id.code)
        self.create(ledger_values)
        for sc in used_sc_list:
            sc.change_ledger_created(True)
        return True ## return berhasil create ledger

    def create_commission_ledger(self, provider_obj,issued_uid):
        booking_obj = provider_obj.booking_id
        agent_commission = {}
        used_sc_list = []
        for sc in provider_obj.cost_service_charge_ids:
            # Pada lionair ada r.ac positif
            if 'RAC' in sc.charge_type and not sc.is_ledger_created:
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

        for agent_id, amount in agent_commission.items():
            ledger_values = self.prepare_vals(booking_obj._name,booking_obj.id,'Commission : ' + booking_obj.name, booking_obj.name, datetime.now()+relativedelta(hours=7),
                                              3, booking_obj.currency_id.id,issued_uid, amount, 0)
            ledger_values.update({
                'agent_id': abs(agent_id),
            })
            pnr_text = provider_obj.pnr if provider_obj.pnr else str(provider_obj.sequence)
            values = self.prepare_vals_for_resv(booking_obj,pnr_text,ledger_values,provider_obj.provider_id.code)
            self.sudo().create(values)

        for sc in used_sc_list:
            sc.change_ledger_created(True)

        return True #return berhasil create ledger

    def action_create_ledger(self, provider_obj,issued_uid):
        #1
        # affected_agent = [rec.commission_agent_id.id if rec.commission_agent_id else provider_obj.booking_id.agent_id.id for rec in provider_obj.cost_service_charge_ids]
        # affected_agent = set(affected_agent)
        # self.waiting_list_process(affected_agent, False,"Create Ledger Provider")
        commission_created = self.create_commission_ledger(provider_obj,issued_uid)
        ledger_created = self.create_ledger(provider_obj,issued_uid)
        return commission_created or ledger_created

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

    def waiting_list_process(self,list_agent_id,customer_parent_id,amount_comment):
        start_time = time.time()
        res = {'error_code': 0}
        second = False
        new_list_of_waiting_list = []

        if customer_parent_id:
            new_waiting_list = self.env['tt.ledger.waiting.list'].create({'customer_parent_id': customer_parent_id,'comment': amount_comment})
            new_list_of_waiting_list.append((False,customer_parent_id,new_waiting_list))
        else:
            waiting_number = False
            for rec in list_agent_id:
                if len(new_list_of_waiting_list) == 1:
                    waiting_number = new_list_of_waiting_list[0][2]['waiting_number']
                new_waiting_list = self.env['tt.ledger.waiting.list'].create({'agent_id': rec,'waiting_number': waiting_number, 'comment': amount_comment})
                new_list_of_waiting_list.append((rec,False, new_waiting_list))
        self.env.cr.commit()
        # print("Done Commit %s" % (new_waiting_list.id))
        # self.env['tt.ledger.waiting.list'].invalidate_cache()
        # sleep_time = ((new_waiting_list.id%10))
        # print(sleep_time)
        # time.sleep(sleep_time)
        last_digit = (new_list_of_waiting_list and new_list_of_waiting_list[0][2].id % 20 or 1)

        if last_digit == 0:
            last_digit = 19
        else:
            last_digit -= 1

        sleep_time = last_digit * 0.3
        _logger.info(" ### SLEEP TIME %s ###" % (sleep_time))
        time.sleep(sleep_time)

        list_of_waiting_list = self.get_waiting_list(new_list_of_waiting_list)
        if list_of_waiting_list:
            res = {'error_code': 1028}
        while list_of_waiting_list and time.time() - start_time < 30:
            list_of_waiting_list = self.get_waiting_list(new_list_of_waiting_list)
            if not list_of_waiting_list:
                res = {'error_code': 0}
                break
            if second:
                _logger.error("### CONCURRENT UPDATE LEDGER ERROR, WAITING LIST: %s. CURRENT IDS: %s ###" % ([str(rec.ids) for rec in list_of_waiting_list],str(list_agent_id)))
                time.sleep(0.5)
            second = True

        for rec in new_list_of_waiting_list:
            rec[2].is_in_transaction = False
        self.env.cr.commit()
        if res['error_code'] != 0:
            raise RequestException(res['error_code'])
        # print("OUT")

    def get_waiting_list(self,list_of_waiting_id):
        self.clear_caches()
        self.env.cr.commit()
        list_of_waiting_list = []
        for rec in list_of_waiting_id:
            current_search = self.env['tt.ledger.waiting.list'].search(['|',('agent_id','=', rec[0]),('customer_parent_id','=', rec[1]),
                                                                        ('is_in_transaction', '=', True),
                                                                        ('waiting_number','<',rec[2].waiting_number)])
            if current_search:
                list_of_waiting_list.append(current_search)

        if list_of_waiting_list:
            _logger.info("Waiting List : " + str([rec.ids for rec in list_of_waiting_list]))
        else:
            _logger.info("Empty Waiting List, current ID: %s." % (str([(rec[0],rec[1],rec[2].id,rec[2].waiting_number) for rec in list_of_waiting_id])))
        return list_of_waiting_list

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
                "provider_type_name": provider_type

            })

        return ERR.get_no_error(res)

class TtLedgerWaitingList(models.Model):
    _name = 'tt.ledger.waiting.list'
    _description = 'Ledger Waiting List'
    _order = 'create_date desc'

    agent_id = fields.Many2one('tt.agent','Agent')
    customer_parent_id = fields.Many2one('tt.customer.parent','Customer Parent')
    is_in_transaction = fields.Boolean("In Transaction",default=True)
    comment = fields.Text("Comment")
    waiting_number = fields.Integer('Waiting Number')

    @api.model
    def create(self, vals_list):
        new_waiting_list = super(TtLedgerWaitingList, self).create(vals_list)
        if not vals_list.get('waiting_number'):
            new_waiting_list.waiting_number = new_waiting_list.id
        return new_waiting_list

    def turn_off_all_transaction(self):
        for rec in self.search([('is_in_transaction','=',True)]):
            rec.is_in_transaction = False
