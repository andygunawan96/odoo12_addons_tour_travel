from odoo import api, fields, models, _
from ...tools import variables,util,ERR
import logging,traceback

_logger = logging.getLogger(__name__)

class TtReservation(models.Model):
    _name = 'tt.reservation'

    name = fields.Char('Order Number', index=True, default='New', readonly=True)
    pnr = fields.Char('PNR', readonly=True, states={'draft': [('readonly', False)]})
    provider_name = fields.Char('List of Provider name')

    date = fields.Datetime('Booking Date', default=lambda self: fields.Datetime.now(), readonly=True, states={'draft': [('readonly', False)]})
    expired_date = fields.Datetime('Expired Date', readonly=True)  # fixme terpakai?
    hold_date = fields.Datetime('Hold Date', readonly=True)

    state = fields.Selection(variables.BOOKING_STATE, 'State', default='draft')

    booked_uid = fields.Many2one('res.users', 'Booked by', readonly=True)
    booked_date = fields.Datetime('Booked Date', readonly=True)
    issued_uid = fields.Many2one('res.users', 'Issued by', readonly=True)
    issued_date = fields.Datetime('Issued Date', readonly=True)
    user_id = fields.Many2one('res.users', 'Create by', readonly=True)  # create_uid

    sid_booked = fields.Char('SID Booked')  # Signature generate sendiri

    booker_id = fields.Many2one('tt.customer','Booker', ondelete='restrict', readonly=True, states={'draft':[('readonly',False)]})
    contact_id = fields.Many2one('tt.customer', 'Contact Person', ondelete='restrict', readonly=True, states={'draft': [('readonly', False)]})

    contact_name = fields.Char('Contact Name')  # fixme oncreate later
    contact_email = fields.Char('Contact Email')
    contact_phone = fields.Char('Contact Phone')

    display_mobile = fields.Char('Contact Person for Urgent Situation',
                                 readonly=True, states={'draft': [('readonly', False)]})

    elder = fields.Integer('Elder', default=0, readonly=True, states={'draft': [('readonly', False)]})
    adult = fields.Integer('Adult', default=1, readonly=True, states={'draft': [('readonly', False)]})
    child = fields.Integer('Child', default=0, readonly=True, states={'draft': [('readonly', False)]})
    infant = fields.Integer('Infant', default=0, readonly=True, states={'draft': [('readonly', False)]})

    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger')

    departure_date = fields.Char('Journey Date', readonly=True, states={'draft': [('readonly', False)]})  # , required=True
    return_date = fields.Char('Return Date', readonly=True, states={'draft': [('readonly', False)]})

    provider_type_id = fields.Many2one('tt.provider.type','Provider Type')

    adjustment_ids = fields.Char('Adjustment')  # One2Many -> tt.adjustment
    error_msg = fields.Char('Error Message')
    notes = fields.Char('Notes')

    ##fixme tambahkan compute field nanti
    # display_provider_name = fields.Char(string='Provider', compute='_action_display_provider', store=True)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)


    # total_fare = fields.Monetary(string='Total Fare', default=0, compute="_compute_total_booking", store=True)
    # total_tax = fields.Monetary(string='Total Tax', default=0, compute="_compute_total_booking", store=True)
    # total = fields.Monetary(string='Grand Total', default=0, compute="_compute_total_booking", store=True)
    # total_discount = fields.Monetary(string='Total Discount', default=0, compute="_compute_total_booking", store=True)
    # total_commission = fields.Monetary(string='Total Commission', default=0, compute="_compute_total_booking", store=True)
    # total_nta = fields.Monetary(string='NTA Amount', compute="_compute_total_booking", store=True)

    total_fare = fields.Monetary(string='Total Fare', default=0, compute= "_compute_total_fare")
    total_tax = fields.Monetary(string='Total Tax', default=0, compute='_compute_total_tax')
    total = fields.Monetary(string='Grand Total', default=0, compute='_compute_grand_total')
    total_discount = fields.Monetary(string='Total Discount', default=0)
    total_commission = fields.Monetary(string='Total Commission', default=0, compute='_compute_total_commission')
    total_nta = fields.Monetary(string='NTA Amount',compute='_compute_total_nta')

    # yang jual
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True,
                               default=lambda self: self.env.user.agent_id,
                               readonly=True, states={'draft': [('readonly', False)]})
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id',
                                    store=True)

    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer', readonly=True, states={'draft': [('readonly', False)]},
                                   help='COR / POR')
    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Type', related='customer_parent_id.customer_parent_type_id',
                                        store=True, readonly=True)

    def create_booker_api(self, vals, context):
        booker_obj = self.env['tt.customer'].sudo()
        get_booker_id = util.get_without_empty(vals,'booker_id')

        if get_booker_id:
            booker_id = int(vals['booker_id'])
            booker_rec = booker_obj.browse(booker_id)
            update_value = {}
            if booker_rec:
                if vals.get('mobile'):
                    for phone in booker_rec.phone_ids:
                        vals_phone_number = '+%s%s' % (vals.get('calling_code',''),vals['mobile'])
                        if phone.phone_number == vals_phone_number:
                            new_phone = [(1,phone.id,{
                                'phone_number': vals_phone_number
                            })]
                        else:
                            new_phone = [(0, 0, {
                                'phone_number': vals_phone_number
                            })]
                        update_value['phone_ids'] = new_phone
                update_value['email'] =vals.get('email', booker_rec.email)

                booker_rec.update(update_value)
                return booker_rec

        country = self.env['res.country'].sudo().search([('code', '=', vals.pop('nationality_code'))])
        agent_obj = self.env['tt.agent'].sudo().browse(context['agent_id'])


        vals.update({
            'agent_id': context['agent_id'],
            'nationality_id': country and country[0].id or False,
            'email': vals.get('email'),
            'phone_ids': [(0,0,{
                'phone_number': '+%s%s' % (vals.get('calling_code',''),vals.get('mobile','')),
                'country_id': country and country[0].id or False,
            })],
            'first_name': vals.get('first_name'),
            'last_name': vals.get('last_name'),
            'gender': vals.get('gender'),
            'customer_parent_ids': [(4,agent_obj.customer_parent_walkin_id.id )],
        })


        return booker_obj.create(vals)

    def create_contact_api(self, vals, booker, context):
        contact_obj = self.env['tt.customer'].sudo()
        get_contact_id = util.get_without_empty(vals,'contact_id',False)


        if get_contact_id or vals.get('is_also_booker'):
            if get_contact_id:
                contact_id = int(get_contact_id)
            else:
                contact_id = booker.id

            contact_rec = contact_obj.browse(contact_id)
            update_value = {}

            if contact_rec:
                if vals.get('mobile'):
                    for phone in contact_rec.phone_ids:
                        vals_phone_number = '+%s%s' % (vals.get('calling_code',''),vals['mobile'])
                        if phone.phone_number == vals_phone_number:
                            new_phone = [(1,phone.id,{
                                'phone_number': vals_phone_number
                            })]
                        else:
                            new_phone = [(0, 0, {
                                'phone_number': vals_phone_number
                            })]
                        update_value['phone_ids'] = new_phone
                update_value['email'] =vals.get('email', contact_rec.email)

                contact_rec.update(update_value)
                return contact_rec

        country = self.env['res.country'].sudo().search([('code', '=', vals.pop('nationality_code'))])
        agent_obj = self.env['tt.agent'].sudo().browse(context['agent_id'])

        vals.update({
            'agent_id': context['agent_id'],
            'nationality_id': country and country[0].id or False,
            'email': vals.get('email'),
            'phone_ids': [(0,0,{
                'phone_number': '+%s%s' % (vals.get('calling_code',''),vals.get('mobile','')),
                'country_id': country and country[0].id or False,
            })],
            'first_name': vals.get('first_name'),
            'last_name': vals.get('last_name'),
            'customer_parent_ids': [(4, agent_obj.customer_parent_walkin_id.id)],
            'gender': vals.get('gender')
        })

        return contact_obj.create(vals)

    def create_customer_api(self,passengers,context,booker_id=False,contact_id=False,extra_list=[]):
        country_obj = self.env['res.country'].sudo()
        passenger_obj = self.env['tt.customer'].sudo()

        res_ids = []

        for psg in passengers:
            country = country_obj.search([('code', '=', psg.pop('nationality_code'))])
            psg['nationality_id'] = country and country[0].id or False
            if psg.get('country_of_issued_code'):
                country = country_obj.search([('code', '=', psg.pop('country_of_issued_code'))])
                psg['country_of_issued_id'] = country and country[0].id or False

            vals_for_update = {}
            update_list = ['passport_number', 'passport_expdate', 'nationality_id', 'country_of_issued_id', 'passport_issued_date', 'identity_type', 'birth_date']
            [vals_for_update.update({
                key: psg[key]
            }) for key in update_list if psg.get(key)]

            booker_contact_id = -1
            if psg.get('is_also_booker'):
                booker_contact_id = booker_id
            elif psg.get('is_also_contact'):
                booker_contact_id = contact_id

            get_psg_id = util.get_without_empty(psg, 'passenger_id')

            extra = {}
            for key,value in psg.items():
                if key in extra_list:
                    extra[key] = value
            if get_psg_id or booker_contact_id > 0:

                current_passenger = passenger_obj.browse(int(get_psg_id or booker_contact_id))
                if current_passenger:
                    current_passenger.update(vals_for_update)
                    res_ids.append((current_passenger,extra))
                    continue

            util.pop_empty_key(psg)
            psg['agent_id'] = context['agent_id']
            agent_obj = self.env['tt.agent'].sudo().browse(context['agent_id'])
            psg.update({
                'customer_parent_ids': [(4, agent_obj.customer_parent_walkin_id.id)],
            })
            psg_obj = passenger_obj.create(psg)
            res_ids.append((psg_obj,extra))

        return res_ids

    def _compute_total_fare(self):
        fare_total = 0
        for rec in self.sale_service_charge_ids:
            if rec.charge_type == 'FARE':
                fare_total += rec.total
        self.total_fare = fare_total

    def _compute_total_tax(self):
        tax_total = 0
        for rec in self.sale_service_charge_ids:
            if rec.charge_type == 'TAX':
                tax_total += rec.total
        self.total_tax = tax_total

    def _compute_grand_total(self):
        grand_total = 0
        for rec in self.sale_service_charge_ids:
            if rec.charge_type != 'RAC':
                grand_total += rec.total
        self.total = grand_total

    def _compute_total_commission(self):
        commission_total = 0
        for rec in self.sale_service_charge_ids:
            if rec.charge_type == 'RAC':
                commission_total += abs(rec.total)
        self.total_commission = commission_total

    def _compute_total_nta(self):
        nta_total = 0
        for rec in self.sale_service_charge_ids:
            nta_total += rec.total
        self.total_nta = nta_total

    def to_dict(self):
        res = {
            'order_number': self.name,
            'book_id': self.id,
            'pnr': self.pnr,
            'state': self.state,
            'state_description': variables.BOOKING_STATE_STR[self.state],
            'hold_date': self.hold_date and self.hold_date.strftime('%Y-%m-%d %H:%M:%S') or '',
            'YCD': self.elder,
            'ADT': self.adult,
            'CHD': self.child,
            'INF': self.infant,
            'departure_date': self.departure_date and self.departure_date or '',
            'return_date': self.return_date and self.return_date or '',
        }

        return res

    def get_book_obj(self, book_id, order_number):
        if book_id:
            book_obj = self.browse(book_id)
        elif order_number:
            book_obj = self.search([('name', '=', order_number)], limit=1)

        if book_obj:
            return book_obj
        else:
            return False

    def channel_pricing_api(self,req,context):
        try:
            book_obj = self.get_book_obj(req.get('book_id'),req.get('order_number'))
            if book_obj:
                for psg in req['passengers']:
                    book_obj.passenger_ids[psg['sequence']-1].create_channel_pricing(psg['pricing'])
            else:
                return ERR.get_error(1001)
        except Exception as e:
            _logger.error(str(e) + traceback.format_exc())

        return ERR.get_no_error()

    def action_failed_book(self):
        self.write({
            'state': 'fail_booking'
        })

    def action_failed_issue(self):
        self.write({
            'state': 'fail_issue'
        })