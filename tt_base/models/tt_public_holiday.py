from odoo import api, fields, models, _


class TtPublicHoliday(models.Model):
    _name = 'tt.public.holiday'
    _description = 'Public Holiday'
    _order = 'date'

    name = fields.Char('Name')
    date = fields.Date('Date')
    country_id = fields.Many2one('res.country', 'Country', default=lambda self: self.env.user.company_id.country_id.id)
    active = fields.Boolean('Active', default=True)

    def ph_fmt(self):
        return {
            self.date: self.name
        }

    def get_public_holiday_api(self, data, context):
        start_date = data['start_date']
        end_date = data.get('end_date') and data['end_date'] or data['start_date']

        res = [{'date': rec.date, 'name': rec.name} for rec in self.sudo().search([('date', '>=', start_date), ('date', '<=', end_date),
                                                                    ('country_id', '=', int(data['country_id'])),
                                                                    ('active', '=', True)])]
        return {
            'error_code': 0,
            'error_msg': '',
            'response': res,
        }

