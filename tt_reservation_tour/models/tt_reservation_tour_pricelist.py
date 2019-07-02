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


class TourPricelist(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.reservation.tour.pricelist'
    _order = 'sequence'

    name = fields.Char('Name', required=True, default='Tour', size=40)
    description = fields.Text('Description')

    tour_code = fields.Char('Tour Code', readonly=True, copy=False)
    tour_route = fields.Selection([('international', 'International'), ('domestic', 'Domestic')],
                                  'Route', required=True, default='international')
    tour_category = fields.Selection([('group', 'Group (Series)'), ('fit', 'Land Tour (FIT)')],
                                     'Tour Category', required=True, default='group')
    tour_type = fields.Selection([('sic', 'SIC'), ('private', 'Private')], 'Tour Type', default='sic')

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
    airport_tax = fields.Monetary('Airport Tax Total', help="(/pax)", default=0)
    tipping_guide = fields.Monetary('Tipping Guide', help="(/pax /day)", default=0)
    tipping_tour_leader = fields.Monetary('Tipping Tour Leader', help="(/pax /day)", default=0)
    guiding_days = fields.Integer('Guiding Days', default=1)

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

    itinerary = fields.Html('Itinerary')
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
            if rec.tour_category == 'group':
                rec.tour_type = False
                rec.start_period = False
                rec.end_period = False
            if rec.tour_category == 'fit':
                if rec.tour_type == 'sic':
                    rec.start_period = False
                    rec.end_period = False
                elif rec.tour_type == 'private':
                    rec.departure_date = False
                    rec.arrival_date = False
                else:
                    rec.start_period = False
                    rec.end_period = False
                    rec.departure_date = False
                    rec.arrival_date = False

    def action_validate(self):
        self.state_tour = 'open'
        self.create_uid = self.env.user.id
        if self.tour_category == 'group':
            self.tour_code = self.env['ir.sequence'].next_by_code('tour.pricelist.code.group')
        elif self.tour_category == 'fit':
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
                adult_sale += rec.retail_price_exclude + rec.rupiah_tipping_driver + rec.visa
                adult_citra += rec.retail_price_exclude + rec.rupiah_tipping_driver + rec.visa - rec.service_charge
                adult_citra_real += rec.retail_price_include - rec.service_charge
                adult_sale_real += rec.retail_price_include
            elif rec.pax_type == 'chd':
                child_nta += rec.total_exclude
                child_sale += rec.retail_price_exclude + rec.rupiah_tipping_driver + rec.visa
                child_citra += rec.retail_price_exclude + rec.rupiah_tipping_driver + rec.visa - rec.service_charge
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
                'country_id': data['country_id'] and data['country_id'] or '0',
                'departure_month': data['month'] and data['month'] or '00',
                'departure_year': data['year'] and data['year'] or '0000',
                'budget_min': data['budget_min'] and data['budget_min'] or 0,
                'budget_max': data['budget_max'] and data['budget_max'] or 0,
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

            if search_request['country_id'] != '0':
                self.env.cr.execute("""SELECT * FROM tt_reservation_tour_pricelist tp LEFT JOIN tour_country_rel tcr ON tp.id = tcr.pricelist_id WHERE tp.state_tour IN ('open', 'definite', 'sold') AND tcr.country_id =%s AND tp.adult_sale_price BETWEEN %s AND %s ORDER BY sequence DESC;""", (search_request['country_id'], search_request['budget_min'], search_request['budget_max']))
            else:
                self.env.cr.execute("""SELECT * FROM tt_reservation_tour_pricelist WHERE state_tour IN ('open', 'definite', 'sold') AND adult_sale_price BETWEEN %s AND %s ORDER BY sequence DESC;""", (search_request['budget_min'], search_request['budget_max']))

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
                    'images_obj': images,
                    'departure_date_f': rec['departure_date'] and datetime.strptime(str(rec['departure_date']), '%Y-%m-%d').strftime("%A, %d-%m-%Y") or '',
                    'arrival_date_f': rec['arrival_date'] and datetime.strptime(str(rec['arrival_date']), '%Y-%m-%d').strftime("%A, %d-%m-%Y") or '',
                    'start_period_f': rec['start_period'] and datetime.strptime(str(rec['start_period']), '%Y-%m-%d').strftime('%B') or '',
                    'end_period_f': rec['end_period'] and datetime.strptime(str(rec['end_period']), '%Y-%m-%d').strftime('%B') or '',
                    'departure_date': rec['departure_date'] and datetime.strptime(str(rec['departure_date']), '%Y-%m-%d').strftime('%d %b') or '',
                    'arrival_date': rec['arrival_date'] and datetime.strptime(str(rec['arrival_date']), '%Y-%m-%d').strftime('%d %b') or '',
                    'start_period': rec['start_period'] and datetime.strptime(str(rec['start_period']), '%Y-%m-%d').strftime('%B') or '',
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
                    'discount': json.dumps(discount),
                    'departure_date_f': rec['departure_date'] and datetime.strptime(str(rec['departure_date']), '%Y-%m-%d').strftime("%A, %d-%m-%Y") or '',
                    'arrival_date_f': rec['arrival_date'] and datetime.strptime(str(rec['arrival_date']), '%Y-%m-%d').strftime("%A, %d-%m-%Y") or '',
                    'start_period_f': rec['start_period'] and datetime.strptime(str(rec['start_period']), '%Y-%m-%d').strftime('%B') or '',
                    'end_period_f': rec['end_period'] and datetime.strptime(str(rec['end_period']), '%Y-%m-%d').strftime('%B') or '',
                    'country_names': country_names,
                    # 'flight':
                    'flight_segment_ids': self.get_flight_segment(search_request['id']),
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
            if not sameBooker and not booker_id:
                if not self.check_pax_similarity(booker_obj):
                    cust_obj = self.env['tt.customer'].create({
                        'title': booker_obj.get('title'),
                        'first_name': booker_obj.get('first_name'),
                        'last_name': booker_obj.get('last_name'),
                        'email': booker_obj.get('email'),
                        'agent_id': booker_obj.get('agent_id'),
                    })
                    if booker_obj.get('mobile'):
                        self.env['phone.detail'].create({
                            'customer_id': cust_obj.id,
                            'type': 'work',
                            'name': 'Work',
                            'phone_number': booker_obj['mobile'],
                        })

            elif booker_id and not sameBooker:
                temp_booker = self.env['tt.customer'].browse(int(booker_id))
                temp_booker.update({
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
                        self.env['phone.detail'].create({
                            'customer_id': int(booker_id),
                            'type': 'work',
                            'name': 'Work',
                            'phone_number': booker_obj['mobile'],
                        })

            for rec in data['booking_data']['all_pax']:
                if not rec.get('passenger_id'):
                    if not self.check_pax_similarity(rec):
                        cust_obj = self.env['tt.customer'].create({
                            'title': rec.get('title'),
                            'first_name': rec.get('first_name'),
                            'last_name': rec.get('last_name'),
                            'email': rec.get('email'),
                            'agent_id': rec.get('agent_id'),
                            'birth_date': rec.get('birth_date_f'),
                            'passport_number': rec.get('passport_number'),
                            'passport_exp_date': rec.get('passport_expdate_f'),
                        })
                        if rec.get('mobile'):
                            self.env['phone.detail'].create({
                                'customer_id': cust_obj.id,
                                'type': 'work',
                                'name': 'Work',
                                'phone_number': rec['mobile'],
                            })
                else:
                    temp = self.env['tt.customer'].browse(int(rec['passenger_id']))
                    temp.update({
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
                            self.env['phone.detail'].create({
                                'customer_id': int(rec['passenger_id']),
                                'type': 'work',
                                'name': 'Work',
                                'phone_number': rec['mobile'],
                            })

            response = {

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
            return True
        else:
            return False

    def commit_booking_api(self, data, context, **kwargs):
        try:
            response = {

            }
            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res

    def get_booking_api(self, data, context, **kwargs):
        try:
            response = {

            }
            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res

    def issued_by_api(self):
        try:
            response = {

            }
            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res
