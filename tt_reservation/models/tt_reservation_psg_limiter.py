from odoo import api,fields,models

##limit rebooking dupe for airlines and probably airlines

class TtAirlineRule(models.Model):

    _name = 'tt.limiter.rule'

    name = fields.Char('Airline Name')
    code = fields.Char('Code')
    rebooking_limit = fields.Integer('Rebooking Limit')
    adm = fields.Char('ADM /P/R')


class TtWhitelistedName(models.Model):

    _name = 'tt.whitelisted.name'

    name = fields.Char('Name')
    chances_left = fields.Integer('Chances Left')

class TtWhitelistedPassport(models.Model):
    _name = 'tt.whitelisted.passport'

    passport = fields.Char('Passport Number')
    chances_left = fields.Integer('Chances Left')