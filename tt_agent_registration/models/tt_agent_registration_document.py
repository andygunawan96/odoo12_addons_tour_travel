from odoo import models, fields, api, _

STATE = [
    ('draft', 'Draft'),
    ('done', 'Done')
]


class AgentRegistrationDocument(models.Model):
    _name = 'tt.agent.registration.document'
    _description = 'Rodex Model'

    registration_document_id = fields.Many2one('tt.agent.registration', 'Registration Document')
    opening_document_id = fields.Many2one('tt.agent.registration', 'Opening Document')
    state = fields.Selection(STATE, 'State', default='draft')
    description = fields.Text('Description')
    # attachment_ids = fields.One2many('ir.attachment')
    document_attach_ids = fields.Many2many('tt.upload.center', 'document_ir_attachments_rel', 'document_id',
                                           'attachment_id', string='Attachments')
    # attachment_ids = fields.Char('Attachments')
    schedule_date = fields.Datetime('Schedule Date')
    receive_date = fields.Datetime('Receive Date')
    qty = fields.Integer('Qty')
    receive_qty = fields.Integer('Receive Qty')
    document_id = fields.Many2one('tt.document.type', 'Document')
    active = fields.Boolean('Active', default=True)


class AgentRegistrationDocumentType(models.Model):
    _name = 'tt.document.type'

    name = fields.Char('Name', required=True)
    description = fields.Text('Description')
    active = fields.Boolean('Active', default=True)
    document_type = fields.Selection([('opening', 'Opening'), ('registration', 'Registration')], 'Document Type')
    agent_type_ids = fields.Many2many('tt.agent.type', 'tt_agent_type_document_type_1_2_rel', 'document_type_id', 'agent_type_id', 'Agent Type',
                                      help='''Agent Type yang memerlukan persyaratan suatu dokumen.''')
