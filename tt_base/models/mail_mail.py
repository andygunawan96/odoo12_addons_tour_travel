from odoo import api,models,fields
from ...tools import ERR, gmail
import logging, traceback
_logger = logging.getLogger(__name__)
import re
regex_check_email_valid = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
class MailMail(models.Model):
    _inherit = "mail.mail"

    def is_email_valid(self, email):

        # pass the regular expression
        # and the string into the fullmatch() method
        if (re.fullmatch(regex_check_email_valid, email)):
            return True

        else:
            return False

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
            google_auth = self.env['ir.mail_server'].connect()
            if google_auth:
                email_user_account = self.env['ir.mail_server'].get_email_name()
                for batch_id in batch_ids:
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
                                gmail.send_message(service=google_auth,destination=destination_email, obj=rec.subject, body=rec.body_html, attachments=attachments_list_file, type='html', email_account=email_user_account)
                                # setelah ngirim di ganti statenya jadi sent agar tidak ke kirim di cron odoo
                                rec.state = 'sent'
                            else:
                                ## EMAIL TIDAK VALID STATE GANTI KE FAILED
                                rec.state = 'exception'
                                _logger.error('Error send email, Invalid email id: %s, display name: %s' % (rec.id, rec.display_name))

                    except Exception as e:
                        _logger.error("%s, %s" % (str(e), traceback.format_exc()))
            else:
                _logger.error("Error send email, Please setup email!")
        # for rec in self:
        #     try:
        #         google_auth = self.env['ir.mail_server'].connect()
        #         attachments_list_file = []
        #         for attachment_obj in rec.attachment_ids:
        #             attachments_list_file.append([attachment_obj.display_name, attachment_obj.datas])
        #         destination_email = {
        #             'to': rec.email_to,
        #             'cc': rec.email_cc,
        #             'bcc': ''
        #         }
        #         gmail.send_message(service=google_auth,destination=destination_email, obj=rec.subject, body=rec.body_html, attachments=attachments_list_file, type='html')
        #     except Exception as e:
        #         _logger.error("%s, %s" % (str(e), traceback.format_exc()))
