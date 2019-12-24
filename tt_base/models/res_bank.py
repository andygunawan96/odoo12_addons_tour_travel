from odoo import models, fields, api
import random


class ResBank(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.bank'
    _rec_name = 'name'
    _description = 'Tour & Travel - Bank'

    name = fields.Char('Name')
    logo = fields.Binary('Bank Logo', attachment=True)
    code = fields.Char('Bank Code')
    bic = fields.Char('Bank Identifier Code', help='BIC / Swift')
    agent_bank_ids = fields.One2many('agent.bank.detail', 'bank_id', 'Agent Bank')
    customer_bank_ids = fields.One2many('customer.bank.detail', 'bank_id', 'Customer Bank')
    payment_acquirer_ids = fields.One2many('payment.acquirer', 'bank_id', 'Payment Acquirer')
    active = fields.Boolean('Active', default=True)
    image = fields.Binary('Bank Logo', attachment=True)
    image_id = fields.Many2one('tt.upload.center', compute="_compute_image_id",store=True)

    @api.depends('image')
    def _compute_image_id(self):
        for rec in self:
            if rec.image:
                res = self.env['tt.upload.center.wizard'].upload_file_api(
                    {
                        'filename': rec.name and '%s.jpg' % (rec.name) or 'bank%d.jpg' % (random.randint(0,1000)),
                        'file_reference': 'master bank image',
                        'file': rec.image,
                    },
                    {
                        'co_agent_id': self.env.user.agent_id.id,
                        'co_uid': self.env.user.id,
                    }
                )
                if res['error_code'] != 0:
                    return
                rec.image_id.unlink()
                new_image_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1).id
                rec.update({
                    'image_id': new_image_id
                })