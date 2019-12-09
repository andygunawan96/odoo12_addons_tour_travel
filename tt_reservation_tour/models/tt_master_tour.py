from odoo import api, fields, models, _
from datetime import datetime
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from ...tools.api import Response
import logging, traceback
import json
import pytz
import base64

_logger = logging.getLogger(__name__)


class Survey(models.Model):
    _inherit = 'survey.survey'

    tour_id = fields.Many2one('tt.master.tour', 'Tour')


class TourItineraryItem(models.Model):
    _name = 'tt.reservation.tour.itinerary.item'

    name = fields.Char('Title')
    description = fields.Text('Description')
    timeslot = fields.Char('Timeslot')
    image_id = fields.Many2one('tt.upload.center', 'Image')
    itinerary_id = fields.Many2one('tt.reservation.tour.itinerary', 'Tour Itinerary')


class TourItinerary(models.Model):
    _name = 'tt.reservation.tour.itinerary'

    name = fields.Char('Title')
    day = fields.Integer('Day')
    date = fields.Date('Date')
    tour_pricelist_id = fields.Many2one('tt.master.tour', 'Tour')
    item_ids = fields.One2many('tt.reservation.tour.itinerary.item', 'itinerary_id', 'Items')


class MasterTour(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.master.tour'
    _order = 'sequence'

    def get_domain(self):
        domain_id = self.env.ref('tt_reservation_tour.tt_provider_type_tour').id
        return [('provider_type_id.id', '=', int(domain_id))]

    name = fields.Char('Name', required=True, default='Tour', size=40)
    description = fields.Text('Description')

    tour_code = fields.Char('Tour Code', readonly=True, copy=False)
    tour_route = fields.Selection([('international', 'International'), ('domestic', 'Domestic')],
                                  'Route', required=True, default='international')
    tour_category = fields.Selection([('group', 'Group'), ('private', 'Private')],
                                     'Tour Category', required=True, default='group')
    tour_type = fields.Selection([('series', 'Series (With Tour Leader)'), ('sic', 'SIC (Without Tour Leader)'), ('land', 'Land Only'), ('city', 'City Tour'), ('private', 'Private Tour')], 'Tour Type', default='series')

    departure_date = fields.Date('Departure Date')
    return_date = fields.Date('Arrival Date')
    duration = fields.Integer('Duration (days)', help="in day(s)", readonly=True,
                              compute='_compute_duration', store=True)

    start_period = fields.Date('Start Period')
    end_period = fields.Date('End Period')
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

    payment_rules_ids = fields.One2many('tt.payment.rules', 'pricelist_id')

    ho_id = fields.Many2one('tt.agent',
                            default=lambda x: x.env['tt.agent'].search([('agent_type_id', '=', 2)], limit=1).id)
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
    itinerary_ids = fields.One2many('tt.reservation.tour.itinerary', 'tour_pricelist_id', 'Itinerary', ondelete='cascade')
    provider_id = fields.Many2one('tt.provider', 'Provider', domain=get_domain, required=True)
    document_url = fields.Many2one('tt.upload.center', 'Document URL')
    import_other_info = fields.Binary('Import JSON')
    export_other_info = fields.Binary('Export JSON')
    file_name = fields.Char("Filename",compute="_compute_filename",store=True)
    active = fields.Boolean('Active', default=True)

    @api.depends("name")
    def _compute_filename(self):
        for rec in self:
            rec.file_name = rec.name+".json"

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
                rec.departure_date = False
                rec.return_date = False
            if rec.tour_category == 'group':
                rec.start_period = False
                rec.end_period = False
                if rec.tour_type == 'private':
                    rec.tour_type = 'series'
                if rec.tour_type == 'sic':
                    rec.tipping_tour_leader = 0

    def action_validate(self):
        self.state = 'open'
        self.create_uid = self.env.user.id
        if self.tour_category == 'group':
            self.tour_code = self.env['ir.sequence'].next_by_code('master.tour.code.group')
        elif self.tour_category == 'private':
            self.tour_code = self.env['ir.sequence'].next_by_code('master.tour.code.fit')

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

    @api.depends('departure_date', 'return_date')
    @api.onchange('departure_date', 'return_date')
    def _compute_survey_date(self):
        for rec in self:
            if rec.departure_date and rec.return_date:
                diff = (datetime.strptime(str(rec.return_date), '%Y-%m-%d') - datetime.strptime(str(rec.departure_date),'%Y-%m-%d')).days
                mod = diff % 2
                mod += int(diff / 2)
                rec.survey_date = str(datetime.strptime(str(rec.departure_date), '%Y-%m-%d') + relativedelta(days=mod))

    @api.depends('departure_date', 'return_date')
    @api.onchange('departure_date', 'return_date')
    def _compute_duration(self):
        for rec in self:
            if rec.departure_date and rec.return_date:
                diff = (datetime.strptime(str(rec.return_date), '%Y-%m-%d') - datetime.strptime(
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

            sql_query = "SELECT tp.* FROM tt_master_tour tp LEFT JOIN tt_tour_location_rel tcr ON tcr.product_id = tp.id left join tt_tour_master_locations loc on loc.id = tcr.location_id WHERE tp.state IN ('open', 'definite') AND tp.seat > 0 AND tp.active = True"

            if search_request.get('tour_query'):
                sql_query += " AND tp.name ILIKE '" + search_request['tour_query'] + "'"

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

            result = []

            for idx, rec in enumerate(result_temp):
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
                if rec.get('start_period'):
                    if search_request['departure_month'] != '00':
                        if search_request['departure_year'] != '0000':
                            if str(rec['start_period'])[:7] <= search_request['departure_date'] <= str(rec['end_period'])[:7]:
                                result.append(rec)
                        else:
                            if str(rec['start_period'])[5:7] <= search_request['departure_month'] <= str(rec['end_period'])[5:7]:
                                result.append(rec)
                    elif search_request['departure_year'] != '0000':
                        if str(rec['start_period'])[:4] <= search_request['departure_year'] <= str(rec['end_period'])[:4]:
                            result.append(rec)
                    else:
                        result.append(rec)

                if rec.get('import_other_info'):
                    rec.pop('import_other_info')

                if rec.get('export_other_info'):
                    rec.pop('export_other_info')

            for idx, rec in enumerate(result):
                try:
                    self.env.cr.execute("""SELECT tuc.* FROM tt_upload_center tuc LEFT JOIN tour_images_rel tir ON tir.image_id = tuc.id WHERE tir.tour_id = %s;""", (rec['id'],))
                    images = self.env.cr.dictfetchall()
                except Exception:
                    images = []

                for rec_img in images:
                    rec_img.update({
                        'create_date': '',
                        'write_date': '',
                    })
                    img_key_list = [img_key for img_key in rec_img.keys()]
                    for img_key in img_key_list:
                        if rec_img[img_key] is None:
                            rec_img.update({
                                img_key: ''
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
                    'images_obj': images,
                    'departure_date': rec['departure_date'] and rec['departure_date'] or '',
                    'return_date': rec['return_date'] and rec['return_date'] or '',
                    'start_period': rec['start_period'] and rec['start_period'] or '',
                    'end_period': rec['end_period'] and rec['end_period'] or '',
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

                key_list = [key for key in rec.keys()]
                for key in key_list:
                    if rec[key] is None:
                        rec.update({
                            key: ''
                        })

            response = {
                'country_id': search_request['country_id'],
                'country': search_request.get('country_name', ''),
                'city_id': search_request['city_id'],
                'city': search_request.get('city_name', ''),
                'search_request': search_request,
                # 'search_request_json': json.dumps(search_request),
                'result': result,
                # 'result_json': json.dumps(result),
                'search_value': 2,
            }
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1022)

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
                'carrier_id': segment.carrier_id.name,
                'carrier_code': segment.carrier_id.code,
                'carrier_number': segment.carrier_number,
                'origin_id': segment.origin_id.display_name,
                'origin_terminal': segment.origin_terminal,
                'departure_date': utc_tz.localize(segment.departure_date).astimezone(user_tz),
                'departure_date_fmt': utc_tz.localize(segment.departure_date).astimezone(user_tz).strftime('%d-%b-%Y %H:%M'),
                'destination_id': segment.destination_id.display_name,
                'destination_terminal': segment.destination_terminal,
                'return_date': utc_tz.localize(segment.return_date).astimezone(user_tz),
                'return_date_fmt': utc_tz.localize(segment.return_date).astimezone(user_tz).strftime('%d-%b-%Y %H:%M'),
                'delay': 'None',
            }
            if old_vals and old_vals['journey_type'] == segment.journey_type:
                time_delta = utc_tz.localize(segment.departure_date).astimezone(user_tz) - old_vals['return_date']
                day = time_delta.days
                hours = time_delta.seconds/3600
                minute = time_delta.seconds % 60
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
                'id': data.get('id') and data['id'] or '0'
            }

            tour_obj = self.env['tt.master.tour'].sudo().search([('id', '=', int(search_request['id']))], limit=1)
            if tour_obj:
                tour_obj = tour_obj[0]

            user_agent_id = self.env.user.agent_id.agent_type_id.id
            if user_agent_id == self.env.ref('tt_base.agent_type_citra').id:
                commission_agent_type = 'citra'
            elif user_agent_id == self.env.ref('tt_base.agent_type_japro').id:
                commission_agent_type = 'japro'
            elif user_agent_id == self.env.ref('tt_base.agent_type_btbr').id or user_agent_id == self.env.ref('tt_base.agent_type_btbo').id:
                commission_agent_type = 'btb'
            else:
                commission_agent_type = 'other'

            try:
                self.env.cr.execute("""SELECT * FROM tt_master_tour_discount WHERE tour_id = %s;""", (tour_obj.id,))
                discount = self.env.cr.dictfetchall()
            except Exception:
                discount = []

            self.env.cr.execute("""SELECT loc.* FROM tt_master_tour tp LEFT JOIN tt_tour_location_rel tcr ON tcr.product_id = tp.id LEFT JOIN tt_tour_master_locations loc ON loc.id = tcr.location_id WHERE tp.id=%s;""",(tour_obj.id,))
            location_ids = self.env.cr.dictfetchall()
            country_names = []
            for location in location_ids:
                if location != 0:
                    self.env.cr.execute("""SELECT id, name FROM res_country WHERE id=%s""", (location['country_id'],))
                    temp = self.env.cr.dictfetchall()
                    country_names.append(temp[0]['name'])

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

                if acc.get('adult_surcharge'):
                    acc.pop('adult_surcharge')
                if acc.get('child_surcharge'):
                    acc.pop('child_surcharge')
                if acc.get('single_supplement'):
                    acc.pop('single_supplement')
                if acc.get('additional_charge'):
                    acc.pop('additional_charge')
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

            for img_temp in images:
                img_key_list = [key for key in img_temp.keys()]
                for key in img_key_list:
                    if img_temp[key] is None:
                        img_temp.update({
                            key: ''
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
                'visa': tour_obj.visa,
                'flight': tour_obj.flight,
                'seat': int(tour_obj.seat),
                'quota': int(tour_obj.quota),
                'accommodations': accommodation,
                'currency_code': tour_obj.currency_id.name,
                'adult_sale_price': adult_sale_price <= 0 and '0' or adult_sale_price,
                'child_sale_price': child_sale_price <= 0 and '0' or child_sale_price,
                'infant_sale_price': infant_sale_price <= 0 and '0' or infant_sale_price,
                'discount': json.dumps(discount),
                'departure_date': tour_obj.departure_date and tour_obj.departure_date or '',
                'return_date': tour_obj.return_date and tour_obj.return_date or '',
                'start_period': tour_obj.start_period and tour_obj.start_period or '',
                'end_period': tour_obj.end_period and tour_obj.end_period or '',
                'country_names': country_names,
                'flight_segments': tour_obj.get_flight_segment(),
                'itinerary_ids': tour_obj.get_itineraries(),
                'other_infos': tour_obj.get_tour_other_info(),
                'hotel_names': hotel_names,
                'duration': tour_obj.duration and tour_obj.duration or 0,
                'images_obj': images,
                'document_url': tour_obj.document_url and tour_obj.document_url.url or '',
            }

            # is_agent = self.env.user.agent_id.agent_type_id.id not in [
            #     self.env.ref('tt_base_rodex.agent_type_cor').id, self.env.ref('tt_base_rodex.agent_type_por').id]

            response = {
                'search_request': search_request,
                'selected_tour': selected_tour,
                'commission_agent_type': commission_agent_type,
                'currency_code': 'IDR',
                # 'is_HO': self.env.user.agent_id.is_HO,
                'agent_id': self.env.user.agent_id.id,
                # 'is_agent': is_agent,
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
            search_tour_id = data.get('id')
            search_tour_obj = self.env['tt.master.tour'].sudo().browse(int(search_tour_id))
            payment_rules = []
            for payment in search_tour_obj.payment_rules_ids:
                vals = {
                    'name': payment.name,
                    'description': payment.description,
                    'payment_type': payment.payment_type,
                    'payment_percentage': payment.payment_percentage,
                    'payment_amount': payment.payment_amount,
                    'due_date': payment.due_date,
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

    def get_config_by_api(self):
        try:
            countries_list = []
            country_objs = self.env['res.country'].sudo().search([('provider_city_ids', '!=', False)])
            for country in country_objs:
                # for rec in country.provider_city_ids:
                #     if rec.provider_id.id == vendor_id:
                city = self.get_cities_by_api(country.id)
                countries_list.append({
                    'name': country.name,
                    'id': country.id,
                    'city': city
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
                    'id': rec.id,
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
            tour_id = req['package_id']
            tour_data_list = self.env['tt.master.tour'].sudo().search([('id', '=', tour_id)], limit=1)
            tour_data = tour_data_list[0]
            price_itinerary = {
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
                tour_room_list = self.env['tt.master.tour.rooms'].sudo().search([('id', '=', int(rec['id']))], limit=1)
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
                'pnr': self.env['ir.sequence'].next_by_code('rodextrip.tour.reservation.code')
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
            response = {
                'success': True
            }
            return ERR.get_no_error(response)
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
                sql_query += " and name ilike %"+query+"%"
            self.env.cr.execute(sql_query)

            result_id_list = self.env.cr.dictfetchall()
            result_list = []

            for result in result_id_list:
                result = {
                    'name': result.get('name') and result['name'] or '',
                }
                result_list.append(result)

            return ERR.get_no_error(result_list)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1022)
