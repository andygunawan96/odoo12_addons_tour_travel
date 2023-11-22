from odoo import api, fields, models, _
import base64,hmac,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError


class TtInputPinWizard(models.TransientModel):
    _name = "tt.input.pin.wizard"
    _description = 'Input Pin Wizard'

    pin = fields.Char('PIN', required=True)
    res_model = fields.Char('Related Model Name', index=True, readonly=True)
    res_id = fields.Integer('Related Model ID', index=True, help='Id of the followed resource', readonly=True)

    def submit_input_pin(self):
        resv_obj = self.env[self.res_model].browse(int(self.res_id))
        encrypted_pin = hmac.new(str.encode('orbisgoldenway'), str.encode(self.pin), digestmod=hashlib.sha256).hexdigest()
        if self.res_model == 'tt.reservation.offline':
            resv_obj.action_validate(encrypted_pin)
        elif self.res_model == 'tt.reservation.visa':
            resv_obj.action_in_process_visa(encrypted_pin)
        else:
            raise UserError('Invalid Model!')
