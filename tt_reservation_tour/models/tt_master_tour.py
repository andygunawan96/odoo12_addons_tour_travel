from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from ...tools.api import Response
import logging, traceback
import json
import pytz
import base64
import csv
import os

_logger = logging.getLogger(__name__)


class Survey(models.Model):
    _inherit = 'survey.survey'

    tour_id = fields.Many2one('tt.master.tour', 'Tour')


class TourSyncProducts(models.TransientModel):
    _name = "tour.sync.product.wizard"
    _description = 'Tour Sync Product Wizard'

    def get_domain(self):
        domain_id = self.env.ref('tt_reservation_tour.tt_provider_type_tour').id
        except_id = self.env.ref('tt_reservation_tour.tt_provider_tour_internal').id
        return [('provider_type_id.id', '=', int(domain_id)), ('id', '!=', int(except_id))]

    provider_id = fields.Many2one('tt.provider', 'Provider', domain=get_domain, required=True)
    provider_code = fields.Char('Provider Code')
    start_num = fields.Char('Start Number', default='1')
    end_num = fields.Char('End Number', default='1')

    def generate_json(self):
        def_name = 'action_get_%s_json' % self.provider_id.code
        if hasattr(self.env['tt.master.tour'], def_name):
            getattr(self.env['tt.master.tour'], def_name)()

    def sync_product(self):
        def_name = 'action_sync_%s' % self.provider_id.code
        start_num = self.start_num
        end_num = self.end_num
        if hasattr(self.env['tt.master.tour'], def_name):
            getattr(self.env['tt.master.tour'], def_name)(start_num, end_num)

    def deactivate_product(self):
        products = self.env['tt.master.tour'].search([('provider_id', '=', self.provider_id.id)])
        for rec in products:
            if rec.active:
                rec.write({
                    'active': False
                })

    @api.depends('provider_id')
    @api.onchange('provider_id')
    def _compute_provider_code(self):
        self.provider_code = self.provider_id.code


class TourItineraryItem(models.Model):
    _name = 'tt.reservation.tour.itinerary.item'
    _description = 'Reservation Tour Itinerary Item'
    _order = 'sequence asc'

    name = fields.Char('Title')
    description = fields.Text('Description')
    timeslot = fields.Char('Timeslot')
    image_id = fields.Many2one('tt.upload.center', 'Image')
    itinerary_id = fields.Many2one('tt.reservation.tour.itinerary', 'Tour Itinerary')
    hyperlink = fields.Char('Hyperlink')
    sequence = fields.Integer('Sequence', required=True, default=50)


class TourItinerary(models.Model):
    _name = 'tt.reservation.tour.itinerary'
    _description = 'Reservation Tour Itinerary'
    _order = 'day asc'

    name = fields.Char('Title')
    day = fields.Integer('Day', default=1, required=True)
    tour_pricelist_id = fields.Many2one('tt.master.tour', 'Tour', ondelete='cascade')
    item_ids = fields.One2many('tt.reservation.tour.itinerary.item', 'itinerary_id', 'Items')


class MasterTour(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.master.tour'
    _description = 'Master Tour'
    _order = "sequence asc, id desc"

    def get_domain(self):
        domain_id = self.env.ref('tt_reservation_tour.tt_provider_type_tour').id
        return [('provider_type_id.id', '=', int(domain_id))]

    name = fields.Text('Name', required=True, default='Tour', size=40)
    description = fields.Text('Description')

    provider_id = fields.Many2one('tt.provider', 'Provider', domain=get_domain, readonly=True,
                                  default=lambda self: self.env.ref('tt_reservation_tour.tt_provider_tour_internal'),
                                  copy=False)
    carrier_id = fields.Many2one('tt.transport.carrier', 'Carrier', domain=get_domain, required=True,
                                 default=lambda self: self.env.ref('tt_reservation_tour.tt_transport_carrier_tour_itt'),
                                 copy=False)
    owner_ho_id = fields.Many2one('tt.agent', 'Owner Head Office', domain=[('is_ho_agent', '=', True)],
                                  default=lambda self: self.env.user.ho_id)
    ho_ids = fields.Many2many('tt.agent', 'tt_master_tour_ho_agent_rel', 'tour_id', 'ho_id',
                              string='Allowed Head Office(s)', domain=[('is_ho_agent', '=', True)])
    agent_id = fields.Many2one('tt.agent', 'Agent')

    tour_code = fields.Char('Tour Code', readonly=True, copy=False)
    tour_slug = fields.Char('Tour Slug', readonly=True, copy=False)
    tour_route = fields.Char('Route', compute='_compute_tour_route', readonly=True, store=True)
    tour_category = fields.Selection([('group', 'For All Agents'), ('private', 'For Selected Agent')],
                                     'Tour Category', required=True, default='group')
    tour_type_id = fields.Many2one('tt.master.tour.type', 'Tour Type', required=True, domain="[('ho_id', '=', owner_ho_id)]")
    is_can_choose_hotel = fields.Boolean('Can Choose Hotel', readonly=True, related='tour_type_id.is_can_choose_hotel')
    is_use_tour_leader = fields.Boolean('Is Use Tour Leader', readonly=True, related='tour_type_id.is_use_tour_leader')
    is_open_date = fields.Boolean('Is Open Date', readonly=True, related='tour_type_id.is_open_date')
    tour_line_ids = fields.One2many('tt.master.tour.lines', 'master_tour_id', 'Tour Lines')
    tour_line_amount = fields.Integer('Available Schedule(s)', readonly=True, compute='_compute_tour_line_amount')

    is_can_hold = fields.Boolean('Can Be Hold', default=True, required=True)
    hold_date_timer = fields.Integer('Hold Date Timer (Hours)', default=6)

    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('closed', 'Closed')], 'State', copy=False, default='draft')

    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    location_ids = fields.Many2many('tt.tour.master.locations', 'tt_tour_location_rel', 'product_id',
                                    'location_id', string='Location')
    country_str = fields.Char('Countries', compute='_compute_country_str', store=True)
    est_starting_price = fields.Monetary('Estimated Starting Price', default=0)
    single_supplement = fields.Monetary('Single Supplement', default=0)
    adult_flight_fare = fields.Monetary('Adult Flight Fare', help="(/pax)", default=0)
    child_flight_fare = fields.Monetary('Child Flight Fare', help="(/pax)", default=0)
    infant_flight_fare = fields.Monetary('Infant Flight Fare', help="(/pax)", default=0)
    adult_visa_fare = fields.Monetary('Adult Visa Fare', help="(/pax)", default=0)
    child_visa_fare = fields.Monetary('Child Visa Fare', help="(/pax)", default=0)
    infant_visa_fare = fields.Monetary('Infant Visa Fare', help="(/pax)", default=0)
    adult_airport_tax = fields.Monetary('Adult Airport Tax', help="(/pax)", default=0)
    child_airport_tax = fields.Monetary('Child Airport Tax', help="(/pax)", default=0)
    infant_airport_tax = fields.Monetary('Infant Airport Tax', help="(/pax)", default=0)
    tipping_guide = fields.Monetary('Tipping Guide', help="(/pax /day)", default=0)
    tipping_tour_leader = fields.Monetary('Tipping Tour Leader', help="(/pax /day)", default=0)
    tipping_driver = fields.Monetary('Tipping Driver', help="(/pax /day)", default=0)
    tipping_guide_child = fields.Boolean('Apply for Child', default=True)
    tipping_tour_leader_child = fields.Boolean('Apply for Child', default=True)
    tipping_driver_child = fields.Boolean('Apply for Child', default=True)
    tipping_guide_infant = fields.Boolean('Apply for Infant', default=True)
    tipping_tour_leader_infant = fields.Boolean('Apply for Infant', default=True)
    tipping_driver_infant = fields.Boolean('Apply for Infant', default=True)
    other_charges_ids = fields.One2many('tt.master.tour.other.charges', 'master_tour_id', 'Other Charges')
    duration = fields.Integer('Duration (days)', help="in day(s)", default=1)
    guiding_days = fields.Integer('Guiding Days', default=1)
    driving_times = fields.Integer('Driving Times', default=0)

    # deprecated
    adult_fare = fields.Monetary('Adult Fare', default=0)
    adult_commission = fields.Monetary('Adult Commission', default=0)

    child_fare = fields.Monetary('Child Fare', default=0)
    child_commission = fields.Monetary('Child Commission', default=0)

    infant_fare = fields.Monetary('Infant Fare', default=0)
    infant_commission = fields.Monetary('Infant Commission', default=0)
    # end of deprecated

    discount_ids = fields.One2many('tt.master.tour.discount', 'tour_id')
    room_ids = fields.One2many('tt.master.tour.rooms', 'tour_pricelist_id')

    tour_leader_ids = fields.Many2many('tt.employee', string="Tour Leader")
    # tour_leader_ids = fields.Many2many('tt.employee', 'tour_leader_rel', 'pricelist_id', 'partner_id',
    #                                    string="Tour Leader")
    # tour_checklist_ids = fields.Char('Tour Checklist')
    tour_checklist_ids = fields.One2many('tt.master.tour.checklist', 'tour_pricelist_id', string="Tour Checklist")

    other_info_ids = fields.One2many('tt.master.tour.otherinfo', 'master_tour_id', 'Other Info')
    other_info_preview = fields.Html('Other Info Preview')
    image_ids = fields.Many2many('tt.upload.center', 'tour_images_rel', 'tour_id', 'image_id', 'Images')

    flight_segment_ids = fields.One2many('flight.segment', 'tour_pricelist_id', string="Flight Segment")
    # visa_pricelist_ids = fields.Many2many('tt.traveldoc.pricelist', 'tour_visa_rel', 'tour_id', 'visa_id',
    #                                       domain=[('transport_type', '=', 'visa')], string='Visa Pricelist')
    passengers_ids = fields.One2many('tt.reservation.passenger.tour', 'master_tour_id', string='Tour Participants', copy=False)
    sequence = fields.Integer('Sequence', default=50, required=True)
    adjustment_ids = fields.One2many('tt.master.tour.adjustment', 'tour_pricelist_id', required=True)
    survey_title_ids = fields.One2many('survey.survey', 'tour_id', string='Tour Surveys', copy=False)
    quotation_ids = fields.One2many('tt.master.tour.quotation', 'tour_id', 'Tour Quotation(s)')

    country_name = fields.Char('Country Name')
    itinerary_ids = fields.One2many('tt.reservation.tour.itinerary', 'tour_pricelist_id', 'Itinerary')
    document_url = fields.Many2one('tt.upload.center', 'Document URL')
    related_provider_ids = fields.One2many('tt.master.tour.provider', 'master_tour_id', 'Related Vendor(s)')
    import_other_info = fields.Binary('Import JSON')
    export_other_info = fields.Binary('Export JSON')
    file_name = fields.Char("Filename", compute="_compute_filename", store=True)
    active = fields.Boolean('Active', default=True)

    @api.depends("name")
    def _compute_filename(self):
        for rec in self:
            rec.file_name = rec.name+".json"

    @api.depends("location_ids")
    @api.onchange("location_ids")
    def _compute_country_str(self):
        for rec in self:
            temp_loc = ''
            for rec2 in rec.location_ids:
                temp_loc += rec2.country_id.name + ', '
            rec.country_str = temp_loc and temp_loc[:-2] or ''

    @api.depends("carrier_id")
    @api.onchange("carrier_id")
    def _compute_tour_route(self):
        for rec in self:
            if rec.carrier_id.id == self.env.ref('tt_reservation_tour.tt_transport_carrier_tour_itt'):
                rec.tour_route = 'international'
            else:
                rec.tour_route = 'domestic'

    @api.depends("tour_line_ids")
    @api.onchange("tour_line_ids")
    def _compute_tour_line_amount(self):
        for rec in self:
            line_amt = 0
            for rec2 in rec.tour_line_ids:
                if rec2.active and rec2.state in ['open', 'definite']:
                    line_amt += 1
            rec.tour_line_amount = line_amt

    @api.onchange('owner_ho_id')
    def _onchange_domain_tour_type(self):
        return {'domain': {
            'tour_type_id': [('ho_id', '=', self.owner_ho_id.id)]
        }}

    @api.onchange('tour_type_id')
    def _set_to_null(self):
        for rec in self:
            if not rec.tour_type_id.is_use_tour_leader:
                rec.tipping_tour_leader = 0

    # temporary function
    def update_tour_code_temp(self):
        all_tours = self.env['tt.master.tour'].search([])
        for rec in all_tours:
            if rec.provider_id and rec.tour_code:
                prefix = rec.provider_id.alias and rec.provider_id.alias + '~' or ''
                rec.write({
                    'tour_code': prefix + rec.tour_code
                })

    @api.model
    def create(self, vals):
        if not vals.get('owner_ho_id'):
            vals.update({
                'owner_ho_id': self.env.user.ho_id.id
            })
        if not vals.get('ho_ids'):
            vals.update({
                'ho_ids': [(4, self.env.user.ho_id.id)]
            })
        if vals.get('name'):
            inc_value = 0
            temp_slug = util.slugify_str(vals['name'])
            existing_tours = self.env['tt.master.tour'].search([('name', '=ilike', vals['name']), '|', ('active', '=', False), ('active', '=', True)])
            # loop untuk cek kasus anomali dimana ada name yang manual diisi pake angka (1, 2, dll)
            while existing_tours:
                inc_value += len(existing_tours)
                temp_slug = '%s-%s' % (util.slugify_str(vals['name']), str(inc_value))
                existing_tours = self.env['tt.master.tour'].search([('tour_slug', '=ilike', temp_slug), '|', ('active', '=', False), ('active', '=', True)], limit=1)
            vals.update({
                'tour_slug': temp_slug
            })
        res = super(MasterTour, self).create(vals)
        return res

    @api.multi
    def write(self, vals):
        admin_obj_id = self.env.ref('base.user_admin').id
        root_obj_id = self.env.ref('base.user_root').id
        if not self.env.user.has_group('base.group_erp_manager') and not self.env.user.id in [admin_obj_id, root_obj_id] and self.env.user.ho_id.id != self.owner_ho_id.id:
            raise UserError('You do not have permission to edit this record.')
        if vals.get('name'):
            inc_value = 0
            temp_slug = util.slugify_str(vals['name'])
            existing_tours = self.env['tt.master.tour'].search([('name', '=ilike', vals['name']), '|', ('active', '=', False), ('active', '=', True)])
            # loop untuk cek kasus anomali dimana ada name yang manual diisi pake angka (1, 2, dll)
            while existing_tours:
                inc_value += len(existing_tours)
                temp_slug = '%s-%s' % (util.slugify_str(vals['name']), str(inc_value))
                existing_tours = self.env['tt.master.tour'].search([('tour_slug', '=ilike', temp_slug), '|', ('active', '=', False), ('active', '=', True)], limit=1)
            vals.update({
                'tour_slug': temp_slug
            })
        return super(MasterTour, self).write(vals)

    def generate_slug_all_tours(self):
        all_tours = self.env['tt.master.tour'].search([('tour_slug', '=', False)])
        for rec in all_tours:
            if rec.name:
                inc_value = 0
                temp_slug = util.slugify_str(rec.name)
                existing_tours = self.env['tt.master.tour'].search([('name', '=ilike', rec.name), ('tour_slug', '!=', False), '|', ('active', '=', False), ('active', '=', True)])
                # loop untuk cek kasus anomali dimana ada name yang manual diisi pake angka (1, 2, dll)
                while existing_tours:
                    inc_value += len(existing_tours)
                    temp_slug = '%s-%s' % (util.slugify_str(rec.name), str(inc_value))
                    existing_tours = self.env['tt.master.tour'].search([('tour_slug', '=ilike', temp_slug), '|', ('active', '=', False), ('active', '=', True)], limit=1)
                rec.write({
                    'tour_slug': temp_slug
                })

    def action_get_internal_tour_json(self):
        raise UserError(_("This Provider does not support Sync Products."))

    def action_sync_internal_tour(self, start, end):
        raise UserError(_("This Provider does not support Sync Products."))

    def action_get_gochina_json(self):
        raise UserError(_("This Provider does not support Sync Products."))

    def action_sync_gochina(self, start, end):
        raise UserError(_("This Provider does not support Sync Products."))

    def action_get_rodextrip_tour_json(self):
        req_post = {
            'country_id': 0,
            'city_id': 0,
            'month': '00',
            'year': '0000',
            'tour_query': '',
            'provider': 'rodextrip_tour',
        }
        ## tambah context
        ## kurang test
        ho_id = self.env.user.ho_id.id
        res = self.env['tt.master.tour.api.con'].search_provider(req_post, ho_id)
        temp = {}
        if res['error_code'] == 0:
            temp = res['response']
        else:
            raise UserError(res['error_msg'])
        if temp:
            folder_path = '/var/log/tour_travel/rodextrip_tour_master_data'
            if not os.path.exists(folder_path):
                os.mkdir(folder_path)
            file = open('/var/log/tour_travel/rodextrip_tour_master_data/rodextrip_tour_master_data.json', 'w')
            file.write(json.dumps(temp))
            file.close()

    def action_sync_rodextrip_tour(self, start, end):
        provider = 'rodextrip_tour'

        file = []
        for i in range(int(start), int(end) + 1):
            file_dat = open('/var/log/tour_travel/rodextrip_tour_master_data/rodextrip_tour_master_data.json', 'r')
            file = json.loads(file_dat.read())
            file_dat.close()
            if file:
                self.sync_products(provider, file)

    def copy_tour(self, return_obj=False):
        if not self.env.user.has_group('tt_base.group_master_data_tour_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 295')
        new_tour_obj = self.copy()
        for rec in self.tour_line_ids:
            new_tour_line_obj = self.env['tt.master.tour.lines'].create({
                'departure_date': rec.departure_date,
                'arrival_date': rec.arrival_date,
                'seat': rec.quota,
                'quota': rec.quota,
                'sequence': rec.sequence,
                'down_payment': rec.down_payment,
                'is_restrict_monday': rec.is_restrict_monday,
                'is_restrict_tuesday': rec.is_restrict_tuesday,
                'is_restrict_wednesday': rec.is_restrict_wednesday,
                'is_restrict_thursday': rec.is_restrict_thursday,
                'is_restrict_friday': rec.is_restrict_friday,
                'is_restrict_saturday': rec.is_restrict_saturday,
                'is_restrict_sunday': rec.is_restrict_sunday,
                'master_tour_id': new_tour_obj.id
            })
            for rec2 in rec.payment_rules_ids:
                self.env['tt.payment.rules'].create({
                    'name': rec2.name,
                    'payment_percentage': rec2.payment_percentage,
                    'description': rec2.description,
                    'due_date': rec2.due_date,
                    'tour_lines_id': new_tour_line_obj.id,
                })
            for rec2 in rec.special_dates_ids:
                self.env['tt.master.tour.special.dates'].create({
                    'name': rec2.name,
                    'date': rec2.date,
                    'currency_id': rec2.currency_id.id,
                    'additional_adult_fare': rec2.additional_adult_fare,
                    'additional_adult_commission': rec2.additional_adult_commission,
                    'additional_child_fare': rec2.additional_child_fare,
                    'additional_child_commission': rec2.additional_child_commission,
                    'additional_infant_fare': rec2.additional_infant_fare,
                    'additional_infant_commission': rec2.additional_infant_commission,
                    'tour_line_id': new_tour_line_obj.id,
                })
        for rec in self.other_charges_ids:
            self.env['tt.master.tour.other.charges'].create({
                'name': rec.name,
                'pax_type': rec.pax_type,
                'currency_id': rec.currency_id.id,
                'amount': rec.amount,
                'charge_type': rec.charge_type,
                'master_tour_id': new_tour_obj.id
            })
        for rec in self.room_ids:
            new_tour_room_obj = self.env['tt.master.tour.rooms'].create({
                'name': rec.name,
                'bed_type': rec.bed_type,
                'description': rec.description,
                'hotel': rec.hotel,
                'address': rec.address,
                'star': rec.star,
                'adult_surcharge': rec.adult_surcharge,
                'child_surcharge': rec.child_surcharge,
                'additional_charge': rec.additional_charge,
                'pax_minimum': rec.pax_minimum,
                'pax_limit': rec.pax_limit,
                'adult_limit': rec.adult_limit,
                'extra_bed_limit': rec.extra_bed_limit,
                'tour_pricelist_id': new_tour_obj.id,
            })
            for rec2 in rec.tour_pricing_ids:
                self.env['tt.master.tour.pricing'].create({
                    'currency_id': rec2.currency_id.id,
                    'min_pax': rec2.min_pax,
                    'is_infant_included': rec2.is_infant_included,
                    'adult_fare': rec2.adult_fare,
                    'adult_commission': rec2.adult_commission,
                    'child_fare': rec2.child_fare,
                    'child_commission': rec2.child_commission,
                    'infant_fare': rec2.infant_fare,
                    'infant_commission': rec2.infant_commission,
                    'room_id': new_tour_room_obj.id
                })
        for rec in self.flight_segment_ids:
            self.env['flight.segment'].create({
                'journey_type': rec.journey_type,
                'class_of_service': rec.class_of_service,
                'carrier_id': rec.carrier_id.id,
                'carrier_number': rec.carrier_number,
                'origin_id': rec.origin_id.id,
                'origin_terminal': rec.origin_terminal,
                'destination_id': rec.destination_id.id,
                'destination_terminal': rec.destination_terminal,
                'departure_date': rec.departure_date,
                'arrival_date': rec.arrival_date,
                'departure_date_fmt': rec.departure_date_fmt,
                'arrival_date_fmt': rec.arrival_date_fmt,
                'tour_pricelist_id': new_tour_obj.id,
            })
        for rec in self.itinerary_ids:
            new_itin_obj = self.env['tt.reservation.tour.itinerary'].create({
                'name': rec.name,
                'day': rec.day,
                'tour_pricelist_id': new_tour_obj.id,
            })
            for rec2 in rec.item_ids:
                self.env['tt.reservation.tour.itinerary.item'].create({
                    'name': rec2.name,
                    'description': rec2.description,
                    'timeslot': rec2.timeslot,
                    'sequence': rec2.sequence,
                    'image_id': rec2.image_id.id,
                    'itinerary_id': new_itin_obj.id,
                })
        new_image_ids = []
        for rec in self.image_ids:
            new_image_ids.append(rec.id)
        new_tour_obj.write({
            'image_ids': [(6, 0, new_image_ids)]
        })

        new_loc_ids = []
        for rec in self.location_ids:
            new_loc_ids.append(rec.id)
        new_tour_obj.write({
            'location_ids': [(6, 0, new_loc_ids)]
        })

        other_info_ids = []
        for rec in self.other_info_ids:
            other_info_ids.append(new_tour_obj.create_other_info_from_json(rec.convert_info_to_dict()))
        new_tour_obj.write({
            'other_info_ids': [(6, 0, other_info_ids)]
        })

        if return_obj:
            return new_tour_obj
        else:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            action_num = self.env.ref('tt_reservation_tour.tt_master_tour_view_action').id
            menu_num = self.env.ref('tt_reservation_tour.submenu_tour_pricelist').id
            return {
                'type': 'ir.actions.act_url',
                'name': new_tour_obj.name,
                'target': 'self',
                'url': base_url + "/web#id=" + str(new_tour_obj.id) + "&action=" + str(
                    action_num) + "&model=tt.master.tour&view_type=form&menu_id=" + str(menu_num),
            }

    def sync_products(self, provider=None, data=None, page=None):
        file = data
        if file:
            for rec in file['result']:
                provider_obj = self.env['tt.provider'].search([('code', '=', rec['provider'])], limit=1)
                provider_obj = provider_obj and provider_obj[0] or False
                carrier_obj = self.env['tt.transport.carrier'].search([('code', '=', rec['carrier_code'])], limit=1)
                carrier_obj = carrier_obj and carrier_obj[0] or False
                currency_obj = self.env['res.currency'].search([('name', '=', rec['currency_code'])], limit=1)
                currency_obj = currency_obj and currency_obj[0] or False
                tour_type_obj = self.env['tt.master.tour.type'].search([('is_can_choose_hotel', '=', rec['tour_type']['is_can_choose_hotel']),
                                                                        ('is_use_tour_leader', '=', rec['tour_type']['is_use_tour_leader']),
                                                                        ('is_open_date', '=', rec['tour_type']['is_open_date']),
                                                                        ('ho_id', '=', self.env.user.ho_id.id)])
                if tour_type_obj:
                    tour_type_obj = tour_type_obj[0]
                else:
                    tour_type_obj = self.env['tt.master.tour.type'].create({
                        'name': rec['tour_type']['name'],
                        'description': rec['tour_type']['description'],
                        'is_can_choose_hotel': rec['tour_type']['is_can_choose_hotel'],
                        'is_use_tour_leader': rec['tour_type']['is_use_tour_leader'],
                        'is_open_date': rec['tour_type']['is_open_date'],
                        'ho_id': self.env.user.ho_id.id
                    })
                vals = {
                    'name': rec['name'],
                    'description': rec['description'],
                    'tour_code': rec['tour_code'],
                    'tour_category': rec['tour_category'],
                    'tour_type_id': tour_type_obj and tour_type_obj.id or False,
                    'duration': rec['duration'],
                    'is_can_hold': rec['is_can_hold'],
                    'hold_date_timer': rec['hold_date_timer'],
                    'est_starting_price': rec['est_starting_price'],
                    'adult_flight_fare': rec['adult_flight_fare'],
                    'child_flight_fare': rec['child_flight_fare'],
                    'infant_flight_fare': rec['infant_flight_fare'],
                    'adult_visa_fare': rec['adult_visa_fare'],
                    'child_visa_fare': rec['child_visa_fare'],
                    'infant_visa_fare': rec['infant_visa_fare'],
                    'adult_airport_tax': rec['adult_airport_tax'],
                    'child_airport_tax': rec['child_airport_tax'],
                    'infant_airport_tax': rec['infant_airport_tax'],
                    'tipping_guide': rec['tipping_guide'],
                    'tipping_tour_leader': rec['tipping_tour_leader'],
                    'tipping_driver': rec['tipping_driver'],
                    'tipping_guide_child': rec['tipping_guide_child'],
                    'tipping_tour_leader_child': rec['tipping_tour_leader_child'],
                    'tipping_driver_child': rec['tipping_driver_child'],
                    'tipping_guide_infant': rec['tipping_guide_infant'],
                    'tipping_tour_leader_infant': rec['tipping_tour_leader_infant'],
                    'tipping_driver_infant': rec['tipping_driver_infant'],
                    'guiding_days': rec['guiding_days'],
                    'driving_times': rec['driving_times'],
                    'provider_id': provider_obj and provider_obj.id or False,
                    'carrier_id': carrier_obj and carrier_obj.id or False,
                    'currency_id': currency_obj and currency_obj.id or False,
                    'active': True,
                    'owner_ho_id': self.env.user.ho_id.id,
                    'ho_ids': [(4, self.env.user.ho_id.id)]
                }
                new_tour_obj = self.env['tt.master.tour'].search([('tour_code', '=', rec['tour_code']), ('provider_id', '=', provider_obj.id), '|', '|', ('owner_ho_id', '=', self.env.user.ho_id.id), ('ho_ids', '=', self.env.user.ho_id.id), ('ho_ids', '=', False), '|', ('active', '=', False), ('active', '=', True)], limit=1)
                if new_tour_obj:
                    new_tour_obj = new_tour_obj[0]
                    new_tour_obj.write(vals)
                else:
                    new_tour_obj = self.env['tt.master.tour'].create(vals)

                req_post = {
                    'tour_code': rec['tour_code'],
                    'provider': rec['provider'],
                }
                ## tambah context
                ## kurang test
                ho_id = self.env.user.ho_id.id
                det_res = self.env['tt.master.tour.api.con'].get_details_provider(req_post, ho_id)
                if det_res['error_code'] == 0:
                    for temp_line in new_tour_obj.tour_line_ids:
                        temp_line.write({
                            'active': False
                        })
                    for temp_charge in new_tour_obj.other_charges_ids:
                        temp_charge.write({
                            'active': False
                        })
                    for temp_room in new_tour_obj.room_ids:
                        temp_room.write({
                            'active': False
                        })
                    for temp_flight in new_tour_obj.flight_segment_ids:
                        temp_flight.unlink()
                    for temp_itin in new_tour_obj.itinerary_ids:
                        temp_itin.unlink()
                    for temp_img in new_tour_obj.image_ids:
                        temp_img.unlink()
                    for temp_loc in new_tour_obj.location_ids:
                        temp_loc.unlink()
                    if det_res['response'].get('selected_tour'):
                        detail_dat = det_res['response']['selected_tour']
                        for rec_det in detail_dat['tour_lines']:
                            new_tour_line_vals = {
                                'tour_line_code': rec_det['tour_line_code'],
                                'departure_date': rec_det['departure_date'],
                                'arrival_date': rec_det['arrival_date'],
                                'seat': rec_det['seat'],
                                'quota': rec_det['quota'],
                                'sequence': rec_det['sequence'],
                                'down_payment': rec_det['down_payment'],
                                'master_tour_id': new_tour_obj.id,
                                'active': True
                            }
                            new_tour_line_obj = self.env['tt.master.tour.lines'].search([('tour_line_code', '=', rec_det['tour_line_code']), ('master_tour_id', '=', new_tour_obj.id), '|', ('active', '=', False), ('active', '=', True)], limit=1)
                            if new_tour_line_obj:
                                new_tour_line_obj = new_tour_line_obj[0]
                                new_tour_line_obj.write(new_tour_line_vals)
                            else:
                                new_tour_line_obj = self.env['tt.master.tour.lines'].create(new_tour_line_vals)

                            for pay_rules in new_tour_line_obj.payment_rules_ids:
                                pay_rules.unlink()

                            if rec_det.get('payment_rules_list'):
                                for rec_det2 in rec_det['payment_rules_list']:
                                    payment_rules_vals = {
                                        'name': rec_det2['name'],
                                        'payment_percentage': rec_det2['payment_percentage'],
                                        'description': rec_det2['description'],
                                        'due_date': rec_det2['due_date'],
                                        'tour_lines_id': new_tour_line_obj.id
                                    }
                                    self.env['tt.payment.rules'].create(payment_rules_vals)

                            for spec_date in new_tour_line_obj.special_dates_ids:
                                spec_date.write({
                                    'active': False
                                })

                            if rec_det.get('special_date_list'):
                                for rec_det2 in rec_det['special_date_list']:
                                    tour_special_date_currency_obj = self.env['res.currency'].search([('name', '=', rec_det2['currency_code'])], limit=1)
                                    new_tour_special_date_vals = {
                                        'name': rec_det2['name'],
                                        'date': rec_det2['date'],
                                        'currency_id': tour_special_date_currency_obj and tour_special_date_currency_obj[0].id or False,
                                        'additional_adult_fare': rec_det2['additional_adult_price'],
                                        'additional_child_fare': rec_det2['additional_child_price'],
                                        'additional_infant_fare': rec_det2['additional_infant_price'],
                                        'tour_line_id': new_tour_line_obj.id,
                                        'active': True
                                    }
                                    new_tour_special_date_obj = self.env['tt.master.tour.special.dates'].search([('date', '=', rec_det2['date']), ('tour_line_id', '=', new_tour_line_obj.id), '|', ('active', '=', False), ('active', '=', True)], limit=1)
                                    if new_tour_special_date_obj:
                                        new_tour_special_date_obj[0].write(new_tour_special_date_vals)
                                    else:
                                        self.env['tt.master.tour.special.dates'].create(new_tour_special_date_vals)

                        for rec_det in detail_dat['other_charges']:
                            tour_other_charges_currency_obj = self.env['res.currency'].search([('name', '=', rec_det['currency_id'])], limit=1)
                            new_tour_other_charges_vals = {
                                'name': rec_det['name'],
                                'pax_type': rec_det['pax_type'],
                                'currency_id': tour_other_charges_currency_obj and tour_other_charges_currency_obj[0].id or False,
                                'amount': rec_det['amount'],
                                'charge_type': rec_det['charge_type'],
                                'master_tour_id': new_tour_obj.id,
                                'active': True
                            }
                            new_other_charges_obj = self.env['tt.master.tour.other.charges'].search([('name', '=', rec_det['name']), ('pax_type', '=', rec_det['pax_type']), ('master_tour_id', '=', new_tour_obj.id), '|', ('active', '=', False), ('active', '=', True)], limit=1)
                            if new_other_charges_obj:
                                new_other_charges_obj[0].write(new_tour_other_charges_vals)
                            else:
                                self.env['tt.master.tour.other.charges'].create(new_tour_other_charges_vals)

                        for rec_det in detail_dat['accommodations']:
                            new_acco_vals = {
                                'name': rec_det['name'],
                                'room_code': rec_det['room_code'],
                                'bed_type': rec_det['bed_type'],
                                'description': rec_det['description'],
                                'hotel': rec_det['hotel'],
                                'address': rec_det['address'],
                                'star': rec_det['star'],
                                'adult_surcharge': rec_det['adult_surcharge'],
                                'child_surcharge': rec_det['child_surcharge'],
                                'additional_charge': rec_det['additional_charge'],
                                'pax_minimum': rec_det['pax_minimum'],
                                'pax_limit': rec_det['pax_limit'],
                                'adult_limit': rec_det['adult_limit'],
                                'extra_bed_limit': rec_det['extra_bed_limit'],
                                'tour_pricelist_id': new_tour_obj.id,
                                'active': True,
                            }
                            new_acco_obj = self.env['tt.master.tour.rooms'].search([('room_code', '=', rec_det['room_code']), ('tour_pricelist_id', '=', new_tour_obj.id), '|', ('active', '=', False), ('active', '=', True)], limit=1)
                            if new_acco_obj:
                                new_acco_obj[0].write(new_acco_vals)
                            else:
                                new_acco_obj = self.env['tt.master.tour.rooms'].create(new_acco_vals)

                            if rec_det.get('pricing'):
                                for rec_det2 in rec_det['pricing']:
                                    tour_pricing_currency_obj = self.env['res.currency'].search([('name', '=', rec_det2['currency_id'])], limit=1)
                                    new_tour_pricing_vals = {
                                        'min_pax': rec_det2['min_pax'],
                                        'is_infant_included': rec_det2['is_infant_included'],
                                        'currency_id': tour_pricing_currency_obj and tour_pricing_currency_obj[0].id or False,
                                        'adult_fare': rec_det2['adult_price'],
                                        'adult_commission': 0,
                                        'child_fare': rec_det2['child_price'],
                                        'child_commission': 0,
                                        'infant_fare': rec_det2['infant_price'],
                                        'infant_commission': 0,
                                        'room_id': new_acco_obj.id,
                                        'active': True
                                    }
                                    new_tour_pricing_obj = self.env['tt.master.tour.pricing'].search([('min_pax', '=', int(rec_det2['min_pax'])), ('room_id', '=', new_acco_obj.id), '|', ('active', '=', False), ('active', '=', True)], limit=1)
                                    if new_tour_pricing_obj:
                                        new_tour_pricing_obj[0].write(new_tour_pricing_vals)
                                    else:
                                        self.env['tt.master.tour.pricing'].create(new_tour_pricing_vals)

                        for rec_flight in detail_dat['flight_segments']:
                            carrier_obj = self.env['tt.transport.carrier'].search([('code', '=', rec_flight['carrier_code']), ('provider_type_id', '=', self.env.ref('tt_reservation_airline.tt_provider_type_airline').id)], limit=1)
                            carrier_obj = carrier_obj and carrier_obj[0] or False
                            origin_obj = self.env['tt.destinations'].search([('code', '=', rec_flight['origin_code']), ('provider_type_id', '=', self.env.ref('tt_reservation_airline.tt_provider_type_airline').id)], limit=1)
                            origin_obj = origin_obj and origin_obj[0] or False
                            destination_obj = self.env['tt.destinations'].search([('code', '=', rec_flight['destination_code']), ('provider_type_id', '=', self.env.ref('tt_reservation_airline.tt_provider_type_airline').id)], limit=1)
                            destination_obj = destination_obj and destination_obj[0] or False
                            self.env['flight.segment'].create({
                                'journey_type': rec_flight['journey_type'],
                                'class_of_service': rec_flight['class_of_service'],
                                'carrier_id': carrier_obj and carrier_obj.id or False,
                                'carrier_number': rec_flight['carrier_number'],
                                'origin_id': origin_obj and origin_obj.id or False,
                                'origin_terminal': rec_flight['origin_terminal'],
                                'destination_id': destination_obj and destination_obj.id or False,
                                'destination_terminal': rec_flight['destination_terminal'],
                                'departure_date': datetime.strptime(rec_flight['departure_date'], "%Y-%m-%d %H:%M:%S"),
                                'arrival_date': datetime.strptime(rec_flight['arrival_date'], "%Y-%m-%d %H:%M:%S"),
                                'departure_date_fmt': datetime.strptime(rec_flight['departure_date_fmt'], "%d-%b-%Y %H:%M"),
                                'arrival_date_fmt': datetime.strptime(rec_flight['arrival_date_fmt'], "%d-%b-%Y %H:%M"),
                                'tour_pricelist_id': new_tour_obj.id,
                            })
                        for rec_itin in detail_dat['itinerary_ids']:
                            new_itin_obj = self.env['tt.reservation.tour.itinerary'].create({
                                'name': rec_itin['name'],
                                'day': rec_itin['day'],
                                'tour_pricelist_id': new_tour_obj.id,
                            })
                            for rec_item in rec_itin['items']:
                                self.env['tt.reservation.tour.itinerary.item'].create({
                                    'name': rec_item['name'],
                                    'description': rec_item['description'],
                                    'timeslot': rec_item['timeslot'],
                                    'sequence': rec_item['sequence'],
                                    'image_id': rec_item.get('image') and self.convert_image_to_own(rec_item['image'], rec_item['image_file_name']) or False,
                                    'itinerary_id': new_itin_obj.id,
                                })
                        new_image_ids = []
                        for rec_det in detail_dat['images_obj']:
                            new_image_ids.append(self.convert_image_to_own(rec_det['url'], rec_det['filename']))
                            self.env.cr.commit()
                        new_tour_obj.write({
                            'image_ids': [(6, 0, new_image_ids)]
                        })
                        for rec_other in detail_dat['other_infos']:
                            new_tour_obj.create_other_info_from_json(rec_other)

                        new_loc_ids = []
                        for rec_loc in detail_dat['locations']:
                            search_params = []
                            new_country_obj = self.env['res.country'].search([('code', '=', rec_loc['country_code'])], limit=1)
                            new_city_obj = self.env['res.city'].search([('name', '=', rec_loc['city_name'])], limit=1)
                            if new_country_obj:
                                search_params.append(('country_id', '=', new_country_obj[0].id))
                            if new_city_obj:
                                search_params.append(('city_id', '=', new_city_obj[0].id))
                            if search_params:
                                temp_loc = self.env['tt.tour.master.locations'].search(search_params, limit=1)
                                if temp_loc:
                                    new_loc = temp_loc[0]
                                else:
                                    new_loc = self.env['tt.tour.master.locations'].create({
                                        'country_id': new_country_obj and new_country_obj[0].id or False,
                                        'city_id': new_city_obj and new_city_obj[0].id or False,
                                        'state_id': False,
                                    })
                                    self.env.cr.commit()
                                new_loc_ids.append(new_loc.id)
                        new_tour_obj.write({
                            'location_ids': [(6, 0, new_loc_ids)]
                        })
                        if new_tour_obj.state == 'draft':
                            new_tour_obj.action_confirm()
                else:
                    raise UserError(det_res['error_msg'])

    def convert_image_to_own(self, img_url, img_filename):
        headers = {
            'Content-Type': 'application/json',
        }
        image_data = util.send_request(img_url, data={}, headers=headers, method='GET', content_type='content', timeout=600)
        if image_data['error_code'] == 0:
            attachment_value = {
                'filename': img_filename and str(img_filename) or 'image.jpg',
                'file_reference': 'Tour Package Image: ' + str(img_filename),
                'file': image_data['response'],
                'delete_date': False
            }
            context = {
                'co_uid': self.env.user.id,
                'co_agent_id': self.env.user.agent_id.id
            }
            attachment_obj = self.env['tt.upload.center.wizard'].upload_file_api(attachment_value, context)
            if attachment_obj['error_code'] == 0:
                upload_obj = self.env['tt.upload.center'].search([('seq_id', '=', attachment_obj['response']['seq_id'])], limit=1)
                return upload_obj and upload_obj[0].id or False
            else:
                return False
        else:
            return False

    def set_to_draft(self):
        if not self.env.user.has_group('tt_base.group_master_data_tour_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 296')
        self.state = 'draft'
        for rec in self.tour_line_ids:
            if rec.state == 'closed':
                rec.action_reopen()

    def action_confirm(self):
        if not self.env.user.has_group('tt_base.group_master_data_tour_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 297')
        if self.state != 'draft':
            raise UserError(_('Cannot confirm master tour because state is not "draft"!'))
        if not self.provider_id:
            raise UserError(_('Please fill Provider!'))
        if not self.tour_line_ids:
            raise UserError(_('Please add at least 1 Tour Line(s)!'))
        if not self.location_ids:
            raise UserError(_('Please add at least 1 Tour Location(s)!'))
        if any(not rec.check_confirm_validity() for rec in self.room_ids):
            raise UserError(_('Please make sure every accommodation rooms in this tour have an active default pricing (pricing for min 1 pax)'))

        self.state = 'confirm'
        prefix = self.provider_id.alias and self.provider_id.alias + '~' or ''
        if not self.tour_code:
            self.tour_code = prefix + self.env['ir.sequence'].next_by_code('master.tour.code')
            # if self.tour_type == 'private':
            #     self.tour_code = prefix + self.env['ir.sequence'].next_by_code('master.tour.code.fit')
            # else:
            #     self.tour_code = prefix + self.env['ir.sequence'].next_by_code('master.tour.code.group')
        for rec in self.tour_line_ids:
            rec.action_validate()

    def action_closed(self):
        if not self.env.user.has_group('tt_base.group_master_data_tour_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 298')
        self.state = 'closed'
        for rec in self.tour_line_ids:
            rec.action_closed()

    @api.multi
    def action_send_email(self, passenger_id):
        return passenger_id

    def action_send_survey(self):
        for rec in self:
            for passenger in rec.passengers_ids:
                self.action_send_email(passenger.id)

    def create_other_info_from_json(self, data):
        message_id_list = []
        for rec in data['message']:
            msg_obj = self.env['tt.master.tour.otherinfo.messages'].create({
                'name': rec['text'],
                'style': rec['style'],
                'sequence': rec['sequence'],
            })
            message_id_list.append(msg_obj.id)

        other_info_obj = self.env['tt.master.tour.otherinfo'].create({
            'child_list_type': data['child_list_type'],
            'sequence': data['sequence'],
            'info_message_ids': [(6, 0, message_id_list)],
            'child_ids': [(6, 0, [self.create_other_info_from_json(chd_obj) for chd_obj in data['children']])]
        })

        return other_info_obj.id

    def export_other_info_json(self):
        list_of_dict = []
        for rec in self.other_info_ids:
            list_of_dict.append(rec.convert_info_to_dict())
        json_data = json.dumps(list_of_dict)
        self.write({
            'export_other_info': base64.b64encode(json_data.encode())
        })

    def import_other_info_json(self):
        if not self.import_other_info:
            raise UserError(_('Please upload a json file before pressing this button!'))
        try:
            other_info_list = []
            upload_file = json.loads(base64.b64decode(self.import_other_info))
            for rec in self.other_info_ids:
                rec.unlink()
            for rec in upload_file:
                other_info_list.append(self.create_other_info_from_json(rec))
            self.write({
                'import_other_info': False,
                'other_info_ids': [(6, 0, other_info_list)]
            })
        except Exception as e:
            raise UserError(_('The uploaded file cannot be read. Please upload a valid JSON file!'))

    def read_other_info_dict(self, data, current_list_type):
        temp_txt = ''
        if data.get('message'):
            if current_list_type != 'none':
                temp_txt += '<li>'

            for rec2 in data['message']:
                if rec2['style'] == 'B':
                    temp_txt += '<b>' + str(rec2['text']) + '</b>'
                elif rec2['style'] == 'I':
                    temp_txt += '<i>' + str(rec2['text']) + '</i>'
                elif rec2['style'] == 'U':
                    temp_txt += '<u>' + str(rec2['text']) + '</u>'
                else:
                    temp_txt += str(rec2['text'])

            if current_list_type != 'none':
                temp_txt += '</li>'
            else:
                temp_txt += '<br/>'

        list_type_opt = {
            'none': {
                'start': '',
                'end': ''
            },
            'number': {
                'start': '<ol type="1">',
                'end': '</ol>'
            },
            'letter': {
                'start': '<ol type="a">',
                'end': '</ol>'
            },
            'dots': {
                'start': '<ul>',
                'end': '</ul>'
            },
            'romans': {
                'start': '<ol type="I">',
                'end': '</ol>'
            },
        }

        if data.get('children'):
            temp_txt += str(list_type_opt[data['child_list_type']]['start'])
            for rec2 in data['children']:
                temp_txt += str(self.read_other_info_dict(rec2, data['child_list_type']))
            temp_txt += str(list_type_opt[data['child_list_type']]['end'])

        return temp_txt

    def generate_other_info_preview(self):
        temp_txt = ''
        list_of_dict = []
        for rec in self.other_info_ids:
            list_of_dict.append(rec.convert_info_to_dict())

        for rec in list_of_dict:
            temp_txt += str(self.read_other_info_dict(rec, 'none'))
            temp_txt += '<br/>'

        self.write({
            'other_info_preview': str(temp_txt)
        })

    def get_tour_other_info(self):
        list_of_dict = []
        for rec in self.other_info_ids.sorted('sequence'):
            list_of_dict.append(rec.convert_info_to_dict())

        return list_of_dict

    def int_with_commas(self, x):
        result = ''
        while x >= 1000:
            x, r = divmod(x, 1000)
            result = ".%03d%s" % (r, result)
        return "%d%s" % (x, result)

    def search_tour_api(self, data, context, **kwargs):
        try:
            search_request = {
                'country_id': data.get('country_id') and data['country_id'] or 0,
                'city_id': data.get('city_id') and data['city_id'] or 0,
                'departure_month': data.get('month') and data['month'] or '00',
                'departure_year': data.get('year') and data['year'] or '0000',
                'tour_query': data.get('tour_query') and str(data['tour_query']) or '',
            }

            search_request.update({
                'departure_date': str(search_request['departure_year']) + '-' + str(search_request['departure_month'])
            })

            result = []
            search_params = [('state', '=', 'confirm')]
            if search_request.get('tour_query'):
                search_params.append(('name', 'ilike', search_request['tour_query']))
            if context.get('co_ho_id'):
                search_params += ['|', '|', ('owner_ho_id', '=', int(context['co_ho_id'])), ('ho_ids', '=', int(context['co_ho_id'])), ('ho_ids', '=', False)]
            elif context.get('ho_seq_id'):
                ho_obj = self.env['tt.agent'].search([('seq_id', '=', context['ho_seq_id'])], limit=1)
                search_params += ['|', '|', ('owner_ho_id', '=', int(ho_obj[0].id)), ('ho_ids', '=', int(ho_obj[0].id)), ('ho_ids', '=', False)]
            else:
                search_params.append(('ho_ids', '=', False))
            master_tour_list = self.env['tt.master.tour'].search(search_params)
            for rec in master_tour_list:
                location_list = []
                country_id_list = []
                city_id_list = []
                qualify = True
                for rec2 in rec.location_ids:
                    location_list.append({
                        'city_name': rec2.city_id and rec2.city_id.name or '',
                        'country_name': rec2.country_id and rec2.country_id.name or '',
                        'state_name': rec2.state_id and rec2.state_id.name or '',
                    })
                    country_id_list.append(rec2.country_id.id)
                    city_id_list.append(rec2.city_id.id)
                if search_request['country_id'] != 0:
                    if search_request['country_id'] not in country_id_list:
                        qualify = False
                if search_request['city_id'] != 0:
                    if search_request['city_id'] not in city_id_list:
                        qualify = False

                if rec.tour_category == 'private':
                    if rec.agent_id != context['co_agent_id']:
                        qualify = False

                if qualify:
                    image_list = []
                    for img in rec.image_ids.sorted('sequence'):
                        image_list.append({
                            'seq_id': img.seq_id and img.seq_id or '',
                            'url': img.url and img.url or '',
                            'filename': img.filename and img.filename or '',
                        })
                    tour_line_qualify = False
                    tour_line_list = []
                    for rec2 in rec.tour_line_ids:
                        if rec2.active:
                            if (rec2.departure_date and rec2.departure_date >= fields.Date.today()) or rec.tour_type_id.is_open_date:
                                tour_line_list.append(rec2.to_dict())
                                str_dept_date = rec2.departure_date.strftime("%Y-%m-%d")
                                if search_request['departure_month'] != '00':
                                    if search_request['departure_year'] != '0000':
                                        if str_dept_date[:7] == search_request['departure_date']:
                                            tour_line_qualify = True
                                    else:
                                        if str_dept_date[5:7] == search_request['departure_month']:
                                            tour_line_qualify = True
                                elif search_request['departure_year'] != '0000':
                                    if str_dept_date[:4] == search_request['departure_year']:
                                        tour_line_qualify = True
                                else:
                                    tour_line_qualify = True
                    if tour_line_qualify:
                        result.append({
                            'name': rec.name,
                            'tour_code': rec.tour_code,
                            'tour_slug': rec.tour_slug,
                            'tour_route': rec.tour_route,
                            'tour_lines': tour_line_list,
                            'tour_line_amount': rec.tour_line_amount,
                            'tour_category': rec.tour_category,
                            'tour_type': rec.tour_type_id.to_dict(),
                            'tour_type_str': rec.tour_type_id.name,
                            'description': rec.description,
                            'currency_code': rec.currency_id.name,
                            'carrier_code': rec.carrier_id.code,
                            'duration': rec.duration,
                            'is_can_hold': rec.is_can_hold,
                            'hold_date_timer': rec.hold_date_timer,
                            'locations': location_list,
                            'provider': rec.provider_id.code,
                            'images_obj': image_list,
                            'est_starting_price': rec.est_starting_price,
                            'adult_flight_fare': rec.adult_flight_fare,
                            'child_flight_fare': rec.child_flight_fare,
                            'infant_flight_fare': rec.infant_flight_fare,
                            'adult_visa_fare': rec.adult_visa_fare,
                            'child_visa_fare': rec.child_visa_fare,
                            'infant_visa_fare': rec.infant_visa_fare,
                            'adult_airport_tax': rec.adult_airport_tax,
                            'child_airport_tax': rec.child_airport_tax,
                            'infant_airport_tax': rec.infant_airport_tax,
                            'tipping_guide': rec.tipping_guide,
                            'tipping_tour_leader': rec.tipping_tour_leader,
                            'tipping_driver': rec.tipping_driver,
                            'tipping_guide_child': rec.tipping_guide_child,
                            'tipping_tour_leader_child': rec.tipping_tour_leader_child,
                            'tipping_driver_child': rec.tipping_driver_child,
                            'tipping_guide_infant': rec.tipping_guide_infant,
                            'tipping_tour_leader_infant': rec.tipping_tour_leader_infant,
                            'tipping_driver_infant': rec.tipping_driver_infant,
                            'guiding_days': rec.guiding_days,
                            'driving_times': rec.driving_times,
                            'state': rec.state
                        })

            response = {
                'country_id': search_request['country_id'],
                'country': search_request.get('country_name', ''),
                'city_id': search_request['city_id'],
                'city': search_request.get('city_name', ''),
                'search_request': search_request,
                'result': result,
            }
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1022)

    def get_availability_api(self, data, context, **kwargs):
        try:
            tour_lines = []
            if not data.get('provider'):
                default_prov = self.env.ref('tt_reservation_tour.tt_provider_tour_internal')
                data.update({
                    'provider': default_prov.code and default_prov.code or ''
                })
            provider_obj = self.env['tt.provider'].search([('code', '=', data['provider'])], limit=1)
            if not provider_obj:
                raise RequestException(1002)
            provider_obj = provider_obj[0]
            search_params = [('tour_code', '=', provider_obj.alias + '~' + data['tour_code']), ('provider_id', '=', provider_obj.id)]
            if context and context.get('co_ho_id'):
                search_params += ['|', '|', ('owner_ho_id', '=', int(context['co_ho_id'])), ('ho_ids', '=', int(context['co_ho_id'])), ('ho_ids', '=', False)]
            else:
                search_params.append(('ho_ids', '=', False))
            tour_obj = self.env['tt.master.tour'].search(search_params, limit=1)
            if not tour_obj:
                raise RequestException(1022, additional_message='Tour not found.')
            tour_obj = tour_obj[0]
            for rec in tour_obj.tour_line_ids:
                tour_lines.append({
                    'tour_line_code': rec.tour_line_code,
                    'seat': rec.seat,
                    'quota': rec.quota,
                    'state': rec.state
                })
            response = {
                'provider': data['provider'],
                'tour_code': data['tour_code'],
                'tour_lines': tour_lines
            }
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1022)

    def update_availability_api(self, data, context, **kwargs):
        try:
            provider_obj = self.env['tt.provider'].search([('code', '=', data['provider'])], limit=1)
            if not provider_obj:
                raise RequestException(1002)
            provider_obj = provider_obj[0]
            search_params = [('tour_code', '=', provider_obj.alias + '~' + data['tour_code']), ('provider_id', '=', provider_obj.id)]
            if context and context.get('co_ho_id'):
                search_params += ['|', '|', ('owner_ho_id', '=', int(context['co_ho_id'])), ('ho_ids', '=', int(context['co_ho_id'])), ('ho_ids', '=', False)]
            else:
                search_params.append(('ho_ids', '=', False))
            tour_obj = self.env['tt.master.tour'].search(search_params, limit=1)
            if not tour_obj:
                raise RequestException(1022, additional_message='Tour not found.')
            tour_obj = tour_obj[0]
            for rec in tour_obj.tour_line_ids:
                for rec2 in data['tour_lines']:
                    if rec.tour_line_code == rec2['tour_line_code']:
                        rec.write({
                            'seat': rec2['seat'],
                            'quota': rec2['quota'],
                            'state': rec2['state'],
                        })

            response = {
                'provider': data['provider'],
                'tour_code': data['tour_code'],
                'tour_lines': data['tour_lines']
            }
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1025)

    def get_delay(self, day, hour, minute):
        delay_str = str(day)
        delay_str += 'd '
        delay_str += str(hour)
        delay_str += 'h '
        delay_str += str(minute)
        delay_str += 'm'
        return delay_str

    def get_flight_segment(self):
        list_obj = []
        old_vals = {}
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        utc_tz = pytz.timezone('UTC')
        for segment in self.flight_segment_ids:
            vals = {
                'journey_type': segment.journey_type and segment.journey_type or '',
                'class_of_service': segment.class_of_service and segment.class_of_service or '',
                'carrier_id': segment.carrier_id and segment.carrier_id.name or '',
                'carrier_code': segment.carrier_id and segment.carrier_id.code or '',
                'carrier_number': segment.carrier_number and segment.carrier_number or '',
                'origin_id': segment.origin_id and segment.origin_id.display_name or '',
                'origin_code': segment.origin_id and segment.origin_id.code or '',
                'origin_terminal': segment.origin_terminal and segment.origin_terminal or '',
                'departure_date': segment.departure_date and utc_tz.localize(segment.departure_date).astimezone(user_tz) or '',
                'departure_date_fmt': segment.departure_date and utc_tz.localize(segment.departure_date).astimezone(user_tz).strftime('%d-%b-%Y %H:%M') or '',
                'destination_id': segment.destination_id and segment.destination_id.display_name or '',
                'destination_code': segment.destination_id and segment.destination_id.code or '',
                'destination_terminal': segment.destination_terminal and segment.destination_terminal or '',
                'arrival_date': segment.arrival_date and utc_tz.localize(segment.arrival_date).astimezone(user_tz) or '',
                'arrival_date_fmt': segment.arrival_date and utc_tz.localize(segment.arrival_date).astimezone(user_tz).strftime('%d-%b-%Y %H:%M') or '',
                'delay': 'None',
            }
            if old_vals and old_vals.get('journey_type') == segment.journey_type and old_vals.get('arrival_date') and segment.departure_date:
                time_delta = utc_tz.localize(segment.departure_date).astimezone(user_tz) - old_vals['arrival_date']
                day = int(time_delta.days)
                hours = int(time_delta.seconds / 3600)
                minute = int((time_delta.seconds / 60) % 60)
                list_obj[-1]['delay'] = self.get_delay(day, hours, minute)
            list_obj.append(vals)
            old_vals = vals
        return list_obj

    def get_itineraries(self):
        list_obj = []
        for itinerary in self.itinerary_ids:
            it_items = []
            for item in itinerary.item_ids:
                it_items.append({
                    'name': item.name,
                    'description': item.description,
                    'timeslot': item.timeslot,
                    'image': item.image_id.url,
                    'hyperlink': item.hyperlink,
                    'image_file_name': item.image_id.filename,
                    'sequence': item.sequence,
                })
            vals = {
                'name': itinerary.name,
                'day': itinerary.day,
                'items': it_items,
            }
            list_obj.append(vals)
        return list_obj

    def get_tour_details_api(self, data, context, **kwargs):
        try:
            search_request = {
                'tour_code': data.get('tour_code') and data['tour_code'] or '',
                'tour_slug': data.get('tour_slug') and data['tour_slug'] or '',
                'provider': data.get('provider') and data['provider'] or ''
            }
            search_params = [('state', '=', 'confirm')]
            if search_request.get('tour_code'):
                provider_obj = self.env['tt.provider'].search([('alias', '=', search_request['provider'])], limit=1)
                if not provider_obj:
                    raise RequestException(1002)
                provider_obj = provider_obj[0]
                search_params += [('tour_code', '=', provider_obj.alias + '~' + search_request['tour_code']), ('provider_id', '=', provider_obj.id)]
            else:
                search_params += [('tour_slug', '=', search_request['tour_slug'])]
            if context and context.get('co_ho_id'):
                search_params += ['|', '|', ('owner_ho_id', '=', int(context['co_ho_id'])), ('ho_ids', '=', int(context['co_ho_id'])), ('ho_ids', '=', False)]
            else:
                search_params.append(('ho_ids', '=', False))
            tour_obj = self.env['tt.master.tour'].search(search_params, limit=1)
            if not tour_obj:
                raise RequestException(1022, additional_message='Tour not found.')
            tour_obj = tour_obj[0]
            search_request.update({
                'id': tour_obj.id
            })

            tour_line_list = []
            for line in tour_obj.tour_line_ids:
                tour_line_list.append(line.to_dict())

            location_list = []
            country_names = []
            city_names = []
            for location in tour_obj.location_ids:
                temp_country_name = False
                temp_country = False
                temp_city = False
                if location != 0:
                    if location.country_id:
                        temp_country = location.country_id.code
                        temp_country_name = location.country_id.name
                        country_names.append(temp_country_name)

                    if location.city_id:
                        temp_city = location.city_id.name
                        city_names.append(temp_city)

                location_list.append({
                    'country_code': temp_country,
                    'country_name': temp_country_name,
                    'city_name': temp_city,
                })

            accommodations = []
            hotel_names = []
            for acc in tour_obj.room_ids:
                accommodations.append({
                    'room_code': acc.room_code and acc.room_code or '',
                    'name': acc.name and acc.name or '',
                    'sequence': acc.sequence and acc.sequence or 0,
                    'bed_type': acc.bed_type and acc.bed_type or '',
                    'description': acc.description and acc.description or '',
                    'hotel': acc.hotel and acc.hotel or '',
                    'address': acc.address and acc.address or '',
                    'star': acc.star and acc.star or 0,
                    'currency_id': acc.currency_id and acc.currency_id.name or '',
                    'adult_surcharge': acc.adult_surcharge and acc.adult_surcharge or 0,
                    'child_surcharge': acc.child_surcharge and acc.child_surcharge or 0,
                    'additional_charge': acc.additional_charge and acc.additional_charge or 0,
                    'pax_minimum': acc.pax_minimum and acc.pax_minimum or 0,
                    'pax_limit': acc.pax_limit and acc.pax_limit or 0,
                    'adult_limit': acc.adult_limit and acc.adult_limit or 0,
                    'extra_bed_limit': acc.extra_bed_limit and acc.extra_bed_limit or 0,
                    'pricing': [rec.to_dict() for rec in acc.tour_pricing_ids]
                })
                if acc.hotel:
                    hotel_names.append(acc.hotel)

            try:
                self.env.cr.execute("""SELECT tuc.* FROM tt_upload_center tuc LEFT JOIN tour_images_rel tir ON tir.image_id = tuc.id WHERE tir.tour_id = %s AND tuc.active = True ORDER BY sequence;""", (tour_obj.id,))
                images = self.env.cr.dictfetchall()
            except Exception:
                images = []

            final_images = []
            for img_temp in images:
                final_images.append({
                    'seq_id': img_temp['seq_id'],
                    'url': img_temp['url'],
                    'filename': img_temp.get('filename') and img_temp['filename'] or False,
                })

            selected_tour = {
                'name': tour_obj.name,
                'description': tour_obj.description,
                'tour_code': tour_obj.tour_code,
                'tour_category': tour_obj.tour_category,
                'tour_type': tour_obj.tour_type_id.to_dict(),
                'tour_type_str': tour_obj.tour_type_id.name,
                'tour_route': tour_obj.tour_route,
                'tour_lines': tour_line_list,
                'carrier_code': tour_obj.carrier_id.code,
                'carrier_data': tour_obj.carrier_id.to_dict(),
                'accommodations': tour_obj.tour_type_id.is_can_choose_hotel and accommodations or accommodations[:1],
                'currency_code': tour_obj.currency_id.name,
                'est_starting_price': tour_obj.est_starting_price,
                'single_supplement': tour_obj.single_supplement,
                'adult_flight_fare': tour_obj.adult_flight_fare,
                'child_flight_fare': tour_obj.child_flight_fare,
                'infant_flight_fare': tour_obj.infant_flight_fare,
                'adult_visa_fare': tour_obj.adult_visa_fare,
                'child_visa_fare': tour_obj.child_visa_fare,
                'infant_visa_fare': tour_obj.infant_visa_fare,
                'adult_airport_tax': tour_obj.adult_airport_tax,
                'child_airport_tax': tour_obj.child_airport_tax,
                'infant_airport_tax': tour_obj.infant_airport_tax,
                'tipping_guide': tour_obj.tipping_guide,
                'tipping_guide_child': tour_obj.tipping_guide_child,
                'tipping_guide_infant': tour_obj.tipping_guide_infant,
                'tipping_tour_leader': tour_obj.tipping_tour_leader,
                'tipping_tour_leader_child': tour_obj.tipping_tour_leader_child,
                'tipping_tour_leader_infant': tour_obj.tipping_tour_leader_infant,
                'tipping_driver': tour_obj.tipping_driver,
                'tipping_driver_child': tour_obj.tipping_driver_child,
                'tipping_driver_infant': tour_obj.tipping_driver_infant,
                'other_charges': [rec.to_dict() for rec in tour_obj.other_charges_ids],
                'locations': location_list,
                'country_names': country_names,
                'flight_segments': tour_obj.get_flight_segment(),
                'itinerary_ids': tour_obj.get_itineraries(),
                'other_infos': tour_obj.get_tour_other_info(),
                'hotel_names': tour_obj.tour_type_id.is_can_choose_hotel and hotel_names or hotel_names[:1],
                'duration': tour_obj.duration and tour_obj.duration or 0,
                'guiding_days': tour_obj.guiding_days and tour_obj.guiding_days or 0,
                'driving_times': tour_obj.driving_times and tour_obj.driving_times or 0,
                'images_obj': final_images,
                'document_url': tour_obj.document_url and tour_obj.document_url.url or '',
                'provider': tour_obj.provider_id and tour_obj.provider_id.code or '',
                'state': tour_obj.state and tour_obj.state or ''
            }

            response = {
                'search_request': search_request,
                'selected_tour': selected_tour,
            }

            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1022)

    def get_payment_rules_api(self, data, context, **kwargs):
        try:
            search_request = {
                'tour_code': data.get('tour_code') and data['tour_code'] or '',
                'tour_line_code': data.get('tour_line_code') and data['tour_line_code'] or '',
                'provider': data.get('provider') and data['provider'] or ''
            }
            provider_obj = self.env['tt.provider'].search([('code', '=', search_request['provider'])], limit=1)
            if not provider_obj:
                raise RequestException(1002)
            provider_obj = provider_obj[0]
            search_tour_obj = self.env['tt.master.tour'].search([('tour_code', '=', provider_obj.alias + '~' + search_request['tour_code']), ('provider_id', '=', provider_obj.id)], limit=1)
            if not search_tour_obj:
                raise RequestException(1022, additional_message='Tour not found.')
            search_tour_obj = search_tour_obj[0]
            search_tour_line_obj = self.env['tt.master.tour.lines'].search([('tour_line_code', '=', search_request['tour_line_code']), ('master_tour_id', '=', search_tour_obj.id)], limit=1)
            if not search_tour_line_obj:
                raise RequestException(1022, additional_message='Tour Line not found.')
            search_tour_line_obj = search_tour_line_obj[0]
            payment_rules = [
                {
                    'name': 'Down Payment',
                    'description': 'Down Payment',
                    'payment_percentage': search_tour_line_obj.down_payment,
                    'due_date': date.today(),
                    'is_dp': True
                }
            ]
            for payment in search_tour_line_obj.payment_rules_ids:
                vals = {
                    'name': payment.name,
                    'description': payment.description,
                    'payment_percentage': payment.payment_percentage,
                    'due_date': payment.due_date,
                    'is_dp': False
                }
                payment_rules.append(vals)

            response = {
                'payment_rules': payment_rules,
            }
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1022)

    def update_payment_rules_api(self, data, context, **kwargs):
        try:
            search_request = {
                'tour_code': data.get('tour_code') and data['tour_code'] or '',
                'tour_line_code': data.get('tour_line_code') and data['tour_line_code'] or '',
                'provider': data.get('provider') and data['provider'] or ''
            }
            provider_obj = self.env['tt.provider'].search([('code', '=', search_request['provider'])], limit=1)
            if not provider_obj:
                raise RequestException(1002)
            provider_obj = provider_obj[0]
            search_tour_obj = self.env['tt.master.tour'].search([('tour_code', '=', provider_obj.alias + '~' + search_request['tour_code']), ('provider_id', '=', provider_obj.id)], limit=1)
            if not search_tour_obj:
                raise RequestException(1022, additional_message='Tour not found.')
            search_tour_obj = search_tour_obj[0]
            search_tour_line_obj = self.env['tt.master.tour.lines'].search([('tour_line_code', '=', search_request['tour_line_code']), ('master_tour_id', '=', search_tour_obj.id)], limit=1)
            if not search_tour_line_obj:
                raise RequestException(1022, additional_message='Tour Line not found.')
            search_tour_line_obj = search_tour_line_obj[0]
            new_pay_rules = data.get('payment_rules') and data['payment_rules']['payment_rules'] or []
            new_pay_ids = []
            for rec in new_pay_rules:
                if rec.get('is_dp'):
                    if float(rec['payment_percentage']) != float(search_tour_line_obj.down_payment):
                        search_tour_line_obj.write({
                            'down_payment': float(rec['payment_percentage'])
                        })
                else:
                    new_pay_obj = self.env['tt.payment.rules'].create({
                        'name': rec['name'],
                        'description': rec['description'],
                        'payment_percentage': rec['payment_percentage'],
                        'due_date': rec['due_date']
                    })
                    new_pay_ids.append(new_pay_obj.id)
                self.env.cr.commit()

            search_tour_line_obj.write({
                'payment_rules_ids': [(6, 0, new_pay_ids)]
            })

            response = {
                'success': True,
            }
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1025)

    def get_config_by_api(self, context):
        try:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            sql_query = """SELECT cnt.id FROM tt_tour_location_rel tour_loc_rel 
                           LEFT JOIN tt_master_tour mst_tour ON tour_loc_rel.product_id = mst_tour.id 
                           LEFT JOIN tt_master_tour_ho_agent_rel tour_ho_rel on tour_ho_rel.tour_id = mst_tour.id 
                           LEFT JOIN tt_tour_master_locations tour_loc ON tour_loc_rel.location_id = tour_loc.id 
                           LEFT JOIN res_country cnt ON tour_loc.country_id = cnt.id 
                           WHERE mst_tour.state IN ('confirm') AND mst_tour.active = True """

            sql_query += 'AND (tour_ho_rel.ho_id IS NULL'
            if context.get('co_ho_id'):
                sql_query += ' OR mst_tour.owner_ho_id = ' + str(context['co_ho_id']) + ''
                sql_query += ' OR tour_ho_rel.ho_id = ' + str(context['co_ho_id']) + ''
            sql_query += ') GROUP BY cnt.id;'

            self.env.cr.execute(sql_query)
            tour_loc_countries = self.env.cr.dictfetchall()
            selected_countries = []
            for cnt in tour_loc_countries:
                selected_countries.append(int(cnt['id']))
            countries_dict = {}
            tour_loc_objs = self.env['tt.tour.master.locations'].search([('country_id', 'in', selected_countries)])
            for loc in tour_loc_objs:
                if loc.country_id.code:
                    if not countries_dict.get(loc.country_id.code):
                        countries_dict.update({
                            loc.country_id.code: {
                                'name': loc.country_id.name,
                                'code': loc.country_id.code,
                                'image': base_url + '/web/image?model=res.country&id=' + str(loc.country_id.id) + '&field=image',
                                'uuid': str(loc.country_id.id),
                                'states': {}
                            }
                        })
                    if loc.state_id:
                        cur_state = str(loc.state_id.id)
                        if not countries_dict[loc.country_id.code]['states'].get(cur_state):
                            countries_dict[loc.country_id.code]['states'].update({
                                cur_state: {
                                    'name': loc.state_id.name,
                                    'uuid': str(loc.state_id.id),
                                    'cities': {}
                                }
                            })
                    else:
                        cur_state = '0'
                        if not countries_dict[loc.country_id.code]['states'].get(cur_state):
                            countries_dict[loc.country_id.code]['states'].update({
                                cur_state: {
                                    'name': 'No State',
                                    'uuid': '0',
                                    'cities': {}
                                }
                            })
                    if loc.city_id:
                        cur_city_id = str(loc.city_id.id)
                        if not countries_dict[loc.country_id.code]['states'][cur_state]['cities'].get(cur_city_id):
                            countries_dict[loc.country_id.code]['states'][cur_state]['cities'].update({
                                cur_city_id: {
                                    'name': loc.city_id.name,
                                    'uuid': str(loc.city_id.id),
                                }
                            })

            tour_types_dict = {}
            tour_types = self.env['tt.master.tour.type'].search([])
            for rec in tour_types:
                if not tour_types_dict.get(rec.ho_id.seq_id):
                    tour_types_dict.update({
                        rec.ho_id.seq_id: []
                    })
                tour_types_dict[rec.ho_id.seq_id].append(rec.to_dict())
            values = {
                'countries': countries_dict,
                'tour_types': tour_types_dict
            }
            return ERR.get_no_error(values)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1021)

    def get_tour_pricing_api(self, req, context):
        try:
            search_request = {
                'tour_code': req.get('tour_code') and req['tour_code'] or '',
                'provider': req.get('provider') and req['provider'] or ''
            }
            provider_obj = self.env['tt.provider'].search([('code', '=', search_request['provider'])], limit=1)
            if not provider_obj:
                raise RequestException(1002)
            provider_obj = provider_obj[0]
            tour_data_list = self.env['tt.master.tour'].search([('tour_code', '=', provider_obj.alias + '~' + search_request['tour_code']), ('provider_id', '=', provider_obj.id)], limit=1)
            if not tour_data_list:
                raise RequestException(1022, additional_message='Tour not found.')
            tour_data = tour_data_list[0]
            price_itinerary = {
                'currency_code': tour_data.currency_id.name,
                'carrier_code': tour_data.carrier_id.code,
                'adult_flight_fare': tour_data.adult_flight_fare,
                'child_flight_fare': tour_data.child_flight_fare,
                'infant_flight_fare': tour_data.infant_flight_fare,
                'adult_visa_fare': tour_data.adult_visa_fare,
                'child_visa_fare': tour_data.child_visa_fare,
                'infant_visa_fare': tour_data.infant_visa_fare,
                'adult_airport_tax': tour_data.adult_airport_tax,
                'child_airport_tax': tour_data.child_airport_tax,
                'infant_airport_tax': tour_data.infant_airport_tax,
                'adult_additional_fare': 0,
                'adult_additional_commission': 0,
                'child_additional_fare': 0,
                'child_additional_commission': 0,
                'infant_additional_fare': 0,
                'infant_additional_commission': 0,
                'adult_tipping_guide': tour_data.tipping_guide,
                'adult_tipping_tour_leader': tour_data.tipping_tour_leader,
                'adult_tipping_driver': tour_data.tipping_driver,
                'child_tipping_guide': 0,
                'child_tipping_tour_leader': 0,
                'child_tipping_driver': 0,
                'infant_tipping_guide': 0,
                'infant_tipping_tour_leader': 0,
                'infant_tipping_driver': 0,
                'guiding_days': tour_data.guiding_days,
                'driving_times': tour_data.driving_times,
                'duration': tour_data.duration,
                'accommodations': [],
                'other_charges': []
            }
            if tour_data.tipping_guide_child:
                price_itinerary.update({
                    'child_tipping_guide': tour_data.tipping_guide,
                })
            if tour_data.tipping_tour_leader_child:
                price_itinerary.update({
                    'child_tipping_tour_leader': tour_data.tipping_tour_leader,
                })
            if tour_data.tipping_driver_child:
                price_itinerary.update({
                    'child_tipping_driver': tour_data.tipping_driver,
                })
            if tour_data.tipping_guide_infant:
                price_itinerary.update({
                    'infant_tipping_guide': tour_data.tipping_guide,
                })
            if tour_data.tipping_tour_leader_infant:
                price_itinerary.update({
                    'infant_tipping_tour_leader': tour_data.tipping_tour_leader,
                })
            if tour_data.tipping_driver_infant:
                price_itinerary.update({
                    'infant_tipping_driver': tour_data.tipping_driver,
                })

            temp_room_list = req['room_list']
            total_adt = 0
            total_chd = 0
            total_inf = 0
            for rec in temp_room_list:
                tour_room_list = self.env['tt.master.tour.rooms'].search([('room_code', '=', rec['room_code']), ('tour_pricelist_id', '=', tour_data.id)], limit=1)
                tour_room = tour_room_list[0]
                adult_amt = child_amt = infant_amt = adult_sur_amt = child_sur_amt = single_sup = 0
                total_pax = int(rec['adult']) + int(rec['child']) + int(rec['infant'])
                total_pax_no_infant = int(rec['adult']) + int(rec['child'])

                used_price = tour_room.tour_pricing_ids[0]
                for rec_price in tour_room.tour_pricing_ids:
                    if rec_price.is_infant_included:
                        total_pax_price = total_pax
                    else:
                        total_pax_price = total_pax_no_infant
                    if total_pax_price >= rec_price.min_pax >= used_price.min_pax:
                        used_price = rec_price

                adult_fare = used_price.adult_fare
                adult_com = used_price.adult_commission
                child_fare = used_price.child_fare
                child_com = used_price.child_commission
                infant_fare = used_price.infant_fare
                infant_com = used_price.infant_commission
                room_currency = used_price.currency_id.name

                extra_bed_limit = tour_room.extra_bed_limit
                if total_pax_no_infant < tour_room.pax_minimum:
                    adult_amt += total_pax_no_infant
                    infant_amt += rec['infant']
                else:
                    if rec['adult'] >= tour_room.pax_minimum:
                        adult_amt += rec['adult']
                        if int(rec['adult']) - int(tour_room.pax_minimum) <= int(extra_bed_limit):
                            adult_sur_amt += rec['adult'] - tour_room.pax_minimum
                            extra_bed_limit -= rec['adult'] - tour_room.pax_minimum
                            child_amt += rec['child']
                            if int(rec['child']) <= extra_bed_limit:
                                child_sur_amt += rec['child']
                            else:
                                child_sur_amt += rec['child'] - extra_bed_limit
                        else:
                            adult_sur_amt += rec['adult'] - tour_room.pax_minimum - extra_bed_limit
                            child_amt += rec['child']
                        infant_amt += rec['infant']
                    else:
                        adult_amt += tour_room.pax_minimum
                        if rec['child'] > 0:
                            if max(rec['child'] - (tour_room.pax_minimum - rec['adult']), 0) != 0:
                                child_amt += rec['child'] - (tour_room.pax_minimum - rec['adult'])
                                if (rec['child'] - (tour_room.pax_minimum - rec['adult'])) > extra_bed_limit:
                                    child_sur_amt += rec['child'] - (tour_room.pax_minimum - rec['adult']) - extra_bed_limit
                                else:
                                    child_sur_amt += rec['child'] - (tour_room.pax_minimum - rec['adult'])
                        if rec['infant'] > 0:
                            if rec['adult'] + rec['child'] < tour_room.pax_minimum:
                                if rec['infant'] - (tour_room.pax_minimum - rec['adult'] - rec['child']) > 0:
                                    infant_amt += rec['infant'] - (tour_room.pax_minimum - rec['adult'] - rec['child'])
                                else:
                                    infant_amt += 0
                            else:
                                infant_amt += rec['infant']

                if total_pax < 2:
                    single_sup += tour_data.single_supplement

                temp_accom = {
                    'room_id': tour_room.id,
                    'room_code': tour_room.room_code,
                    'currency_code': room_currency,
                    'adult_fare': adult_fare,
                    'adult_commission': adult_com,
                    'child_fare': child_fare,
                    'child_commission': child_com,
                    'infant_fare': infant_fare,
                    'infant_commission': infant_com,
                    'adult_amount': adult_amt,
                    'child_amount': child_amt,
                    'infant_amount': infant_amt,
                    'adult_surcharge_amount': adult_sur_amt,
                    'child_surcharge_amount': child_sur_amt,
                    'adult_surcharge': int(tour_room.adult_surcharge),
                    'child_surcharge': int(tour_room.child_surcharge),
                    'single_supplement': single_sup,
                    'additional_charge': int(tour_room.additional_charge),
                }
                price_itinerary['accommodations'].append(temp_accom)
                total_adt += adult_amt
                total_chd += child_amt
                total_inf += infant_amt
            price_itinerary.update({
                'total_adult': total_adt,
                'total_child': total_chd,
                'total_infant': total_inf,
            })

            pax_type_conv = {
                'ADT': total_adt,
                'CHD': total_chd,
                'INF': total_inf,
            }
            for rec_charges in tour_data.other_charges_ids:
                price_itinerary['other_charges'].append({
                    'name': rec_charges.name,
                    'pax_type': rec_charges.pax_type,
                    'pax_count': pax_type_conv[rec_charges.pax_type],
                    'charge_type': rec_charges.charge_type,
                    'currency_code': rec_charges.currency_id.name,
                    'amount': rec_charges.amount
                })

            if tour_data.tour_type_id.is_open_date:
                if not req.get('tour_line_code') or not req.get('departure_date'):
                    raise RequestException(1022, additional_message='A valid tour line code and your departure date are required to check Open Trip Price.')
                tour_line_data_list = self.env['tt.master.tour.lines'].search([('tour_line_code', '=', req['tour_line_code']), ('master_tour_id', '=', tour_data.id)], limit=1)
                if not tour_line_data_list:
                    raise RequestException(1022, additional_message='Tour line not found.')
                tour_line_data = tour_line_data_list[0]
                temp_departure_date = req['departure_date']
                visited_date_list = []
                for i in range(tour_data.duration + 1):
                    cur_iteration = datetime.strptime(temp_departure_date, '%Y-%m-%d') + timedelta(days=i)
                    visited_date_list.append(cur_iteration.strftime('%Y-%m-%d'))
                for rec in tour_line_data.special_dates_ids:
                    if rec.date.strftime('%Y-%m-%d') in visited_date_list:
                        if not price_itinerary.get('adult_additional_fare'):
                            price_itinerary.update({
                                'adult_additional_fare': rec.additional_adult_fare
                            })
                        else:
                            price_itinerary['adult_additional_fare'] += rec.additional_adult_fare
                        if not price_itinerary.get('adult_additional_commission'):
                            price_itinerary.update({
                                'adult_additional_commission': rec.additional_adult_commission
                            })
                        else:
                            price_itinerary['adult_additional_commission'] += rec.additional_adult_commission
                        if not price_itinerary.get('child_additional_fare'):
                            price_itinerary.update({
                                'child_additional_fare': rec.additional_child_fare
                            })
                        else:
                            price_itinerary['child_additional_fare'] += rec.additional_child_fare
                        if not price_itinerary.get('child_additional_commission'):
                            price_itinerary.update({
                                'child_additional_commission': rec.additional_child_commission
                            })
                        else:
                            price_itinerary['child_additional_commission'] += rec.additional_child_commission
                        if not price_itinerary.get('infant_additional_fare'):
                            price_itinerary.update({
                                'infant_additional_fare': rec.additional_infant_fare
                            })
                        else:
                            price_itinerary['infant_additional_fare'] += rec.additional_infant_fare
                        if not price_itinerary.get('infant_additional_commission'):
                            price_itinerary.update({
                                'infant_additional_commission': rec.additional_infant_commission
                            })
                        else:
                            price_itinerary['infant_additional_commission'] += rec.additional_infant_commission
            return ERR.get_no_error(price_itinerary)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1022)

    def commit_booking_vendor(self, data, context, **kwargs):
        try:
            response = {
                'success': True,
                'pnr': self.env['ir.sequence'].next_by_code('rodextrip.tour.reservation.code'),
                'status': 'booked'
            }
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1004)

    def issued_booking_vendor(self, data, context, **kwargs):
        try:
            book_obj = self.env['tt.reservation.tour'].search([('name', '=', data['order_number'])], limit=1)
            if book_obj:
                book_obj = book_obj[0]
            response = {
                'success': True,
                'pnr': book_obj.pnr,
                'booking_uuid': book_obj.name,
                'status': 'issued',
            }
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1004)

    def get_booking_vendor(self, data, context, **kwargs):
        try:
            response = self.env['tt.reservation.tour'].get_booking_api(data, context, **kwargs)
            return response
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1004)

    def get_autocomplete_api(self, req, context):
        try:
            search_params = []
            if req.get('name'):
                search_params.append(('name', 'ilike', req['name']))
            if context.get('co_ho_id'):
                search_params += ['|', '|', ('owner_ho_id', '=', int(context['co_ho_id'])),('ho_ids', '=', int(context['co_ho_id'])), ('ho_ids', '=', False)]
            else:
                search_params.append(('ho_ids', '=', False))
            result_id_list = self.env['tt.master.tour'].search(search_params)
            result_list = []
            for result in result_id_list:
                result_list.append({
                    'name': result.name and result.name or '',
                })
            return ERR.get_no_error(result_list)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1022)

    def product_sync_webhook_nosend(self, req, context):
        try:
            ho_obj = False
            if context.get('co_ho_id'):
                ho_obj = self.env['tt.agent'].browse(int(context['co_ho_id']))
            elif context.get('co_ho_seq_id'):
                ho_obj = self.env['tt.agent'].search([('seq_id', '=', context['co_ho_seq_id'])], limit=1)
            if not ho_obj:
                raise RequestException(1022, additional_message='Invalid context, cannot sync tour data.')
            _logger.info("Receiving tour data from webhook...")
            provider_id = self.env['tt.provider'].search([('code', '=', req['provider'])], limit=1)
            if not provider_id:
                raise RequestException(1002)
            for rec in req['data']:
                currency_obj = self.env['res.currency'].search([('name', '=', rec['currency_code'])], limit=1)
                carrier_id = self.env['tt.transport.carrier'].search([('code', '=', rec['carrier_code'])], limit=1)
                if not carrier_id:
                    carrier_id = [self.env.ref('tt_reservation_tour.tt_transport_carrier_tour_itt')]
                tour_type_obj = self.env['tt.master.tour.type'].search(
                    [('is_can_choose_hotel', '=', rec['tour_type']['is_can_choose_hotel']),
                     ('is_use_tour_leader', '=', rec['tour_type']['is_use_tour_leader']),
                     ('is_open_date', '=', rec['tour_type']['is_open_date']),
                     ('ho_id', '=', ho_obj.id)])
                if tour_type_obj:
                    tour_type_obj = tour_type_obj[0]
                else:
                    tour_type_obj = self.env['tt.master.tour.type'].create({
                        'name': rec['tour_type']['name'],
                        'description': rec['tour_type']['description'],
                        'is_can_choose_hotel': rec['tour_type']['is_can_choose_hotel'],
                        'is_use_tour_leader': rec['tour_type']['is_use_tour_leader'],
                        'is_open_date': rec['tour_type']['is_open_date'],
                        'ho_id': ho_obj.id
                    })
                vals = {
                    'name': rec['name'],
                    'tour_code': rec['tour_code'],
                    'provider_id': provider_id[0].id,
                    'carrier_id': carrier_id[0].id,
                    'sequence': rec['sequence'],
                    'is_can_hold': rec['is_can_hold'],
                    'hold_date_timer': rec['hold_date_timer'],
                    'currency_id': currency_obj and currency_obj[0].id or False,
                    'description': rec['description'],
                    'tour_category': rec['tour_category'],
                    'tour_type': tour_type_obj and tour_type_obj.id or False,
                    'duration': rec['duration'],
                    'guiding_days': rec['guiding_days'],
                    'driving_times': rec['driving_times'],
                    'est_starting_price': rec['est_starting_price'],
                    'adult_flight_fare': rec['adult_flight_fare'],
                    'child_flight_fare': rec['child_flight_fare'],
                    'infant_flight_fare': rec['infant_flight_fare'],
                    'adult_visa_fare': rec['adult_visa_fare'],
                    'child_visa_fare': rec['child_visa_fare'],
                    'infant_visa_fare': rec['infant_visa_fare'],
                    'adult_airport_tax': rec['adult_airport_tax'],
                    'child_airport_tax': rec['child_airport_tax'],
                    'infant_airport_tax': rec['infant_airport_tax'],
                    'tipping_guide': rec['tipping_guide'],
                    'tipping_tour_leader': rec['tipping_tour_leader'],
                    'tipping_driver': rec['tipping_driver'],
                    'tipping_guide_child': rec['tipping_guide_child'],
                    'tipping_tour_leader_child': rec['tipping_tour_leader_child'],
                    'tipping_driver_child': rec['tipping_driver_child'],
                    'tipping_guide_infant': rec['tipping_guide_infant'],
                    'tipping_tour_leader_infant': rec['tipping_tour_leader_infant'],
                    'tipping_driver_infant': rec['tipping_driver_infant'],
                }
                tour_obj = self.env['tt.master.tour'].search([('tour_code', '=',  rec['tour_code']), ('provider_id', '=', provider_id[0].id), ('owner_ho_id', '=', ho_obj.id)], limit=1)
                if tour_obj:
                    tour_obj = tour_obj[0]
                    tour_obj.write(vals)
                    for fli in tour_obj.flight_segment_ids:
                        fli.unlink()
                    for itin in tour_obj.itinerary_ids:
                        itin.unlink()
                    for temp_charge in tour_obj.other_charges_ids:
                        temp_charge.write({
                            'active': False
                        })
                    for temp_room in tour_obj.room_ids:
                        temp_room.write({
                            'active': False
                        })
                else:
                    vals.update({
                        'owner_ho_id': ho_obj.id
                    })
                    tour_obj = self.env['tt.master.tour'].create(vals)
                self.env.cr.commit()

                for rec2 in rec['tour_lines_ids']:
                    line_vals = {
                        'tour_line_code': rec2['tour_line_code'],
                        'departure_date': rec2['departure_date'],
                        'arrival_date': rec2['arrival_date'],
                        'seat': rec2['seat'],
                        'quota': rec2['quota'],
                        'state': rec2['state'],
                        'sequence': rec2['sequence'],
                        'down_payment': rec2['down_payment'],
                        'master_tour_id': tour_obj.id,
                        'active': True
                    }
                    tour_line_obj = self.env['tt.master.tour.lines'].search([('tour_line_code', '=', rec2['tour_line_code']), ('master_tour_id', '=', tour_obj.id), '|',('active', '=', False), ('active', '=', True)], limit=1)
                    if tour_line_obj:
                        tour_line_obj = tour_line_obj[0]
                        tour_line_obj.write(line_vals)
                    else:
                        tour_line_obj = self.env['tt.master.tour.lines'].create(line_vals)

                    for pay_rules in tour_line_obj.payment_rules_ids:
                        pay_rules.unlink()

                    if rec2.get('payment_rules_ids'):
                        for rec3 in rec2['payment_rules_ids']:
                            payment_rules_vals = {
                                'name': rec3['name'],
                                'payment_percentage': rec3['payment_percentage'],
                                'description': rec3['description'],
                                'due_date': rec3['due_date'],
                                'tour_lines_id': tour_line_obj.id
                            }
                            self.env['tt.payment.rules'].create(payment_rules_vals)

                    for spec_date in tour_line_obj.special_dates_ids:
                        spec_date.write({
                            'active': False
                        })

                    if rec['tour_type']['is_open_date'] and rec2.get('special_date_ids'):
                        for rec3 in rec2['special_date_ids']:
                            special_date_currency_obj = self.env['res.currency'].search([('name', '=', rec3['currency_code'])], limit=1)
                            special_date_vals = {
                                'name': rec3['name'],
                                'date': rec3['date'],
                                'currency_id': special_date_currency_obj and special_date_currency_obj[0].id or False,
                                'additional_adult_fare': rec3['additional_adult_price'],
                                'additional_child_fare': rec3['additional_child_price'],
                                'additional_infant_fare': rec3['additional_infant_price'],
                                'tour_line_id': tour_line_obj.id,
                                'active': True
                            }
                            special_date_obj = self.env['tt.master.tour.special.dates'].search([('date', '=', rec3['date']), ('tour_line_id', '=', tour_line_obj.id), '|',('active', '=', False), ('active', '=', True)], limit=1)
                            if special_date_obj:
                                special_date_obj = special_date_obj[0]
                                special_date_obj.write(special_date_vals)
                            else:
                                special_date_obj = self.env['tt.master.tour.special.dates'].create(special_date_vals)

                location_list = []
                for rec2 in rec['location_ids']:
                    search_params = []
                    country_obj = self.env['res.country'].search([('code', '=', rec2['country_code'])], limit=1)
                    if country_obj:
                        search_params.append(('country_id', '=', country_obj[0].id))
                    city_obj = self.env['res.city'].search([('name', '=', rec2['city_name'])], limit=1)
                    if city_obj:
                        search_params.append(('city_id', '=', city_obj[0].id))
                    loc_obj = self.env['tt.tour.master.locations'].search(search_params, limit=1)
                    if loc_obj:
                        loc_obj = loc_obj[0]
                    else:
                        loc_obj = self.env['tt.tour.master.locations'].create({
                            'country_id': country_obj and country_obj[0].id or False,
                            'city_id': city_obj and city_obj[0].id or False,
                        })
                    location_list.append(loc_obj.id)

                for rec2 in rec['other_charges_ids']:
                    other_charges_currency_obj = self.env['res.currency'].search([('name', '=', rec2['currency_code'])], limit=1)
                    other_charges_vals = {
                        'name': rec2['name'],
                        'pax_type': rec2['pax_type'],
                        'currency_id': other_charges_currency_obj and other_charges_currency_obj[0].id or False,
                        'amount': rec2['amount'],
                        'charge_type': rec2['charge_type'],
                        'master_tour_id': tour_obj.id,
                        'active': True
                    }
                    other_charges_obj = self.env['tt.master.tour.other.charges'].search([('name', '=', rec2['name']), ('pax_type', '=', rec2['pax_type']), ('master_tour_id', '=', tour_obj.id), '|',('active', '=', False), ('active', '=', True)], limit=1)
                    if other_charges_obj:
                        other_charges_obj = other_charges_obj[0]
                        other_charges_obj.write(other_charges_vals)
                    else:
                        other_charges_obj = self.env['tt.master.tour.other.charges'].create(other_charges_vals)

                for rec2 in rec['room_ids']:
                    room_vals = {
                        'name': rec2['name'],
                        'room_code': rec2['room_code'],
                        'bed_type': rec2['bed_type'],
                        'description': rec2['description'],
                        'hotel': rec2['hotel'],
                        'address': rec2['address'],
                        'star': rec2['star'],
                        'adult_surcharge': rec2['adult_surcharge'],
                        'child_surcharge': rec2['child_surcharge'],
                        'additional_charge': rec2['additional_charge'],
                        'pax_minimum': rec2['pax_minimum'],
                        'pax_limit': rec2['pax_limit'],
                        'adult_limit': rec2['adult_limit'],
                        'extra_bed_limit': rec2['extra_bed_limit'],
                        'tour_pricelist_id': tour_obj.id,
                        'active': True,
                    }
                    room_obj = self.env['tt.master.tour.rooms'].search([('room_code', '=', rec2['room_code']), ('tour_pricelist_id', '=', tour_obj.id), '|',('active', '=', False), ('active', '=', True)], limit=1)
                    if room_obj:
                        room_obj = room_obj[0]
                        room_obj.write(room_vals)
                    else:
                        room_obj = self.env['tt.master.tour.rooms'].create(room_vals)

                    for temp_pricing in room_obj.tour_pricing_ids:
                        temp_pricing.write({
                            'active': False
                        })

                    if rec2.get('tour_pricing_ids'):
                        for rec3 in rec2['tour_pricing_ids']:
                            tour_pricing_currency_obj = self.env['res.currency'].search([('name', '=', rec3['currency_code'])], limit=1)
                            tour_pricing_vals = {
                                'currency_id': tour_pricing_currency_obj and tour_pricing_currency_obj[0].id or '',
                                'min_pax': rec3['min_pax'],
                                'is_infant_included': rec3['is_infant_included'],
                                'adult_fare': rec3['adult_price'],
                                'adult_commission': 0,
                                'child_fare': rec3['child_price'],
                                'child_commission': 0,
                                'infant_fare': rec3['infant_price'],
                                'infant_commission': 0,
                                'room_id': room_obj.id,
                                'active': True
                            }
                            tour_pricing_obj = self.env['tt.master.tour.pricing'].search([('min_pax', '=', int(rec3['min_pax'])), ('room_id', '=', room_obj.id), '|', ('active', '=', False), ('active', '=', True)], limit=1)
                            if tour_pricing_obj:
                                tour_pricing_obj = tour_pricing_obj[0]
                                tour_pricing_obj.write(tour_pricing_vals)
                            else:
                                tour_pricing_obj = self.env['tt.master.tour.pricing'].create(tour_pricing_vals)

                for rec2 in rec['flight_segment_ids']:
                    carrier_obj = self.env['tt.transport.carrier'].search([('code', '=', rec2['carrier_code']),('provider_type_id', '=', self.env.ref('tt_reservation_airline.tt_provider_type_airline').id)],limit=1)
                    carrier_obj = carrier_obj and carrier_obj[0] or False
                    origin_obj = self.env['tt.destinations'].search([('code', '=', rec2['origin_code']), ('provider_type_id', '=', self.env.ref('tt_reservation_airline.tt_provider_type_airline').id)],limit=1)
                    origin_obj = origin_obj and origin_obj[0] or False
                    destination_obj = self.env['tt.destinations'].search([('code', '=', rec2['destination_code']),('provider_type_id', '=', self.env.ref('tt_reservation_airline.tt_provider_type_airline').id)],limit=1)
                    destination_obj = destination_obj and destination_obj[0] or False
                    self.env['flight.segment'].create({
                        'journey_type': rec2['journey_type'],
                        'class_of_service': rec2['class_of_service'],
                        'carrier_id': carrier_obj and carrier_obj.id or False,
                        'carrier_number': rec2['carrier_number'],
                        'origin_id': origin_obj and origin_obj.id or False,
                        'origin_terminal': rec2['origin_terminal'],
                        'destination_id': destination_obj and destination_obj.id or False,
                        'destination_terminal': rec2['destination_terminal'],
                        'departure_date': datetime.strptime(rec2['departure_date'], "%Y-%m-%d %H:%M:%S"),
                        'arrival_date': datetime.strptime(rec2['arrival_date'], "%Y-%m-%d %H:%M:%S"),
                        'tour_pricelist_id': tour_obj.id,
                    })

                image_list = []
                for rec2 in rec['image_ids']:
                    temp_img_list_id = self.convert_image_to_own(rec2['url'], rec2['filename'])
                    if temp_img_list_id:
                        image_list.append(temp_img_list_id)

                for rec2 in rec['itinerary_ids']:
                    new_itin_obj = self.env['tt.reservation.tour.itinerary'].create({
                        'name': rec2['name'],
                        'day': rec2['day'],
                        'tour_pricelist_id': tour_obj.id,
                    })
                    for rec3 in rec2['item_ids']:
                        self.env['tt.reservation.tour.itinerary.item'].create({
                            'name': rec3['name'],
                            'description': rec3['description'],
                            'timeslot': rec3['timeslot'],
                            'sequence': rec3['sequence'],
                            'image_id': rec3.get('image_id') and self.convert_image_to_own(rec3['image_id']['url'], rec3['image_id']['filename']) or False,
                            'itinerary_id': new_itin_obj.id,
                        })

                for rec2 in rec['other_info_ids']:
                    tour_obj.create_other_info_from_json(rec2)

                tour_obj.write({
                    'location_ids': [(6, 0, location_list)],
                    'image_ids': [(6, 0, image_list)]
                })

                if tour_obj.state == 'draft':
                    tour_obj.action_confirm()
            response = {
                'success': True
            }
            return ERR.get_no_error(response)
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error()

    # def generate_all_room_codes(self):
    #     room_list = self.env['tt.master.tour.rooms'].search([('room_code', '=', False)])
    #     for rec in room_list:
    #         rec.write({
    #             'room_code': self.env['ir.sequence'].next_by_code('master.tour.room.code') or 'New'
    #         })

    # temporary function
    def convert_to_new_pricing(self):
        all_tours = self.env['tt.master.tour'].search([])
        for rec in all_tours:
            for rec2 in rec.room_ids:
                if not rec2.tour_pricing_ids:
                    self.env['tt.master.tour.pricing'].create({
                        'room_id': rec2.id,
                        'min_pax': 1,
                        'adult_fare': rec.adult_fare,
                        'adult_commission': rec.adult_commission,
                        'child_fare': rec.child_fare,
                        'child_commission': rec.child_commission,
                        'infant_fare': rec.infant_fare,
                        'infant_commission': rec.infant_commission
                    })


class TourSyncProductsChildren(models.TransientModel):
    _name = "tour.sync.product.children.wizard"
    _description = 'Tour Sync Product Children Wizard'

    ho_id = fields.Many2one('tt.agent', 'From Head Office', domain=[('is_ho_agent', '=', True)],
                            default=lambda self: self.env.user.ho_id)

    def sync_data_to_children(self):
        try:
            tour_data_list = []
            tour_datas = self.env['tt.master.tour'].search([('state', 'in', ['confirm']), ('owner_ho_id', '=', self.ho_id.id)])
            for rec in tour_datas:
                dict_vals = {
                    'name': rec.name,
                    'tour_code': rec.tour_code,
                    'carrier_code': rec.carrier_id.code,
                    'sequence': rec.sequence,
                    'is_can_hold': rec.is_can_hold,
                    'hold_date_timer': rec.hold_date_timer,
                    'currency_code': rec.currency_id.name,
                    'description': rec.description,
                    'tour_category': rec.tour_category,
                    'tour_type': rec.tour_type_id.to_dict(),
                    'duration': rec.duration,
                    'guiding_days': rec.guiding_days,
                    'driving_times': rec.driving_times,
                    'est_starting_price': rec.est_starting_price,
                    'adult_flight_fare': rec.adult_flight_fare,
                    'child_flight_fare': rec.child_flight_fare,
                    'infant_flight_fare': rec.infant_flight_fare,
                    'adult_visa_fare': rec.adult_visa_fare,
                    'child_visa_fare': rec.child_visa_fare,
                    'infant_visa_fare': rec.infant_visa_fare,
                    'adult_airport_tax': rec.adult_airport_tax,
                    'child_airport_tax': rec.adult_airport_tax,
                    'infant_airport_tax': rec.adult_airport_tax,
                    'tipping_guide': rec.tipping_guide,
                    'tipping_tour_leader': rec.tipping_tour_leader,
                    'tipping_driver': rec.tipping_driver,
                    'tipping_guide_child': rec.tipping_guide_child,
                    'tipping_tour_leader_child': rec.tipping_tour_leader_child,
                    'tipping_driver_child': rec.tipping_driver_child,
                    'tipping_guide_infant': rec.tipping_guide_infant,
                    'tipping_tour_leader_infant': rec.tipping_tour_leader_infant,
                    'tipping_driver_infant': rec.tipping_driver_infant
                }
                tour_line_list = []
                for rec2 in rec.tour_line_ids:
                    tour_line_dict = {
                        'tour_line_code': rec2.tour_line_code,
                        'departure_date': rec2.departure_date and rec2.departure_date.strftime("%Y-%m-%d") or False,
                        'arrival_date': rec2.arrival_date and rec2.arrival_date.strftime("%Y-%m-%d") or False,
                        'seat': rec2.seat,
                        'quota': rec2.quota,
                        'state': rec2.state,
                        'down_payment': rec2.down_payment,
                        'sequence': rec2.sequence
                    }
                    payment_rules_list = []
                    for rec3 in rec2.payment_rules_ids:
                        payment_rules_list.append({
                            'name': rec3.name,
                            'payment_percentage': rec3.payment_percentage,
                            'description': rec3.description,
                            'due_date': rec3.due_date and rec3.due_date.strftime("%Y-%m-%d") or False,
                        })
                    tour_line_dict.update({
                        'payment_rules_ids': payment_rules_list
                    })
                    if rec.tour_type_id.is_open_date:
                        special_date_list = []
                        for rec3 in rec2.special_dates_ids:
                            special_date_list.append({
                                'name': rec3.name,
                                'date': rec3.date.strftime("%Y-%m-%d"),
                                'currency_code': rec3.currency_id.name,
                                'additional_adult_price': rec3.additional_adult_fare + rec3.additional_adult_commission,
                                'additional_child_price': rec3.additional_child_fare + rec3.additional_child_commission,
                                'additional_infant_price': rec3.additional_infant_fare + rec3.additional_infant_commission
                            })
                        tour_line_dict.update({
                            'special_date_ids': special_date_list
                        })
                    tour_line_list.append(tour_line_dict)

                location_list = []
                for rec2 in rec.location_ids:
                    location_list.append({
                        'city_name': rec2.city_id.name,
                        'country_code': rec2.country_id.code
                    })

                flight_list = []
                for rec2 in rec.flight_segment_ids:
                    flight_list.append({
                        'carrier_number': rec2.carrier_number,
                        'carrier_code': rec2.carrier_id.code,
                        'journey_type': rec2.journey_type,
                        'class_of_service': rec2.class_of_service,
                        'origin_code': rec2.origin_id.code,
                        'destination_code': rec2.destination_id.code,
                        'departure_date': rec2.departure_date and rec2.departure_date.strftime("%Y-%m-%d %H:%M:%S") or False,
                        'arrival_date': rec2.arrival_date and rec2.arrival_date.strftime("%Y-%m-%d %H:%M:%S") or False,
                        'origin_terminal': rec2.origin_terminal,
                        'destination_terminal': rec2.destination_terminal,
                    })

                image_list = []
                for rec2 in rec.image_ids:
                    image_list.append({
                        'url': rec2.url,
                        'filename': rec2.filename
                    })

                other_charges_list = []
                for rec2 in rec.other_charges_ids:
                    other_charges_list.append({
                        'name': rec2.name,
                        'pax_type': rec2.pax_type,
                        'currency_code': rec2.currency_id.name,
                        'amount': rec2.amount,
                        'charge_type': rec2.charge_type
                    })

                room_list = []
                for rec2 in rec.room_ids:
                    tour_pricing_list = []
                    for rec3 in rec2.tour_pricing_ids:
                        tour_pricing_list.append({
                            'currency_code': rec3.currency_id.name,
                            'min_pax': rec3.min_pax,
                            'is_infant_included': rec3.is_infant_included,
                            'adult_price': rec3.adult_fare + rec3.adult_commission,
                            'child_price': rec3.child_fare + rec3.child_commission,
                            'infant_price': rec3.infant_fare + rec3.infant_commission
                        })
                    room_list.append({
                        'room_code': rec2.room_code,
                        'hotel': rec2.hotel,
                        'star': rec2.star,
                        'address': rec2.address,
                        'name': rec2.name,
                        'bed_type': rec2.bed_type,
                        'description': rec2.description,
                        'pax_minimum': rec2.pax_minimum,
                        'pax_limit': rec2.pax_limit,
                        'adult_limit': rec2.adult_limit,
                        'extra_bed_limit': rec2.extra_bed_limit,
                        'adult_surcharge': rec2.adult_surcharge,
                        'child_surcharge': rec2.child_surcharge,
                        'additional_charge': rec2.additional_charge,
                        'tour_pricing_ids': tour_pricing_list
                    })

                itinerary_list = []
                for rec2 in rec.itinerary_ids:
                    item_list = []
                    for rec3 in rec2.item_ids:
                        item_list.append({
                            'sequence': rec3.sequence,
                            'name': rec3.name,
                            'description': rec3.description,
                            'timeslot': rec3.timeslot,
                            'image_id': {
                                'url': rec3.image_id.url,
                                'filename': rec3.image_id.filename
                            },
                        })
                    itinerary_list.append({
                        'name': rec2.name,
                        'day': rec2.day,
                        'item_ids': item_list,
                    })

                other_info_list = []
                for rec2 in rec.other_info_ids:
                    other_info_list.append(rec2.convert_info_to_dict())

                dict_vals.update({
                    'tour_lines_ids': tour_line_list,
                    'location_ids': location_list,
                    'flight_segment_ids': flight_list,
                    'image_ids': image_list,
                    'other_charges_ids': other_charges_list,
                    'room_ids': room_list,
                    'itinerary_ids': itinerary_list,
                    'other_info_ids': other_info_list,
                })
                tour_data_list.append(dict_vals)

            # gw_timeout = int(len(tour_data_list) / 3) > 60 and int(len(tour_data_list) / 3) or 60
            # di perpendek krn di child kerjany lama, di buat timeout utk langsung next child
            gw_timeout = 10
            vals = {
                'provider_type': 'tour',
                'action': 'sync_products_to_children',
                'data': tour_data_list,
                'timeout': gw_timeout
            }
            self.env['tt.api.webhook.data'].notify_subscriber(vals)
        except Exception as e:
            raise UserError(_('Failed to sync tour data to children!'))
