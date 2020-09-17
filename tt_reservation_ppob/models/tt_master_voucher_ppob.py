from odoo import api, fields, models
from odoo.exceptions import UserError
from ...tools import variables
from datetime import datetime
import json, logging

_logger = logging.getLogger(__name__)


class TtMasterVoucherPPOB(models.Model):
    _inherit = 'tt.history'
    _name = 'tt.master.voucher.ppob'
    _rec_name = 'display_name'
    _order = 'sequence'
    _description = 'Rodex Model'

    name = fields.Char('Operator Name', default='Unnamed')
    code = fields.Char('Code', default='')
    value = fields.Integer('Nominal', default=0)
    type = fields.Selection([('prepaid_mobile', 'Prepaid Mobile'), ('game', 'Game Voucher')], 'Voucher Type', default='game')
    sequence = fields.Integer('Sequence', default=50)
    display_name = fields.Char('Display Name', compute='_compute_display_name')
    active = fields.Boolean('Active', default=True)

    def get_rupiah(self, price):
        try:
            if price:
                temp = int(price)
                positif = temp > -1 and True or False

                temp = str(temp)
                temp = temp.split('-')[-1]
                pj = len(str(temp.split('.')[0]))
                priceshow = ''
                for x in range(pj):
                    if (pj - x) % 3 == 0 and x != 0:
                        priceshow += ','
                    priceshow += temp[x]
                if len(temp.split('.')) == 2:
                    for x in range(pj, len(temp)):
                        priceshow += temp[x]

                if not positif:
                    priceshow = '-' + priceshow
                return priceshow
            else:
                return ''
        except Exception as e:
            return price

    @api.depends('name', 'value')
    @api.onchange('name', 'value')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.name + ' - ' + rec.get_rupiah(rec.value)
