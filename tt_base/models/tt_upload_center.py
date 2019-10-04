from odoo import api, fields, models, _

class TtUploadFile(models.Model):
    _name = 'tt.upload.center'
    _description = 'Upload Center'

    name = fields.Char('Reference Name')
    filename = fields.Char('Filename', readonly=True)
    file_reference = fields.Text('File Reference',readonly=True)
    path = fields.Char('Path', readonly=True)
    url = fields.Char('URL')

    @api.model
    def create(self, vals_list):
        vals_list['name'] = '%s %s' % (vals_list['filename'],vals_list['file_reference'])
        super(TtUploadFile, self).create(vals_list)
