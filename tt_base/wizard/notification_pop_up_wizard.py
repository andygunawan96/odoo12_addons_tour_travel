from odoo import api, fields, models, _


class NotificationPopUpWizard(models.TransientModel):
    _name = "notification.pop.up.wizard"
    _description = 'Notification Pop Up Wizard'

    msg = fields.Text("Message",readonly=True)