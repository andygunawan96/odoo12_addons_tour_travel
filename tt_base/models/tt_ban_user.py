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

    def ban_user_api(self,req,context):
        self.ban_user(req['user_id'],
                      req['duration_minutes'])
        return ERR.get_no_error()

    def ban_user(self,user_id,duration_minutes):
        user_obj = self.env['res.users'].browse(user_id)
        if not user_obj.create_date:
            raise Exception("User not found.")
        current_ban_time = self.search([('user_id','=',user_obj.id)],order='id desc',limit=1)
        if current_ban_time:
            current_ban_time.write({
                'end_datetime': datetime.now() + timedelta(minutes=duration_minutes)
            })
        else:
            self.create({
                'name': user_obj.name,
                'user_id': user_obj.id,
                'end_datetime': datetime.now() + timedelta(minutes=duration_minutes)
            })
        user_obj.is_banned = True

    def unban_user_from_button(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake.')
        self.unban_user(self.user_id.id)

    def unban_user(self,user_id):
        for rec in self.search([('user_id','=',user_id)]):
            rec.user_id.is_banned = False
            rec.active = False
