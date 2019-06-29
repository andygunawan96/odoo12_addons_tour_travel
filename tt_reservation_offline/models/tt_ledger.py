from odoo import api, fields, models, _

SERVICE_TYPE = [
    ('airline', 'Airline'),
    ('train', 'Train'),
    ('ship', 'Ship'),
    # ('visa', 'Visa'),
    ('cruise', 'Cruise'),
    ('car', 'Car/Rent'),
    ('bus', 'Bus'),
    ('tour', 'Tours'),
    ('merchant', 'Merchandise'),
    ('others', 'Other(s)'),
    # ('passport', 'Passport'),
    ('activity', 'Activity'),
    ('travel_doc', 'Travel Doc.'),
    ('hotel', 'Hotel')
]


class TtLedger(models.Model):
    _inherit = 'tt.ledger'

    issued_offline_id = fields.Many2one('issued.offline', 'Issued Offline')
    provider_type_id = fields.Many2one('tt.provider.type', 'Service Type')
    display_provider_name = fields.Char(string='Name')

    rel_agent_name = fields.Char('Partner', help='Used to know Network commission from')
    issued_uid = fields.Many2one('res.users', 'Issued By', related=False)

    def get_rel_agent_id(self):
        for rec in self:
            rec.rel_agent_name = rec.issued_offline_id and rec.issued_offline_id.sub_agent_id.name or False

    def change_vendor_to_provider(self):
        for rec in self:
            if rec.issued_offline_id:
                rec.display_provider_name = rec.issued_offline_id.provider

    def remove_name_pnr(self):
        for rec in self:
            if rec.transaction_type == 3:
                rec.pnr = ''
                rec.display_provider_name = ''
