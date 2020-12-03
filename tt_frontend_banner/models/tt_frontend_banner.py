from odoo import api, fields, models
from ...tools.api import Response
import traceback,logging
from ...tools import ERR
import json

_logger = logging.getLogger(__name__)

class FrontendBanner(models.Model):
    _name = 'tt.frontend.banner'
    _description = 'Rodextrip Frontend Banner'
    _rec_name = 'type'

    type = fields.Selection([('big_banner', 'Big Banner'), ('small_banner', 'Small Banner'), ('promotion', 'Promotion')], default='big_banner')
    image_ids = fields.Many2many('tt.upload.center', 'tt_frontend_banner_tt_upload_center_rel' 'banner_id', 'image_id', string = 'Image',
                                 context={'active_test': True, 'form_view_ref':'tt_base.tt_upload_center_form_view'})

    def add_banner_api(self,data,context):
        #
        try:
            _logger.info("Add Banner\n" + json.dumps(data))
            upload = self.env['tt.upload.center.wizard']
            #KASIH TRY EXCEPT
            upload = upload.upload_file_api(data, context)
            # UPLOAD IMAGE IVAN
            type = ''
            if data['type'] == 'files_bigbanner':
                image_objs = self.env.ref('tt_frontend_banner.big_banner')
            elif data['type'] == 'files_smallbanner':
                image_objs = self.env.ref('tt_frontend_banner.small_banner')
            elif data['type'] == 'files_promotionbanner':
                image_objs = self.env.ref('tt_frontend_banner.promotion')

            image_objs.write({
                'image_ids': [(4, self.env['tt.upload.center'].search([('seq_id', '=', upload['response']['seq_id'])],limit=1)[0].id)]
            })
        except Exception as e:
            _logger.error('Exception Upload Center')
            _logger.error(traceback.format_exc())
            return ERR.get_error()
        return ERR.get_no_error('success')

    def set_inactive_delete_banner_api(self, data):
        #
        try:
            _logger.info("delete or inactive Banner\n" + json.dumps(data))

            # UPLOAD IMAGE IVAN
            type = ''
            if data['type'] == 'big_banner':
                banner_objs = self.env.ref('tt_frontend_banner.big_banner')
            elif data['type'] == 'small_banner':
                banner_objs = self.env.ref('tt_frontend_banner.small_banner')
            elif data['type'] == 'promotion_banner':
                banner_objs = self.env.ref('tt_frontend_banner.promotion')

            for img in banner_objs.image_ids:
                if img.seq_id == data['seq_id']:
                    if data['action'] == 'active':
                        img.toggle_active()
                    elif data['action'] == 'delete':
                        img.unlink()
                    break

        except Exception as e:
            _logger.error('Exception Upload Center')
            _logger.error(traceback.format_exc())
            return ERR.get_error()
        return ERR.get_no_error('success')

        #
    def get_banner_api(self, data):
        imgs = []

        if data['type'] == 'big_banner':
            image_objs = self.env.ref('tt_frontend_banner.big_banner')
        elif data['type'] == 'small_banner':
            image_objs = self.env.ref('tt_frontend_banner.small_banner')
        elif data['type'] == 'promotion':
            image_objs = self.env.ref('tt_frontend_banner.promotion')

        for img in image_objs.image_ids:
            imgs.append({
                'url': img['url'],
                'active': img['active'],
                'seq_id': img['seq_id']
            })

        return ERR.get_no_error(imgs)