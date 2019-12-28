from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR

_logger = logging.getLogger(__name__)


class TtRescheduleWizard(models.TransientModel):
    _name = "tt.reschedule.wizard"
    _description = 'Reschedule Wizard'

    agent_id = fields.Many2one('tt.agent', 'Agent', readonly=True)

    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id',
                                    readonly=True)

    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer Parent', readonly=True)

    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Parent Type', related='customer_parent_id.customer_parent_type_id',
                                    readonly=True)

    currency_id = fields.Many2one('res.currency', readonly=True)
    service_type = fields.Char('Service Type', required=True, readonly=True)
    old_segment_ids = fields.Many2many('tt.segment.airline', 'tt_reschedule_wizard_old_segment_rel', 'reschedule_id',
                                       'segment_id', string='Old Segments',
                                       readonly=True, compute="_compute_old_segments")
    new_segment_ids = fields.Many2many('tt.segment.airline', 'tt_reschedule_wizard_new_segment_rel', 'reschedule_id',
                                       'segment_id', string='New Segments', ondelete="cascade", compute="_compute_new_segments", readonly=False)
    reschedule_type = fields.Selection([('reschedule', 'Reschedule'), ('revalidate', 'Upgrade Service'),
                                        ('reissued', 'Reroute'), ('upgrade', 'Upgrade')], 'Reschedule Type', default='reschedule', required=True)

    referenced_document = fields.Char('Ref. Document',required=True,readonly=True)

    res_model = fields.Char(
        'Related Reservation Name', index=True, readonly=True)
    res_id = fields.Integer(
        'Related Reservation ID', index=True, help='Id of the followed resource', readonly=True)

    notes = fields.Text('Notes')

    @api.depends('res_model', 'res_id')
    @api.onchange('res_model', 'res_id')
    def _compute_old_segments(self):
        old_segment_list = []
        book_obj = self.env[self.res_model].sudo().browse(int(self.res_id))
        for rec in book_obj.segment_ids:
            old_segment_list.append(rec.id)
        self.old_segment_ids = [(6, 0, old_segment_list)]

    @api.depends('res_model', 'res_id')
    @api.onchange('res_model', 'res_id')
    def _compute_new_segments(self):
        new_segment_list = []
        book_obj = self.env[self.res_model].sudo().browse(int(self.res_id))
        for rec in book_obj.segment_ids:
            new_seg_obj = self.env['tt.segment.airline'].sudo().create({
                'segment_code': rec.segment_code,
                'fare_code': rec.fare_code,
                'carrier_id': rec.carrier_id.id,
                'carrier_code': rec.carrier_code,
                'carrier_number': rec.carrier_number,
                'provider_id': rec.provider_id.id,
                'origin_id': rec.origin_id.id,
                'destination_id': rec.destination_id.id,
                'origin_terminal': rec.origin_terminal,
                'destination_terminal': rec.destination_terminal,
                'departure_date': rec.departure_date,
                'arrival_date': rec.arrival_date,
                'class_of_service': rec.class_of_service,
                'cabin_class': rec.cabin_class,
                'sequence': rec.sequence,
            })
            new_segment_list.append(new_seg_obj.id)
        self.new_segment_ids = [(6, 0, new_segment_list)]

    def submit_reschedule(self):
        old_segment_list = []
        new_segment_list = []
        for rec in self.old_segment_ids:
            old_segment_list.append(rec.id)
        for rec in self.new_segment_ids:
            new_segment_list.append(rec.id)
            self.sudo().write({
                'new_segment_ids': [(3, rec.id)]
            })
        self.env['tt.reschedule'].create({
            'agent_id': self.agent_id.id,
            'customer_parent_id': self.customer_parent_id.id,
            'currency_id': self.currency_id.id,
            'service_type': self.service_type,
            'reschedule_type': self.reschedule_type,
            'old_segment_ids': [(6, 0, old_segment_list)],
            'new_segment_ids': [(6, 0, new_segment_list)],
            'res_model': self.res_model,
            'res_id': self.res_id,
            'notes': self.notes
        })

