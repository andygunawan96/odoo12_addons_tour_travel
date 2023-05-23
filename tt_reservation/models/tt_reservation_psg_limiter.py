from odoo import api,fields,models

##limit rebooking dupe for airlines and probably airlines

class TtAirlineRule(models.Model):

    _name = 'tt.limiter.rule'
    _description = 'Limiter Rule'
    _rec_name = 'carrier_id'

    carrier_id = fields.Many2one('tt.transport.carrier','Carrier', required=True)
    carrier_code = fields.Char('Code',related="carrier_id.code")
    provider_type_id = fields.Many2one('tt.provider.type','Provider Type',related='carrier_id.provider_type_id')
    passenger_check_type = fields.Selection([('passenger', 'Passenger'),
                                             ('contact', 'Contact')],'Pax Check Type',
                                            default='passenger')
    rebooking_limit = fields.Integer('Rebooking Limit',default=2,help="Book while another booking is still valid")
    churning_limit = fields.Integer('Churning Limit',default=2,help="Cancel then rebook")
    adm = fields.Char('ADM /P/R', default="30USD")
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)])
    active = fields.Boolean("Active",default=True)

class TtWhitelistedName(models.Model):
    _name = 'tt.whitelisted.name'
    _description = 'Whitelisted Name'

    name = fields.Char('Name')
    chances_left = fields.Integer('Chances Left')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)])

class TtWhitelistedPassport(models.Model):
    _name = 'tt.whitelisted.passport'
    _description = 'Whitelisted Passport'
    _rec_name = 'passport'

    passport = fields.Char('Passport Number')
    chances_left = fields.Integer('Chances Left')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)])
