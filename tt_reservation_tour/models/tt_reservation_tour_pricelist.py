from odoo import api, fields, models, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from ...tools.api import Response
import json

DP_TYPE = [
    ('percentage', 'Percentage'),
    ('amount', 'Amount'),
]


class Survey(models.Model):
    _inherit = 'survey.survey'

    tour_id = fields.Many2one('tt.reservation.tour.pricelist', 'Tour')


class TourItineraryItem(models.Model):
    _name = 'tt.reservation.tour.itinerary.item'

    name = fields.Char('Title')
    description = fields.Text('Description')
    timeslot = fields.Char('Timeslot')
    image = fields.Char('Image URL')
    itinerary_id = fields.Many2one('tt.reservation.tour.itinerary', 'Tour Itinerary')


class TourItinerary(models.Model):
    _name = 'tt.reservation.tour.itinerary'

    name = fields.Char('Title')
    day = fields.Integer('Day')
    date = fields.Date('Date')
    tour_pricelist_id = fields.Many2one('tt.reservation.tour.pricelist', 'Tour')
    item_ids = fields.One2many('tt.reservation.tour.itinerary.item', 'itinerary_id', 'Items')


class TourPricelist(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.reservation.tour.pricelist'
    _order = 'sequence'

    name = fields.Char('Name', required=True, default='Tour', size=40)
    description = fields.Text('Description')

    tour_code = fields.Char('Tour Code', readonly=True, copy=False)
    tour_route = fields.Selection([('international', 'International'), ('domestic', 'Domestic')],
                                  'Route', required=True, default='international')
    tour_category = fields.Selection([('group', 'Group'), ('private', 'Private')],
                                     'Tour Category', required=True, default='group')
    tour_type = fields.Selection([('series', 'Series (With Tour Leader)'), ('sic', 'SIC (Without Tour Leader)'), ('land', 'Land Only'), ('city', 'City Tour'), ('private', 'Private Tour')], 'Tour Type', default='series')

    departure_date = fields.Date('Departure Date')
    arrival_date = fields.Date('Arrival Date')
    duration = fields.Integer('Duration (days)', help="in day(s)", readonly=True,
                              compute='_compute_duration', store=True)

    start_period = fields.Date('Start Period')
    end_period = fields.Date('End Period')
    survey_date = fields.Date('Survey Send Date', readonly=True, compute='_compute_survey_date')

    commercial_duration = fields.Char('Duration', readonly=1)  # compute='_compute_duration'
    seat = fields.Integer('Seat Available', required=True, default=1)
    quota = fields.Integer('Quota', required=True, default=1)
    is_can_hold = fields.Boolean('Can Be Hold', default=True, required=True)

    state_tour = fields.Selection([('draft', 'Draft'), ('open', 'Open'), ('definite', 'Definite'), ('sold', 'Sold Out'),
                                   ('on_going', 'On Going'), ('done', 'Done'), ('closed', 'Closed'),
                                   ('cancelled', 'Canceled')],
                                  'State', copy=False, default='draft', help="draft = tidak tampil di front end"
                                                                             "definite = pasti berangkat"
                                                                             "done = sudah pulang"
                                                                             "closed = sisa uang sdh masuk ke HO"
                                                                             "cancelled = tidak jadi berangkat")

    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    country_ids = fields.Many2many('res.country', 'tour_country_rel', 'pricelist_id', 'country_id', string='Country',
                                   required=True)
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

    adult_nta_price = fields.Monetary('Adult NTA Price', default=0)
    adult_citra_price = fields.Monetary('Adult Citra Price', default=0)
    adult_sale_price = fields.Monetary('Adult Sale Price', default=0)

    child_nta_price = fields.Monetary('Child NTA Price', default=0)
    child_citra_price = fields.Monetary('Child Citra Price', default=0)
    child_sale_price = fields.Monetary('Child Sale Price', default=0)

    infant_nta_price = fields.Monetary('Infant NTA Price', default=0)
    infant_citra_price = fields.Monetary('Infant Citra Price', default=0)
    infant_sale_price = fields.Monetary('Infant Sale Price', default=0)

    adult_citra_price_real = fields.Monetary('Adult Citra Price', default=0)
    adult_sale_price_real = fields.Monetary('Adult Sale Price', default=0)

    child_citra_price_real = fields.Monetary('Child Citra Price', default=0)
    child_sale_price_real = fields.Monetary('Child Sale Price', default=0)

    infant_citra_price_real = fields.Monetary('Infant Citra Price', default=0)
    infant_sale_price_real = fields.Monetary('Infant Sale Price', default=0)

    adult_nta_price_rel = fields.Monetary('Adult NTA Price', default=0, readonly=1, related='adult_nta_price')
    adult_citra_price_rel = fields.Monetary('Adult Citra Price', default=0, readonly=1,
                                            related='adult_citra_price')
    adult_sale_price_rel = fields.Monetary('Adult Sale Price', default=0, readonly=1, related='adult_sale_price')

    child_nta_price_rel = fields.Monetary('Child NTA Price', default=0, readonly=1, related='child_nta_price')
    child_citra_price_rel = fields.Monetary('Child Citra Price', default=0, readonly=1,
                                            related='child_citra_price')
    child_sale_price_rel = fields.Monetary('Child Sale Price', default=0, readonly=1, related='child_sale_price')

    infant_nta_price_rel = fields.Monetary('Infant NTA Price', default=0, readonly=1, related='infant_nta_price')
    infant_citra_price_rel = fields.Monetary('Infant Citra Price', default=0, readonly=1,
                                             related='infant_citra_price')
    infant_sale_price_rel = fields.Monetary('Infant Sale Price', default=0, readonly=1,
                                            related='infant_sale_price')

    discount_ids = fields.One2many('tt.reservation.tour.discount.fit', 'tour_pricelist_id')
    room_ids = fields.One2many('tt.reservation.tour.rooms', 'tour_pricelist_id', required=True)

    dp = fields.Float('Down Payment Percent (%)')
    dp_type = fields.Selection(DP_TYPE, 'Down Payment Type')
    dp_amount = fields.Monetary('Down Payment Amount', default=0)
    dp_percentage = fields.Float('Down Payment Percentage (%)', default=0)
    payment_rules_ids = fields.One2many('tt.payment.rules', 'pricelist_id')

    ho_id = fields.Many2one('tt.agent',
                            default=lambda x: x.env['tt.agent'].search([('agent_type_id', '=', 2)], limit=1).id)
    tour_leader_ids = fields.Many2many('res.employee', string="Tour Leader")
    # tour_leader_ids = fields.Many2many('res.employee', 'tour_leader_rel', 'pricelist_id', 'partner_id',
    #                                    string="Tour Leader")
    # tour_checklist_ids = fields.Char('Tour Checklist')
    tour_checklist_ids = fields.One2many('tt.reservation.tour.checklist', 'tour_pricelist_id', string="Tour Checklist")

    requirements = fields.Html('Remarks')
    images = fields.One2many('tt.reservation.tour.images', 'pricelist_id', 'Images')
    # images = fields.Many2many('ir.attachment', 'tour_images_rel',
    #                           'pricelist_id', 'image_id', domain=[('res_model', '=', 'tt.reservation.tour.pricelist')],
    #                           string='Add Image', required=True)

    flight_segment_ids = fields.One2many('flight.segment', 'tour_pricelist_id', string="Flight Segment")
    # visa_pricelist_ids = fields.Many2many('tt.traveldoc.pricelist', 'tour_visa_rel', 'tour_id', 'visa_id',
    #                                       domain=[('transport_type', '=', 'visa')], string='Visa Pricelist')
    passengers_ids = fields.One2many('tt.reservation.tour.line', 'tour_pricelist_id', string='Tour Participants', copy=False)
    sequence = fields.Integer('Sequence', default=3)
    adjustment_ids = fields.One2many('tt.reservation.tour.adjustment', 'tour_pricelist_id', required=True)
    survey_title_ids = fields.One2many('survey.survey', 'tour_id', string='Tour Surveys', copy=False)
    quotation_ids = fields.One2many('tt.reservation.tour.package.quotation', 'tour_pricelist_id', 'Tour Quotation(s)')

    country_name = fields.Char('Country Name')
    itinerary_ids = fields.One2many('tt.reservation.tour.itinerary', 'tour_pricelist_id', 'Itinerary')

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
                rec.arrival_date = False
            if rec.tour_category == 'group':
                rec.start_period = False
                rec.end_period = False
                if rec.tour_type == 'private':
                    rec.tour_type = 'series'
                if rec.tour_type == 'sic':
                    rec.tipping_tour_leader = 0

    def action_validate(self):
        self.state_tour = 'open'
        self.create_uid = self.env.user.id
        if self.tour_category == 'group':
            self.tour_code = self.env['ir.sequence'].next_by_code('tour.pricelist.code.group')
        elif self.tour_category == 'private':
            self.tour_code = self.env['ir.sequence'].next_by_code('tour.pricelist.code.fit')

    def action_closed(self):
        self.state_tour = 'on_going'
        # dup_survey = self.env['survey.survey'].search([('type', '=', 'tour'), ('is_default', '=', True)], limit=1)
        # if dup_survey:
        #     a = dup_survey[0].copy()
        #     a.tour_id = self.id
        #     a.name = self.name

    def action_definite(self):
        self.state_tour = 'definite'

    def action_cancelled(self):
        self.state_tour = 'cancelled'

    def action_adjustment(self):
        # Calculate Adjustment
        adt = chd = inf = 0
        adt_price = self.adult_citra_price - self.adult_nta_price
        chd_price = self.child_citra_price - self.child_nta_price
        inf_price = self.infant_citra_price - self.infant_nta_price

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
        self.state_tour = 'closed'

    def action_done(self):
        self.state_tour = 'done'

    def action_sold(self):
        self.state_tour = 'sold'

    def action_reopen(self):
        self.state_tour = 'open'

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

    @api.depends('quotation_ids')
    @api.onchange('quotation_ids')
    def _compute_all_prices(self):
        adult_nta = 0
        adult_citra = 0
        adult_sale = 0
        child_nta = 0
        child_citra = 0
        child_sale = 0
        infant_nta = 0
        infant_citra = 0
        infant_sale = 0
        adult_citra_real = 0
        adult_sale_real = 0
        child_citra_real = 0
        child_sale_real = 0
        infant_citra_real = 0
        infant_sale_real = 0

        # looping semua quotation_ids yang ada
        for rec in self.quotation_ids:
            if rec.pax_type == 'adt':
                print('Adult')
                adult_nta += rec.total_exclude
                adult_sale += rec.retail_price_exclude + rec.visa
                adult_citra += rec.retail_price_exclude + rec.visa - rec.service_charge
                adult_citra_real += rec.retail_price_include - rec.service_charge
                adult_sale_real += rec.retail_price_include
            elif rec.pax_type == 'chd':
                child_nta += rec.total_exclude
                child_sale += rec.retail_price_exclude + rec.visa
                child_citra += rec.retail_price_exclude + rec.visa - rec.service_charge
                child_citra_real += rec.retail_price_include - rec.service_charge
                child_sale_real += rec.retail_price_include
            elif rec.pax_type == 'inf':
                infant_nta += rec.total_exclude
                infant_sale += rec.total_exclude
                infant_citra += rec.total_exclude
                infant_sale_real += rec.total_exclude
                infant_citra_real += rec.total_exclude

        # Masukkan nilai variable ke self.variable
        # Adult
        self.adult_nta_price = adult_nta
        self.adult_citra_price = adult_citra
        self.adult_sale_price = adult_sale
        self.adult_citra_price_real = adult_citra_real
        self.adult_sale_price_real = adult_sale_real

        # Child
        self.child_nta_price = child_nta
        self.child_citra_price = child_citra
        self.child_sale_price = child_sale
        self.child_citra_price_real = child_citra_real
        self.child_sale_price_real = child_sale_real

        # Infant
        self.infant_nta_price = infant_nta
        self.infant_citra_price = infant_citra
        self.infant_sale_price = infant_sale
        self.infant_citra_price_real = infant_citra_real
        self.infant_sale_price_real = infant_sale_real

    def int_with_commas(self, x):
        result = ''
        while x >= 1000:
            x, r = divmod(x, 1000)
            result = ".%03d%s" % (r, result)
        return "%d%s" % (x, result)

    def get_tour_countries_api(self, data, context, **kwargs):
        try:
            temp = []
            self.env.cr.execute("""SELECT country_id FROM tour_country_rel""")
            countries = self.env.cr.dictfetchall()
            for country in countries:
                if not country['country_id'] in temp:
                    temp.append(country['country_id'])

            countries = []
            if temp:
                self.env.cr.execute("""SELECT id, name, code, phone_code FROM res_country WHERE id in %s""",
                                    (tuple(temp),))
                countries = self.env.cr.dictfetchall()

            response = {
                'countries': countries,
            }
            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res

    def search_tour_api(self, data, context, **kwargs):
        try:
            search_request = {
                'country_id': data.get('country_id') and data['country_id'] or '0',
                'departure_month': data.get('month') and data['month'] or '00',
                'departure_year': data.get('year') and data['year'] or '0000',
                'tour_query': data.get('tour_query') and '%' + str(data['tour_query']) + '%' or '',
            }

            search_request.update({
                'departure_date': str(search_request['departure_year']) + '-' + str(search_request['departure_month'])
            })

            if search_request['country_id'] != '0':
                self.env.cr.execute("""SELECT id, name FROM res_country WHERE id=%s""",
                                    (search_request['country_id'],))
                temp = self.env.cr.dictfetchall()
                search_request.update({
                    'country_name': temp[0]['name']
                })

            if search_request.get('tour_query'):
                if search_request['country_id'] != '0':
                    self.env.cr.execute("""SELECT * FROM tt_reservation_tour_pricelist tp LEFT JOIN tour_country_rel tcr ON tp.id = tcr.pricelist_id WHERE tp.state_tour IN ('open', 'definite', 'sold') AND tp.name ILIKE '%s' AND tcr.country_id = %s;""" % (search_request['tour_query'], search_request['country_id']))
                else:
                    self.env.cr.execute("""SELECT * FROM tt_reservation_tour_pricelist WHERE state_tour IN ('open', 'definite', 'sold') AND name ILIKE '%s';""" % (search_request['tour_query']))
            else:
                if search_request['country_id'] != '0':
                    self.env.cr.execute("""SELECT * FROM tt_reservation_tour_pricelist tp LEFT JOIN tour_country_rel tcr ON tp.id = tcr.pricelist_id WHERE tp.state_tour IN ('open', 'definite', 'sold') AND tcr.country_id = %s;""" % (search_request['country_id']))
                else:
                    self.env.cr.execute("""SELECT * FROM tt_reservation_tour_pricelist WHERE state_tour IN ('open', 'definite', 'sold');""")

            result_temp = self.env.cr.dictfetchall()

            result = []

            for idx, rec in enumerate(result_temp):
                if rec['departure_date']:
                    if search_request['departure_month'] != '00':
                        if search_request['departure_year'] != '0000':
                            if rec['departure_date'][:7] == search_request['departure_date']:
                                result.append(rec)
                        else:
                            if rec['departure_date'][5:7] == search_request['departure_month']:
                                result.append(rec)
                    elif search_request['departure_year'] != '0000':
                        if rec['departure_date'][:4] == search_request['departure_year']:
                            result.append(rec)
                    else:
                        result.append(rec)
                if rec['start_period']:
                    if search_request['departure_month'] != '00':
                        if search_request['departure_year'] != '0000':
                            if rec['start_period'][:7] <= search_request['departure_date'] <= rec['end_period'][:7]:
                                result.append(rec)
                        else:
                            if rec['start_period'][5:7] <= search_request['departure_month'] <= rec['end_period'][5:7]:
                                result.append(rec)
                    elif search_request['departure_year'] != '0000':
                        if rec['start_period'][:4] <= search_request['departure_year'] <= rec['end_period'][:4]:
                            result.append(rec)
                    else:
                        result.append(rec)

            for idx, rec in enumerate(result):
                try:
                    self.env.cr.execute("""SELECT * FROM tt_reservation_tour_images WHERE pricelist_id = %s;""", (rec['id'],))
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

                rec.update({
                    'name': rec['name'],
                    'adult_sale_price_with_comma': self.int_with_commas(rec['adult_sale_price']),
                    'child_sale_price_with_comma': self.int_with_commas(rec['child_sale_price']),
                    'infant_sale_price_with_comma': self.int_with_commas(rec['infant_sale_price']),
                    'airport_tax_with_comma': self.int_with_commas(rec['airport_tax']),
                    'tipping_guide_with_comma': self.int_with_commas(rec['tipping_guide']),
                    'tipping_tour_leader_comma': self.int_with_commas(rec['tipping_tour_leader']),
                    'tipping_driver_with_comma': self.int_with_commas(rec['tipping_driver']),
                    'images_obj': images,
                    'departure_date_f': rec['departure_date'] and datetime.strptime(str(rec['departure_date']), '%Y-%m-%d').strftime("%A, %d-%m-%Y") or '',
                    'arrival_date_f': rec['arrival_date'] and datetime.strptime(str(rec['arrival_date']), '%Y-%m-%d').strftime("%A, %d-%m-%Y") or '',
                    'start_period_f': rec['start_period'] and datetime.strptime(str(rec['start_period']), '%Y-%m-%d').strftime('%B') or '',
                    'end_period_f': rec['end_period'] and datetime.strptime(str(rec['end_period']), '%Y-%m-%d').strftime('%B') or '',
                    'departure_date': rec['departure_date'] and datetime.strptime(str(rec['departure_date']), '%Y-%m-%d').strftime('%d %b %Y') or '',
                    'departure_date_ori': rec['departure_date'] and rec['departure_date'] or '',
                    'arrival_date': rec['arrival_date'] and datetime.strptime(str(rec['arrival_date']), '%Y-%m-%d').strftime('%d %b %Y') or '',
                    'start_period': rec['start_period'] and datetime.strptime(str(rec['start_period']), '%Y-%m-%d').strftime('%B') or '',
                    'start_period_ori': rec['start_period'] and rec['start_period'] or '',
                    'end_period': rec['end_period'] and datetime.strptime(str(rec['end_period']), '%Y-%m-%d').strftime('%B') or '',
                    'create_date': '',
                    'write_date': '',
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
                'search_request': search_request,
                # 'search_request_json': json.dumps(search_request),
                'result': result,
                # 'result_json': json.dumps(result),
                'search_value': 2,
                'currency_id': self.env.user.company_id.currency_id.id
            }
            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res

    def get_delay(self, day, hour, minute):
        delay_str = str(day)
        delay_str += 'd '
        delay_str += str(hour)
        delay_str += 'h '
        delay_str += str(minute)
        delay_str += 'm'
        return delay_str

    def get_flight_segment(self, id):
        list_obj = []
        old_vals = {}
        context_timestamp = lambda t: fields.Datetime.context_timestamp(self, t)
        for segment in self.env['tt.reservation.tour.pricelist'].sudo().browse(int(id)).flight_segment_ids:
            vals = {
                'journey_type': segment.journey_type,
                'carrier_id': segment.carrier_id.name,
                'carrier_code': segment.carrier_id.code,
                'carrier_number': segment.carrier_number,
                'origin_id': segment.origin_id.display_name,
                'origin_terminal': segment.origin_terminal,
                'departure_date': segment.departure_date,
                'departure_date_fmt': context_timestamp(segment.departure_date).strftime('%d-%b-%Y %H:%M'),
                'destination_id': segment.destination_id.display_name,
                'destination_terminal': segment.destination_terminal,
                'arrival_date': segment.arrival_date,
                'arrival_date_fmt': context_timestamp(segment.arrival_date).strftime('%d-%b-%Y %H:%M'),
                'delay': 'None',
            }
            if old_vals and old_vals['journey_type'] == segment.journey_type:
                time_delta = segment.departure_date - old_vals['arrival_date']
                day = time_delta.days
                hours = time_delta.seconds/3600
                minute = time_delta.seconds % 60
                list_obj[-1]['delay'] = self.get_delay(day, hours, minute)
            list_obj.append(vals)
            old_vals = vals
        return list_obj

    def get_itineraries(self, id):
        list_obj = []
        for itinerary in self.env['tt.reservation.tour.pricelist'].sudo().browse(int(id)).itinerary_ids:
            it_items = []
            for item in itinerary.item_ids:
                it_items.append({
                    'name': item.name,
                    'description': item.description,
                    'timeslot': item.timeslot,
                    'image': item.image,
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

            self.env.cr.execute("""SELECT * FROM tt_reservation_tour_pricelist tp WHERE id=%s;""", (search_request['id'],))
            tour_list = self.env.cr.dictfetchall()

            user_agent_id = self.env.user.agent_id.agent_type_id.id
            if user_agent_id == self.env.ref('tt_base.agent_type_citra').id:
                commission_agent_type = 'citra'
            elif user_agent_id == self.env.ref('tt_base.agent_type_japro').id:
                commission_agent_type = 'japro'
            elif user_agent_id == self.env.ref('tt_base.agent_type_btbr').id or user_agent_id == self.env.ref('tt_base.agent_type_btbo').id:
                commission_agent_type = 'btb'
            else:
                commission_agent_type = 'other'

            for idx, rec in enumerate(tour_list):
                adult_commission = (rec['adult_sale_price'] - rec['adult_citra_price']) > 0 and rec['adult_sale_price'] - rec['adult_citra_price'] or '0'
                child_commission = (rec['child_sale_price'] - rec['child_citra_price']) > 0 and rec['child_sale_price'] - rec['child_citra_price'] or '0'
                infant_commission = (rec['infant_sale_price'] - rec['infant_citra_price']) > 0 and rec['infant_sale_price'] - rec['infant_citra_price'] or '0'

                try:
                    self.env.cr.execute("""SELECT * FROM tt_reservation_tour_discount_fit WHERE tour_pricelist_id = %s;""", (rec['id'],))
                    discount = self.env.cr.dictfetchall()
                except Exception:
                    discount = []

                self.env.cr.execute("""SELECT * FROM tt_reservation_tour_pricelist tp LEFT JOIN tour_country_rel tcr ON tp.id = tcr.pricelist_id WHERE id=%s;""",(search_request['id'],))
                country_ids = self.env.cr.dictfetchall()
                country_names = []
                for country in country_ids:
                    if country != 0:
                        self.env.cr.execute("""SELECT id, name FROM res_country WHERE id=%s""", (country['country_id'],))
                        temp = self.env.cr.dictfetchall()
                        country_names.append(temp[0]['name'])

                try:
                    self.env.cr.execute(
                        """SELECT * FROM tt_reservation_tour_rooms WHERE tour_pricelist_id = %s;""", (rec['id'],))
                    accommodation = self.env.cr.dictfetchall()
                except Exception:
                    accommodation = []

                hotel_names = []
                for acc in accommodation:
                    if acc.get('hotel'):
                        if acc['hotel'] not in hotel_names:
                            hotel_names.append(acc['hotel'])

                    acc_key_list = [key for key in acc.keys()]
                    for key in acc_key_list:
                        if acc[key] is None:
                            acc.update({
                                key: ''
                            })

                for acc in accommodation:
                    acc.update({
                        'additional_charge_with_comma': self.int_with_commas(acc['additional_charge']),
                        # 'extra_bed_charge_with_comma': self.int_with_commas(rec['extra_bed_charge']),
                        'adult_surcharge_with_comma': self.int_with_commas(acc['adult_surcharge']),
                        'child_surcharge_with_comma': self.int_with_commas(acc['child_surcharge']),
                    })

                try:
                    self.env.cr.execute("""SELECT * FROM tt_reservation_tour_images WHERE pricelist_id = %s;""", (rec['id'],))
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

                rec.update({
                    'name': rec['name'],
                    'accommodations': accommodation,
                    'adult_sale_price_with_comma': self.int_with_commas(rec['adult_sale_price']),
                    'child_sale_price_with_comma': self.int_with_commas(rec['child_sale_price']),
                    'infant_sale_price_with_comma': self.int_with_commas(rec['infant_sale_price']),
                    'adult_sale_price': rec['adult_sale_price'] <= 0 and '0' or rec['adult_sale_price'],
                    'child_sale_price': rec['child_sale_price'] <= 0 and '0' or rec['child_sale_price'],
                    'infant_sale_price': rec['infant_sale_price'] <= 0 and '0' or rec['infant_sale_price'],
                    'adult_commission': adult_commission,
                    'child_commission': child_commission,
                    'infant_commission': infant_commission,
                    'airport_tax_with_comma': self.int_with_commas(rec['airport_tax']),
                    'tipping_guide_with_comma': self.int_with_commas(rec['tipping_guide']),
                    'tipping_tour_leader_with_comma': self.int_with_commas(rec['tipping_tour_leader']),
                    'tipping_driver_with_comma': self.int_with_commas(rec['tipping_driver']),
                    'discount': json.dumps(discount),
                    'departure_date_clean': rec['departure_date'] and datetime.strptime(str(rec['departure_date']),'%Y-%m-%d').strftime('%d %b %Y') or '',
                    'departure_date_f': rec['departure_date'] and datetime.strptime(str(rec['departure_date']), '%Y-%m-%d').strftime("%A, %d-%m-%Y") or '',
                    'arrival_date_clean': rec['arrival_date'] and datetime.strptime(str(rec['arrival_date']), '%Y-%m-%d').strftime('%d %b %Y') or '',
                    'arrival_date_f': rec['arrival_date'] and datetime.strptime(str(rec['arrival_date']), '%Y-%m-%d').strftime("%A, %d-%m-%Y") or '',
                    'start_period_f': rec['start_period'] and datetime.strptime(str(rec['start_period']), '%Y-%m-%d').strftime('%B') or '',
                    'end_period_f': rec['end_period'] and datetime.strptime(str(rec['end_period']), '%Y-%m-%d').strftime('%B') or '',
                    'country_names': country_names,
                    'flight_segment_ids': self.get_flight_segment(search_request['id']),
                    'itinerary_ids': self.get_itineraries(search_request['id']),
                    'hotel_names': hotel_names,
                    'duration': rec.get('duration') and rec['duration'] or 0,
                    'images_obj': images,
                })

                key_list = [key for key in rec.keys()]
                for key in key_list:
                    if rec[key] is None:
                        rec.update({
                            key: ''
                        })

            # is_agent = self.env.user.agent_id.agent_type_id.id not in [
            #     self.env.ref('tt_base_rodex.agent_type_cor').id, self.env.ref('tt_base_rodex.agent_type_por').id]

            response = {
                'search_request': search_request,
                'result': tour_list,
                'commission_agent_type': commission_agent_type,
                'currency_id': self.env.user.company_id.currency_id.id,
                # 'is_HO': self.env.user.agent_id.is_HO,
                'agent_id': self.env.user.agent_id.id,
                # 'is_agent': is_agent,
            }

            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res

    def update_passenger_api(self, data, context, **kwargs):
        try:
            sameBooker = False
            if data['booking_data']['sameBooker'] == "yes":
                sameBooker = True
            else:
                sameBooker = False

            booker_obj = data['booking_data']['contact']
            booker_id = booker_obj.get('booker_id')
            res_booker_id = False
            res_pax_list = []
            book_line_list = []
            contact_person = data['booking_data']['contact_person']
            tour_data = data['booking_data']['tour_data']
            if len(contact_person) > 0:
                similar = self.check_pax_similarity(contact_person[0])
                if not similar:
                    cust_obj = self.env['tt.customer'].sudo().create({
                        'title': contact_person[0].get('title'),
                        'first_name': contact_person[0].get('first_name'),
                        'last_name': contact_person[0].get('last_name'),
                        'email': contact_person[0].get('email'),
                        'agent_id': contact_person[0].get('agent_id') and contact_person[0]['agent_id'] or 2,
                    })
                    if contact_person[0].get('mobile'):
                        self.env['phone.detail'].sudo().create({
                            'customer_id': cust_obj.id,
                            'type': 'work',
                            'name': 'Work',
                            'phone_number': contact_person[0]['mobile'],
                        })
                    res_booker_id = cust_obj.id
                else:
                    res_booker_id = similar.id
            elif not sameBooker and not booker_id:
                similar = self.check_pax_similarity(booker_obj)
                if not similar:
                    cust_obj = self.env['tt.customer'].sudo().create({
                        'title': booker_obj.get('title'),
                        'first_name': booker_obj.get('first_name'),
                        'last_name': booker_obj.get('last_name'),
                        'email': booker_obj.get('email'),
                        'agent_id': booker_obj.get('agent_id') and booker_obj['agent_id'] or 2,
                    })
                    if booker_obj.get('mobile'):
                        self.env['phone.detail'].sudo().create({
                            'customer_id': cust_obj.id,
                            'type': 'work',
                            'name': 'Work',
                            'phone_number': booker_obj['mobile'],
                        })
                    res_booker_id = cust_obj.id
                else:
                    res_booker_id = similar.id

            elif booker_id and not sameBooker:
                temp_booker = self.env['tt.customer'].browse(int(booker_id))
                temp_booker.sudo().update({
                    'title': booker_obj.get('title') and booker_obj['title'] or temp_booker.title,
                    'first_name': booker_obj.get('first_name') and booker_obj['first_name'] or temp_booker.first_name,
                    'last_name': booker_obj.get('last_name') and booker_obj['last_name'] or temp_booker.last_name,
                    'email': booker_obj.get('email') and booker_obj['email'] or temp_booker.email,
                    'agent_id': booker_obj.get('agent_id') and booker_obj['agent_id'] or temp_booker.agent_id,
                })
                if booker_obj.get('mobile'):
                    found = False
                    for ph in temp_booker.phone_ids:
                        if ph.phone_number == booker_obj['mobile']:
                            found = True
                    if not found:
                        self.env['phone.detail'].sudo().create({
                            'customer_id': int(booker_id),
                            'type': 'work',
                            'name': 'Work',
                            'phone_number': booker_obj['mobile'],
                        })
                res_booker_id = int(booker_id)

            temp_idx = 0
            for rec in data['booking_data']['all_pax']:
                if not rec.get('passenger_id'):
                    similar = self.check_pax_similarity(rec)
                    if not similar:
                        cust_obj = self.env['tt.customer'].sudo().create({
                            'title': rec.get('title'),
                            'first_name': rec.get('first_name'),
                            'last_name': rec.get('last_name'),
                            'email': rec.get('email'),
                            'agent_id': rec.get('agent_id') and rec['agent_id'] or 2,
                            'birth_date': rec.get('birth_date_f'),
                            'passport_number': rec.get('passport_number'),
                            'passport_exp_date': rec.get('passport_expdate_f'),
                        })
                        if rec.get('mobile'):
                            self.env['phone.detail'].sudo().create({
                                'customer_id': cust_obj.id,
                                'type': 'work',
                                'name': 'Work',
                                'phone_number': rec['mobile'],
                            })
                        res_pax_list.append(cust_obj.id)
                        if sameBooker and temp_idx == 0 and rec.get('pax_type') == 'ADT':
                            cust_obj.update({
                                'email': booker_obj.get('email'),
                            })
                            if booker_obj.get('mobile'):
                                self.env['phone.detail'].sudo().create({
                                    'customer_id': cust_obj.id,
                                    'type': 'work',
                                    'name': 'Work',
                                    'phone_number': booker_obj['mobile'],
                                })
                            res_booker_id = cust_obj.id
                            temp_idx += 1

                        cust_line_obj = self.env['tt.reservation.tour.line'].sudo().create({
                            'passenger_id': cust_obj.id,
                            'room_id': rec.get('room_id') and rec['room_id'] or False,
                            'room_number': rec.get('room_seq') and rec['room_seq'] or False,
                            'pax_type': rec.get('pax_type') and rec['pax_type'] or False,
                            'tour_pricelist_id': tour_data and tour_data['id'] or False,
                        })
                        book_line_list.append(cust_line_obj.id)
                    else:
                        cust_line_obj = self.env['tt.reservation.tour.line'].sudo().create({
                            'passenger_id': similar.id,
                            'room_id': rec.get('room_id') and rec['room_id'] or False,
                            'room_number': rec.get('room_seq') and rec['room_seq'] or False,
                            'pax_type': rec.get('pax_type') and rec['pax_type'] or False,
                            'tour_pricelist_id': tour_data and tour_data['id'] or False,
                        })
                        book_line_list.append(cust_line_obj.id)

                else:
                    temp = self.env['tt.customer'].browse(int(rec['passenger_id']))
                    temp.sudo().update({
                        'title': rec.get('title') and rec['title'] or temp.title,
                        'first_name': rec.get('first_name') and rec['first_name'] or temp.first_name,
                        'last_name': rec.get('last_name') and rec['last_name'] or temp.last_name,
                        'email': rec.get('email') and rec['email'] or temp.email,
                        'agent_id': rec.get('agent_id') and rec['agent_id'] or temp.agent_id,
                        'birth_date': rec.get('birth_date_f') and rec['birth_date_f'] or temp.birth_date,
                        'passport_number': rec.get('passport_number') and rec['passport_number'] or temp.passport_number,
                        'passport_exp_date': rec.get('passport_expdate_f') and rec['passport_expdate_f'] or temp.passport_exp_date,
                    })
                    if rec.get('mobile'):
                        found = False
                        for ph in temp.phone_ids:
                            if ph.phone_number == rec['mobile']:
                                found = True
                        if not found:
                            self.env['phone.detail'].sudo().create({
                                'customer_id': int(rec['passenger_id']),
                                'type': 'work',
                                'name': 'Work',
                                'phone_number': rec['mobile'],
                            })
                    res_pax_list.append(int(rec['passenger_id']))
                    cust_line_obj = self.env['tt.reservation.tour.line'].sudo().create({
                        'passenger_id': int(rec['passenger_id']),
                        'room_id': rec.get('room_id') and rec['room_id'] or False,
                        'room_number': rec.get('room_seq') and rec['room_seq'] or False,
                        'pax_type': rec.get('pax_type') and rec['pax_type'] or False,
                        'tour_pricelist_id': tour_data and tour_data['id'] or False,
                    })
                    book_line_list.append(cust_line_obj.id)

            response = {
                'booker_data': res_booker_id,
                'pax_list': res_pax_list,
                'book_line': book_line_list,
            }
            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res

    def check_pax_similarity(self, vals):
        result = []
        parameters = []
        if vals.get('first_name'):
            parameters.append(('first_name', '=ilike', vals['first_name']))
        if vals.get('last_name'):
            parameters.append(('last_name', '=ilike', vals['last_name']))
        if vals.get('title'):
            parameters.append(('title', '=', vals['title']))
        if vals.get('agent_id'):
            parameters.append(('agent_id', '=', int(vals['agent_id'])))
        if vals.get('birth_date_f'):
            parameters.append(('birth_date', '=', vals['birth_date_f']))

        search_result = self.env['tt.customer'].search(parameters)

        if vals.get('mobile'):
            for rec in search_result:
                for rec2 in rec['phone_ids']:
                    if rec2.phone_number == vals.get('mobile'):
                        result.append(rec)
        else:
            result = search_result

        if len(result) > 0:
            return result[0]
        else:
            return False

    def commit_booking_api(self, data, context, **kwargs):
        try:
            booking_data = data.get('booking_data')
            price_itinerary = {}
            tour_data = {}
            pricelist_id = 0
            if booking_data:
                tour_data = booking_data.get('tour_data')
                pricelist_id = tour_data.get('id') and int(tour_data['id']) or 0
                price_itinerary = booking_data.get('price_itinerary')
            force_issued = data.get('force_issued') and int(data['force_issued']) or 0
            booker_id = data.get('booker_id') and data['booker_id'] or False
            pax_ids_str = data.get('pax_ids') and data['pax_ids'] or '|'
            book_line_ids_str = data.get('book_line_ids') and data['book_line_ids'] or '|'
            temp = pax_ids_str.split('|')
            temp2 = book_line_ids_str.split('|')
            pax_ids = []
            book_line_ids = []
            service_charge = []
            service_charge_ids = []
            def_currency = self.env['res.currency'].search([('name', '=', 'IDR')])[0].id

            for rec in temp:
                if rec:
                    pax_ids.append(int(rec))

            for rec in temp2:
                if rec:
                    book_line_ids.append(int(rec))

            if price_itinerary.get('adult_amount'):
                service_charge.append({
                    'pax_type': 'ADT',
                    'charge_code': 'fare',
                    'charge_type': 'fare',
                    'amount': price_itinerary['adult_price'] / price_itinerary['adult_amount'],
                    'pax_count': price_itinerary['adult_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Adult Price',
                })
                service_charge.append({
                    'pax_type': 'ADT',
                    'charge_code': 'tax',
                    'charge_type': 'tax',
                    'amount': price_itinerary['airport_tax_total'] / (price_itinerary['adult_amount'] + price_itinerary['child_amount'] + price_itinerary['infant_amount']),
                    'pax_count': price_itinerary['adult_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Airport Tax',
                })

            if price_itinerary.get('adult_surcharge_amount'):
                service_charge.append({
                    'pax_type': 'ADT',
                    'charge_code': 'tax',
                    'charge_type': 'tax',
                    'amount': price_itinerary['adult_surcharge_price'] / price_itinerary['adult_surcharge_amount'],
                    'pax_count': price_itinerary['adult_surcharge_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Adult Surcharge',
                })

            if price_itinerary.get('single_supplement_amount'):
                service_charge.append({
                    'pax_type': 'ADT',
                    'charge_code': 'tax',
                    'charge_type': 'tax',
                    'amount': price_itinerary['single_supplement_price'] / price_itinerary['single_supplement_amount'],
                    'pax_count': price_itinerary['single_supplement_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Single Supplement',
                })

            if price_itinerary.get('tipping_guide_amount'):
                service_charge.append({
                    'pax_type': 'ADT',
                    'charge_code': 'tax',
                    'charge_type': 'tax',
                    'amount': price_itinerary['tipping_guide_total'] / price_itinerary['tipping_guide_amount'],
                    'pax_count': price_itinerary['tipping_guide_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Tipping Tour Guide',
                })

            if price_itinerary.get('tipping_tour_leader_amount'):
                service_charge.append({
                    'pax_type': 'ADT',
                    'charge_code': 'tax',
                    'charge_type': 'tax',
                    'amount': price_itinerary['tipping_tour_leader_total'] / price_itinerary['tipping_tour_leader_amount'],
                    'pax_count': price_itinerary['tipping_tour_leader_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Tipping Tour Leader',
                })

            if price_itinerary.get('tipping_driver_amount'):
                service_charge.append({
                    'pax_type': 'ADT',
                    'charge_code': 'tax',
                    'charge_type': 'tax',
                    'amount': price_itinerary['tipping_driver_total'] / price_itinerary['tipping_driver_amount'],
                    'pax_count': price_itinerary['tipping_driver_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Tipping Driver',
                })

            if price_itinerary.get('additional_charge_amount'):
                service_charge.append({
                    'pax_type': 'ADT',
                    'charge_code': 'tax',
                    'charge_type': 'tax',
                    'amount': price_itinerary['additional_charge_total'] / price_itinerary['additional_charge_amount'],
                    'pax_count': price_itinerary['additional_charge_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Additional Charge',
                })

            if price_itinerary.get('child_amount'):
                service_charge.append({
                    'pax_type': 'CHD',
                    'charge_code': 'fare',
                    'charge_type': 'fare',
                    'amount': price_itinerary['child_price'] / price_itinerary['child_amount'],
                    'pax_count': price_itinerary['child_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Child Price',
                })
                service_charge.append({
                    'pax_type': 'CHD',
                    'charge_code': 'tax',
                    'charge_type': 'tax',
                    'amount': price_itinerary['airport_tax_total'] / (price_itinerary['adult_amount'] + price_itinerary['child_amount'] + price_itinerary['infant_amount']),
                    'pax_count': price_itinerary['child_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Airport Tax',
                })

            if price_itinerary.get('child_surcharge_amount'):
                service_charge.append({
                    'pax_type': 'CHD',
                    'charge_code': 'tax',
                    'charge_type': 'tax',
                    'amount': price_itinerary['child_surcharge_price'] / price_itinerary['child_surcharge_amount'],
                    'pax_count': price_itinerary['child_surcharge_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Child Surcharge',
                })

            if price_itinerary.get('infant_amount'):
                service_charge.append({
                    'pax_type': 'INF',
                    'charge_code': 'fare',
                    'charge_type': 'fare',
                    'amount': price_itinerary['infant_price'] / price_itinerary['infant_amount'],
                    'pax_count': price_itinerary['infant_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Infant Price',
                })
                service_charge.append({
                    'pax_type': 'INF',
                    'charge_code': 'tax',
                    'charge_type': 'tax',
                    'amount': price_itinerary['airport_tax_total'] / (price_itinerary['adult_amount'] + price_itinerary['child_amount'] + price_itinerary['infant_amount']),
                    'pax_count': price_itinerary['infant_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Airport Tax',
                })

            if price_itinerary.get('commission_total'):
                service_charge.append({
                    'pax_type': 'ADT',
                    'charge_code': 'r.ac',
                    'charge_type': 'r.ac',
                    'amount': price_itinerary['commission_total'] * -1,
                    'pax_count': 1,
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Commission',
                })

            if price_itinerary.get('commission_total'):
                service_charge.append({
                    'pax_type': 'ADT',
                    'charge_code': 'r.oc',
                    'charge_type': 'r.oc',
                    'amount': price_itinerary['commission_total'],
                    'pax_count': 1,
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Commission',
                })

            if price_itinerary.get('discount_total_itinerary_price'):
                service_charge.append({
                    'pax_type': 'ADT',
                    'charge_code': 'disc',
                    'charge_type': 'disc',
                    'amount': price_itinerary['discount_total_itinerary_price'] * -1,
                    'pax_count': 1,
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Discount',
                })

            for rec in service_charge:
                sc_obj = self.env['tt.service.charge'].create(rec)

                if sc_obj:
                    service_charge_ids.append(sc_obj.id)

            booking_obj = self.env['tt.reservation.tour'].sudo().create({
                'contact_id': booker_id != 'false' and int(booker_id) or False,
                'passenger_ids': [(6, 0, pax_ids)],
                'tour_id': pricelist_id,
                'agent_id': 2,
                'line_ids': [(6, 0, book_line_ids)],
                'sale_service_charge_ids': [(6, 0, service_charge_ids)],
            })

            if booking_obj:
                booking_obj.action_confirm()
                booking_obj.action_booked_tour()

                if force_issued == 1:
                    booking_obj.write({
                        'payment_method': data.get('payment_method') and data['payment_method'] or 'cash'
                    })
                    booking_obj.action_issued()

                response = {
                    'booking_num': booking_obj.name
                }

            else:
                response = {
                    'booking_num': 0
                }
            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res

    def get_booking_api(self, data, context, **kwargs):
        try:
            search_booking_num = data.get('order_number')
            book_objs = self.env['tt.reservation.tour'].sudo().search([('name', '=', search_booking_num)])
            book_obj = book_objs[0]
            result = {
                'id': book_obj.id,
                'pnr': book_obj.pnr,
                'state': book_obj.state,
                'display_mobile': book_obj.display_mobile,
                'elder': book_obj.elder,
                'adult': book_obj.adult,
                'child': book_obj.child,
                'infant': book_obj.infant,
                'departure_date': book_obj.departure_date,
                'arrival_date': book_obj.arrival_date,
                'name': book_obj.name,
                'hold_date': book_obj.hold_date,
            }

            if book_obj.contact_id:
                contact_phone = self.env['phone.detail'].sudo().search([('customer_id', '=', book_obj.contact_id.id)])
                result.update({
                    'contact_first_name': book_obj.contact_id.first_name and book_obj.contact_id.first_name or '',
                    'contact_last_name': book_obj.contact_id.last_name and book_obj.contact_id.last_name or '',
                    'contact_title': book_obj.contact_id.title and book_obj.contact_id.title or '',
                    'contact_email': book_obj.contact_id.email and book_obj.contact_id.email or '',
                    'contact_phone': contact_phone[0].phone_number
                })

            tour_package = {
                'id': book_obj.tour_id.id,
                'name': book_obj.tour_id.name,
                'duration': book_obj.tour_id.duration,
                'departure_date': book_obj.tour_id.departure_date,
                'arrival_date': book_obj.tour_id.arrival_date,
                'departure_date_f': datetime.strptime(str(book_obj.tour_id.arrival_date), '%Y-%m-%d').strftime("%A, %d-%m-%Y") or '',
                'arrival_date_f': datetime.strptime(str(book_obj.tour_id.arrival_date), '%Y-%m-%d').strftime("%A, %d-%m-%Y") or '',
                'visa': book_obj.tour_id.visa,
                'flight': book_obj.tour_id.flight,
            }

            passengers = []
            rooms = []
            room_id_list = []
            for rec in book_obj.line_ids:
                passengers.append({
                    'pax_id': rec.passenger_id.id,
                    'first_name': rec.passenger_id.first_name and rec.passenger_id.first_name or '',
                    'last_name': rec.passenger_id.last_name and rec.passenger_id.last_name or '',
                    'title': rec.passenger_id.title and rec.passenger_id.title or '',
                    'pax_type': rec.pax_type,
                    'birth_date': rec.passenger_id.birth_date,
                    'room_id': rec.room_id.id,
                    'room_name': rec.room_id.name,
                    'room_bed_type': rec.room_id.bed_type,
                    'room_hotel': rec.room_id.hotel,
                    'room_number': rec.room_number,
                })

                if rec.room_id.id not in room_id_list:
                    room_id_list.append(rec.room_id.id)
                    rooms.append({
                        'room_number': rec.room_number,
                        'room_name': rec.room_id.name,
                        'room_bed_type': rec.room_id.bed_type,
                        'room_hotel': rec.room_id.hotel and rec.room_id.hotel or '-',
                        'room_notes': rec.description and rec.description or '-',
                    })

            price_itinerary = {
                'adult_amount': 0,
                'adult_price': 0,
                'adult_surcharge_amount': 0,
                'adult_surcharge_price': 0,
                'child_amount': 0,
                'child_price': 0,
                'child_surcharge_amount': 0,
                'child_surcharge_price': 0,
                'infant_amount': 0,
                'infant_price': 0,
                'single_supplement_amount': 0,
                'single_supplement_price': 0,
                'airport_tax_amount': 0,
                'airport_tax_total': 0,
                'tipping_guide_amount': 0,
                'tipping_guide_total': 0,
                'tipping_tour_leader_amount': 0,
                'tipping_tour_leader_total': 0,
                'additional_charge_amount': 0,
                'additional_charge_total': 0,
                'sub_total_itinerary_price': 0,
                'discount_total_itinerary_price': 0,
                'total_itinerary_price': 0,
                'commission_total': 0,
            }

            grand_total = 0
            for price in book_obj.sale_service_charge_ids:
                if price.description == 'Adult Price':
                    price_itinerary.update({
                        'adult_amount': price.pax_count,
                        'adult_price': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Airport Tax':
                    price_itinerary.update({
                        'airport_tax_amount': price.pax_count,
                        'airport_tax_total': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Adult Surcharge':
                    price_itinerary.update({
                        'adult_surcharge_amount': price.pax_count,
                        'adult_surcharge_price': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Single Supplement':
                    price_itinerary.update({
                        'single_supplement_amount': price.pax_count,
                        'single_supplement_price': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Tipping Tour Guide':
                    price_itinerary.update({
                        'tipping_guide_amount': price.pax_count,
                        'tipping_guide_total': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Tipping Tour Leader':
                    price_itinerary.update({
                        'tipping_tour_leader_amount': price.pax_count,
                        'tipping_tour_leader_total': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Additional Charge':
                    price_itinerary.update({
                        'additional_charge_amount': price.pax_count,
                        'additional_charge_total': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Child Price':
                    price_itinerary.update({
                        'child_amount': price.pax_count,
                        'child_price': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Child Surcharge':
                    price_itinerary.update({
                        'child_surcharge_amount': price.pax_count,
                        'child_surcharge_price': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Infant Price':
                    price_itinerary.update({
                        'infant_amount': price.pax_count,
                        'infant_price': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Commission' and price.charge_code == 'r.oc':
                    price_itinerary.update({
                        'commission_total': int(price.total),
                    })
                if price.description == 'Discount':
                    price_itinerary.update({
                        'discount_total_itinerary_price': int(price.total),
                    })
                    grand_total -= int(price.total)

            sub_total = grand_total + price_itinerary['discount_total_itinerary_price']

            price_itinerary.update({
                'total_itinerary_price': grand_total,
                'sub_total_itinerary_price': sub_total,
            })

            response = {
                'result': result,
                'tour_package': tour_package,
                'passengers': passengers,
                'rooms': rooms,
                'price_itinerary': price_itinerary,
            }
            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res

    def issued_by_api(self, data, context, **kwargs):
        try:
            search_booking_num = data.get('order_number')
            book_objs = self.env['tt.reservation.tour'].sudo().search([('name', '=', search_booking_num)])
            for book_obj in book_objs:
                book_obj.action_issued()

            response = {
                'order_number': book_objs[0].name,
            }
            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res

    def get_payment_rules_api(self, data, context, **kwargs):
        try:
            search_tour_id = data.get('id')
            payment_rules = []
            for payment in self.env['tt.reservation.tour.pricelist'].sudo().browse(int(search_tour_id)).payment_rules_ids:
                vals = {
                    'name': payment.name,
                    'description': payment.description,
                    'payment_percentage': payment.payment_percentage,
                    'due_date': payment.due_date,
                }
                payment_rules.append(vals)

            response = {
                'payment_rules': payment_rules
            }
            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res
