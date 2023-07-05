from odoo import api, fields, models, _


class TtPublicHoliday(models.Model):
    _name = 'tt.public.holiday'
    _description = 'Public Holiday'
    _order = 'date'

    name = fields.Char('Name')
    date = fields.Date('Date')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], required=False, default=lambda self: self.env.user.ho_id)
    country_id = fields.Many2one('res.country', 'Country', default=lambda self: self.env.user.company_id.country_id.id)
    active = fields.Boolean('Active', default=True)

    def ph_fmt(self):
        return {
            self.date: self.name
        }

    def get_public_holiday_api(self, data, context):
        start_date = data['start_date']
        end_date = data.get('end_date') and data['end_date'] or data['start_date']
        res = []
        if context:
            if context.get('co_ho_seq_id'):
                res = [{'date': rec.date, 'name': rec.name} for rec in self.sudo().search([('date', '>=', start_date), ('date', '<=', end_date),
                                                                    ('country_id', '=', int(data['country_id'])),
                                                                    ('active', '=', True), ('ho_id.id', '=', context['co_ho_id'])])]
        else: ## DARI CRON MEDICAL
            # ho_list = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
            ho_obj = None
            if self.env.user.ho_id:
                ho_obj = self.env.user.ho_id
            elif self.env.user.agent_id:
                ho_obj = self.env.user.agent_id.ho_id
            if ho_obj:
                res = [{'date': rec.date, 'name': rec.name} for rec in
                   self.sudo().search([('date', '>=', start_date), ('date', '<=', end_date),
                                       ('country_id', '=', int(data['country_id'])),
                                       ('active', '=', True), ('ho_id.id', '=', ho_obj.id)])]

        return {
            'error_code': 0,
            'error_msg': '',
            'response': res,
        }

