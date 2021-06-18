from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from datetime import datetime, date, timedelta
from odoo.exceptions import UserError
from ...tools import ERR

_logger = logging.getLogger(__name__)


class TtReschedulePHCWizard(models.TransientModel):
    _name = "tt.reschedule.phc.wizard"
    _description = 'After Sales Wizard'

    agent_id = fields.Many2one('tt.agent', 'Agent', readonly=True)

    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id',
                                    readonly=True)

    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer Parent', readonly=True)

    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Parent Type', related='customer_parent_id.customer_parent_type_id',
                                              readonly=True)

    currency_id = fields.Many2one('res.currency', readonly=True)
    service_type = fields.Char('Service Type', required=True, readonly=True)
    old_picked_timeslot_id = fields.Many2one('tt.timeslot.phc', 'Old Picked Timeslot', readonly=True)
    new_picked_timeslot_id = fields.Many2one('tt.timeslot.phc', 'New Picked Timeslot', domain=[('datetimeslot', '>=', datetime.now())])
    passenger_ids = fields.Many2many('tt.reservation.passenger.phc', 'tt_reschedule_phc_wizard_passenger_rel', 'reschedule_id',
                                     'passenger_id', compute='_compute_passengers', readonly=True)

    referenced_document = fields.Char('Ref. Document',required=True,readonly=True)
    booker_id = fields.Many2one('tt.customer', 'Booker', ondelete='restrict', readonly=True)

    res_model = fields.Char(
        'Related Reservation Name', index=True, readonly=True)
    res_id = fields.Integer(
        'Related Reservation ID', index=True, help='Id of the followed resource', readonly=True)

    notes = fields.Text('Notes')

    @api.depends('res_model', 'res_id')
    @api.onchange('res_model', 'res_id')
    def _compute_passengers(self):
        passenger_list = []
        try:
            book_obj = self.env[self.res_model].sudo().browse(int(self.res_id))
        except:
            _logger.info('Warning: Error res_model di production')
            book_obj = self.env[self.env.context['active_model']].sudo().browse(int(self.env.context['active_id']))
        for rec in book_obj.passenger_ids:
            passenger_list.append(rec.id)
        self.passenger_ids = [(6, 0, passenger_list)]

    def submit_reschedule(self):
        passenger_list = []
        for rec in self.passenger_ids:
            passenger_list.append(rec.id)
        reschedule_obj = self.env['tt.reschedule.phc'].sudo().create({
            'agent_id': self.agent_id.id,
            'customer_parent_id': self.customer_parent_id.id,
            'booker_id': self.booker_id.id,
            'currency_id': self.currency_id.id,
            'service_type': self.service_type,
            'old_picked_timeslot_id': self.old_picked_timeslot_id.id,
            'new_picked_timeslot_id': self.new_picked_timeslot_id.id,
            'passenger_ids': [(6, 0, passenger_list)],
            'res_model': self.res_model,
            'res_id': self.res_id,
            'notes': self.notes
        })

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action_num = self.env.ref('tt_reschedule_phc.tt_reschedule_phc_action').id
        menu_num = self.env.ref('tt_reschedule_phc.menu_transaction_reschedule_phc').id
        return {
            'type': 'ir.actions.act_url',
            'name': reschedule_obj.name,
            'target': 'self',
            'url': base_url + "/web#id=" + str(
                reschedule_obj.id) + "&action=" + str(action_num) + "&model=tt.reschedule.phc&view_type=form&menu_id=" + str(menu_num),
        }

