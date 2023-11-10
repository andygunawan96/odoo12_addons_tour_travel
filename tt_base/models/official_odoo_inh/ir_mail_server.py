from odoo import api,models,fields
from odoo.exceptions import UserError
from odoo.addons.auth_signup.models.res_partner import SignupError, now
import os
import pickle
import codecs
from ....tools import ERR, gmail
import logging
import time
import json
from odoo import _
from odoo.tools import ustr
from ....tools.db_connector import GatewayConnector

_logger = logging.getLogger(__name__)
def_folder = '/var/log/tour_travel/gmailcredentials'

class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    smtp_user = fields.Char(string='Username', help="Optional username for SMTP authentication",
                            groups='base.group_erp_manager,tt_base.group_user_data_level_3')
    smtp_pass = fields.Char(string='Password', help="Optional password for SMTP authentication",
                            groups='base.group_erp_manager,tt_base.group_user_data_level_3')
    is_gmail = fields.Boolean('Gmail Oauth2')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id)

    def _check_folder_exists(self, folder_path):
        if not os.path.exists(folder_path):
            os.mkdir(folder_path)

    def set_email_from_gateway(self, data):
        self._check_folder_exists(def_folder)
        dom = [('smtp_user', '=', data['email'])]
        if data['ho_id']:
            dom.append(('ho_id','=', data['ho_id']))
        mail_server = self.search(dom, limit=1)
        if not mail_server:
            data_create = {
                "name": data['email'],
                "smtp_user": data['email'],
                "is_gmail": True,
                "smtp_host": "Google Mail",
                "smtp_port": "443",
                "smtp_encryption": "none"
            }
            if data.get('ho_id'):
                data_create.update({
                    'ho_id': data['ho_id']
                })
            mail_server = self.create(data_create)
        if data['ho_id']:
            agent_obj = self.env['tt.agent'].browse(data['ho_id'])
            if agent_obj and not agent_obj.email_server_id:
                agent_obj.email_server_id = mail_server

        ## JSON CREDS
        _file = open("%s/%s.json" % (def_folder, data['email']), 'w+')
        _file.write(data['google_credential_json'])
        _file.close()

        ## FILE UPDATE STATUS EMAIL
        _file = open("%s/update_status_email_%s.txt" % (def_folder, data['email']), 'w')
        _file.write(json.dumps({
            "is_update": False,
            "last_update": time.time(),
        }))
        _file.close()

        ## PICKLE
        credential = pickle.loads(codecs.decode(data['credential'].encode(), "base64"))
        with open("%s/%s.pickle" % (def_folder, data['email']), "wb") as token:
            pickle.dump(credential, token)
        return ERR.get_no_error()

    #########OVERRIDE FUNCTION ODOO OFFICIAL#############
    #override odoo official connect function
    def test_smtp_connection(self):
        if self.is_gmail:
            connection = self.connect()
            if connection:
                raise UserError('Connection Success')
            else:
                raise UserError('Connection Failed')
        else:
            return self.test_smtp_connection_custom_odoo()

    @api.multi
    def test_smtp_connection_custom_odoo(self):
        for server in self:
            smtp = False
            try:
                smtp = self.connect(mail_server_id=server.id)
                # simulate sending an email from current user's address - without sending it!
                email_from, email_to = self.smtp_user, 'noreply@odoo.com'
                if not email_from:
                    raise UserError(_('Please configure an email on the current user to simulate '
                                      'sending an email message via this outgoing server'))
                # Testing the MAIL FROM step should detect sender filter problems
                (code, repl) = smtp.mail(email_from)
                if code != 250:
                    raise UserError(_('The server refused the sender address (%(email_from)s) '
                                      'with error %(repl)s') % locals())
                # Testing the RCPT TO step should detect most relaying problems
                (code, repl) = smtp.rcpt(email_to)
                if code not in (250, 251):
                    raise UserError(_('The server refused the test recipient (%(email_to)s) '
                                      'with error %(repl)s') % locals())
                # Beginning the DATA step should detect some deferred rejections
                # Can't use self.data() as it would actually send the mail!
                smtp.putcmd("data")
                (code, repl) = smtp.getreply()
                if code != 354:
                    raise UserError(_('The server refused the test connection '
                                      'with error %(repl)s') % locals())
            except UserError as e:
                # let UserErrors (messages) bubble up
                raise e
            except Exception as e:
                raise UserError(_("Connection Test Failed! Here is what we got instead:\n %s") % ustr(e))
            finally:
                try:
                    if smtp:
                        smtp.close()
                except Exception:
                    # ignored, just a consequence of the previous exception
                    pass
        raise UserError(_("Connection Test Succeeded! Everything seems properly set up!"))

    def connect(self, host=None, port=None, user=None, password=None, encryption=None,
                smtp_debug=False, mail_server_id=None):
        # login using pickle here
        if self.is_gmail:
            connection = None
            email_name = self.get_email_name()
            self._check_folder_exists(def_folder)
            if os.path.exists("%s/%s.pickle" % (def_folder, email_name)):
                with open("%s/%s.pickle" % (def_folder, email_name), "rb") as token:
                    creds = pickle.load(token)
                try:
                    connection = gmail.connect_gmail(creds, email_name)
                except:
                    data = {
                        'code': 9999,
                        'title': 'ERROR EMAIL BACKEND',
                        'message': 'Error refresh token email backend %s' % (self.get_email_name()),
                    }
                    context = {
                        "co_ho_id": self.ho_id.id
                    }
                    GatewayConnector().telegram_notif_api(data, context)
            return connection
        else:
            return super(IrMailServer, self).connect(host, port, user, password, encryption, smtp_debug, mail_server_id)

    def get_email_name(self):
        return self.smtp_user

class IrModelData(models.Model):
    _inherit = "ir.model.data"

    def multi_set_to_updatable(self, vals=1):
        for rec in self:
            rec.noupdate = vals == 1