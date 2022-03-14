from odoo import http
import odoo, datetime
import werkzeug
import logging
from odoo.http import request
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from werkzeug import urls

_logger = logging.getLogger(__name__)

def content_disposition(filename):
    filename = odoo.tools.ustr(filename)
    escaped = urls.url_quote(filename, safe='')

    return "attachment; filename*=UTF-8''%s" % escaped
class Database(http.Controller):
    @http.route('/web/database/backup_custom_rodex', type='http', auth="none", methods=['GET'], csrf=False)
    def backup_custom_rodex(self, master_pwd, name, backup_format='zip'):
        try:
            odoo.service.db.check_super(master_pwd)
            ts = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
            filename = "%s_%s.%s" % (name, ts, backup_format)
            headers = [
                ('Content-Type', 'application/octet-stream; charset=binary'),
                ('Content-Disposition', content_disposition(filename)),
            ]
            dump_stream = odoo.service.db.dump_db(name, None, backup_format)
            response = werkzeug.wrappers.Response(dump_stream, headers=headers, direct_passthrough=True)
            return response
        except Exception as e:
            _logger.exception('Database.backup')
            error = "Database backup error: %s" % (str(e) or repr(e))
            return self._render_template(error=error)

class AuthSignupHomeInherit(AuthSignupHome):

    def get_auth_signup_config(self):
        original_values = super(AuthSignupHomeInherit,self).get_auth_signup_config()
        original_values.update({
            'redirectrodex': request.env['ir.config_parameter'].sudo().get_param('tt_base.redirect_url_rodex')
        })
        return original_values