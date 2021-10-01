from odoo import api, fields, models
from odoo.exceptions import UserError
import os


class TtUploadFile(models.Model):
    _name = 'tt.upload.center'
    _description = 'Upload Center'
    _order = 'create_date desc'

    seq_id = fields.Char('Sequence ID', index=True, readonly=True)
    name = fields.Char('Reference Name')
    filename = fields.Char('Filename', readonly=True)
    file_reference = fields.Text('File Reference',readonly=True)
    path = fields.Char('Path', readonly=True)
    url = fields.Char('URL', readonly=True)
    agent_id = fields.Many2one('tt.agent','Owner', readonly=True)
    upload_uid = fields.Many2one('res.users','Uploaded By', readonly=True)
    active = fields.Boolean('Active',default=True)
    will_be_deleted_date = fields.Date('Will be deleted on')
    will_be_deleted_time = fields.Datetime('Will be deleted on', readonly=True)
    sequence = fields.Integer('Sequence',default=100)

    @api.model
    def create(self, vals_list):
        if len(vals_list) <= 0:
            return self.search([],limit=1)
        vals_list['name'] = '%s %s' % (vals_list.get('filename'),vals_list.get('file_reference'))
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('tt.upload.center')
        return super(TtUploadFile, self).create(vals_list)

    @api.multi
    def unlink(self):
        for rec in self:
            # has_admin = ({self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids)))
            has_admin = self.env.user.has_group('base.group_system')
            if self.env.user.id != rec.upload_uid.id and not has_admin:
                raise UserError('You can only delete files uploaded by you!')
            ##remove the real file
            if rec.path:
                if os.path.exists(rec.path):
                    os.remove(rec.path)
        return super(TtUploadFile, self).unlink()

