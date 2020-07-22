from odoo import api,models,fields
from ...tools.ERR import RequestException
from ...tools import ERR
from datetime import datetime

class TtAgentThirdPartyKey(models.Model):
    _name = 'tt.agent.third.party.key'
    _inherit = 'tt.history'
    _rec_name = 'name'
    _description = 'Rodex Model Agent 3rd Party Key'

    name = fields.Char('Name', required=True, default='New Key')
    key = fields.Char('Key')
    active = fields.Boolean('acitve',default=True)
    agent_id = fields.Many2one('tt.agent','Agent')
    is_connected = fields.Boolean('Connected',default=False)
    connected_account_id = fields.Char('Connected Account ID')
    connected_account_name = fields.Char('Connected Account ID')
    connected_time = fields.Datetime('Connected Time', default=fields.Datetime.now())

    def validate_key(self,req,is_connected=False):
        found_key = self.search([('key', '=', req['key']), ('is_connected', '=', is_connected)])
        if not found_key:
            raise RequestException(1033)
        return found_key

    def external_connect_key_api(self,req,context):
        key_obj = self.validate_key(req)
        if key_obj:
            key_obj.write({
                'is_connected': True,
                'connected_account_id': req['id'],
                'connected_account_name': req['name'],
                'connected_time': datetime.now()
            })
            return ERR.get_no_error()
        raise RequestException(1033)

    def external_get_balance_api(self,req,context):
        key_obj = self.validate_key(req,True)
        if key_obj:
            return ERR.get_no_error({'balance': key_obj.agent_id.balance})
        raise RequestException(1033)

    def external_payment_api(self,req,context):
        key_obj = self.validate_key(req,True)
        if key_obj:
            if key_obj.agent_id.balance >= req['payment_amount']:
                next_seq = self.env['ir.sequence'].next_by_code('tt.agent.third.party.key.payment')
                new_ledger = self.env['tt.ledger'].create_ledger_vanilla(
                    'tt.agent.third.party.key',
                    key_obj.id,
                    next_seq,
                    '%s %s' % (next_seq, req['reference']),
                    datetime.now(),
                    2,
                    self.env.ref('base.IDR').id,
                    context['co_uid'],
                    key_obj.agent_id.id,
                    False,
                    0,
                    req['payment_amount'],
                    'External payment from %s by %s, %s' % (key_obj.name,key_obj.connected_account_name,req['reference']),
                    {'pnr': req['reference']}
                )
                return ERR.get_no_error({
                    'ledger_reference': new_ledger.name,
                })
            raise RequestException(1007)
        raise RequestException(1033)

    def external_reverse_payment_api(self,req,context):
        key_obj = self.validate_key(req,True)
        if key_obj:
            ledger_obj = self.env['tt.ledger'].search([('name','=',req['ledger_reference'])])
            if ledger_obj:
                reversed_ledger = ledger_obj.reverse_ledger()
                return ERR.get_no_error({
                    'ledger_reference':reversed_ledger.name
                })
            raise RequestException(1033)
