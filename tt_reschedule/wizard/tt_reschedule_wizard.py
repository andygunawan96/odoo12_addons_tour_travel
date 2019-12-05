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

    reschedule_type = fields.Selection([('reschedule', 'Reschedule'), ('upgrade', 'Upgrade Service'),
                                        ('reroute', 'Reroute'), ('seat', 'Request Seat'),
                                        ('corename', 'Core Name'), ('ssr', 'SSR')
                                        ], 'Reissue Type', default='reschedule', required=True)

    referenced_document = fields.Char('Ref. Document',required=True,readonly=True)

    res_model = fields.Char(
        'Related Reservation Name', index=True, readonly=True)
    res_id = fields.Integer(
        'Related Reservation ID', index=True, help='Id of the followed resource', readonly=True)

    notes = fields.Text('Notes')

    def submit_reschedule(self):
        self.env['tt.reschedule'].create({
            'agent_id': self.agent_id.id,
            'customer_parent_id': self.customer_parent_id.id,
            'currency_id': self.currency_id.id,
            'service_type': self.service_type,
            'reschedule_type': self.reschedule_type,
            'res_model': self.res_model,
            'res_id': self.res_id,
            'notes': self.notes
        })

