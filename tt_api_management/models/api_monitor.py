from odoo import api,models,fields

class ApiMonitor(models.Model):
    _name = 'tt.api.monitor'
    _description = 'Rodex Model API Monitor'

    user_id = fields.Many2one('res.users', 'User')
    name = fields.Char('Name', related='user_id.name')
    agent_id = fields.Many2one('tt.agent', 'Agent ID', related='user_id.agent_id')
    monitor_data_ids = fields.One2many('tt.api.monitor.data', 'monitor_id', 'Monitor Data')

    def create_monitor_api(self,req, context):
        monitor_obj = self.search([('user_id','=',context['co_uid'])])
        if not monitor_obj:
            monitor_obj = self.create({
                'user_id': context['co_uid']
            })

        provider_obj = self.env['tt.provider'].search([('code','=',req['provider'])],limit=1)

        monitor_data_obj = monitor_obj.monitor_data_ids.filtered(lambda x: x.action == req['action']
                                                                           and x.provider_id.id == provider_obj.id
                                                                           and x.req_data == req['req_data'])
        if not monitor_data_obj:
            monitor_data_obj = self.env['tt.api.monitor.data'].create({
                'action': req['action'],
                'monitor_id': monitor_obj.id,
                'provider_id': provider_obj.id,
                'req_data': req['req_data'],
            })

        self.env['tt.api.monitor.data.record'].create({
            'monitor_data_id': monitor_data_obj.id
        })


class ApiMonitorData(models.Model):
    _name = 'tt.api.monitor.data'
    _description = 'Rodex Model API Monitor Data'

    action = fields.Char('Action')
    monitor_id = fields.Many2one('tt.api.monitor', 'Monitor')
    provider_id = fields.Many2one('tt.provider', 'Provider')
    req_data = fields.Text('Request Data')
    hit_counter = fields.Integer('Hit Counter', compute="_compute_hit_counter", store=True)
    unverified_counter = fields.Integer('Unverified Hit Counter', compute="_compute_unverified_counter", store=True)
    record_ids = fields.One2many('tt.api.monitor.data.record', 'monitor_data_id', 'Records')

    @api.depends('record_ids')
    def _compute_hit_counter(self):
        for rec in self:
            rec.hit_counter = len(rec.record_ids.ids)

    @api.depends('record_ids','record_ids.is_verified')
    def _compute_unverified_counter(self):
        for rec in self:
            rec.unverified_counter = len(rec.record_ids.filtered(lambda x: x.is_verified == True).ids)

class ApiMonitorDataRecord(models.Model):
    _name = 'tt.api.monitor.data.record'
    _description = 'Rodex Model API Monitor Data Record'

    is_verified = fields.Boolean('Verified')
    monitor_data_id = fields.Many2one('tt.api.monitor.data','Monitor Data')