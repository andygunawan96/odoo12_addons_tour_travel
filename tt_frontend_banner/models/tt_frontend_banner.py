from odoo import api, fields, models
from ...tools.api import Response
import traceback,logging
from ...tools import ERR
import json

_logger = logging.getLogger(__name__)

class FrontendBanner(models.Model):
    _name = 'tt.frontend.banner'
    _description = 'Frontend Banner'
    _rec_name = 'type'

    type = fields.Selection([('big_banner', 'Big Banner'), ('small_banner', 'Small Banner'), ('promotion', 'Promotion')], default='big_banner')
    image_line_ids = fields.One2many('tt.frontend.banner.line', 'frontend_banner_line_id','Image', domain=['|',('active', '=', True),('active', '=', False)])

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

            ho_agent_obj = None
            if context.get('co_ho_seq_id'):
                ho_agent_obj = self.env['tt.agent'].search([('seq_id','=', context['co_ho_seq_id'])], limit=1)

            image_line_obj = self.env['tt.frontend.banner.line'].create({
                "image_id": self.env['tt.upload.center'].search([('seq_id', '=', upload['response']['seq_id'])], limit=1)[0].id,
                "ho_id": ho_agent_obj.id if ho_agent_obj else False,
                "domain": data.get('domain')
            })
            image_objs.write({'image_line_ids': [(4, image_line_obj.id)]})
        except Exception as e:
            _logger.error('Exception Upload Center')
            _logger.error(traceback.format_exc())
            return ERR.get_error()
        return ERR.get_no_error('success')

    def set_inactive_delete_banner_api(self, data, context):
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

            ho_agent_obj = None
            if context.get('co_ho_seq_id'):
                ho_agent_obj = self.env['tt.agent'].search([('seq_id','=', context['co_ho_seq_id'])], limit=1)

            for img in banner_objs.image_line_ids:
                if img.image_id.seq_id == data['seq_id'] and ho_agent_obj == img.ho_id:
                    img.url = data['url']
                    img.sequence = data['sequence']
                    img.provider_type_id = self.env['tt.provider.type'].search([('code', '=', data['provider_type'])], limit=1).id
                    if data['action'] == 'active':
                        img.active = not img.active
                    elif data['action'] == 'delete':
                        img.unlink()
                    break

        except Exception as e:
            _logger.error('Exception Upload Center')
            _logger.error(traceback.format_exc())
            return ERR.get_error()
        return ERR.get_no_error('success')

        #

    def get_banner_api(self, data, context):
        imgs = []

        if data['type'] == 'big_banner':
            image_objs = self.env.ref('tt_frontend_banner.big_banner')
        elif data['type'] == 'small_banner':
            image_objs = self.env.ref('tt_frontend_banner.small_banner')
        elif data['type'] == 'promotion':
            image_objs = self.env.ref('tt_frontend_banner.promotion')

        ho_agent_obj = None
        if context.get('co_ho_seq_id'):
            ho_agent_obj = self.env['tt.agent'].search([('seq_id', '=', context['co_ho_seq_id'])], limit=1)
        ### UPDATE DOMAIN DATA LAMA ####
        img_line_filter_objs = image_objs.image_line_ids.filtered(lambda x: x.domain in [False, data['domain']] and x.ho_id.id == ho_agent_obj.id)
        for img in img_line_filter_objs:
            if data.get('domain'):
                if not img.domain:
                    img.update({
                        "domain": data['domain']
                    })
            imgs.append({
                'url': img.image_id['url'],
                'active': img.active,
                'seq_id': img.image_id['seq_id'],
                'url_page': img.url,
                'provider_type': img.provider_type_id.code,
                'sequence': img.sequence
            })

        return ERR.get_no_error(imgs)

class FrontendBannerLine(models.Model):
    _name = 'tt.frontend.banner.line'
    _description = 'Frontend Banner Line'
    _rec_name = 'url'
    _order = 'sequence asc'

    url = fields.Char('URL Redirect')
    frontend_banner_line_id = fields.Many2one('tt.frontend.banner', 'Image List')
    image_id = fields.Many2one('tt.upload.center', 'Image', invisible=True)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], required=True, default=lambda self: self.env.user.ho_id.id)
    domain = fields.Char('Domain', default='')
    sequence = fields.Char('Sequence')
    active = fields.Boolean('Active', default=True)

    def unlink(self):
        for rec in self:
            rec.image_id.unlink()
        return super(FrontendBannerLine, self).unlink()
