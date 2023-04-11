from odoo import api, fields, models, _
from ...tools import variables
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException
import json
import base64
import logging
import traceback

_logger = logging.getLogger(__name__)


class ImportRequestTourWizard(models.TransientModel):
    _name = "tt.import.request.tour.wizard"
    _description = 'Import Tour Request Wizard'

    def _get_ho_id_domain(self):
        return [('agent_type_id', '=', self.env.ref('tt_base.agent_type_ho').id)]

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=_get_ho_id_domain, required=False, readonly=True, default=lambda self: self.env.user.ho_id.id)
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True, readonly=True, default=lambda self: self.env.user.agent_id.id)
    booker_id = fields.Many2one('tt.customer', 'Booker', ondelete='restrict', required=True, domain="[('agent_id', '=', agent_id)]")
    contact_id = fields.Many2one('tt.customer', 'Contact Person', ondelete='restrict', required=True, domain="[('agent_id', '=', agent_id)]")
    contact_number = fields.Char('Contact Number', required=True)
    contact_email = fields.Char('Contact Email', required=True)
    contact_address = fields.Char('Contact Address', required=True)
    import_data = fields.Binary('Import JSON')

    def execute_import_request_tour(self):
        if not self.import_data:
            raise UserError(_('Please upload a json file before pressing this button!'))
        try:
            upload_file = json.loads(base64.b64decode(self.import_data))
            locations_list = []
            if upload_file.get('locations'):
                for rec in upload_file['locations']:
                    temp_city_id = rec.get('city_name') and self.env['res.city'].sudo().search([('name', '=', rec['city_name'])], limit=1) or False
                    temp_country_id = rec.get('country_code') and self.env['res.country'].sudo().search([('code', '=', rec['country_code'])], limit=1) or False
                    city_id = temp_city_id and temp_city_id[0] or False
                    country_id = temp_country_id and temp_country_id[0] or False
                    if city_id and country_id:
                        loc_objs = self.env['tt.tour.master.locations'].sudo().search([('city_id', '=', city_id.id), ('country_id', '=', country_id.id)], limit=1)
                        if loc_objs:
                            locations_list.append(loc_objs[0].id)
                        else:
                            new_loc_obj = self.env['tt.tour.master.locations'].sudo().create({
                                'city_id': city_id.id,
                                'country_id': country_id.id,
                            })
                            locations_list.append(new_loc_obj.id)
                    else:
                        _logger.info('Cannot find city or country!')

            if upload_file.get('carrier_code'):
                temp_carrier_id = self.env['tt.transport.carrier'].sudo().search([('code', '=', upload_file['carrier_code'])], limit=1)
                carrier_id = temp_carrier_id and temp_carrier_id[0].id or False
            else:
                carrier_id = False

            req_obj = self.env['tt.request.tour'].create({
                'agent_id': self.agent_id and self.agent_id.id or False,
                'booker_id': self.booker_id and self.booker_id.id or False,
                'contact_id': self.contact_id and self.contact_id.id or False,
                'contact_number': self.contact_number,
                'contact_email': self.contact_email,
                'contact_address': self.contact_address,
                'tour_category': upload_file.get('tour_category') and upload_file['tour_category'] or False,
                'location_ids': [(6,0,locations_list)],
                'est_departure_date': upload_file.get('est_departure_date') and datetime.strptime(upload_file['est_departure_date'], '%d %B %Y') or False,
                'est_return_date': upload_file.get('est_return_date') and datetime.strptime(upload_file['est_return_date'], '%d %B %Y') or False,
                'est_departure_time': upload_file.get('est_departure_time') and upload_file['est_departure_time'] or False,
                'est_return_time': upload_file.get('est_return_time') and upload_file['est_return_time'] or False,
                'adult': upload_file.get('adult') and upload_file['adult'] or False,
                'child': upload_file.get('child') and upload_file['child'] or False,
                'infant': upload_file.get('infant') and upload_file['infant'] or False,
                'min_budget': upload_file.get('min_budget') and upload_file['min_budget'] or False,
                'max_budget': upload_file.get('max_budget') and upload_file['max_budget'] or False,
                'hotel_star': upload_file.get('hotel_star') and upload_file['hotel_star'] or False,
                'est_hotel_price': upload_file.get('est_hotel_price') and upload_file['est_hotel_price'] or False,
                'carrier_id': carrier_id,
                'class_of_service': upload_file.get('class_of_service') and upload_file['class_of_service'] or False,
                'food_preference': upload_file.get('food_preference') and upload_file['food_preference'] or False,
                'notes': upload_file.get('notes') and upload_file['notes'] or False,
            })

            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            action_num = self.env.ref('tt_reservation_tour.tt_request_tour_view_action').id
            menu_num = self.env.ref('tt_reservation_tour.submenu_request_tour_package').id
            return {
                'type': 'ir.actions.act_url',
                'name': req_obj.name,
                'target': 'self',
                'url': base_url + "/web#id=" + str(req_obj.id) + "&action=" + str(
                    action_num) + "&model=tt.request.tour&view_type=form&menu_id=" + str(menu_num),
            }
        except Exception as e:
            raise UserError(_('The uploaded file cannot be read. Please upload a valid JSON file!'))

