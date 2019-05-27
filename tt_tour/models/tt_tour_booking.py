from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
import logging, traceback
# from ...tools.telegram import TelegramInfoNotification
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError

# from Ap
_logger = logging.getLogger(__name__)

STATE = [
    ('booked', 'Booked'),
    ('issued', 'Issued'),
    ('confirm', 'Confirm To HO'),
    ('confirmed', 'Confirm'),
    ('process', 'In Process'),
    ('rejected', 'Rejected'),
    ('cancelled', 'Cancelled'),
    ('expired', 'Expired'),
    ('done', 'Done')
]


class TransportBookTour(models.Model):
    _inherit = 'tt.history'
    _name = 'tt.tour.booking'
    _order = 'id DESC'

    name = fields.Char('Name', required=True, default='New')
    hold_date = fields.Datetime('Booking Time Limit')

    booked_date = fields.Datetime('Booked Date', readonly=1)
    booked_uid = fields.Many2one('res.users', 'Booked By', readonly=1)

    issued_date = fields.Datetime('Issued Date', readonly=1)
    issued_uid = fields.Many2one('res.users', 'Issued By', readonly=1)

    confirm_date = fields.Datetime('Confirm Date', readonly=1, help='Agent Confirm Date')
    confirm_uid = fields.Many2one('res.users', 'Confirm By', readonly=1)

    confirmed_date = fields.Datetime('HO Confirmed Date', readonly=1, help='HO Confirm Date')
    confirmed_uid = fields.Many2one('res.users', 'Confirmed By', readonly=1)

    process_date = fields.Datetime('Process Date', readonly=1)
    process_uid = fields.Many2one('res.users', 'Process By', readonly=1)

    cancelled_date = fields.Datetime('Cancelled Date', readonly=1)
    cancelled_uid = fields.Many2one('res.users', 'Cancelled By', readonly=1)

    rejected_date = fields.Datetime('Rejected Date', readonly=1)
    rejected_uid = fields.Many2one('res.users', 'Rejected By', readonly=1)

    expired_date = fields.Datetime('Expired Date', readonly=1)

    tour_id = fields.Many2one('tt.tour.pricelist', 'Tour ID')
    agent_id = fields.Many2one('tt.agent', 'Agent')
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type',
                                    # related='agent_id.agent_type_id',
                                    store=True)
    sub_agent_id = fields.Many2one('tt.customer', 'Sub-Agent', help='COR / POR')
    sub_agent_type_id = fields.Many2one('tt.agent.type', 'Sub Agent Type',
                                        # related='sub_agent_id.agent_type_id',
                                        store=True, readonly=True)

    contact_id = fields.Many2one('tt.customer.details', 'Contact Person')
    display_mobile = fields.Char('Contact Person for Urgent Situation',
                                 readonly=True, states={'draft': [('readonly', False)]})
    user_id = fields.Many2one('res.users', 'User')

    departure_date = fields.Date('Departure Date')
    arrival_date = fields.Date('Arrival Date')

    line_ids = fields.One2many('tt.tour.booking.line', 'tour_booking_id', string='Line')
    sale_service_charge_ids = fields.One2many('tt.tour.booking.price', 'tour_booking_id', string='Prices')
    installment_ids = fields.One2many('tt.installment.invoice', 'tour_transaction_id', string='Installment')
    # ledger_ids = fields.One2many('tt.ledger', 'tour_booking_id', string='Ledger')
    ledger_ids = fields.Char('Ledger')
    next_installment_date = fields.Date('Next Due Date', compute='_next_installment_date', store=True)
    is_trouble = fields.Boolean('Is Trouble', default=False)

    grand_total = fields.Monetary('Grand Total', compute='_calc_grand_total', store=True)
    total_fare = fields.Monetary('Total Fare', compute='_calc_grand_total', store=True)
    total_tax = fields.Monetary('Total Tax', compute='_calc_grand_total', store=True)
    total_disc = fields.Monetary('Total Discount', compute='_calc_grand_total', store=True)
    total_commission = fields.Monetary('Total Commission', compute='_calc_grand_total', store=True)
    nta_amount = fields.Monetary('NTA Amount', compute='_calc_grand_total', store=True)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)

    state = fields.Selection(STATE, help='''booked = hold booking
                issued = issued
                confirm = confirmed to HO
                confirmed = confirmed / accepted by HO
                process = in process (payment period)
                rejected = rejected by HO
                cancelled = cancelled by pax
                expired = cancelled because payment trouble / hold booking expired
                done = paid''')

    def calc_next_installment_date(self):
        self._next_installment_date()

    @api.onchange('installment_ids')
    def _next_installment_date(self):
        for rec in self:
            ids = rec.installment_ids.filtered(lambda x: datetime.strptime(x.due_date, '%Y-%m-%d').date() > date.today())
            rec.sudo().next_installment_date = ids and ids[0].due_date or False

    def _calc_grand_total(self):
        for rec in self:
            rec.grand_total = 0
            rec.total_tax = 0
            rec.total_disc = 0
            rec.total_commission = 0

            for line in rec.sale_service_charge_ids:
                if line.charge_code == 'fare':
                    rec.total_fare += line.total
                if line.charge_code == 'tax':
                    rec.total_tax += line.total
                if line.charge_code == 'disc':
                    rec.total_disc += line.total
                if line.charge_code == 'r.oc':
                    rec.total_commission += line.total

            rec.grand_total = rec.total_fare + rec.total_tax + rec.total_disc
            rec.nta_amount = rec.grand_total - rec.total_commission

    @api.multi
    def message_post(self, message_type='notification', subtype=None, **kwargs):
        pass
        # question_followers = self.env['res.partner']
        # if self.ids and message_type == 'comment':  # user comments have a restriction on karma
        #     # add followers of comments on the parent post
        #     if self.parent_id:
        #         partner_ids = kwargs.get('partner_ids', [])
        #         comment_subtype = self.sudo().env.ref('mail.mt_comment')
        #         question_followers = self.env['mail.followers'].sudo().search([
        #             ('res_model', '=', self._name),
        #             ('res_id', '=', self.parent_id.id),
        #             ('partner_id', '!=', False),
        #         ]).filtered(lambda fol: comment_subtype in fol.subtype_ids).mapped('partner_id')
        #         partner_ids += [(4, partner.id) for partner in question_followers]
        #         kwargs['partner_ids'] = partner_ids
        #
        #     self.ensure_one()
        #     if not kwargs.get('record_name') and self.parent_id:
        #         kwargs['record_name'] = self.parent_id.name
        # return super(TransportBookTour, self).message_post(message_type=message_type, subtype=subtype, **kwargs)

    @api.model
    def create(self, vals):
        new = super(TransportBookTour, self.with_context(mail_create_nolog=True)).create(vals)
        new.message_post(body='Order CREATED')
        return new

    def action_booked(self):
        self.write({
            'state': 'booked',
            'booked_date': datetime.now(),
            'booked_uid': self.env.user.id,
            'hold_date': datetime.now() + relativedelta(days=1),
        })
        self.message_post(body='Order BOOKED')

    def action_issued(self):
        self.write({
            'state': 'issued',
            'issued_date': datetime.now(),
            'issued_uid': self.env.user.id
        })
        self.message_post(body='Order ISSUED')

    def action_reissued(self):
        pax_amount = sum(1 for temp in self.line_ids if temp.pax_type != 'INF')
        if (self.tour_id.seat - pax_amount) >= 0:
            self.tour_id.seat -= pax_amount
            self.write({
                'state': 'issued',
                'issued_date': datetime.now(),
                'issued_uid': self.env.user.id
            })
            self.message_post(body='Order REISSUED')
        else:
            raise UserError(
                _('Cannot reissued because there is not enough seat quota.'))

    def action_confirm_to_ho(self):
        self.write({
            'state': 'confirm',
            'confirm_date': datetime.now(),
            'confirm_uid': self.env.user.id
        })
        self.message_post(body='Order CONFIRM TO HO')

    def action_confirmed(self):
        self.write({
            'state': 'confirmed',
            'confirmed_date': datetime.now(),
            'confirmed_uid': self.env.user.id
        })
        self.message_post(body='Order CONFIRMED')
        if self.installment_ids[-1].state_invoice == 'done':
            self.action_done()

    def action_process(self):
        self.write({
            'state': 'process',
            'process_date': datetime.now(),
            'process_uid': self.env.user.id
        })
        self.message_post(body='Order IN PROCESS')

    def action_rejected(self):
        counter = 1
        self.write({
            'state': 'rejected',
            'rejected_date': datetime.now(),
            'rejected_uid': self.env.user.id
        })
        self.message_post(body='Order REJECTED')
        pax_amount = sum(1 for temp in self.line_ids if temp.pax_type != 'INF')
        self.tour_id.seat += pax_amount
        if self.tour_id.seat > self.tour_id.quota:
            self.tour_id.seat = self.tour_id.quota
        self.tour_id.state_tour = 'open'
        # for rec in self.tour_id.passengers_ids.filtered(lambda x: x.tour_booking_id.id == self.id):
        for rec in self.tour_id.passengers_ids:
            if rec.tour_booking_id.id == self.id:
                rec.sudo().pricelist_id = False

        for rec in self.installment_ids:
            counter = rec.action_cancel(counter)

    def action_cancelled(self):
        counter = 1
        self.write({
            'state': 'cancelled',
            'cancelled_date': datetime.now(),
            'cancelled_uid': self.env.user.id
        })
        self.message_post(body='Order CANCELLED')
        pax_amount = sum(1 for temp in self.line_ids if temp.pax_type != 'INF')
        self.tour_id.seat += pax_amount
        if self.tour_id.seat > self.tour_id.quota:
            self.tour_id.seat = self.tour_id.quota
        self.tour_id.state_tour = 'open'

        for rec in self.tour_id.passengers_ids:
            if rec.tour_booking_id.id == self.id:
                rec.sudo().pricelist_id = False

        for rec in self.installment_ids:
            counter = rec.action_cancel(counter)

    def action_expired(self):
        self.write({
            'state': 'expired',
            'expired_date': datetime.now()
        })
        self.message_post(body='Order EXPIRED')
        pax_amount = sum(1 for temp in self.line_ids if temp.pax_type != 'INF')
        self.tour_id.seat += pax_amount
        if self.tour_id.seat > self.tour_id.quota:
            self.tour_id.seat = self.tour_id.quota
        self.tour_id.state_tour = 'open'

    def action_done(self):
        self.write({
            'state': 'done',
        })
        self.message_post(body='Order DONE')

    #######################################################################################################
    #######################################################################################################

    def send_push_notif(self, type):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        obj_id = str(self.id)
        model = 'tt.tour.booking'
        url = base_url + '/web#id=' + obj_id + '&view_type=form&model=' + model
        if type == 'issued':
            desc = 'Tour Issued ' + self.name + ' From ' + self.agent_id.name
        else:
            desc = 'Tour Booking ' + self.name + ' From ' + self.agent_id.name
        # Vanesa 20/04
        data = {
            'main_title': 'Tour',
            'message': desc,
            'notes': url
        }
        # tele = TelegramInfoNotification(data)
        # tele.send_message()
        # tele.send_message('tour')
        # End

    def cron_tour_set_expired(self):
        self.send_notif_tour_3_days()
        self.send_notif_tour_due()
        # self.send_notif_tour_overdue()
        try:
            recs = self.env['tt.tour.pricelist'].search([('departure_date', '<=', str(datetime.today() + relativedelta(days=7))), ('state_tour', 'not in', ['draft', 'done', 'closed', 'cancelled'])])
            message = ''
            number = 1
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            model = 'tt.tour.booking'
            for rec in self.search([('tour_id', 'in', recs.ids)]):
                if rec.installment_ids:
                    if rec.installment_ids[-1].state_invoice != 'done':
                        rec.action_expired()
                        obj_id = str(rec.id)
                        url = base_url + '/web#id=' + obj_id + '&view_type=form&model=' + model
                        name = '<a href="{}">{}</a>'.format(url, rec.name)
                        message += "{}. {}\nName : {}\nExpired Date : {}\n".format(number, name, rec.tour_id.name, datetime.strptime(str(rec.expired_date)[:10], '%Y-%m-%d').strftime('%d-%b-%Y'))
                        number += 1
            data = {
                'main_title': 'Tour Payment Expired',
                'message': message,
            }
            # tele = TelegramInfoNotification(data)
            # tele.send_message()
            # tele.send_message('tour')
        except Exception as e:
            _logger.error('Cron Error: Active Tour Booking Expired' + '\n' + traceback.format_exc())

        try:
            objs = self.env['tt.tour.booking'].search([('hold_date', '<', fields.Datetime.now()), ('state', '=', 'booked')])
            for rec in objs:
                rec.action_expired()
        except Exception as e:
            _logger.error('Cron Error: Active Tour Hold Booking Expired' + '\n' + traceback.format_exc())


    def send_notif_tour_3_days(self):
        message = ''
        objs = self.env['tt.tour.booking'].search([('next_installment_date', '>=', fields.Date.context_today(self)), ('next_installment_date', '<=', datetime.strptime(fields.Date.context_today(self), '%Y-%m-%d') + timedelta(days=3)), ('state', '=', 'process')])
        number = 1
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        model = 'tt.tour.booking'
        for rec in objs:
            obj_id = str(rec.id)
            url = base_url + '/web#id=' + obj_id + '&view_type=form&model=' + model
            name = '<a href="{}">{}</a>'.format(url, rec.name)
            message += "{}. {}\nName : {}\nDue Date : {}\n".format(number, name, rec.tour_id.name, datetime.strptime(rec.next_installment_date, '%Y-%m-%d').strftime('%d-%b-%Y'))
            number += 1
        data = {
            'main_title': 'Tour Next Due Date in 3 Days',
            'message': message,
        }
        # tele = TelegramInfoNotification(data)
        # tele.send_message()
        # tele.send_message('tour')

    def send_notif_tour_due(self):
        message = ''
        objs = self.env['tt.tour.booking'].search([('next_installment_date', '=', fields.Date.context_today(self)), ('state', '=', 'process')])
        number = 1
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        model = 'tt.tour.booking'
        for rec in objs:
            obj_id = str(rec.id)
            url = base_url + '/web#id=' + obj_id + '&view_type=form&model=' + model
            name = '<a href="{}">{}</a>'.format(url, rec.name)
            message += "{}. {}\nName : {}\nDue Date : {}\n".format(number, name, rec.tour_id.name,
                                                                   datetime.strptime(rec.next_installment_date,
                                                                                     '%Y-%m-%d').strftime('%d-%b-%Y'))
            number += 1
        data = {
            'main_title': 'Tour Due',
            'message': message,
        }
        # tele = TelegramInfoNotification(data)
        # tele.send_message()
        # tele.send_message('tour')

    def send_notif_tour_overdue(self):
        message = ''
        objs = self.env['tt.tour.booking'].search([('next_installment_date', '<', fields.Date.context_today(self)), ('state', '=', 'process')])
        number = 1
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        model = 'tt.tour.booking'
        for rec in objs:
            obj_id = str(rec.id)
            url = base_url + '/web#id=' + obj_id + '&view_type=form&model=' + model
            name = '<a href="{}">{}</a>'.format(url, rec.name)
            message += "{}. {}\nName : {}\nDue Date : {}\n".format(number, name, rec.tour_id.name,
                                                                   datetime.strptime(rec.next_installment_date,
                                                                                     '%Y-%m-%d').strftime('%d-%b-%Y'))
            number += 1
        data = {
            'main_title': 'Tour Overdue',
            'message': message,
        }
        # tele = TelegramInfoNotification(data)
        # tele.send_message()
        # tele.send_message('tour')

    def _validate_tour(self, data, type):
        list_data = []
        if type == 'context':
            list_data = ['co_uid', 'is_company_website']
        elif type == 'header':
            list_data = ['adult', 'child', 'infant']

        keys_data = []
        for rec in data.iterkeys():
            keys_data.append(str(rec))

        for ls in list_data:
            if not ls in keys_data:
                raise Exception('ERROR Validate %s, key : %s' % (type, ls))
        return True

    def _tour_header_normalization(self, data):
        res = {}
        int_key_att = ['adult', 'child', 'infant']
        #
        # for rec in str_key_att:
        #     res.update({
        #         rec: data[rec]
        #     })

        for rec in int_key_att:
            res.update({
                rec: int(data[rec])
            })

        return res


    def update_api_context(self, sub_agent_id, context):
        context['co_uid'] = int(context['co_uid'])
        user_obj = self.env['res.users'].sudo().browse(context['co_uid'])
        if context['is_company_website']:
            #============================================
            #====== Context dari WEBSITE/FRONTEND =======
            #============================================
            if user_obj.agent_id.agent_type_id.id in \
                    (self.env.ref('tt_base_rodex.agent_type_cor').id, self.env.ref('tt_base_rodex.agent_type_por').id):
                # ===== COR/POR User =====
                context.update({
                    'agent_id': user_obj.agent_id.parent_agent_id.id,
                    'sub_agent_id': user_obj.agent_id.id,
                    'booker_type': 'COR/POR',
                })
            elif sub_agent_id:
                # ===== COR/POR in Contact =====
                context.update({
                    'agent_id': user_obj.agent_id.id,
                    'sub_agent_id': sub_agent_id,
                    'booker_type': 'COR/POR',
                })
            else:
                # ===== FPO in Contact =====
                context.update({
                    'agent_id': user_obj.agent_id.id,
                    'sub_agent_id': user_obj.agent_id.id,
                    'booker_type': 'FPO',
                })
        else:
            # ===============================================
            # ====== Context dari API Client ( BTBO ) =======
            # ===============================================
            context.update({
                'agent_id': user_obj.agent_id.id,
                'sub_agent_id': user_obj.agent_id.id,
                'booker_type': 'FPO',
            })
        return context

    def _create_contact(self, vals, context):
        country_obj = self.env['res.country'].sudo()
        contact_obj = self.env['tt.customer.details'].sudo()
        if vals.get('contact_id'):
            vals['contact_id'] = int(vals['contact_id'])
            contact_rec = contact_obj.browse(vals['contact_id'])
            if contact_rec:
                contact_rec.update({
                    'email': vals.get('email', contact_rec.email),
                    'mobile': vals.get('mobile', contact_rec.mobile),
                })
            return contact_rec

        country = country_obj.search([('code', '=', vals.pop('nationality_code'))])
        vals['nationality_id'] = country and country[0].id or False

        if context['booker_type'] == 'COR/POR':
            vals['passenger_on_partner_ids'] = [(4, context['sub_agent_id'])]

        country = False
        if vals.get('country_code'):
            country = country_obj.search([('code', '=', vals.pop('country_code'))])
        vals.update({
            'commercial_agent_id': context['agent_id'],
            'agent_id': context['agent_id'],
            'country_id': country and country[0].id or False,
            'pax_type': 'ADT',
            'bill_to': '<span><b>{title} {first_name} {last_name}</b> <br>Phone: {mobile}</span>'.format(**vals),
            'mobile_orig': vals.get('mobile', ''),
            'email': vals.get('email', vals['email']),
            'mobile': vals.get('mobile', vals['mobile']),
        })
        return contact_obj.sudo().create(vals)

    def issued_booking(self, service_charge_summary, tour_data, context, kwargs):
        book_obj = self.sudo().browse(context['order_id'])
        book_obj.sudo().action_issued_tour(service_charge_summary, tour_data, kwargs, context)
        book_obj.sudo().calc_next_installment_date()
        self.env.cr.commit()
        return {
            'error_code': 0,
            'error_msg': 'Success',
            'response': {
                'order_id': book_obj.id,
                'order_number': book_obj.name,
                'status': book_obj.state,
            }
        }

    def create_booking(self, contact_data, passengers, service_charge_summary, tour_data, search_request, context, kwargs):
        try:
            self._validate_tour(context, 'context')
            self._validate_tour(search_request, 'header')
            context = self.update_api_context(int(contact_data.get('agent_id')), context)

            # ========= Validasi agent_id ===========
            # TODO : Security Issue VERY HIGH LEVEL
            # 1. Jika BUKAN is_company_website, maka contact.contact_id DIABAIKAN
            # 2. Jika ADA contact.contact_id MAKA agent_id = contact.contact_id.agent_id
            # 3. Jika TIDAK ADA contact.contact_id MAKA agent_id = co_uid.agent_id

            # PRODUCTION
            # self.validate_booking(api_context=context)
            user_obj = self.env['res.users'].sudo().browse(int(context['co_uid']))
            contact_data.update({
                'agent_id': user_obj.agent_id.id,
                'commercial_agent_id': user_obj.agent_id.id,
                'booker_type': 'FPO',
                'display_mobile': user_obj.mobile,
            })
            if user_obj.agent_id.agent_type_id.id in (
                    self.env.ref('tt_base_rodex.agent_type_cor').id, self.env.ref('tt_base_rodex.agent_type_por').id):
                if user_obj.agent_id.parent_agent_id:
                    contact_data.update({
                        'commercial_agent_id': user_obj.agent_id.parent_agent_id.id,
                        'booker_type': 'COR/POR',
                        'display_mobile': user_obj.mobile,
                    })

            # header_val = self._prepare_booking(journeys_booking, tour_data, search_request, context, kwargs)
            header_val = self._tour_header_normalization(search_request)
            contact_obj = self._create_contact(contact_data, context)

            psg_ids = self._evaluate_passenger_info(passengers, contact_obj.id, context['agent_id'])

            header_val.update({
                'contact_id': contact_obj.id,
                'state': 'booked',
                'agent_id': context['agent_id'],
                'user_id': context['co_uid'],
                'tour_id': tour_data['id'],
                'departure_date': search_request['tour_departure_date'],
                'arrival_date': search_request['tour_arrival_date'],
            })

            # create header & Update SUB_AGENT_ID
            book_obj = self.sudo().create(header_val)

            for psg in passengers:
                # if psg['room_number'].is_integer():
                is_int = isinstance(psg['room_number'], int)
                if is_int:
                    room_number = psg['room_number'] + 1
                    room_index = psg['room_number']
                else:
                    room_number = int(psg['room_number'][5:])
                    room_index = room_number - 1
                vals = {
                    'tour_booking_id': book_obj.id,
                    'passenger_id': psg['passenger_id'],
                    'pax_type': psg['pax_type'],
                    'pax_mobile': psg.get('mobile'),
                    'room_number': 'Room ' + str(room_number),
                    'extra_bed_description': context['room_data'][room_index]['description'],
                    'room_id': psg['room_id'],
                    'description': context['room_data'][room_index]['notes'],
                    'pricelist_id': book_obj.tour_id.id
                }
                self.env['tt.tour.booking.line'].sudo().create(vals)

            for rec in service_charge_summary:
                rec.update({
                    'tour_booking_id': book_obj.id,
                })
                self.env['tt.tour.booking.price'].sudo().create(rec)
            self._calc_grand_total()

            book_obj.sub_agent_id = contact_data['agent_id']

            book_obj.action_booked_tour(context)
            context['order_id'] = book_obj.id
            if kwargs.get('force_issued'):
                book_obj.action_issued_tour(service_charge_summary, tour_data, kwargs, context)
                book_obj.calc_next_installment_date()

            # self._create_passengers(passengers, book_obj, contact_obj.id, context)

            self.env.cr.commit()
            return {
                'error_code': 0,
                'error_msg': 'Success',
                'response': {
                    'order_id': book_obj.id,
                    'order_number': book_obj.name,
                    'status': book_obj.state,
                }
            }
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            return {
                'error_code': 1,
                'error_msg': str(e)
            }

    def _evaluate_passenger_info(self, passengers, contact_id, agent_id):
        res = []
        country_obj = self.env['res.country'].sudo()
        psg_obj = self.env['tt.customer.details'].sudo()
        for psg in passengers:
            p_id = psg.get('passenger_id')
            if p_id:
                p_object = psg_obj.browse(int(p_id))
                if p_object:
                    res.append(int(p_id))
                    if psg.get('passport_number'):
                        p_object['passport_number'] = psg['passport_number']
                    if psg.get('passport_expdate'):
                        p_object['passport_expdate'] = psg['passport_expdate']
                    if psg.get('country_of_issued_id'):
                        p_object['country_of_issued_id'] = psg['country_of_issued_id']
                    p_object.write({
                        'domicile': psg.get('domicile'),
                        'mobile': psg.get('mobile')
                    })
            else:
                country = country_obj.search([('code', '=', psg.pop('nationality_code'))])
                psg['nationality_id'] = country and country[0].id or False
                if psg.get('country_of_issued_code'):
                    country = country_obj.search([('code', '=', psg.pop('country_of_issued_code'))])
                    psg['country_of_issued_id'] = country and country[0].id or False
                if not psg.get('passport_expdate'):
                    psg.pop('passport_expdate')

                psg.update({
                    'contact_id': contact_id,
                    'passenger_id': False,
                    'agent_id': agent_id
                })
                psg_res = psg_obj.sudo().create(psg)
                psg.update({
                    'passenger_id': psg_res.id,
                })
                res.append(psg_res.id)
        return res

    def _get_pricelist_ids(self, service_charge_summary):
        res = []
        for rec in service_charge_summary:
            res.append(rec['pricelist_id'])
        return res

    def action_booked_tour(self, api_context=None):
        if not api_context:  # Jika dari call from backend
            api_context = {
                'co_uid': self.env.user.id
            }
        vals = {}
        if self.name == 'New':
            vals.update({
                'name': self.env['ir.sequence'].next_by_code('transport.booking.tour'),
                'state': 'partial_booked',
            })

        vals.update({
            'state': 'booked',
            'booked_uid': api_context and api_context['co_uid'],
            'booked_date': datetime.now(),
            'hold_date': datetime.now() + relativedelta(days=1),
        })
        self.write(vals)

        pax_amount = sum(1 for temp in self.line_ids if temp.pax_type != 'INF')
        self.tour_id.seat -= pax_amount
        # definite 80%
        if self.tour_id.seat <= int(0.2 * self.tour_id.quota):
            self.tour_id.state_tour = 'definite'
        if self.tour_id.seat == 0:
            self.tour_id.state_tour = 'sold'
        self.send_push_notif('booked')

    @api.one
    def action_issued_tour(self, service_charge_summary, tour_data, kwargs, api_context=None):
        if not api_context:  # Jika dari call from backend
            api_context = {
                'co_uid': self.env.user.id
            }
        if not api_context.get('co_uid'):
            api_context.update({
                'co_uid': self.env.user.id
            })

        vals = {}

        # if self.name == 'New':
        #     vals.update({
        #         'name': self.env['ir.sequence'].next_by_code('transport.booking.tour'),
        #         'state': 'partial_booked',
        #     })

        # self._validate_issue(api_context=api_context)
        if kwargs['payment_opt'] == 'installment':
            is_enough = self.env['res.partner'].check_balance_limit(self.sub_agent_id.id, api_context['payment_rules'][0]['amount'])
        else:
            is_enough = self.env['res.partner'].check_balance_limit(self.sub_agent_id.id, kwargs['payment_amount'])

        if is_enough['error_code'] != 0:
            raise UserError(_("Balance not enough!"))

        vals.update({
            'state': 'issued',
            'issued_uid': api_context['co_uid'],
            'issued_date': datetime.now(),
        })
        self.sudo().write(vals)

        # TODO create tt installment invoice
        if kwargs['payment_opt'] == 'installment':
            # for rec in self.tour_id.payment_rules_ids:
            for rec in api_context['payment_rules']:
                if self.tour_id.departure_date:
                    desc = rec['name'] + ' ' + self.tour_id.name + '\n' + self.tour_id.departure_date + ' | ' + self.tour_id.arrival_date
                elif self.tour_id.start_period:
                    desc = rec['name'] + ' ' + self.tour_id.name + '\n' + self.tour_id.start_period + ' | ' + self.tour_id.end_period
                else:
                    desc = rec['name'] + ' ' + self.tour_id.name
                desc += '\nAn. '
                for line in self.line_ids:
                    desc += line.passenger_id.title + ' ' + line.passenger_id.first_name + ' ' + line.passenger_id.last_name + '\n'

                self.env['tt.installment.invoice'].sudo().create({
                    'currency_id': self.sudo().env.user.company_id.currency_id.id,
                    'amount': rec['amount'],
                    'due_date': rec['due_date'],
                    'tour_transaction_id': self.id,
                    'description': desc
                })

            for obj in self.installment_ids:
                if obj.due_date == str(date.today()):
                    is_enough = self.env['res.partner'].check_balance_limit(self.sub_agent_id.id, obj.amount)
                    if is_enough['error_code'] == 0:
                        obj.action_confirm()
                    else:
                        obj.state_invoice = 'trouble'
                        obj.tour_transaction_id.is_trouble = True
        else:
            if self.tour_id.departure_date:
                desc = 'Full Payment ' + self.tour_id.name + '\n' + self.tour_id.departure_date + ' | ' + self.tour_id.arrival_date
            elif self.tour_id.start_period:
                desc = 'Full Payment ' + self.tour_id.name + '\n' + self.tour_id.start_period + ' | ' + self.tour_id.end_period
            else:
                desc = 'Full Payment ' + self.tour_id.name
            desc += '\nAn. '
            for line in self.line_ids:
                desc += line.passenger_id.title + ' ' + line.passenger_id.first_name + ' ' + line.passenger_id.last_name + '\n'

            obj = self.env['tt.installment.invoice'].sudo().create({
                'currency_id': self.sudo().env.user.company_id.currency_id.id,
                'amount': kwargs['payment_amount'],
                'due_date': date.today(),
                'tour_transaction_id': self.id,
                'description': desc
            })
            obj.action_confirm()
        self.send_push_notif('issued')

    def get_id(self, booking_number):
        row = self.env['tt.tour.booking'].search([('name', '=', booking_number)])
        if not row:
            return ''
        return row.id

    def get_booking_tour(self, booking_number=None, booking_id=None, api_context=None):
        if booking_number:
            booking_id = self.sudo().get_id(booking_number)

        if not booking_id:
            return {
                'error_code': 200,
                'error_msg': 'Invalid booking number %s or agent id' % booking_number
            }

        book_obj = self.sudo().browse(booking_id)

        # ENABLE IN PRODUCTION
        user_obj = self.env['res.users'].sudo().browse(api_context['co_uid'])
        if book_obj.agent_id.id != user_obj.agent_id.id:
            return {
                'error_code': 200,
                'error_msg': 'Invalid booking number %s or agent id' % booking_number,
                'response': {}
            }

        def get_pricelist_info(tour_id, price_itinerary):
            dp = tour_id.dp
            amount = 0
            payment_rules = []
            for payment in tour_id.payment_rules_ids[::-1]:
                if datetime.strptime(payment['due_date'], "%Y-%m-%d") > datetime.now():
                    vals = {
                        'name': payment['name'],
                        'amount': int(payment['payment_percentage'] / 100 * price_itinerary['total_itinerary_price']),
                        'due_date': payment['due_date']
                    }
                    payment_rules.append(vals)
                    amount = 0
                else:
                    amount += int(payment['payment_percentage'] / 100 * price_itinerary['total_itinerary_price'])

            if amount != 0:
                vals = {
                    'name': 'Payment',
                    'amount': amount,
                    'due_date': date.today().strftime("%Y-%m-%d")
                }
                payment_rules.append(vals)

            payment_rules.append({
                'name': 'Down Payment',
                'amount': int(dp / 100 * price_itinerary['total_itinerary_price']),
                'due_date': date.today().strftime("%Y-%m-%d")
            })

            payment_rules = payment_rules[::-1]

            values = {
                'id': tour_id.id,
                'duration': tour_id.duration,
                'departure_date': tour_id.departure_date,
                'departure_date_f': datetime.strptime(tour_id.departure_date, '%Y-%m-%d').strftime('%d %b'),
                'description': tour_id.description,
                'flight': tour_id.flight,
                'name': tour_id.name,
                'tour_category': tour_id.tour_category,
                'visa': tour_id.visa,
                'payment_rules': payment_rules,
            }
            return values

        def get_itinerary_price(rec):
            res = {
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

            for price in rec:
                if price.description == 'Adult Price':
                    res.update({
                        'adult_amount': price.pax_count,
                        'adult_price': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Airport Tax':
                    res.update({
                        'airport_tax_amount': price.pax_count,
                        'airport_tax_total': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Adult Surcharge':
                    res.update({
                        'adult_surcharge_amount': price.pax_count,
                        'adult_surcharge_price': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Single Supplement':
                    res.update({
                        'single_supplement_amount': price.pax_count,
                        'single_supplement_price': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Tipping Tour Guide':
                    res.update({
                        'tipping_guide_amount': price.pax_count,
                        'tipping_guide_total': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Tipping Tour Leader':
                    res.update({
                        'tipping_tour_leader_amount': price.pax_count,
                        'tipping_tour_leader_total': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Additional Charge':
                    res.update({
                        'additional_charge_amount': price.pax_count,
                        'additional_charge_total': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Child Price':
                    res.update({
                        'child_amount': price.pax_count,
                        'child_price': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Child Surcharge':
                    res.update({
                        'child_surcharge_amount': price.pax_count,
                        'child_surcharge_price': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Infant Price':
                    res.update({
                        'infant_amount': price.pax_count,
                        'infant_price': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Commission' and price.charge_code == 'r.oc':
                    res.update({
                        'commission_total': int(price.total),
                    })
                if price.description == 'Discount':
                    res.update({
                        'discount_total_itinerary_price': int(price.total),
                    })
                    grand_total -= int(price.total)


            sub_total = grand_total + res['discount_total_itinerary_price']

            res.update({
                'total_itinerary_price': grand_total,
                'sub_total_itinerary_price': sub_total,
            })
            return res

        def get_contacts(rec):
            values = {
                'title': rec.title or '',
                'first_name': rec.first_name or '',
                'last_name': rec.last_name or '',
                'mobile': rec.mobile or '',
                'email': rec.email or '',
                'agent_id': rec.commercial_agent_id.id or '',
                'contact_id': rec.id or '',
                'nationality_id': rec.nationality_id.id or '',
                'nationality_code': rec.nationality_id.code or '',
                'country_code': rec.country_id.code or '',
            }
            return values

        def get_booking_line(passenger_ids):
            res = []
            temp = []
            for rec in passenger_ids:
                if rec.room_number not in temp:
                    temp.append(rec.room_number)
                    values = {
                        'name': rec.room_id.name or '',
                        'bed_type': rec.room_id.bed_type or '',
                        'hotel': rec.room_id.hotel or '',
                        'notes': rec.description or '',
                        'description': rec.extra_bed_description or '',
                    }
                    res.append(values)
            return res

        def get_passengers(passenger_ids):
            res = []
            for rec in passenger_ids:
                passenger = rec.passenger_id
                passenger_values = {
                    'room_number': rec.room_number or '',
                    'room_id': rec.room_id.id or '',
                    'title': passenger.title or '',
                    'first_name': passenger.first_name or '',
                    'last_name': passenger.last_name or '',
                    'pax_type': passenger.pax_type or '',
                    'birth_date': passenger.birth_date or '',
                    'mobile': passenger.mobile or '',
                    'email': passenger.email or '',
                    'passenger_id': passenger.id or '',
                    'passport_number': passenger.passport_number or '',
                    'passport_expdate': passenger.passport_expdate or '',
                    'country_of_issued_id': passenger.country_of_issued_id.id or '',
                    'country_of_issued_code': passenger.country_of_issued_id.code or '',
                    'domicile': passenger.domicile or '',
                    'nationality_code': passenger.nationality_id.code or '',
                    'nationality_id': passenger.nationality_id.id or '',
                }
                res.append(passenger_values)
            return res

        booking_row = {
            'id': book_obj.id or '',
            'name': book_obj.name or '',
            'date': book_obj.issued_date or '',
            'state': book_obj.state or '',
            'hold_date': book_obj.hold_date or '',
            'booker_agent_id': book_obj.agent_id.id or ''
        }
        booking_row.update({
            'price_itinerary': get_itinerary_price(book_obj.sale_service_charge_ids) or [],
        })
        booking_row.update({
            'tour_data': get_pricelist_info(book_obj.tour_id, booking_row['price_itinerary']) or {},
            'contacts': get_contacts(book_obj.contact_id) or {},
            'result': get_booking_line(book_obj.line_ids) or [],
            'passengers': get_passengers(book_obj.line_ids) or [],
        })

        if not booking_row:
            return {
                'error_code': 200,
                'error_msg': 'Invalid booking number or agent id'
            }

        return {
            'response': booking_row,
            'error_code': 0,
            'error_msg': False
        }

    def do_print_out_tour_confirmation(self):
        self.ensure_one()
        return self.env['report'].get_action(self, 'tt_tour.printout_tour_confirmation')


class PrintoutTourConfirmation(models.AbstractModel):
    _name = 'report.tt_tour.printout_tour_confirmation'

    @api.model
    def render_html(self, docids, data=None):
        tt_tour = self.env["tt.tour.booking"].browse(docids)
        docargs = {
            'doc_ids': docids,
            'docs': tt_tour
        }
        return self.env['report'].with_context(landscape=False).render('tt_tour.printout_tour_confirmation_template', docargs)
