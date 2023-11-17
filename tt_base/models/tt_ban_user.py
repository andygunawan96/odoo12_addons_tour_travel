from odoo import api, models, fields
from odoo.exceptions import UserError
from datetime import datetime,timedelta
from ...tools import ERR

class TtBanUser(models.Model):
    _name = 'tt.ban.user'
    _description = 'Ban User'

    name = fields.Char('Username')
    user_id = fields.Many2one('res.users','User')
    end_datetime = fields.Datetime('End Time')
    active = fields.Boolean('Active',default=True)
    ho_id = fields.Many2one('tt.agent', string="Head Office", domain=[('is_ho_agent', '=', True)])

    def ban_user_api(self,req,context):
        self.ban_user(req['user_id'], req['duration_minutes'], context)
        return ERR.get_no_error()

    def ban_user(self,user_id,duration_minutes, context={}):
        user_obj = self.env['res.users'].browse(user_id)
        if not user_obj.create_date:
            raise Exception("User not found.")
        ho_agent_obj = None
        if context:
            agent_obj = self.env['tt.agent'].search([('id', '=', context['co_agent_id'])], limit=1)
            if agent_obj:
                ho_agent_obj = agent_obj.ho_id
        dom = [('user_id','=',user_obj.id)]
        if not ho_agent_obj:
            ho_agent_obj = user_obj.ho_id
        dom.append(('ho_id','=',ho_agent_obj.id))
        current_ban_time = self.search(dom, order='id desc',limit=1)
        if current_ban_time:
            current_ban_time.write({
                'end_datetime': datetime.now() + timedelta(minutes=duration_minutes)
            })
        else:
            self.create({
                'name': user_obj.name,
                'user_id': user_obj.id,
                'end_datetime': datetime.now() + timedelta(minutes=duration_minutes),
                'ho_id': ho_agent_obj.id if ho_agent_obj else ''
            })
        user_obj.is_banned = True

    def unban_user_from_button(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 57')
        self.unban_user(self.user_id.id)

    def unban_user(self,user_id):
        for rec in self.search([('user_id','=',user_id)]):
            rec.user_id.is_banned = False
            rec.active = False
            self.env["tt.pin.log"].ban_user_bypass_pin_log(user_id)
