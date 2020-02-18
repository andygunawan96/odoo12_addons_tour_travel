from odoo import api, fields, models, _
from datetime import date, datetime
from ...tools.ERR import RequestException
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
# from ...tools.telegram import TelegramInfoNotification
import logging,json,traceback

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
        'Related Reservation ID', index=True, help='Id of the followed resource')

    def calc_balance(self, vals):
        # Pertimbangkan Multi Currency Ledgers
        balance = 0
        if vals.get('agent_id'):
            balance = self.env['tt.agent'].browse(vals['agent_id']).balance
            # sql_query = 'select id,balance from tt_ledger where agent_id = %s order by id desc limit 1;' % (vals['agent_id'])
            # self.env.cr.execute(sql_query)
            # balance = self.env.cr.dictfetchall()
        elif vals.get('customer_parent_id'):
            balance = self.env['tt.customer.parent'].browse(vals['customer_parent_id']).balance
            # sql_query = 'select id,balance from tt_ledger where customer_parent_id = %s order by id desc limit 1;' % (vals['customer_parent_id'])
            # self.env.cr.execute(sql_query)
            # balance = self.env.cr.dictfetchall()
        # if balance:
        #     return (balance[0]['balance'] + vals['debit']) - vals['credit']
        # else:
        #     return 0
        return (balance + vals['debit']) - vals['credit']

    def prepare_vals(self, res_model,res_id,name, ref, date, ledger_type, currency_id, issued_uid, debit=0, credit=0,description = ''):
        return {
                'name': name,
                'debit': debit,
                'credit': credit,
                'ref': ref,
                'currency_id': currency_id,
                'date': date,
                'transaction_type': ledger_type,
                'res_model': res_model,
                'res_id': res_id,
                'description': description,
                'issued_uid': issued_uid
            }

    def create_ledger_vanilla(self, res_model,res_id,name, ref, date, ledger_type, currency_id, issued_uid,agent_id,customer_parent_id, debit=0, credit=0,description = '',**kwargs):
        vals = self.prepare_vals(res_model,
                          res_id,name, ref,
                          date, ledger_type,
                          currency_id, issued_uid,
                          debit, credit,description)
        if customer_parent_id:
            vals['customer_parent_id'] = customer_parent_id
        else:
            vals['agent_id'] = agent_id

        if kwargs:
            vals.update(kwargs)
        self.create(vals)


    def reverse_ledger(self):
        reverse_id = self.env['tt.ledger'].create({
            'name': 'Reverse:' + self.name,
            'debit': self.credit,
            'credit': self.debit,
            'ref': self.ref,
            'date': fields.datetime.now(),
            'currency_id': self.currency_id.id,
            'reverse_id': self.id,
            'agent_id': self.agent_id.id,
            'customer_parent_id': self.customer_parent_id.id,
            'issued_uid': self.issued_uid.id,
            'is_reversed': True,
            'adjustment_id': self.adjustment_id and self.adjustment_id.id or False,
            'refund_id': self.refund_id and self.refund.id or False
        })
        self.update({
            'reverse_id': reverse_id.id,
            'is_reversed': True,
        })

    @api.model
    def create(self, vals_list):
        vals_list['balance'] = self.calc_balance(vals_list)
        ledger_obj = super(Ledger, self).create(vals_list)
        return ledger_obj

    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:
    #         vals['balance'] = self.calc_balance(vals)
    #     return super(Ledger, self).create(vals_list)

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

    def get_allowed_list(self):
        return {
            'is_reversed': ['is_reversed', 'reverse_id']
        }


    ##fungsi return tuple
    ## [0] ada key apa
    ## [1]
    @api.multi
    def write(self, vals):
        for check_key, restriction in self.get_allowed_list().items():
            if getattr(self, check_key):
                for item in restriction:
                    if item in vals.keys():
                        raise UserError('Error not allowed to edit ledger')
        return super(Ledger, self).write(vals)

    @api.multi
    def unlink(self):
        raise UserError(_('You cannot delete a Ledger which is not draft or cancelled.'))


    # API START #####################################################################
    def create_ledger(self, provider_obj,issued_uid):
        amount = 0

        for sc in provider_obj.cost_service_charge_ids:
            if sc.charge_type != 'RAC' and not sc.is_ledger_created:
                amount += sc.get_total_for_payment()

        if amount == 0:
            return

        booking_obj = provider_obj.booking_id
        ledger_values = self.prepare_vals(booking_obj._name,booking_obj.id,'Order : ' + booking_obj.name, booking_obj.name, datetime.now()+relativedelta(hours=7),
                                          2, booking_obj.currency_id.id, issued_uid, 0, amount)

        ledger_values = self.prepare_vals_for_resv(booking_obj,provider_obj.pnr,ledger_values)
        self.create(ledger_values)

    def create_commission_ledger(self, provider_obj,issued_uid):
        booking_obj = provider_obj.booking_id

        agent_commission = {}
        for sc in provider_obj.cost_service_charge_ids:
            amount = 0
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

        for agent_id, amount in agent_commission.items():
            ledger_values = self.prepare_vals(booking_obj._name,booking_obj.id,'Commission : ' + booking_obj.name, booking_obj.name, datetime.now()+relativedelta(hours=7),
                                       3, booking_obj.currency_id.id,issued_uid, amount, 0)
            ledger_values.update({
                'agent_id': abs(agent_id),
            })
            values = self.prepare_vals_for_resv(booking_obj,provider_obj.pnr,ledger_values)
            _logger.info('Create Ledger Commission\n')
            self.sudo().create(values)

    def action_create_ledger(self, provider_obj,issued_uid):
        self.create_commission_ledger(provider_obj,issued_uid)
        self.create_ledger(provider_obj,issued_uid)

    # api_context : ['type', 'agent_id', 'amount', 'pnr', 'ref_name', 'order']
    # def get_agent_ledger(self, start_date=False, end_date=False, limit=10, offset=1, api_context=None):
    #     try:
    #         # user_obj = self.env['res.users'].browse(user_id)
    #         # partner_obj = self.env['res.partner'].browse(user_obj.agent_id.id)
    #
    #         user_obj = self.env['res.users'].browse(api_context['co_uid'])
    #         domain = [('agent_id', 'in', user_obj.allowed__ids.ids)]
    #         # domain.append(('agent_id', '=', partner_obj.id))
    #         if api_context.get('type', False):
    #             type = LEDGER_TYPE_TO_INT[api_context['type']]
    #             domain.append(('transaction_type', '=', type))
    #         if start_date and end_date:
    #             domain += [('date', '>=', start_date), ('date', '<=', end_date)]
    #         if api_context.get('agent_id', False):
    #             domain += [('agent_id.name', 'ilike', api_context['agent_id'])]
    #         if api_context.get('amount', False):
    #             domain += ['|', ('debit', '=', api_context['amount']), ('credit', '=', api_context['amount'])]
    #         if api_context.get('pnr', False):
    #             domain.append(('pnr', 'ilike', api_context['pnr']))
    #         if api_context.get('ref_name', False):
    #             domain += ['|', ('name', 'ilike', api_context['ref_name']),
    #                        ('ref', 'ilike', api_context['ref_name'])]
    #
    #         order = api_context.get('order', 'id DESC')
    #         ledger_ids = self.search(domain, limit=limit, offset=offset, order=order)
    #         list_ledger = []
    #         for rec in ledger_ids:
    #             list_ledger.append({
    #                 'name': rec.name,
    #                 'date': rec.create_date,
    #                 'type': dict(rec._fields['transaction_type'].selection).get(rec.transaction_type),
    #                 'transport_type': rec.transport_type,
    #                 'reference': rec.ref,
    #                 'debit': rec.debit,
    #                 'credit': rec.credit,
    #                 'provider': rec.transport_booking_id and rec.transport_booking_id.display_provider_name or
    #                             rec.issued_offline_id and rec.issued_offline_id.provider or
    #                             rec.itank_booking_id and rec.itank_booking_id.supplier_name or False,
    #                 'pnr': rec.pnr,
    #                 'desc': rec.description,
    #             })
    #
    #         response = {
    #             'error_code': 0,
    #             'error_msg': '',
    #             'response': {
    #                 'ledger': list_ledger,
    #             }
    #         }
    #
    #     except Exception as e:
    #         response = {
    #             'error_code': 100,
    #             'error_msg': str(e),
    #         }
    #
    #     return response

    # API END #######################################################################