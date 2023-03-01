from odoo import api,models,fields
from ...tools import ERR
import traceback, logging


_logger = logging.getLogger(__name__)


class ApiMonitor(models.Model):
    _name = 'tt.api.monitor'
    _description = 'API Monitor'

    user_id = fields.Many2one('res.users', 'User')
    name = fields.Char('Name', related='user_id.name')
    agent_id = fields.Many2one('tt.agent', 'Agent', related='user_id.agent_id')
    monitor_data_ids = fields.One2many('tt.api.monitor.data', 'monitor_id', 'Monitor Data')

    def create_monitor_api(self,req, context):
        try:
            monitor_obj = self.search([('user_id','=',context['co_uid'])],limit=1)
            if not monitor_obj:
                monitor_obj = self.create({
                    'user_id': context['co_uid']
                })

            provider_type_obj = self.env['tt.provider.type'].search([('code','=',req['provider_type_code'])],limit=1)

            # filtered is slow when the data are large
            # monitor_data_obj = monitor_obj.monitor_data_ids.filtered(lambda x: x.action == req['action']
            #                                                                    and x.req_data == str(req['req_data']))
            monitor_data_obj = self.env['tt.api.monitor.data'].search([('monitor_id','=',monitor_obj.id),
                                                                       ('action','=',req['action']),
                                                                       ('req_data','=',str(req['req_data']))])

            if not monitor_data_obj:
                monitor_data_obj = self.env['tt.api.monitor.data'].create({
                    'action': req['action'],
                    'monitor_id': monitor_obj.id,
                    'provider_type_id': provider_type_obj.id,
                    'req_data': req['req_data'],
                })
            else:
                monitor_data_obj = monitor_data_obj[0]

            self.env['tt.api.monitor.data.record'].create({
                'monitor_data_id': monitor_data_obj[0].id
            })

            if monitor_data_obj.unverified_counter > monitor_data_obj.monitor_rule_id.ban_limit:
                self.env['tt.ban.user'].ban_user_api({
                    'user_id': monitor_data_obj.user_id.id,
                    'duration_minutes': 180
                }, {})
                return ERR.get_no_error({
                    'send_telegram': 'ban',
                    'hit_count': monitor_data_obj.unverified_counter
                })
            elif monitor_data_obj.unverified_counter > monitor_data_obj.monitor_rule_id.notification_limit:
                return ERR.get_no_error({
                    'send_telegram': 'notification',
                    'hit_count': monitor_data_obj.unverified_counter
                })
        except:
            _logger.error('Error Create Monitor API, %s' % traceback.format_exc())
            return ERR.get_error()
        return ERR.get_no_error({})

class ApiMonitorData(models.Model):
    _name = 'tt.api.monitor.data'
    _description = 'API Monitor Data'

    action = fields.Char('Action')
    monitor_id = fields.Many2one('tt.api.monitor', 'Monitor',ondelete='cascade')
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')
    req_data = fields.Text('Request Data')
    hit_counter = fields.Integer('Hit Counter', compute="_compute_hit_counter", store=False)
    unverified_counter = fields.Integer('Unverified Hit Counter', compute="_compute_unverified_counter", store=False)
    record_ids = fields.One2many('tt.api.monitor.data.record', 'monitor_data_id', 'Records')
    user_id = fields.Many2one('res.users','User', related='monitor_id.user_id',store=True)
    monitor_rule_id = fields.Many2one('tt.api.monitor.rule','Monitor Rule', compute="_compute_monitor_rule",store=True)

    @api.depends('provider_type_id')
    def _compute_monitor_rule(self):
        for rec in self:
            rule_obj = self.env['tt.api.monitor.rule'].search([('provider_type_id','=',rec.provider_type_id.id)],limit=1)
            if rule_obj:
                rec.monitor_rule_id = rule_obj.id

    @api.depends('record_ids')
    def _compute_hit_counter(self):
        for rec in self:
            rec.hit_counter = len(rec.record_ids.ids)

    @api.depends('record_ids','record_ids.is_verified')
    def _compute_unverified_counter(self):
        for rec in self:
            #filtered is slow when the data are too large
            # rec.unverified_counter = len(rec.record_ids.filtered(lambda x: x.is_verified == False).ids)
            rec.unverified_counter = len(self.env['tt.api.monitor.data.record'].search([('monitor_data_id','=',rec.id),
                                                                                        ('is_verified','=',False)]).ids)
class ApiMonitorDataRecord(models.Model):
    _name = 'tt.api.monitor.data.record'
    _description = 'API Monitor Data Record'

    is_verified = fields.Boolean('Verified')
    monitor_data_id = fields.Many2one('tt.api.monitor.data','Monitor Data',ondelete='cascade')
    user_id = fields.Many2one('res.users','User', related='monitor_data_id.user_id',store=True)

class ApiMonitorRule(models.Model):
    _name = 'tt.api.monitor.rule'
    _description = 'API Monitor'
    _rec_name = 'provider_type_id'

    provider_type_id = fields.Many2one('tt.provider.type','Provider Type')
    notification_limit = fields.Integer('Notification Limit')
    ban_limit = fields.Integer('Ban Limit')