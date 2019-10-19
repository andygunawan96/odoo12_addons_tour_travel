from odoo import models, fields, api, _

AMOUNT_TYPE = [
    ('amount', 'Amount'),
    ('percentage', 'Percentage')
]


class AgentRegistrationPromotion(models.Model):
    _name = 'tt.agent.registration.promotion'
    _description = 'Rodex Model'
    _order = 'sequence desc'

    name = fields.Char('Name', required=True)
    active = fields.Boolean('Active', default=True)
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type yang Merekrut')
    agent_type_ids = fields.One2many('tt.agent.registration.promotion.agent.type', 'promotion_id',
                                     'Agent2 Type yang akan Direkrut',
                                     help='''Agent Type yang berhak untuk mendapatkan promo.''')
    description = fields.Char('Description')
    default = fields.Boolean('Default Commission')
    sequence = fields.Integer('Sequence')

    def get_name(self):
        # Perlu diupdate lagi, sementara menggunakan ini
        if self.agent_type_id:
            res = '%s - %s' % (self.agent_type_id.code.title(), self.name)
            return res
        else:
            return self.name

    def write(self, values):
        res = super(AgentRegistrationPromotion, self).write(values)
        if not values.get('name'):
            self.write({'name': self.get_name()})
        return res


class AgentRegistrationPromotionAgentType(models.Model):
    _name = 'tt.agent.registration.promotion.agent.type'
    _description = 'Rodex Model'

    promotion_id = fields.Many2one('tt.agent.registration.promotion', 'Promotion', readonly=True)
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id)
    discount_amount_type = fields.Selection(AMOUNT_TYPE, 'Discount Amount Type')
    discount_amount = fields.Float('Discount Amount')
    preview_price = fields.Monetary('Preview Price', default=0, compute='set_preview_price')
    line_ids = fields.One2many('tt.agent.registration.promotion.line', 'res_id', 'Lines')

    @api.depends('agent_type_id', 'discount_amount', 'discount_amount_type')
    @api.onchange('agent_type_id', 'discount_amount', 'discount_amount_type')
    def set_preview_price(self):
        for rec in self:
            if rec.agent_type_id and rec.discount_amount:
                if rec.discount_amount_type:
                    if rec.discount_amount_type == 'amount':
                        rec.preview_price = rec.agent_type_id.registration_fee - rec.discount_amount
                    elif rec.discount_amount_type == 'percentage':
                        rec.preview_price = rec.agent_type_id.registration_fee - (rec.agent_type_id.registration_fee / 100 * rec.discount_amount)


class AgentRegistrationPromotionLine(models.Model):
    _name = 'tt.agent.registration.promotion.line'
    _description = 'Rodex Model'

    res_id = fields.Many2one('tt.agent.registration.promotion.agent.type', 'Res ID')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id)
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type')
    amount = fields.Monetary('Amount')
