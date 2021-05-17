from odoo import api,models,fields,_
from ...tools import util,ERR
import logging,traceback
import json

_logger = logging.getLogger(__name__)


class TtReservation(models.Model):
    _inherit = 'tt.reservation'

    def send_ledgers_to_accounting(self):
        try:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            pay_acq = self.env['payment.acquirer'].search([('seq_id', '=', self.payment_method)], limit=1)
            ledger_list = []
            for rec in self.ledger_ids:
                if not rec.is_sent_to_acc:
                    if rec.transaction_type == 2:
                        trans_type = 'Transport Booking'
                    elif rec.transaction_type == 3:
                        trans_type = 'Commission'
                        if rec.agent_type_id.id == self.env.ref('tt_base.agent_type_ho').id:
                            trans_type += ' HO'
                        else:
                            trans_type += ' Channel'
                    else:
                        trans_type = ''

                    ledger_list.append({
                        'reference_number': rec.ref and rec.ref or '',
                        'name': rec.name and rec.name or '',
                        'debit': rec.debit and rec.debit or 0,
                        'credit': rec.credit and rec.credit or 0,
                        'currency_id': rec.currency_id and rec.currency_id.name or '',
                        'create_date': rec.create_date,
                        'date': rec.date and rec.date or '',
                        'create_uid': rec.create_uid and rec.create_uid.name or '',
                        'commission': 0.0,
                        'description': rec.description and rec.description or '',
                        'agent_id': rec.agent_id and rec.agent_id.name,
                        'company_sender': rec.agent_id and rec.agent_id.name,
                        'company_receiver': self.env.ref('tt_base.rodex_ho').name,
                        'state': 'Done',
                        'display_provider_name': rec.display_provider_name and rec.display_provider_name or '',
                        'pnr': rec.pnr and rec.pnr or '',
                        'url_legacy': base_url + '/web#id=' + str(rec.id) + '&model=tt.ledger&view_type=form',
                        'transaction_type': trans_type,
                        'transport_type': self.provider_type_id and self.provider_type_id.name or '',
                        'payment_method': '',
                        'NTA_amount_real': self.total_nta and self.total_nta or 0,
                        'payment_acquirer': pay_acq and pay_acq.name or ''
                    })
                    rec.sudo().write({
                        'is_sent_to_acc': True
                    })
            res = self.env['tt.accounting.connector'].add_sales_order(ledger_list)
            return ERR.get_no_error(res)
        except Exception as e:
            _logger.info("Failed to send ledgers to accounting software. Ignore this message if tt_accounting_connector is currently not installed.")
            _logger.error(traceback.format_exc())
            return ERR.get_error(1000)


class TtReservationAirline(models.Model):
    _inherit = 'tt.reservation.airline'

    def action_issued_airline(self,co_uid,customer_parent_id,acquirer_id = False):
        super(TtReservationAirline, self).action_issued_airline(co_uid,customer_parent_id,acquirer_id)
        self.send_ledgers_to_accounting()


class TtReservationTrain(models.Model):
    _inherit = 'tt.reservation.train'

    def action_issued_train(self,co_uid,customer_parent_id,acquirer_id = False):
        super(TtReservationTrain, self).action_issued_train(co_uid,customer_parent_id,acquirer_id)
        self.send_ledgers_to_accounting()


class TtReservationActivity(models.Model):
    _inherit = 'tt.reservation.activity'

    def action_issued_activity(self,co_uid,customer_parent_id,acquirer_id = False):
        super(TtReservationActivity, self).action_issued_activity(co_uid,customer_parent_id,acquirer_id)
        self.send_ledgers_to_accounting()


class TtReservationTour(models.Model):
    _inherit = 'tt.reservation.tour'

    def action_issued_tour(self,co_uid,customer_parent_id,acquirer_id = False):
        super(TtReservationTour, self).action_issued_tour(co_uid,customer_parent_id,acquirer_id)
        self.send_ledgers_to_accounting()


class TtReservationPPOB(models.Model):
    _inherit = 'tt.reservation.ppob'

    def action_issued_ppob(self,co_uid,customer_parent_id,acquirer_id = False):
        super(TtReservationPPOB, self).action_issued_ppob(co_uid,customer_parent_id,acquirer_id)
        self.send_ledgers_to_accounting()


class TtReservationEvent(models.Model):
    _inherit = 'tt.reservation.event'

    def action_issued_event(self, context):
        super(TtReservationEvent, self).action_issued_event(context)
        self.send_ledgers_to_accounting()


class TtReservationHotel(models.Model):
    _inherit = 'tt.reservation.hotel'

    def action_issued(self, acquirer_id, co_uid, kwargs=False):
        super(TtReservationHotel, self).action_issued(acquirer_id, co_uid, kwargs)
        self.send_ledgers_to_accounting()


class TtReservationOffline(models.Model):
    _inherit = 'tt.reservation.offline'

    def action_issued_backend(self):
        super(TtReservationOffline, self).action_issued_backend()
        self.send_ledgers_to_accounting()


class TtReservationPassport(models.Model):
    _inherit = 'tt.reservation.passport'

    def action_issued_passport_api(self, data, context):
        super(TtReservationPassport, self).action_issued_passport_api(data, context)
        self.send_ledgers_to_accounting()


class TtReservationVisa(models.Model):
    _inherit = 'tt.reservation.visa'

    def action_issued_visa_api(self, data, context):
        super(TtReservationVisa, self).action_issued_visa_api(data, context)
        self.send_ledgers_to_accounting()
