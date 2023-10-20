# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models
from odoo.http import request
from odoo.exceptions import UserError, Warning
from odoo.tools.translate import _


class IrHttp(models.AbstractModel):

    _inherit = 'ir.http'

    @classmethod
    def _authenticate(cls, auth_method='user'):
        res = super(IrHttp, cls)._authenticate(auth_method=auth_method)
        if request and request.session and request.session.uid:
            # try:
            #     request.env.user._auth_timeout_check()
            # except:
            #     # TODO Pop UP + f5
            #     raise Warning('Your Odoo session expired. Please refresh the current web page.')
            request.env.user._auth_timeout_check()
        return res
