from odoo import api,fields,models
from datetime import datetime,timedelta
from ...tools import ERR
from ...tools.ERR import RequestException
import json,logging,traceback,pytz
import calendar

_logger = logging.getLogger(__name__)

class TtPnrQuota(models.Model):
    _name = 'tt.pnr.quota'
    _rec_name = 'name'
    _description = 'Rodex Model PNR Quota'
    _order = 'id desc'

    name = fields.Char('Name')
    used_amount = fields.Integer('Used Amount', compute='_compute_used_amount',store=True)
    amount = fields.Integer('Amount', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    price_package_id = fields.Many2one('tt.pnr.quota.price.package', 'Price Package')
    start_date = fields.Date('Start')
    expired_date = fields.Date('Expired Date', store=True)
    usage_ids = fields.One2many('tt.pnr.quota.usage', 'pnr_quota_id','Quota Usage', readonly=True)
    agent_id = fields.Many2one('tt.agent','Agent', domain="[('is_using_pnr_quota','=',True)]")
    is_expired = fields.Boolean('Expired')
    state = fields.Selection([('active', 'Active'), ('waiting', 'Waiting'), ('payment', 'Payment'), ('done', 'Done'), ('failed', 'Failed')], 'State',compute="_compute_state",store=True)
    transaction_amount_internal = fields.Monetary('Transaction Amount Internal', copy=False, readonly=True)
    transaction_amount_external = fields.Monetary('Transaction Amount External', copy=False, readonly=True)
    total_amount = fields.Monetary('Total Amount', copy=False, readonly=True)

    @api.model
    def create(self, vals_list):
        package_obj = self.env['tt.pnr.quota.price.package'].browse(vals_list['price_package_id'])
        if package_obj:
            exp_date = datetime.now() + timedelta(days=package_obj.validity)
            now = datetime.now()
            vals_list['name'] = self.env['ir.sequence'].next_by_code('tt.pnr.quota')
            vals_list['expired_date'] = "%s-%s-%s" % (exp_date.year, exp_date.month, exp_date.day)
            vals_list['start_date'] = "%s-%s-%s" % (now.year, now.month, now.day)
            vals_list['state'] = 'active'
            vals_list['amount'] = package_obj.minimum_fee
        else:
            raise Exception('Package not fount')
        return super(TtPnrQuota, self).create(vals_list)

    @api.depends('usage_ids', 'usage_ids.active')
    def _compute_used_amount(self):
        for rec in self:
            if len(rec.usage_ids.ids) != 0:
                rec.used_amount = len(rec.usage_ids.ids) + 1

    # @api.depends('price_list_id')
    # def _compute_amount(self):
    #     for rec in self:
    #         rec.amount = rec.price_list_id and rec.price_list_id.price or False

    # @api.depends('is_expired')
    # def _compute_state(self):
    #     for rec in self:
    #         if rec.is_expired:
    #             rec.state = 'expired'
    #         else:
    #             rec.state = 'active'

    # @api.onchange('agent_id')
    # def _onchange_domain_agent_id(self):
    #     return {'domain': {
    #         'price_list_id': [('id','in',self.agent_id.quota_package_id.available_price_list_ids.ids)]
    #     }}

    def to_dict(self):
        return {
            'name': self.name,
            'used_amount': self.used_amount,
            'amount': self.amount,
            'expired_date': self.expired_date,
            'state': self.state
        }

    @api.onchange('min_amount', 'usage_ids')
    def calc_amount_internal(self):
        for rec in self:
            total_amount = 0
            for usage_obj in rec.usage_ids:
                if usage_obj.inventory == 'internal':
                    total_amount += usage_obj.amount
            rec.transaction_amount_internal = total_amount

    @api.onchange('min_amount', 'usage_ids')
    def calc_amount_external(self):
        for rec in self:
            total_amount = 0
            for usage_obj in rec.usage_ids:
                if usage_obj.inventory == 'external':
                    total_amount += usage_obj.amount
            rec.transaction_amount_external = total_amount

    @api.onchange('transaction_amount_internal', 'transaction_amount_external', 'usage_ids')
    def calc_amount_total(self):
        for rec in self:
            minimum = rec.amount
            if minimum == 0: #check jika minimum 0 ambil dari package
                rec.amount = rec.price_package_id.minimum_fee
                minimum = rec.price_package_id.minimum_fee
            if rec.price_package_id.fix_profit_share == False:
                if rec.transaction_amount_internal > minimum:
                    rec.total_amount = rec.transaction_amount_external
                else:
                    rec.total_amount = minimum - rec.transaction_amount_internal + rec.transaction_amount_external
            else:
                rec.total_amount = minimum + rec.transaction_amount_external

    def payment_pnr_quota_api(self):
        for rec in self:
            if rec.agent_id.balance > rec.total_amount:
                # bikin ledger
                self.env['tt.ledger'].create_ledger_vanilla(rec._name,
                                                            rec.id,
                                                            'Order: %s' % (rec.name),
                                                            rec.name,
                                                            datetime.now(pytz.timezone('Asia/Jakarta')).date(),
                                                            2,
                                                            rec.currency_id.id,
                                                            self.env.user.id,
                                                            rec.agent_id.id,
                                                            False,
                                                            debit=0,
                                                            credit=rec.total_amount,
                                                            description='Buying PNR Quota for %s' % (rec.agent_id.name)
                                                            )
                rec.state = 'payment'


    def get_pnr_quota_api(self,data,context):
        try:
            print(json.dumps(data))
            agent_obj = self.browse(context['co_agent_id'])
            try:
                agent_obj.create_date
            except:
                raise RequestException(1008)

            res = []
            dom = [('agent_id','=',agent_obj.id)]
            if data.get('state'):
                if data.get('state') != 'all':
                    dom.append(('state', '=', data['state']))

            for rec in self.search(dom):
                res.append(rec.to_dict())

            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1012,additional_message="PNR Quota")

    def create_pnr_quota_api(self,req,context):
        try:
            agent_obj = self.env['tt.agent'].browse(context['co_agent_id'])
            try:
                agent_obj.create_date
            except:
                raise RequestException(1008)

            price_package_obj = self.env['tt.pnr.quota.price.package'].search([('seq_id','=',req['quota_seq_id'])])
            try:
                price_package_obj.create_date
            except:
                raise RequestException(1032)

            # if agent_obj.balance < price_package_obj.price:
            #     raise RequestException(1007,additional_message='agent balance')

            new_pnr_quota = self.create({
                'agent_id': agent_obj.id,
                'price_package_id': price_package_obj.id
            })
            agent_obj.quota_total_duration = new_pnr_quota.expired_date

            # self.env['tt.ledger'].create_ledger_vanilla(new_pnr_quota._name,
            #                                             new_pnr_quota.id,
            #                                             'Order: %s' % (new_pnr_quota.name),
            #                                             new_pnr_quota.name,
            #                                             datetime.now(pytz.timezone('Asia/Jakarta')).date(),
            #                                             2,
            #                                             price_list_obj.currency_id.id,
            #                                             self.env.user.id,
            #                                             agent_obj.id,
            #                                             False,
            #                                             debit=0,
            #                                             credit=price_list_obj.price,
            #                                             description='Buying PNR Quota for %s' % (agent_obj.name)
            #                                             )

            agent_obj.unban_user_api()

            return ERR.get_no_error()
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1031)

