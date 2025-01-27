from odoo import api,models,fields
from ....tools import ERR, gmail
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
import copy
from datetime import datetime, timedelta

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
                            ho_agent_obj = resv_obj.agent_id.ho_id
                            if ho_agent_obj.email_server_id:
                                if ho_agent_obj.email_server_id.is_gmail:
                                    self.send_gmail(batch_id, ho_agent_obj.email_server_id, auto_commit, raise_exception)
                                else:
                                    self.send_smtp(server_id, batch_id, ho_agent_obj.email_server_id, auto_commit, raise_exception)
                except Exception as e:
                    _logger.error("%s, %s" % (str(e), traceback.format_exc()))
            # mail_obj = self.env[]

    @api.model
    def process_email_queue(self, ids=None):
        #matikan email yg stuck
        on_going_list = self.search([('state', '=', 'outgoing'), ('scheduled_date', '<', datetime.now() - timedelta(hours=12))])
        if on_going_list:
            sql_query = """
                        update mail_mail set state = 'cancel' where id in %s;
                        """ % (str(on_going_list.ids).replace('[', '(').replace(']', ')'))
            self.env.cr.execute(sql_query)
            self.env.cr.commit()
        if ids:
            fake_ids = copy.deepcopy(ids)
            for idx, rec in enumerate(fake_ids):
                if rec in on_going_list.ids:
                    ids.pop(idx)

        #delete attachment email lama
        # search email yang punay attachment
        delete_attachment_list = self.search([('attachment_ids','!=',False),
                                              ('create_date','<',datetime.now() - timedelta(days=30))],
                                             limit=100)
        for attach_obj in delete_attachment_list:
            attach_obj.attachment_ids.unlink()
        self.env.cr.commit()

        return super(MailMail, self).process_email_queue(ids)

    def send_smtp(self, server_id, batch_id, email_server_obj, auto_commit=False, raise_exception=False): ## update fungsi official odoo karena dibuat dynamic dengan google
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
            self.browse(batch_id)._send_custom_odoo(
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


    @api.multi
    def _send_custom_odoo(self, auto_commit=False, raise_exception=False, smtp_session=None): ## update fungsi official odoo hanya ambil body & to
        IrMailServer = self.env['ir.mail_server']
        IrAttachment = self.env['ir.attachment']
        for mail_id in self.ids:
            success_pids = []
            failure_type = None
            processing_pid = None
            mail = None
            try:
                mail = self.browse(mail_id)
                if mail.state != 'outgoing':
                    if mail.state != 'exception' and mail.auto_delete:
                        mail.sudo().unlink()
                    continue

                # remove attachments if user send the link with the access_token
                body = mail.body_html or ''
                attachments = mail.attachment_ids
                for link in re.findall(r'/web/(?:content|image)/([0-9]+)', body):
                    attachments = attachments - IrAttachment.browse(int(link))

                # load attachment binary data with a separate read(), as prefetching all
                # `datas` (binary field) could bloat the browse cache, triggerring
                # soft/hard mem limits with temporary data.
                attachments = [(a['datas_fname'], base64.b64decode(a['datas']), a['mimetype'])
                               for a in attachments.sudo().read(['datas_fname', 'datas', 'mimetype'])]

                # specific behavior to customize the send email for notified partners
                email_list = []
                if mail.email_to:
                    mail.email_from = smtp_session.user
                    email_list.append(mail._send_prepare_values())
                for partner in mail.recipient_ids:
                    values = mail._send_prepare_values(partner=partner)
                    values['partner_id'] = partner
                    email_list.append(values)

                # headers
                headers = {}
                ICP = self.env['ir.config_parameter'].sudo()
                bounce_alias = ICP.get_param("mail.bounce.alias")
                catchall_domain = ICP.get_param("mail.catchall.domain")
                if bounce_alias and catchall_domain:
                    if mail.model and mail.res_id:
                        headers['Return-Path'] = '%s+%d-%s-%d@%s' % (
                        bounce_alias, mail.id, mail.model, mail.res_id, catchall_domain)
                    else:
                        headers['Return-Path'] = '%s+%d@%s' % (bounce_alias, mail.id, catchall_domain)
                if mail.headers:
                    try:
                        headers.update(safe_eval(mail.headers))
                    except Exception:
                        pass

                # Writing on the mail object may fail (e.g. lock on user) which
                # would trigger a rollback *after* actually sending the email.
                # To avoid sending twice the same email, provoke the failure earlier
                mail.write({
                    'state': 'exception',
                    'failure_reason': _(
                        'Error without exception. Probably due do sending an email without computed recipients.'),
                })
                # Update notification in a transient exception state to avoid concurrent
                # update in case an email bounces while sending all emails related to current
                # mail record.
                notifs = self.env['mail.notification'].search([
                    ('is_email', '=', True),
                    ('mail_id', 'in', mail.ids),
                    ('email_status', 'not in', ('sent', 'canceled'))
                ])
                if notifs:
                    notif_msg = _(
                        'Error without exception. Probably due do concurrent access update of notification records. Please see with an administrator.')
                    notifs.write({
                        'email_status': 'exception',
                        'failure_type': 'UNKNOWN',
                        'failure_reason': notif_msg,
                    })

                # build an RFC2822 email.message.Message object and send it without queuing
                res = None
                for email in email_list:
                    msg = IrMailServer.build_email(
                        email_from=mail.email_from,
                        email_to=email.get('email_to'),
                        subject=mail.subject,
                        body=email.get('body'),
                        body_alternative=email.get('body_alternative'),
                        email_cc=tools.email_split(mail.email_cc),
                        reply_to=mail.reply_to,
                        attachments=attachments,
                        message_id=mail.message_id,
                        references=mail.references,
                        object_id=mail.res_id and ('%s-%s' % (mail.res_id, mail.model)),
                        subtype='html',
                        subtype_alternative='plain',
                        headers=headers)
                    processing_pid = email.pop("partner_id", None)
                    try:
                        res = IrMailServer.send_email(
                            msg, mail_server_id=mail.mail_server_id.id, smtp_session=smtp_session)
                        if processing_pid:
                            success_pids.append(processing_pid)
                        processing_pid = None
                    except AssertionError as error:
                        if str(error) == IrMailServer.NO_VALID_RECIPIENT:
                            failure_type = "RECIPIENT"
                            # No valid recipient found for this particular
                            # mail item -> ignore error to avoid blocking
                            # delivery to next recipients, if any. If this is
                            # the only recipient, the mail will show as failed.
                            _logger.info("Ignoring invalid recipients for mail.mail %s: %s",
                                         mail.message_id, email.get('email_to'))
                        else:
                            raise
                if res:  # mail has been sent at least once, no major exception occured
                    mail.write({'state': 'sent', 'message_id': res, 'failure_reason': False})
                    _logger.info('Mail with ID %r and Message-Id %r successfully sent', mail.id, mail.message_id)
                    # /!\ can't use mail.state here, as mail.refresh() will cause an error
                    # see revid:odo@openerp.com-20120622152536-42b2s28lvdv3odyr in 6.1
                mail._postprocess_sent_message(success_pids=success_pids, failure_type=failure_type)
            except MemoryError:
                # prevent catching transient MemoryErrors, bubble up to notify user or abort cron job
                # instead of marking the mail as failed
                _logger.exception(
                    'MemoryError while processing mail with ID %r and Msg-Id %r. Consider raising the --limit-memory-hard startup option',
                    mail.id, mail.message_id)
                # mail status will stay on ongoing since transaction will be rollback
                raise
            except psycopg2.Error:
                # If an error with the database occurs, chances are that the cursor is unusable.
                # This will lead to an `psycopg2.InternalError` being raised when trying to write
                # `state`, shadowing the original exception and forbid a retry on concurrent
                # update. Let's bubble it.
                raise
            except Exception as e:
                failure_reason = tools.ustr(e)
                _logger.exception('failed sending mail (id: %s) due to %s', mail.id, failure_reason)
                mail.write({'state': 'exception', 'failure_reason': failure_reason})
                mail._postprocess_sent_message(success_pids=success_pids, failure_reason=failure_reason,
                                               failure_type='UNKNOWN')
                if raise_exception:
                    if isinstance(e, (AssertionError, UnicodeEncodeError)):
                        if isinstance(e, UnicodeEncodeError):
                            value = "Invalid text: %s" % e.object
                        else:
                            # get the args of the original error, wrap into a value and throw a MailDeliveryException
                            # that is an except_orm, with name and value as arguments
                            value = '. '.join(e.args)
                        raise MailDeliveryException(_("Mail Delivery Failed"), value)
                    raise

            if auto_commit is True:
                self._cr.commit()
        return True
