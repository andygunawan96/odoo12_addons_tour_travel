from odoo import api, fields, models, _
from datetime import datetime, date
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
    _description = 'Rodex Model'

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
        products = self.env['tt.master.tour'].sudo().search([('provider_id', '=', self.provider_id.id)])
        for rec in products:
            if rec.active:
                rec.sudo().write({
                    'active': False
                })

    @api.depends('provider_id')
    @api.onchange('provider_id')
    def _compute_provider_code(self):
        self.provider_code = self.provider_id.code


class TourItineraryItem(models.Model):
    _name = 'tt.reservation.tour.itinerary.item'
    _description = 'Rodex Model'
    _order = 'sequence asc'

    name = fields.Char('Title')
    description = fields.Text('Description')
    timeslot = fields.Char('Timeslot')
    image_id = fields.Many2one('tt.upload.center', 'Image')
    itinerary_id = fields.Many2one('tt.reservation.tour.itinerary', 'Tour Itinerary')
    sequence = fields.Integer('Sequence', required=True, default=50)


class TourItinerary(models.Model):
    _name = 'tt.reservation.tour.itinerary'
    _description = 'Rodex Model'
    _order = 'day asc'

    name = fields.Char('Title')
    day = fields.Integer('Day', default=1, required=True)
    date = fields.Date('Date')
    tour_pricelist_id = fields.Many2one('tt.master.tour', 'Tour', ondelete='cascade')
    item_ids = fields.One2many('tt.reservation.tour.itinerary.item', 'itinerary_id', 'Items')


class MasterTour(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.master.tour'
    _description = 'Rodex Model'
    _order = 'sequence'

    def get_domain(self):
        domain_id = self.env.ref('tt_reservation_tour.tt_provider_type_tour').id
        return [('provider_type_id.id', '=', int(domain_id))]

    name = fields.Text('Name', required=True, default='Tour', size=40)
    description = fields.Text('Description')

    tour_code = fields.Char('Tour Code', readonly=True, copy=False)
    tour_route = fields.Selection([('international', 'International'), ('domestic', 'Domestic')],
                                  'Route', required=True, default='international')
    tour_category = fields.Selection([('group', 'Group'), ('private', 'Private')],
                                     'Tour Category', required=True, default='group')
    tour_type = fields.Selection([('series', 'Series (With Tour Leader)'), ('sic', 'SIC (Without Tour Leader)'), ('land', 'Land Only'), ('city', 'City Tour'), ('private', 'Private Tour')], 'Tour Type', default='series')

    departure_date = fields.Date('Departure Date', required=True)
    return_date = fields.Date('Arrival Date')
    arrival_date = fields.Date('Arrival Date', required=True)
    name_with_date = fields.Text('Display Name', readonly=True, compute='_compute_name_with_date', store=True)
    duration = fields.Integer('Duration (days)', help="in day(s)", readonly=True,
                              compute='_compute_duration', store=True)

    start_period = fields.Date('Start Period')
    end_period = fields.Date('End Period')
    agent_id = fields.Many2one('tt.agent', 'Agent')
    survey_date = fields.Date('Survey Send Date', readonly=True, compute='_compute_survey_date')

    commercial_duration = fields.Char('Duration', readonly=1)  # compute='_compute_duration'
    seat = fields.Integer('Seat Available', required=True, default=1)
    quota = fields.Integer('Quota', required=True, default=1)
    is_can_hold = fields.Boolean('Can Be Hold', default=True, required=True)

    state = fields.Selection([('draft', 'Draft'), ('open', 'Open'), ('definite', 'Definite'), ('sold', 'Sold Out'),
                              ('on_going', 'On Going'), ('done', 'Done'), ('closed', 'Closed'),
                              ('cancel', 'Canceled')],
                             'State', copy=False, default='draft', help="draft = tidak tampil di front end"
                                                                        "definite = pasti berangkat"
                                                                        "done = sudah pulang"
                                                                        "closed = sisa uang sdh masuk ke HO"
                                                                        "cancelled = tidak jadi berangkat")

    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    location_ids = fields.Many2many('tt.tour.master.locations', 'tt_tour_location_rel', 'product_id',
                                    'location_id', string='Location')
    country_str = fields.Char('Countries', compute='_compute_country_str', store=True)
    visa = fields.Selection([('include', 'Include'), ('exclude', 'Exclude')],
                            'Visa', required=True, default='include')
    flight = fields.Selection([('include', 'Include'), ('exclude', 'Exclude')],
                              'Flight', required=True, default='exclude')
    airport_tax = fields.Monetary('Airport Tax', help="(/pax)", default=0)
    tipping_guide = fields.Monetary('Tipping Guide', help="(/pax /day)", default=0)
    tipping_tour_leader = fields.Monetary('Tipping Tour Leader', help="(/pax /day)", default=0)
    tipping_driver = fields.Monetary('Tipping Driver', help="(/pax /day)", default=0)
    tipping_guide_child = fields.Boolean('Apply for Child', default=True)
    tipping_tour_leader_child = fields.Boolean('Apply for Child', default=True)
    tipping_driver_child = fields.Boolean('Apply for Child', default=True)
    tipping_guide_infant = fields.Boolean('Apply for Infant', default=True)
    tipping_tour_leader_infant = fields.Boolean('Apply for Infant', default=True)
    tipping_driver_infant = fields.Boolean('Apply for Infant', default=True)
    guiding_days = fields.Integer('Guiding Days', default=1)
    driving_times = fields.Integer('Driving Times', default=0)

    adult_fare = fields.Monetary('Adult Fare', default=0)
    adult_commission = fields.Monetary('Adult Commission', default=0)

    child_fare = fields.Monetary('Child Fare', default=0)
    child_commission = fields.Monetary('Child Commission', default=0)

    infant_fare = fields.Monetary('Infant Fare', default=0)
    infant_commission = fields.Monetary('Infant Commission', default=0)

    discount_ids = fields.One2many('tt.master.tour.discount', 'tour_id')
    room_ids = fields.One2many('tt.master.tour.rooms', 'tour_pricelist_id', required=True)

    down_payment = fields.Float('Down Payment (%)', default=100)
    payment_rules_ids = fields.One2many('tt.payment.rules', 'pricelist_id')
    tour_leader_ids = fields.Many2many('res.employee', string="Tour Leader")
    # tour_leader_ids = fields.Many2many('res.employee', 'tour_leader_rel', 'pricelist_id', 'partner_id',
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
    sequence = fields.Integer('Sequence', default=3)
    adjustment_ids = fields.One2many('tt.master.tour.adjustment', 'tour_pricelist_id', required=True)
    survey_title_ids = fields.One2many('survey.survey', 'tour_id', string='Tour Surveys', copy=False)
    quotation_ids = fields.One2many('tt.master.tour.quotation', 'tour_id', 'Tour Quotation(s)')

    country_name = fields.Char('Country Name')
    itinerary_ids = fields.One2many('tt.reservation.tour.itinerary', 'tour_pricelist_id', 'Itinerary')
    provider_id = fields.Many2one('tt.provider', 'Provider', domain=get_domain, readonly=True,
                                  default=lambda self: self.env.ref('tt_reservation_tour.tt_provider_tour_internal'), copy=False)
    carrier_id = fields.Many2one('tt.transport.carrier', 'Carrier', domain=get_domain, readonly=True,
                                 default=lambda self: self.env.ref('tt_reservation_tour.tt_transport_carrier_tour_itt'), copy=False)
    document_url = fields.Many2one('tt.upload.center', 'Document URL')
    import_other_info = fields.Binary('Import JSON')
    export_other_info = fields.Binary('Export JSON')
    file_name = fields.Char("Filename",compute="_compute_filename",store=True)
    active = fields.Boolean('Active', default=True)

    @api.multi
    def write(self, vals):
        if vals.get('down_payment'):
            total_percent = 0
            for rec in self.payment_rules_ids:
                total_percent += rec.payment_percentage
            if total_percent + vals['down_payment'] > 100.00:
                raise UserError(_('Total Installments and Down Payment cannot be more than 100%. Please re-adjust your Installment Payment Rules!'))
        return super(MasterTour, self).write(vals)

    @api.depends("name", "departure_date", "arrival_date")
    def _compute_name_with_date(self):
        for rec in self:
            start_date = rec.departure_date and rec.departure_date.strftime('%d %b %Y') or ''
            end_date = rec.arrival_date and rec.arrival_date.strftime('%d %b %Y') or ''
            rec.name_with_date = "[" + start_date + " - " + end_date + "] " + rec.name

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

    @api.onchange('payment_rules_ids')
    def _calc_dp(self):
        dp = 100
        for rec in self:
            for pp in rec.payment_rules_ids:
                dp -= pp.payment_percentage
            rec.dp = dp

    @api.onchange('tour_category', 'tour_type')
    def _set_to_null(self):
        for rec in self:
            if rec.tour_category == 'private':
                rec.tour_type = 'private'
            if rec.tour_category == 'group':
                if rec.tour_type == 'private':
                    rec.tour_type = 'series'
                if rec.tour_type == 'sic':
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

        res = self.env['tt.master.tour.api.con'].search_provider(req_post)
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

    def copy_tour(self):
        new_tour_obj = self.copy()
        new_tour_obj.sudo().write({
            'seat': new_tour_obj.quota
        })
        for rec in self.payment_rules_ids:
            self.env['tt.payment.rules'].sudo().create({
                'name': rec.name,
                'payment_percentage': rec.payment_percentage,
                'description': rec.description,
                'due_date': rec.due_date,
                'pricelist_id': new_tour_obj.id,
            })
        for rec in self.room_ids:
            self.env['tt.master.tour.rooms'].sudo().create({
                'name': rec.name,
                'room_code': rec.room_code,
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
        for rec in self.flight_segment_ids:
            self.env['flight.segment'].sudo().create({
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
            new_itin_obj = self.env['tt.reservation.tour.itinerary'].sudo().create({
                'name': rec.name,
                'day': rec.day,
                'date': rec.date,
                'tour_pricelist_id': new_tour_obj.id,
            })
            for rec2 in rec.item_ids:
                self.env['tt.reservation.tour.itinerary.item'].sudo().create({
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
        new_tour_obj.sudo().write({
            'image_ids': [(6, 0, new_image_ids)]
        })

        new_loc_ids = []
        for rec in self.location_ids:
            new_loc_ids.append(rec.id)
        new_tour_obj.sudo().write({
            'location_ids': [(6, 0, new_loc_ids)]
        })

        other_info_ids = []
        for rec in self.other_info_ids:
            other_info_ids.append(new_tour_obj.create_other_info_from_json(rec.convert_info_to_dict()))
        new_tour_obj.sudo().write({
            'other_info_ids': [(6, 0, other_info_ids)]
        })

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
                provider_obj = self.env['tt.provider'].sudo().search([('code', '=', rec['provider'])], limit=1)
                provider_obj = provider_obj and provider_obj[0] or False
                currency_obj = self.env['res.currency'].sudo().search([('name', '=', rec['currency_code'])], limit=1)
                currency_obj = currency_obj and currency_obj[0] or False
                vals = {
                    'name': rec['name'],
                    'description': rec['description'],
                    'tour_code': rec['tour_code'],
                    'tour_route': rec['tour_route'],
                    'tour_category': rec['tour_category'],
                    'tour_type': rec['tour_type'],
                    'departure_date': datetime.strptime(rec['departure_date'], "%Y-%m-%d"),
                    'arrival_date': datetime.strptime(rec['arrival_date'], "%Y-%m-%d"),
                    'adult_fare': rec['adult_sale_price'],
                    'child_fare': rec['child_sale_price'],
                    'infant_fare': rec['infant_sale_price'],
                    'duration': rec['duration'],
                    'seat': rec['seat'],
                    'quota': rec['quota'],
                    'is_can_hold': rec['is_can_hold'],
                    'visa': rec['visa'],
                    'flight': rec['flight'],
                    'airport_tax': rec['airport_tax'],
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
                    'currency_id': currency_obj and currency_obj.id or False,
                    'active': True
                }
                new_tour_obj = self.env['tt.master.tour'].sudo().search([('tour_code', '=', rec['tour_code']), ('provider_id', '=', provider_obj.id), '|', ('active', '=', False), ('active', '=', True)], limit=1)
                if new_tour_obj:
                    new_tour_obj = new_tour_obj[0]
                    new_tour_obj.sudo().write(vals)
                else:
                    new_tour_obj = self.env['tt.master.tour'].sudo().create(vals)

                req_post = {
                    'tour_code': rec['tour_code'],
                    'provider': rec['provider'],
                }
                det_res = self.env['tt.master.tour.api.con'].get_details_provider(req_post)
                if det_res['error_code'] == 0:
                    for temp_room in new_tour_obj.room_ids:
                        temp_room.sudo().write({
                            'active': False
                        })
                    for temp_flight in new_tour_obj.flight_segment_ids:
                        temp_flight.sudo().unlink()
                    for temp_itin in new_tour_obj.itinerary_ids:
                        temp_itin.sudo().unlink()
                    for temp_img in new_tour_obj.image_ids:
                        temp_img.sudo().unlink()
                    for temp_loc in new_tour_obj.location_ids:
                        temp_loc.sudo().unlink()
                    if det_res['response'].get('selected_tour'):
                        detail_dat = det_res['response']['selected_tour']
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
                            new_acco_obj = self.env['tt.master.tour.rooms'].sudo().search([('room_code', '=', rec_det['room_code']), ('tour_pricelist_id', '=', new_tour_obj.id), '|', ('active', '=', False), ('active', '=', True)], limit=1)
                            if new_acco_obj:
                                new_acco_obj[0].sudo().write(new_acco_vals)
                            else:
                                self.env['tt.master.tour.rooms'].sudo().create(new_acco_vals)
                        for rec_flight in detail_dat['flight_segments']:
                            carrier_obj = self.env['tt.transport.carrier'].sudo().search([('code', '=', rec_flight['carrier_code']), ('provider_type_id', '=', self.env.ref('tt_reservation_airline.tt_provider_type_airline').id)], limit=1)
                            carrier_obj = carrier_obj and carrier_obj[0] or False
                            origin_obj = self.env['tt.destinations'].sudo().search([('code', '=', rec_flight['origin_code']), ('provider_type_id', '=', self.env.ref('tt_reservation_airline.tt_provider_type_airline').id)], limit=1)
                            origin_obj = origin_obj and origin_obj[0] or False
                            destination_obj = self.env['tt.destinations'].sudo().search([('code', '=', rec_flight['destination_code']), ('provider_type_id', '=', self.env.ref('tt_reservation_airline.tt_provider_type_airline').id)], limit=1)
                            destination_obj = destination_obj and destination_obj[0] or False
                            self.env['flight.segment'].sudo().create({
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
                            new_itin_obj = self.env['tt.reservation.tour.itinerary'].sudo().create({
                                'name': rec_itin['name'],
                                'day': rec_itin['day'],
                                'date': rec_itin['date'],
                                'tour_pricelist_id': new_tour_obj.id,
                            })
                            for rec_item in rec_itin['items']:
                                self.env['tt.reservation.tour.itinerary.item'].sudo().create({
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
                        new_tour_obj.sudo().write({
                            'image_ids': [(6, 0, new_image_ids)]
                        })
                        for rec_other in detail_dat['other_infos']:
                            new_tour_obj.create_other_info_from_json(rec_other)

                        new_loc_ids = []
                        for rec_loc in detail_dat['locations']:
                            search_params = []
                            new_country_obj = self.env['res.country'].sudo().search([('code', '=', rec_loc['country_code'])], limit=1)
                            new_city_obj = self.env['res.city'].sudo().search([('name', '=', rec_loc['city_name'])], limit=1)
                            if new_country_obj:
                                search_params.append(('country_id', '=', new_country_obj[0].id))
                            if new_city_obj:
                                search_params.append(('city_id', '=', new_city_obj[0].id))
                            if search_params:
                                temp_loc = self.env['tt.tour.master.locations'].sudo().search(search_params, limit=1)
                                if temp_loc:
                                    new_loc = temp_loc[0]
                                else:
                                    new_loc = self.env['tt.tour.master.locations'].sudo().create({
                                        'country_id': new_country_obj and new_country_obj[0].id or False,
                                        'city_id': new_city_obj and new_city_obj[0].id or False,
                                        'state_id': False,
                                    })
                                    self.env.cr.commit()
                                new_loc_ids.append(new_loc.id)
                        new_tour_obj.sudo().write({
                            'location_ids': [(6, 0, new_loc_ids)]
                        })
                        if new_tour_obj.state == 'draft':
                            new_tour_obj.action_validate()
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
                upload_obj = self.env['tt.upload.center'].sudo().search([('seq_id', '=', attachment_obj['response']['seq_id'])], limit=1)
                return upload_obj and upload_obj[0].id or False
            else:
                return False
        else:
            return False

    def action_validate(self):
        if self.state != 'draft':
            raise UserError(_('Cannot validate master tour because state is not "draft"!'))
        if not self.provider_id:
            raise UserError(_('Please fill Provider!'))
        self.state = 'open'
        self.create_uid = self.env.user.id
        prefix = self.provider_id.alias and self.provider_id.alias + '~' or ''
        if not self.tour_code:
            if self.tour_category == 'group':
                self.tour_code = prefix + self.env['ir.sequence'].next_by_code('master.tour.code.group')
            elif self.tour_category == 'private':
                self.tour_code = prefix + self.env['ir.sequence'].next_by_code('master.tour.code.fit')

    def action_closed(self):
        self.state = 'on_going'
        # dup_survey = self.env['survey.survey'].search([('type', '=', 'tour'), ('is_default', '=', True)], limit=1)
        # if dup_survey:
        #     a = dup_survey[0].copy()
        #     a.tour_id = self.id
        #     a.name = self.name

    def action_definite(self):
        self.state = 'definite'

    def action_cancel(self):
        self.state = 'cancel'

    def action_adjustment(self):
        # Calculate Adjustment
        adt = chd = inf = 0
        adt_price = self.adult_citra_price - self.adult_fare
        chd_price = self.child_citra_price - self.child_fare
        inf_price = self.infant_citra_price - self.infant_fare

        for pax in self.passengers_ids:
            if pax.pax_type == 'ADT' and pax.state == 'done':
                adt += 1
            if pax.pax_type == 'CHD' and pax.state == 'done':
                chd += 1
            if pax.pax_type == 'INF' and pax.state == 'done':
                inf += 1
        ho_profit = (adt * adt_price) + (chd * chd_price) + (inf * inf_price)
        debit = credit = 0
        for rec in self.adjustment_ids:
            if rec.type == 'debit':
                debit += rec.total
            if rec.type == 'credit':
                credit += rec.total
        ho_profit = ho_profit + debit - credit
        acc_debit = acc_credit = 0
        if ho_profit >= 0:
            acc_debit = ho_profit
        else:
            acc_credit = ho_profit * -1
        self.state = 'closed'

    def action_done(self):
        self.state = 'done'

    def action_sold(self):
        self.state = 'sold'

    def action_reopen(self):
        self.state = 'open'

    @api.multi
    def action_send_email(self, passenger_id):
        return passenger_id

    def action_send_survey(self):
        for rec in self:
            for passenger in rec.passengers_ids:
                self.action_send_email(passenger.id)

    @api.depends('departure_date', 'arrival_date')
    @api.onchange('departure_date', 'arrival_date')
    def _compute_survey_date(self):
        for rec in self:
            if rec.departure_date and rec.arrival_date:
                diff = (datetime.strptime(str(rec.arrival_date), '%Y-%m-%d') - datetime.strptime(str(rec.departure_date),'%Y-%m-%d')).days
                mod = diff % 2
                mod += int(diff / 2)
                rec.survey_date = str(datetime.strptime(str(rec.departure_date), '%Y-%m-%d') + relativedelta(days=mod))

    @api.depends('departure_date', 'arrival_date')
    @api.onchange('departure_date', 'arrival_date')
    def _compute_duration(self):
        for rec in self:
            if rec.departure_date and rec.arrival_date:
                diff = (datetime.strptime(str(rec.arrival_date), '%Y-%m-%d') - datetime.strptime(
                    str(rec.departure_date), '%Y-%m-%d')).days
                rec.duration = str(diff)

    def create_other_info_from_json(self, data):
        message_id_list = []
        for rec in data['message']:
            msg_obj = self.env['tt.master.tour.otherinfo.messages'].sudo().create({
                'name': rec['text'],
                'style': rec['style'],
                'sequence': rec['sequence'],
            })
            message_id_list.append(msg_obj.id)

        other_info_obj = self.env['tt.master.tour.otherinfo'].sudo().create({
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
        self.sudo().write({
            'export_other_info': base64.b64encode(json_data.encode())
        })

    def import_other_info_json(self):
        if not self.import_other_info:
            raise UserError(_('Please upload a json file before pressing this button!'))
        try:
            other_info_list = []
            upload_file = json.loads(base64.b64decode(self.import_other_info))
            for rec in self.other_info_ids:
                rec.sudo().unlink()
            for rec in upload_file:
                other_info_list.append(self.create_other_info_from_json(rec))
            self.sudo().write({
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

        self.sudo().write({
            'other_info_preview': str(temp_txt)
        })

    def get_tour_other_info(self):
        list_of_dict = []
        for rec in self.other_info_ids:
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
                'tour_query': data.get('tour_query') and '%' + str(data['tour_query']) + '%' or '',
            }

            search_request.update({
                'departure_date': str(search_request['departure_year']) + '-' + str(search_request['departure_month'])
            })

            sql_query = "SELECT tp.* FROM tt_master_tour tp LEFT JOIN tt_tour_location_rel tcr ON tcr.product_id = tp.id left join tt_tour_master_locations loc on loc.id = tcr.location_id WHERE tp.state IN ('open', 'definite', 'sold') AND tp.active = True"

            if search_request.get('tour_query'):
                sql_query += " AND tp.name_with_date ILIKE '" + search_request['tour_query'] + "'"

            if search_request['country_id'] != 0:
                self.env.cr.execute("""SELECT id, name FROM res_country WHERE id=%s""",
                                    (str(search_request['country_id']),))
                temp = self.env.cr.dictfetchall()
                search_request.update({
                    'country_name': temp[0]['name']
                })
                sql_query += " AND loc.country_id = " + str(search_request['country_id'])

            if search_request['city_id'] != 0:
                self.env.cr.execute("""SELECT id, name FROM res_city WHERE id=%s""",
                                    (search_request['city_id'],))
                temp = self.env.cr.dictfetchall()
                search_request.update({
                    'city_name': temp[0]['name']
                })
                sql_query += " AND loc.city_id = " + str(search_request['city_id'])

            sql_query += ' group by tp.id'
            self.env.cr.execute(sql_query)
            result_temp = self.env.cr.dictfetchall()

            result_final = []
            for rec in result_temp:
                if rec['tour_category'] == 'private':
                    if not rec.get('agent_id'):
                        result_final.append(rec)
                    elif rec['agent_id'] == context['co_agent_id']:
                        result_final.append(rec)
                else:
                    result_final.append(rec)

            result = []
            for idx, rec in enumerate(result_final):
                if rec.get('departure_date'):
                    if search_request['departure_month'] != '00':
                        if search_request['departure_year'] != '0000':
                            if str(rec['departure_date'])[:7] == search_request['departure_date']:
                                result.append(rec)
                        else:
                            if str(rec['departure_date'])[5:7] == search_request['departure_month']:
                                result.append(rec)
                    elif search_request['departure_year'] != '0000':
                        if str(rec['departure_date'])[:4] == search_request['departure_year']:
                            result.append(rec)
                    else:
                        result.append(rec)
                # if rec.get('start_period'):
                #     if search_request['departure_month'] != '00':
                #         if search_request['departure_year'] != '0000':
                #             if str(rec['start_period'])[:7] <= search_request['departure_date'] <= str(rec['end_period'])[:7]:
                #                 result.append(rec)
                #         else:
                #             if str(rec['start_period'])[5:7] <= search_request['departure_month'] <= str(rec['end_period'])[5:7]:
                #                 result.append(rec)
                #     elif search_request['departure_year'] != '0000':
                #         if str(rec['start_period'])[:4] <= search_request['departure_year'] <= str(rec['end_period'])[:4]:
                #             result.append(rec)
                #     else:
                #         result.append(rec)

            deleted_keys = ['import_other_info', 'export_other_info', 'adult_fare', 'adult_commission', 'child_fare',
                            'child_commission', 'infant_fare', 'infant_commission', 'document_url', 'down_payment',
                            'other_info_preview', 'create_date', 'create_uid', 'write_date', 'write_uid']

            for idx, rec in enumerate(result):
                try:
                    self.env.cr.execute("""SELECT tuc.* FROM tt_upload_center tuc LEFT JOIN tour_images_rel tir ON tir.image_id = tuc.id WHERE tir.tour_id = %s ORDER BY tuc.sequence;""", (rec['id'],))
                    images = self.env.cr.dictfetchall()
                except Exception:
                    images = []

                final_images = []
                for rec_img in images:
                    final_images.append({
                        'seq_id': rec_img['seq_id'],
                        'url': rec_img['url'],
                        'filename': rec_img.get('filename') and rec_img['filename'] or False,
                    })

                adult_sale_price = int(rec['adult_fare']) + int(rec['adult_commission'])
                child_sale_price = int(rec['child_fare']) + int(rec['child_commission'])
                infant_sale_price = int(rec['infant_fare']) + int(rec['infant_commission'])
                res_provider = rec.get('provider_id') and self.env['tt.provider'].browse(rec['provider_id']) or None
                rec.update({
                    'name': rec['name'],
                    'adult_sale_price': adult_sale_price,
                    'child_sale_price': child_sale_price,
                    'infant_sale_price': infant_sale_price,
                    'images_obj': final_images,
                    'departure_date': rec['departure_date'] and rec['departure_date'] or '',
                    'arrival_date': rec['arrival_date'] and rec['arrival_date'] or '',
                    'provider_id': rec.get('provider_id') and rec['provider_id'] or '',
                    'provider': res_provider and res_provider.code or '',
                    'create_date': '',
                    'write_date': '',
                })

                if rec.get('currency_id'):
                    curr_id = rec.pop('currency_id')
                    rec.update({
                        'currency_code': self.env['res.currency'].sudo().browse(int(curr_id)).name
                    })

                result_obj = self.env['tt.master.tour'].browse(int(rec['id']))
                location_objs = result_obj.location_ids
                location_temp = []
                for location_obj in location_objs:
                    loc_temp = {
                        'country_name': location_obj.country_id.name,
                        'state_name': location_obj.state_id.name,
                        'city_name': location_obj.city_id.name,
                    }
                    location_temp.append(loc_temp)
                rec.update({
                    'locations': location_temp,
                })

                key_list = [key for key in rec.keys()]
                for key in key_list:
                    if rec[key] is None:
                        rec.update({
                            key: ''
                        })
                    if key in deleted_keys:
                        rec.pop(key)

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
            response = {
                'seat': 0,
                'quota': 0,
                'state': 'sold',
                'availability': False
            }
            if not data.get('provider'):
                default_prov = self.env.ref('tt_reservation_tour.tt_provider_tour_internal')
                data.update({
                    'provider': default_prov.code and default_prov.code or ''
                })
            provider_obj = self.env['tt.provider'].sudo().search([('code', '=', data['provider'])], limit=1)
            if not provider_obj:
                raise RequestException(1002)
            provider_obj = provider_obj[0]
            tour_obj = self.env['tt.master.tour'].sudo().search([('tour_code', '=', provider_obj.alias + '~' + data['tour_code']), ('provider_id', '=', provider_obj.id)], limit=1)
            if tour_obj:
                tour_obj = tour_obj[0]
                response.update({
                    'seat': tour_obj.seat,
                    'quota': tour_obj.quota,
                    'state': tour_obj.state,
                    'availability': int(tour_obj.seat) > 0 and True or False
                })
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1022)

    def update_availability_api(self, data, context, **kwargs):
        try:
            provider_obj = self.env['tt.provider'].sudo().search([('code', '=', data['provider'])], limit=1)
            if not provider_obj:
                raise RequestException(1002)
            provider_obj = provider_obj[0]
            tour_obj = self.env['tt.master.tour'].sudo().search([('tour_code', '=', data['tour_code']), ('provider_id', '=', provider_obj.id)], limit=1)
            if tour_obj:
                tour_obj = tour_obj[0]
                tour_obj.sudo().write({
                    'seat': data['seat'],
                    'quota': data['quota'],
                    'state': data['state'],
                })
            response = {
                'tour_code': data['tour_code'],
                'seat': data['seat'],
                'quota': data['quota'],
                'availability': int(data['seat']) > 0 and True or False
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
                'journey_type': segment.journey_type,
                'class_of_service': segment.class_of_service,
                'carrier_id': segment.carrier_id.name,
                'carrier_code': segment.carrier_id.code,
                'carrier_number': segment.carrier_number,
                'origin_id': segment.origin_id.display_name,
                'origin_code': segment.origin_id.code,
                'origin_terminal': segment.origin_terminal,
                'departure_date': utc_tz.localize(segment.departure_date).astimezone(user_tz),
                'departure_date_fmt': utc_tz.localize(segment.departure_date).astimezone(user_tz).strftime('%d-%b-%Y %H:%M'),
                'destination_id': segment.destination_id.display_name,
                'destination_code': segment.destination_id.code,
                'destination_terminal': segment.destination_terminal,
                'arrival_date': utc_tz.localize(segment.arrival_date).astimezone(user_tz),
                'arrival_date_fmt': utc_tz.localize(segment.arrival_date).astimezone(user_tz).strftime('%d-%b-%Y %H:%M'),
                'delay': 'None',
            }
            if old_vals and old_vals['journey_type'] == segment.journey_type:
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
                    'image_file_name': item.image_id.filename,
                    'sequence': item.sequence,
                })
            vals = {
                'name': itinerary.name,
                'day': itinerary.day,
                'date': itinerary.date,
                'items': it_items,
            }
            list_obj.append(vals)
        return list_obj

    def get_tour_details_api(self, data, context, **kwargs):
        try:
            search_request = {
                'tour_code': data.get('tour_code') and data['tour_code'] or '',
                'provider': data.get('provider') and data['provider'] or ''
            }
            provider_obj = self.env['tt.provider'].sudo().search([('alias', '=', search_request['provider'])], limit=1)
            if not provider_obj:
                raise RequestException(1002)
            provider_obj = provider_obj[0]
            tour_obj = self.env['tt.master.tour'].sudo().search([('tour_code', '=', provider_obj.alias + '~' + search_request['tour_code']), ('provider_id', '=', provider_obj.id)], limit=1)
            if not tour_obj:
                raise RequestException(1022, additional_message='Tour not found.')
            tour_obj = tour_obj[0]
            search_request.update({
                'id': tour_obj.id
            })
            self.env.cr.execute("""SELECT loc.* FROM tt_master_tour tp LEFT JOIN tt_tour_location_rel tcr ON tcr.product_id = tp.id LEFT JOIN tt_tour_master_locations loc ON loc.id = tcr.location_id WHERE tp.id=%s;""",(tour_obj.id,))
            location_ids = self.env.cr.dictfetchall()
            location_list = []
            country_names = []
            city_names = []
            for location in location_ids:
                temp_country_name = False
                temp_country = False
                temp_city = False
                if location != 0:
                    if location.get('country_id'):
                        self.env.cr.execute("""SELECT id, name, code FROM res_country WHERE id=%s""", (location['country_id'],))
                        temp = self.env.cr.dictfetchall()
                        if temp:
                            country_names.append(temp[0]['name'])
                            temp_country = temp[0]['code']
                            temp_country_name = temp[0]['name']

                    if location.get('city_id'):
                        self.env.cr.execute("""SELECT id, name FROM res_city WHERE id=%s""", (location['city_id'],))
                        temp2 = self.env.cr.dictfetchall()
                        if temp2:
                            city_names.append(temp2[0]['name'])
                            temp_city = temp2[0]['name']
                location_list.append({
                    'country_code': temp_country,
                    'country_name': temp_country_name,
                    'city_name': temp_city,
                })

            try:
                self.env.cr.execute(
                    """SELECT * FROM tt_master_tour_rooms WHERE tour_pricelist_id = %s;""", (tour_obj.id,))
                accommodation = self.env.cr.dictfetchall()
            except Exception:
                accommodation = []

            hotel_names = []
            for acc in accommodation:
                if acc.get('hotel'):
                    if acc['hotel'] not in hotel_names:
                        hotel_names.append(acc['hotel'])

                if acc.get('active'):
                    acc.pop('active')
                if acc.get('write_date'):
                    acc.pop('write_date')
                if acc.get('write_uid'):
                    acc.pop('write_uid')
                if acc.get('currency_id'):
                    acc.pop('currency_id')

                acc_key_list = [key for key in acc.keys()]
                for key in acc_key_list:
                    if acc[key] is None:
                        acc.update({
                            key: ''
                        })

            try:
                self.env.cr.execute("""SELECT tuc.* FROM tt_upload_center tuc LEFT JOIN tour_images_rel tir ON tir.image_id = tuc.id WHERE tir.tour_id = %s;""", (tour_obj.id,))
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

            adult_sale_price = int(tour_obj.adult_fare) + int(tour_obj.adult_commission)
            child_sale_price = int(tour_obj.child_fare) + int(tour_obj.child_commission)
            infant_sale_price = int(tour_obj.infant_fare) + int(tour_obj.infant_commission)

            selected_tour = {
                'name': tour_obj.name,
                'description': tour_obj.description,
                'tour_code': tour_obj.tour_code,
                'tour_route': tour_obj.tour_route,
                'tour_category': tour_obj.tour_category,
                'tour_type': tour_obj.tour_type,
                'currency': tour_obj.currency_id.name,
                'visa': tour_obj.visa,
                'flight': tour_obj.flight,
                'seat': int(tour_obj.seat),
                'quota': int(tour_obj.quota),
                'accommodations': accommodation,
                'currency_code': tour_obj.currency_id.name,
                'adult_sale_price': adult_sale_price <= 0 and '0' or adult_sale_price,
                'child_sale_price': child_sale_price <= 0 and '0' or child_sale_price,
                'infant_sale_price': infant_sale_price <= 0 and '0' or infant_sale_price,
                'departure_date': tour_obj.departure_date and tour_obj.departure_date or '',
                'arrival_date': tour_obj.arrival_date and tour_obj.arrival_date or '',
                'locations': location_list,
                'country_names': country_names,
                'flight_segments': tour_obj.get_flight_segment(),
                'itinerary_ids': tour_obj.get_itineraries(),
                'other_infos': tour_obj.get_tour_other_info(),
                'hotel_names': hotel_names,
                'duration': tour_obj.duration and tour_obj.duration or 0,
                'images_obj': final_images,
                'document_url': tour_obj.document_url and tour_obj.document_url.url or '',
                'provider': tour_obj.provider_id and tour_obj.provider_id.code or '',
            }

            response = {
                'search_request': search_request,
                'selected_tour': selected_tour,
                'currency_code': 'IDR',
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
                'provider': data.get('provider') and data['provider'] or ''
            }
            provider_obj = self.env['tt.provider'].sudo().search([('code', '=', search_request['provider'])], limit=1)
            if not provider_obj:
                raise RequestException(1002)
            provider_obj = provider_obj[0]
            search_tour_obj = self.env['tt.master.tour'].sudo().search([('tour_code', '=', provider_obj.alias + '~' + search_request['tour_code']), ('provider_id', '=', provider_obj.id)], limit=1)
            if not search_tour_obj:
                raise RequestException(1022, additional_message='Tour not found.')
            search_tour_obj = search_tour_obj[0]
            payment_rules = [
                {
                    'name': 'Down Payment',
                    'description': 'Down Payment',
                    'payment_percentage': search_tour_obj.down_payment,
                    'due_date': date.today(),
                    'is_dp': True
                }
            ]
            for payment in search_tour_obj.payment_rules_ids:
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
                'provider': data.get('provider') and data['provider'] or ''
            }
            provider_obj = self.env['tt.provider'].sudo().search([('code', '=', search_request['provider'])], limit=1)
            if not provider_obj:
                raise RequestException(1002)
            provider_obj = provider_obj[0]
            search_tour_obj = self.env['tt.master.tour'].sudo().search([('tour_code', '=', provider_obj.alias + '~' + search_request['tour_code']), ('provider_id', '=', provider_obj.id)], limit=1)
            if not search_tour_obj:
                raise RequestException(1022, additional_message='Tour not found.')
            search_tour_obj = search_tour_obj[0]
            new_pay_rules = data.get('payment_rules') and data['payment_rules']['payment_rules'] or []
            new_pay_ids = []
            for rec in new_pay_rules:
                if rec.get('is_dp'):
                    if float(rec['payment_percentage']) != float(search_tour_obj.down_payment):
                        search_tour_obj.sudo().write({
                            'down_payment': float(rec['payment_percentage'])
                        })
                else:
                    new_pay_obj = self.env['tt.payment.rules'].sudo().create({
                        'name': rec['name'],
                        'description': rec['description'],
                        'payment_percentage': rec['payment_percentage'],
                        'due_date': rec['due_date']
                    })
                    new_pay_ids.append(new_pay_obj.id)
                self.env.cr.commit()

            search_tour_obj.sudo().write({
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

    def get_config_by_api(self):
        try:
            countries_list = []
            country_objs = self.env['res.country'].sudo().search([('provider_city_ids', '!=', False)])
            for country in country_objs:
                state = self.get_states_by_api(country.id)
                if state.get('error_code'):
                    _logger.info(state['error_msg'])
                    raise Exception(state['error_msg'])
                if len(state['response']) > 0:
                    state_list = []
                    for temp_state in state['response']:
                        city = self.get_cities_state_by_api(int(temp_state['uuid']))
                        if city.get('error_code'):
                            _logger.info(city['error_msg'])
                            raise Exception(city['error_msg'])
                        city_list = []
                        for temp_city in city['response']:
                            city_list.append(temp_city)
                        temp_state.update({
                            'cities': city_list
                        })
                        state_list.append(temp_state)
                else:
                    city = self.get_cities_by_api(country.id)
                    if city.get('error_code'):
                        _logger.info(city['error_msg'])
                        raise Exception(city['error_msg'])
                    city_list = []
                    for temp_city in city['response']:
                        city_list.append(temp_city)
                    state_list = [{
                        'name': False,
                        'uuid': False,
                        'cities': city_list
                    }]

                countries_list.append({
                    'name': country.name,
                    'code': country.code,
                    'uuid': country.id,
                    'states': state_list
                })

            values = {
                'countries': countries_list,
            }
            return ERR.get_no_error(values)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1021)

    def get_cities_by_api(self, id):
        try:
            result_objs = self.env['res.city'].sudo().search([('country_id', '=', int(id))])
            cities = []
            for rec in result_objs:
                cities.append({
                    'name': rec.name,
                    'uuid': rec.id,
                })
            return ERR.get_no_error(cities)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1021)

    def get_states_by_api(self, id):
        try:
            result_objs = self.env['res.country.state'].sudo().search([('country_id', '=', int(id))])
            states = []
            for rec in result_objs:
                states.append({
                    'name': rec.name,
                    'uuid': rec.id,
                })
            return ERR.get_no_error(states)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1021)

    def get_cities_state_by_api(self, id):
        try:
            result_objs = self.env['res.city'].sudo().search([('state_id', '=', int(id))])
            cities = []
            for rec in result_objs:
                cities.append({
                    'name': rec.name,
                    'uuid': rec.id,
                })
            return ERR.get_no_error(cities)
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
            provider_obj = self.env['tt.provider'].sudo().search([('code', '=', search_request['provider'])], limit=1)
            if not provider_obj:
                raise RequestException(1002)
            provider_obj = provider_obj[0]
            tour_data_list = self.env['tt.master.tour'].sudo().search([('tour_code', '=', provider_obj.alias + '~' + search_request['tour_code']), ('provider_id', '=', provider_obj.id)], limit=1)
            if not tour_data_list:
                raise RequestException(1022, additional_message='Tour not found.')
            tour_data = tour_data_list[0]
            price_itinerary = {
                'carrier_code': tour_data.carrier_id.code,
                'adult_fare': tour_data.adult_fare,
                'adult_commission': tour_data.adult_commission,
                'child_fare': tour_data.child_fare,
                'child_commission': tour_data.child_commission,
                'infant_fare': tour_data.infant_fare,
                'infant_commission': tour_data.infant_commission,
                'adult_airport_tax': tour_data.airport_tax,
                'child_airport_tax': tour_data.airport_tax,
                'infant_airport_tax': tour_data.airport_tax,
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
                'accommodations': []
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
            grand_total_pax = 0
            grand_total_pax_no_infant = 0
            for rec in temp_room_list:
                tour_room_list = self.env['tt.master.tour.rooms'].sudo().search([('room_code', '=', rec['room_code']), ('tour_pricelist_id', '=', tour_data.id)], limit=1)
                tour_room = tour_room_list[0]
                total_amount = int(rec['adult']) + int(rec['child']) + int(rec['infant'])
                grand_total_pax += total_amount
                total_amount_no_infant = int(rec['adult']) + int(rec['child'])
                grand_total_pax_no_infant += total_amount_no_infant
                adult_amt = child_amt = infant_amt = adult_sur_amt = child_sur_amt = adult_sur = child_sur = 0
                extra_bed_limit = tour_room.extra_bed_limit
                single_sup = 0
                if total_amount_no_infant < tour_room.pax_minimum:
                    single_sup = (tour_room.pax_minimum - total_amount_no_infant) * int(tour_room.single_supplement)
                    adult_amt += total_amount_no_infant
                    infant_amt += rec['infant']
                else:
                    if rec['adult'] >= tour_room.pax_minimum:
                        adult_amt += rec['adult']
                        if int(rec['adult']) - int(tour_room.pax_minimum) <= int(extra_bed_limit):
                            adult_sur_amt += rec['adult'] - tour_room.pax_minimum
                            adult_sur += (rec['adult'] - tour_room.pax_minimum) * int(tour_room.adult_surcharge)
                            extra_bed_limit -= rec['adult'] - tour_room.pax_minimum
                            child_amt += rec['child']
                            if int(rec['child']) <= extra_bed_limit:
                                child_sur_amt += rec['child']
                                child_sur += rec['child'] * int(tour_room.child_surcharge)
                            else:
                                child_sur_amt += rec['child'] - extra_bed_limit
                                child_sur += (rec['child'] - extra_bed_limit) * int(tour_room.child_surcharge)
                        else:
                            adult_sur_amt += rec['adult'] - tour_room.pax_minimum - extra_bed_limit
                            adult_sur += adult_sur * int(tour_room.adult_surcharge)
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
                                child_sur += child_sur_amt * int(tour_room.child_surcharge)
                        if rec['infant'] > 0:
                            if rec['adult'] + rec['child'] < tour_room.pax_minimum:
                                if rec['infant'] - (tour_room.pax_minimum - rec['adult'] - rec['child']) > 0:
                                    infant_amt += rec['infant'] - (tour_room.pax_minimum - rec['adult'] - rec['child'])
                                else:
                                    infant_amt += 0
                            else:
                                infant_amt += rec['infant']

                temp_accom = {
                    'room_id': tour_room.id,
                    'room_code': tour_room.room_code,
                    'adult_amount': adult_amt,
                    'child_amount': child_amt,
                    'infant_amount': infant_amt,
                    'adult_surcharge_amount': adult_sur_amt,
                    'child_surcharge_amount': child_sur_amt,
                    'adult_surcharge': tour_room.adult_surcharge,
                    'child_surcharge': tour_room.child_surcharge,
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
            # if tour_data.tour_category == 'private':
            #     for rec in tour_data.discount_ids:
            #         if rec.min_pax <= grand_total_pax_no_infant <= rec.max_pax:
            #             price_itinerary.update({
            #                 'discount_per_pax': rec.discount_per_pax,
            #                 'discount_total': rec.discount_total,
            #             })
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
            book_obj = self.env['tt.reservation.tour'].sudo().search([('name', '=', data['order_number'])], limit=1)
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
            query = req.get('name') and '%' + req['name'] + '%' or False
            sql_query = "select * from tt_master_tour where state IN ('open', 'definite') AND seat > 0 AND active = True"
            if query:
                sql_query += " and name_with_date ilike %"+query+"%"
            self.env.cr.execute(sql_query)

            result_id_list = self.env.cr.dictfetchall()
            result_list = []

            for result in result_id_list:
                result = {
                    'name': result.get('name_with_date') and result['name_with_date'] or '',
                }
                result_list.append(result)

            return ERR.get_no_error(result_list)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1022)

    def product_sync_webhook_nosend(self, req, context):
        try:
            _logger.info("Receiving tour data from webhook...")
            provider_id = self.env['tt.provider'].sudo().search([('code', '=', req['provider'])], limit=1)
            if not provider_id:
                raise RequestException(1002)
            prefix = provider_id[0].alias and provider_id[0].alias + '~' or ''
            for rec in req['data']:
                currency_obj = self.env['res.currency'].sudo().search([('name', '=', rec['currency_code'])], limit=1)
                vals = {
                    'name': rec['name'],
                    'tour_code': prefix + rec['tour_code'],
                    'provider_id': provider_id[0].id,
                    'tour_route': rec['tour_route'],
                    'sequence': rec['sequence'],
                    'is_can_hold': rec['is_can_hold'],
                    'currency_id': currency_obj and currency_obj[0].id or False,
                    'description': rec['description'],
                    'tour_category': rec['tour_category'],
                    'tour_type': rec['tour_type'],
                    'departure_date': datetime.strptime(rec['departure_date'], "%Y-%m-%d"),
                    'arrival_date': datetime.strptime(rec['arrival_date'], "%Y-%m-%d"),
                    'duration': rec['duration'],
                    'guiding_days': rec['guiding_days'],
                    'driving_times': rec['driving_times'],
                    'survey_date': datetime.strptime(rec['survey_date'], "%Y-%m-%d"),
                    'seat': rec['seat'],
                    'quota': rec['quota'],
                    'visa': rec['visa'],
                    'flight': rec['flight'],
                    'adult_fare': rec['adult_fare'],
                    'child_fare': rec['child_fare'],
                    'infant_fare': rec['infant_fare'],
                    'adult_commission': rec['adult_commission'],
                    'child_commission': rec['child_commission'],
                    'infant_commission': rec['infant_commission'],
                    'airport_tax': rec['airport_tax'],
                    'tipping_guide': rec['tipping_guide'],
                    'tipping_tour_leader': rec['tipping_tour_leader'],
                    'tipping_driver': rec['tipping_driver'],
                    'tipping_guide_child': rec['tipping_guide_child'],
                    'tipping_tour_leader_child': rec['tipping_tour_leader_child'],
                    'tipping_driver_child': rec['tipping_driver_child'],
                    'tipping_guide_infant': rec['tipping_guide_infant'],
                    'tipping_tour_leader_infant': rec['tipping_tour_leader_infant'],
                    'tipping_driver_infant': rec['tipping_driver_infant'],
                    'down_payment': rec['down_payment'],
                }
                tour_obj = self.env['tt.master.tour'].sudo().search([('tour_code', '=', rec['tour_code']), ('provider_id', '=', provider_id[0].id)], limit=1)
                if tour_obj:
                    tour_obj = tour_obj[0]
                    tour_obj.sudo().write(vals)
                    for fli in tour_obj.flight_segment_ids:
                        fli.sudo().unlink()
                    for itin in tour_obj.itinerary_ids:
                        itin.sudo().unlink()
                    for temp_room in tour_obj.room_ids:
                        temp_room.sudo().write({
                            'active': False
                        })
                else:
                    tour_obj = self.env['tt.master.tour'].sudo().create(vals)
                self.env.cr.commit()

                location_list = []
                for rec2 in rec['location_ids']:
                    search_params = []
                    country_obj = self.env['res.country'].sudo().search([('code', '=', rec2['country_code'])], limit=1)
                    if country_obj:
                        search_params.append(('country_id', '=', country_obj[0].id))
                    city_obj = self.env['res.city'].sudo().search([('name', '=', rec2['city_name'])], limit=1)
                    if city_obj:
                        search_params.append(('city_id', '=', city_obj[0].id))
                    loc_obj = self.env['tt.tour.master.locations'].sudo().search(search_params, limit=1)
                    if loc_obj:
                        loc_obj = loc_obj[0]
                    else:
                        loc_obj = self.env['tt.tour.master.locations'].sudo().create({
                            'country_id': country_obj and country_obj[0].id or False,
                            'city_id': city_obj and city_obj[0].id or False,
                        })
                    location_list.append(loc_obj.id)

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
                    room_obj = self.env['tt.master.tour.rooms'].sudo().search([('room_code', '=', rec2['room_code']), ('tour_pricelist_id', '=', tour_obj.id), '|',('active', '=', False), ('active', '=', True)], limit=1)
                    if room_obj:
                        room_obj = room_obj[0]
                        room_obj.sudo().write(room_vals)
                    else:
                        room_obj = self.env['tt.master.tour.rooms'].sudo().create(room_vals)

                for rec2 in rec['flight_segment_ids']:
                    carrier_obj = self.env['tt.transport.carrier'].sudo().search([('code', '=', rec2['carrier_code']),('provider_type_id', '=', self.env.ref('tt_reservation_airline.tt_provider_type_airline').id)],limit=1)
                    carrier_obj = carrier_obj and carrier_obj[0] or False
                    origin_obj = self.env['tt.destinations'].sudo().search([('code', '=', rec2['origin_code']), ('provider_type_id', '=', self.env.ref('tt_reservation_airline.tt_provider_type_airline').id)],limit=1)
                    origin_obj = origin_obj and origin_obj[0] or False
                    destination_obj = self.env['tt.destinations'].sudo().search([('code', '=', rec2['destination_code']),('provider_type_id', '=', self.env.ref('tt_reservation_airline.tt_provider_type_airline').id)],limit=1)
                    destination_obj = destination_obj and destination_obj[0] or False
                    self.env['flight.segment'].sudo().create({
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
                    new_itin_obj = self.env['tt.reservation.tour.itinerary'].sudo().create({
                        'name': rec2['name'],
                        'day': rec2['day'],
                        'date': datetime.strptime(rec2['date'], "%Y-%m-%d"),
                        'tour_pricelist_id': tour_obj.id,
                    })
                    for rec3 in rec2['item_ids']:
                        self.env['tt.reservation.tour.itinerary.item'].sudo().create({
                            'name': rec3['name'],
                            'description': rec3['description'],
                            'timeslot': rec3['timeslot'],
                            'sequence': rec3['sequence'],
                            'image_id': rec3.get('image_id') and self.convert_image_to_own(rec3['image_id']['url'], rec3['image_id']['filename']) or False,
                            'itinerary_id': new_itin_obj.id,
                        })

                for rec2 in rec['other_info_ids']:
                    tour_obj.create_other_info_from_json(rec2)

                tour_obj.sudo().write({
                    'location_ids': [(6, 0, location_list)],
                    'image_ids': [(6, 0, image_list)],
                })

                if tour_obj.state == 'draft':
                    tour_obj.action_validate()
            response = {
                'success': True
            }
            return ERR.get_no_error(response)
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error()

    # def generate_all_room_codes(self):
    #     room_list = self.env['tt.master.tour.rooms'].sudo().search([('room_code', '=', False)])
    #     for rec in room_list:
    #         rec.sudo().write({
    #             'room_code': self.env['ir.sequence'].next_by_code('master.tour.room.code') or 'New'
    #         })


class TourSyncProductsChildren(models.TransientModel):
    _name = "tour.sync.product.children.wizard"
    _description = 'Rodex Model'

    def sync_data_to_children(self):
        try:
            tour_data_list = []
            tour_datas = self.env['tt.master.tour'].sudo().search([('state', 'in', ['open', 'definite'])])
            for rec in tour_datas:
                dict_vals = {
                    'name': rec.name,
                    'tour_code': rec.tour_code,
                    'tour_route': rec.tour_route,
                    'sequence': rec.sequence,
                    'is_can_hold': rec.is_can_hold,
                    'currency_code': rec.currency_id.name,
                    'description': rec.description,
                    'tour_category': rec.tour_category,
                    'tour_type': rec.tour_type,
                    'departure_date': rec.departure_date and rec.departure_date.strftime("%Y-%m-%d") or False,
                    'arrival_date': rec.arrival_date and rec.arrival_date.strftime("%Y-%m-%d") or False,
                    'duration': rec.duration,
                    'guiding_days': rec.guiding_days,
                    'driving_times': rec.driving_times,
                    'survey_date': rec.survey_date and rec.survey_date.strftime("%Y-%m-%d") or False,
                    'seat': rec.seat,
                    'quota': rec.quota,
                    'visa': rec.visa,
                    'flight': rec.flight,
                    'adult_fare': rec.adult_fare,
                    'child_fare': rec.child_fare,
                    'infant_fare': rec.infant_fare,
                    'adult_commission': rec.adult_commission,
                    'child_commission': rec.child_commission,
                    'infant_commission': rec.infant_commission,
                    'airport_tax': rec.airport_tax,
                    'tipping_guide': rec.tipping_guide,
                    'tipping_tour_leader': rec.tipping_tour_leader,
                    'tipping_driver': rec.tipping_driver,
                    'tipping_guide_child': rec.tipping_guide_child,
                    'tipping_tour_leader_child': rec.tipping_tour_leader_child,
                    'tipping_driver_child': rec.tipping_driver_child,
                    'tipping_guide_infant': rec.tipping_guide_infant,
                    'tipping_tour_leader_infant': rec.tipping_tour_leader_infant,
                    'tipping_driver_infant': rec.tipping_driver_infant,
                    'down_payment': rec.down_payment,
                }

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

                room_list = []
                for rec2 in rec.room_ids:
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
                        'single_supplement': rec2.single_supplement,
                        'additional_charge': rec2.additional_charge,
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
                        'date': rec2.date and rec2.date.strftime("%Y-%m-%d") or False,
                        'item_ids': item_list,
                    })

                other_info_list = []
                for rec2 in rec.other_info_ids:
                    other_info_list.append(rec2.convert_info_to_dict())

                dict_vals.update({
                    'location_ids': location_list,
                    'flight_segment_ids': flight_list,
                    'image_ids': image_list,
                    'room_ids': room_list,
                    'itinerary_ids': itinerary_list,
                    'other_info_ids': other_info_list,
                })
                tour_data_list.append(dict_vals)
            vals = {
                'provider_type': 'tour',
                'action': 'sync_products_to_children',
                'data': tour_data_list,
            }
            self.env['tt.api.webhook.data'].notify_subscriber(vals)
        except Exception as e:
            raise UserError(_('Failed to sync tour data to children!'))
