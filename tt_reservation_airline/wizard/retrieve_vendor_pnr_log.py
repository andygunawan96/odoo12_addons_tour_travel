from odoo import api, fields, models, _
import json,copy
from odoo.exceptions import UserError
from datetime import date
from dateutil.relativedelta import relativedelta
from ...tools import ERR
from ...tools.api import Response
import traceback, logging
from datetime import datetime


_logger = logging.getLogger(__name__)


class RetrieveVendorPnrLog(models.TransientModel):
    _name = "retrieve.vendor.pnr.log"
    _description = "Retrieve Vendor PNR Log"

    pnr = fields.Char('PNR', required=True)
    last_name = fields.Char('Last Name')

    provider_ho_data_id = fields.Many2one('tt.provider.ho.data', 'Provider')
    provider_id = fields.Many2one('tt.provider', 'Provider', readonly=True, related="provider_ho_data_id.provider_id")
    provider_required_last_name = fields.Boolean('Provider Required Last Name', readonly=1, related="provider_id.required_last_name_on_retrieve")
    parent_agent_id = fields.Many2one('tt.agent', 'Parent Agent', readonly=True, related="agent_id.parent_agent_id")
    ho_id = fields.Many2one('tt.agent', 'Head Office', readonly=True, domain=[('is_ho_agent', '=', True)], required=True, compute='_compute_ho_id')
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True)

    @api.depends('agent_id')
    @api.onchange('agent_id')
    def _compute_ho_id(self):
        self.ho_id = self.agent_id.ho_id.id

    @api.onchange('agent_id')
    def _onchange_provider_ho_data_id(self):
        if self.agent_id:
            return {'domain': {
                'provider_ho_data_id': [('ho_id','=', self.agent_id.ho_id.id)]
            }}

    @api.onchange("agent_id")
    def _onchange_agent_id(self):
        if self.agent_id:
            self.customer_parent_id = self.agent_id.customer_parent_walkin_id.id
            return {'domain': {
                'user_id': [('agent_id','=',self.agent_id.id)],
                'customer_parent_id': [('parent_agent_id','=',self.agent_id.id)]
            }}

    def send_get_booking(self):
        req = {
            'pnr': self.pnr,
            'last_name': self.last_name,
            'provider': self.provider_ho_data_id.provider_id.code
        }

        if self.agent_id:
            req.update({
                'ho_id': self.agent_id.ho_id.id
            })
        res = self.env['tt.airline.api.con'].send_retrieve_vendor_pnr_log(req)
        if res['error_code'] != 0:
            raise UserError(res['error_msg'])
        get_booking_res = res['response']
        wizard_form = self.env.ref('tt_reservation_airline.retrieve_vendor_pnr_log_review_form_view', False)
        view_id = self.env['retrieve.vendor.pnr.log.review']

        vals = {
            'pnr': self.pnr,
            'last_name': self.last_name,
            'ho_id': self.ho_id.id,
            'agent_id': self.agent_id.id,
            'provider_ho_data_id': self.provider_ho_data_id.id,
            'data': get_booking_res.get('data', ''),
            'journeys': get_booking_res.get('journeys', ''),
            'segments': get_booking_res.get('segments', ''),
            'prices': get_booking_res.get('prices', ''),
            'tickets': get_booking_res.get('tickets', ''),
            'payments': get_booking_res.get('payments', ''),
            'paxs': get_booking_res.get('paxs', ''),
            'contacts': get_booking_res.get('contacts', ''),
            'after_sales': get_booking_res.get('after_sales', ''),
        }
        new = view_id.create(vals)

        return {
            'name': _('PNR Review'),
            'type': 'ir.actions.act_window',
            'res_model': 'retrieve.vendor.pnr.log.review',
            'res_id': new.id,
            'view_id': wizard_form.id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new'
        }


class RetrieveVendorPnrLogReview(models.TransientModel):
    _name = "retrieve.vendor.pnr.log.review"
    _description = "Retrieve Vendor PNR Log Review"

    pnr = fields.Char("PNR", readonly=1)
    last_name = fields.Char("Last Name", readonly=1)
    ho_id = fields.Many2one('tt.agent', 'Head Office', readonly=1)
    agent_id = fields.Many2one("tt.agent","Agent", readonly=1)
    provider_ho_data_id = fields.Many2one('tt.provider.ho.data', 'Provider', readonly=1)
    data = fields.Text('Data', readonly=1)
    journeys = fields.Text('Journeys', readonly=1)
    segments = fields.Text('Segments', readonly=1)
    paxs = fields.Text('Paxs', readonly=1)
    prices = fields.Text('Prices', readonly=1)
    tickets = fields.Text('Tickets', readonly=1)
    payments = fields.Text('Payments', readonly=1)
    contacts = fields.Text('Contacts', readonly=1)
    after_sales = fields.Text('After Sales', readonly=1)
