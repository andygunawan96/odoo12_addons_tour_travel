from odoo import api,fields,models

##limit rebooking dupe for airlines and probably airlines

class TtAirlineRule(models.Model):

    _name = 'tt.limiter.rule'
    _description = 'Limiter Rule'

    name = fields.Char('Name')
    provider_type_id = fields.Char('Provider Type Id')
    code = fields.Char('Code')
    rebooking_limit = fields.Integer('Rebooking Limit')
    adm = fields.Char('ADM /P/R')


class TtWhitelistedName(models.Model):

    _name = 'tt.whitelisted.name'
    _description = 'Whitelisted Name'

    name = fields.Char('Name')
    chances_left = fields.Integer('Chances Left')

class TtWhitelistedPassport(models.Model):
    _name = 'tt.whitelisted.passport'
    _description = 'Whitelisted Passport'

    passport = fields.Char('Passport Number')
    chances_left = fields.Integer('Chances Left')