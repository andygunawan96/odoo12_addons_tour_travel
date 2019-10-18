from odoo import api, fields, models, _
import os


class TtUploadFile(models.Model):
    _name = 'tt.upload.center'
    _description = 'Upload Center'

    seq_id = fields.Char('Sequence Code')
    name = fields.Char('Reference Name')
    filename = fields.Char('Filename', readonly=True)
    file_reference = fields.Text('File Reference',readonly=True)
    path = fields.Char('Path', readonly=True)
    url = fields.Char('URL')
    agent_id = fields.Many2one('tt.agent','Owner')
    active = fields.Boolean('Active',default=True)
    will_be_deleted_date = fields.Date('Will be deleted on')


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
            print("UNLINK OVERRIDE")
            ##remove the real file
            if rec.path:
                if os.path.exists(rec.path):
                    os.remove(rec.path)
            return super(TtUploadFile, self).unlink()

