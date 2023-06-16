from odoo import api, fields, models
from odoo.http import request
from ...tools import session
import logging
import json

_logger = logging.getLogger(__name__)
SESSION_NT = session.Session()


class MasterImages(models.Model):
    _name = 'tt.master.event.image'
    _description = 'Orbis Event Images Master'

    event_id = fields.Many2one('tt.master.event', 'Event ID', ondelete="cascade")
    image_url = fields.Char('Image URL')
    image_path = fields.Char('Image Path')
    desc = fields.Char('Image Description')


class MasterVideos(models.Model):
    _name = 'tt.master.event.video'
    _description = 'Orbis Event Video Master'

    event_id = fields.Many2one('tt.master.event', 'Event ID', ondelete="cascade")
    video_url = fields.Char('Video URL')
    video_path = fields.Char('Video Path')
    desc = fields.Char('Image Description')