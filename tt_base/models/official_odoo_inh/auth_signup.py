from odoo import http, api, fields, models
import logging
from odoo.http import request
from odoo.addons.auth_signup.controllers.main import AuthSignupHome

_logger = logging.getLogger(__name__)


class AuthSignupHomeInherit(AuthSignupHome):

    def get_auth_signup_config(self):
        original_values = super(AuthSignupHomeInherit,self).get_auth_signup_config()
        qcontext = self.get_auth_signup_qcontext()
        redirect_param = '/'
        user_obj = request.env['res.users'].sudo().search([('login', '=', qcontext.get('login'))], limit=1)
        if user_obj and user_obj.agent_id:
            ho_obj = user_obj.agent_id.get_ho_parent_agent()
            if ho_obj:
                redirect_param = ho_obj.redirect_url_signup and ho_obj.redirect_url_signup or '/'
            elif user_obj.ho_id:
                ho_obj = user_obj.ho_id
                redirect_param = ho_obj.redirect_url_signup and ho_obj.redirect_url_signup or '/'

        # original_values.update({
        #     'redirectorbis': request.env['ir.config_parameter'].sudo().get_param('tt_base.redirect_url_signup_orbis')
        # })
        original_values.update({
            'redirectorbis': redirect_param
        })
        return original_values
