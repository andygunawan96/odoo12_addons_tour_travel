from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from ...tools import util


class InactiveDormantUserWizard(models.TransientModel):
    _name = "inactive.dormant.user.wizard"
    _description = 'Archive Dupe Customer Wizard'

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id)
    dormant_days_amount = fields.Integer('Days Since Last Login', default=lambda self: self.env.user.ho_id.dormant_days_inactive)

    def inactive_dormant_user(self):
        if not ({self.env.ref('tt_base.group_user_data_level_4').id, self.env.ref('base.group_erp_manager').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 468')

        self.env['res.users'].inactive_all_dormant_users(self.ho_id.id, self.dormant_days_amount)
