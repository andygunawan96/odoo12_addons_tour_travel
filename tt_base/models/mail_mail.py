from odoo import api,models,fields
from ...tools import ERR, gmail
import logging, traceback
_logger = logging.getLogger(__name__)
import re
regex_check_email_valid = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

import base64
import datetime
import logging
import psycopg2
import threading
import re

from collections import defaultdict
from email.utils import formataddr

from odoo import _, api, fields, models
from odoo import tools
from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.tools.safe_eval import safe_eval
class MailMail(models.Model):
    _inherit = "mail.mail"

    def is_email_valid(self, email_str_list):

        # pass the regular expression
        # and the string into the fullmatch() method
        check_one_email_valid = False
        for email in email_str_list.split(','):
            if (re.fullmatch(regex_check_email_valid, email)):
                check_one_email_valid = True
        return check_one_email_valid

    @api.multi
    def send(self, auto_commit=False, raise_exception=False):
        """ Sends the selected emails immediately, ignoring their current
            state (mails that have already been sent should not be passed
            unless they should actually be re-sent).
            Emails successfully delivered are marked as 'sent', and those
            that fail to be deliver are marked as 'exception', and the
            corresponding error mail is output in the server logs.

            :param bool auto_commit: whether to force a commit of the mail status
                after sending each mail (meant only for scheduler processing);
                should never be True during normal transactions (default: False)
            :param bool raise_exception: whether to raise an exception if the
                email sending process has failed
            :return: True
        """
        for server_id, batch_ids in self._split_by_server():
            for batch_id in batch_ids:
                try:
                    rec = self.browse(batch_id)
                    if rec.state == 'outgoing':
                        resv_obj = self.env[rec.model].browse(rec.res_id)
                        if hasattr(resv_obj, 'agent_id'):
                            ho_agent_obj = resv_obj.agent_id.get_ho_parent_agent()
                            if ho_agent_obj.email_server_id:
                                if ho_agent_obj.email_server_id.is_gmail:
                                    self.send_gmail(batch_id, ho_agent_obj.email_server_id, auto_commit, raise_exception)
                                else:
                                    self.send_smtp(server_id, batch_id, ho_agent_obj.email_server_id, auto_commit, raise_exception)
                except Exception as e:
                    _logger.error("%s, %s" % (str(e), traceback.format_exc()))
            # mail_obj = self.env[]


    def send_smtp(self, server_id, batch_id, email_server_obj, auto_commit=False, raise_exception=False):
        smtp_session = None
        try:
            smtp_session = email_server_obj.connect(mail_server_id=email_server_obj.id)
        except Exception as exc:
            if raise_exception:
                # To be consistent and backward compatible with mail_mail.send() raised
                # exceptions, it is encapsulated into an Odoo MailDeliveryException
                raise MailDeliveryException(_('Unable to connect to SMTP Server'), exc)
            else:
                batch = self.browse(batch_id)
                batch.write({'state': 'exception', 'failure_reason': exc})
                batch._postprocess_sent_message(success_pids=[], failure_type="SMTP")
        else:
            self.browse(batch_id)._send(
                auto_commit=auto_commit,
                raise_exception=raise_exception,
                smtp_session=smtp_session)
            _logger.info('Sent batch %s emails via mail server ID #%s', 1, server_id)
        finally:
            if smtp_session:
                smtp_session.quit()

    def send_gmail(self, batch_id, email_server_obj, auto_commit=False, raise_exception=False):
        google_auth = email_server_obj.connect()
        if google_auth:
            email_user_account = email_server_obj.get_email_name()
            try:
                # kalau mau ngirim di cek juga statenya
                rec = self.browse(batch_id)
                if rec.state == 'outgoing':
                    if self.is_email_valid(rec.email_to) or self.is_email_valid(rec.email_cc):
                        attachments_list_file = []
                        for attachment_obj in rec.attachment_ids:
                            attachments_list_file.append(attachment_obj)
                        destination_email = {
                            'to': rec.email_to if self.is_email_valid(rec.email_to) else '',
                            'cc': rec.email_cc if self.is_email_valid(rec.email_cc) else '',
                            'bcc': ''
                        }
                        gmail.send_message(service=google_auth, destination=destination_email, obj=rec.subject,
                                           body=rec.body_html, attachments=attachments_list_file, type='html',
                                           email_account=email_user_account)
                        # setelah ngirim di ganti statenya jadi sent agar tidak ke kirim di cron odoo
                        rec.state = 'sent'
                    else:
                        ## EMAIL TIDAK VALID STATE GANTI KE FAILED
                        rec.state = 'exception'
                        _logger.error(
                            'Error send email, Invalid email id: %s, display name: %s' % (rec.id, rec.display_name))

            except Exception as e:
                _logger.error("%s, %s" % (str(e), traceback.format_exc()))
        else:
            _logger.error("Error send email, Please setup email!")