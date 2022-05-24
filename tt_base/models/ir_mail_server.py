from odoo import api,models,fields
from odoo.exceptions import UserError
from odoo.addons.auth_signup.models.res_partner import SignupError, now
import os
import pickle
import codecs
from ...tools import ERR, gmail
import logging
_logger = logging.getLogger(__name__)
def_folder = '/var/log/tour_travel/gmailcredentials'

class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    smtp_user = fields.Char(string='Username', help="Optional username for SMTP authentication",
                            groups='base.group_erp_manager')
    smtp_pass = fields.Char(string='Password', help="Optional password for SMTP authentication",
                            groups='base.group_erp_manager')

    def _check_folder_exists(self, folder_path):
        if not os.path.exists(folder_path):
            os.mkdir(folder_path)
        if not os.path.exists("%s/credentials.json" % folder_path):
            path = os.path.dirname(__file__)
            for idx, rec in enumerate(path.split('/')):
                if 'tt' in rec:
                    break
            path = path.split('/')[0:idx]
            path.append('tools')

            file = open("%s/credentials.json" % ("/".join(path)), "r")
            data = file.read()
            file.close()
            _file = open("%s/credentials.json" % def_folder, 'w+')
            _file.write(data)
            _file.close()

    def set_email_from_gateway(self, data):
        self._check_folder_exists(def_folder)
        _file = open("%s/email_name.txt" % def_folder, 'w+')
        _file.write(data['email'])
        _file.close()
        credential = pickle.loads(codecs.decode(data['credential'].encode(), "base64"))
        with open("%s/token.pickle" % def_folder, "wb") as token:
            pickle.dump(credential, token)
        return ERR.get_no_error()

    def test_smtp_oauth2_connection(self):
        self._check_folder_exists(def_folder)
        if os.path.exists("%s/token.pickle" % (def_folder)):
            with open("%s/token.pickle" % (def_folder), "rb") as token:
                creds = pickle.load(token)
            connection = gmail.connect_gmail(creds)
            if connection:
                raise UserError('Connection Success')
            else:
                raise UserError('Connection Failed')
        raise UserError('Connection Failed')

    #########OVERRIDE FUNCTION ODOO OFFICIAL#############
    #override odoo official connect function
    def test_smtp_connection(self):
        connection = self.connect()
        if connection:
            raise UserError('Connection Success')
        else:
            raise UserError('Connection Failed')

    def connect(self):
        # login using pickle here
        connection = None
        self._check_folder_exists(def_folder)
        if os.path.exists("%s/token.pickle" % (def_folder)):
            with open("%s/token.pickle" % (def_folder), "rb") as token:
                creds = pickle.load(token)
            connection = gmail.connect_gmail(creds)
        return connection

    def get_email_name(self):
        self._check_folder_exists(def_folder)
        file = open("%s/email_name.txt" % def_folder, "r")
        email = file.read()
        file.close()
        return email

class IrModelData(models.Model):
    _inherit = "ir.model.data"

    def multi_set_to_updatable(self, vals=1):
        for rec in self:
            rec.noupdate = vals == 1