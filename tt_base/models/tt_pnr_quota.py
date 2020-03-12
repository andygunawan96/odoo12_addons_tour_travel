from odoo import api,fields,models
from datetime import datetime,timedelta
from ...tools import ERR
from ...tools.ERR import RequestException
import json,logging,traceback,pytz

_logger = logging.getLogger(__name__)

class TtPnrQuota(models.Model):
    _name = 'tt.pnr.quota'
    _rec_name = 'name'
    _description = 'Rodex Model PNR Quota'
    _order = 'state,expired_date,available_amount'

    name = fields.Char('Name')
    used_amount = fields.Integer('Used Amount', compute='_compute_used_amount',store=True)
    available_amount = fields.Integer('Available Amount', compute='_compute_used_amount',store=True)
    amount = fields.Integer('Amount', compute='_compute_amount', store=True)
    price_list_id = fields.Many2one('tt.pnr.quota.price.list', 'Price Data', domain=[('id','=',-1)])
    expired_date = fields.Date('Expired Date', compute="_compute_expired_date",store=True)
    usage_ids = fields.One2many('tt.pnr.quota.usage','pnr_quota_id','Quota Usage', readonly=True)
    agent_id = fields.Many2one('tt.agent','Agent', domain="[('is_using_pnr_quota','=',True)]")
    is_expired = fields.Boolean('Expired')
    state = fields.Selection([('active','Active'),('expired','Expired')],'State',compute="_compute_state",store=True)

    @api.model
    def create(self, vals_list):
        vals_list['name'] = self.env['ir.sequence'].next_by_code('tt.pnr.quota')
        return super(TtPnrQuota, self).create(vals_list)

    @api.depends('price_list_id')
    def _compute_amount(self):
        for rec in self:
            rec.amount = rec.price_list_id and rec.price_list_id.amount or False

    @api.depends('is_expired')
    def _compute_state(self):
        for rec in self:
            if rec.is_expired:
                rec.state = 'expired'
            else:
                rec.state = 'active'

    @api.depends('usage_ids','usage_ids.active')
    def _compute_used_amount(self):
        for rec in self:
            rec.used_amount = len(rec.usage_ids.ids)
            rec.available_amount = max(rec.amount - rec.used_amount,0)

    @api.depends('price_list_id')
    def _compute_expired_date(self):
        today_date = datetime.now(pytz.timezone('Asia/Jakarta')).date()
        for rec in self:
            rec.expired_date = today_date + timedelta(days=rec.price_list_id.validity_duration-1)

    @api.onchange('agent_id')
    def _onchange_domain_agent_id(self):
        return {'domain': {
            'price_list_id': [('id','in',self.agent_id.quota_package_id.available_price_list_ids.ids)]
        }}

    def to_dict(self):
        return {
            'name': self.name,
            'used_amount': self.used_amount,
            'available_amount': self.available_amount,
            'amount': self.amount,
            'expired_date': self.expired_date,
            'state': self.state
        }

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

            price_list_obj = self.env['tt.pnr.quota.price.list'].search([('seq_id','=',req['quota_seq_id'])])
            try:
                price_list_obj.create_date
            except:
                raise RequestException(1032)

            if agent_obj.balance < price_list_obj.price:
                raise RequestException(1007,additional_message='agent balance')

            new_pnr_quota = self.create({
                'agent_id': agent_obj.id,
                'price_list_id': price_list_obj.id
            })

            self.env['tt.ledger'].create_ledger_vanilla(new_pnr_quota._name,
                                                        new_pnr_quota.id,
                                                        'Order: %s' % (new_pnr_quota.name),
                                                        new_pnr_quota.name,
                                                        datetime.now(pytz.timezone('Asia/Jakarta')).date(),
                                                        2,
                                                        price_list_obj.currency_id.id,
                                                        self.env.user.id,
                                                        agent_obj.id,
                                                        False,
                                                        debit=0,
                                                        credit=price_list_obj.price,
                                                        description='Buying PNR Quota for %s' % (agent_obj.name)
                                                        )

            agent_obj.unban_user_api()

            return ERR.get_no_error()
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1031)

