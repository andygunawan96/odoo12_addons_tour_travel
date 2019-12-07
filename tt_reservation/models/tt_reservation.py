from odoo import api, fields, models, _
from ...tools import variables, util, ERR
from ...tools.ERR import RequestException
import logging, traceback

_logger = logging.getLogger(__name__)


class TtReservation(models.Model):
    _name = 'tt.reservation'
    _inherit = 'tt.history'
    _description = 'Rodex Model'

    name = fields.Char('Order Number', index=True, default='New', readonly=True)
    pnr = fields.Char('PNR', readonly=True, states={'draft': [('readonly', False)]})
    provider_name = fields.Char('List of Provider', readonly=True)
    carrier_name = fields.Char('List of Carriers', readonly=True)

    date = fields.Datetime('Booking Date', default=lambda self: fields.Datetime.now(), readonly=True, states={'draft': [('readonly', False)]})
    expired_date = fields.Datetime('Expired Date', readonly=True)  # fixme terpakai?
    hold_date = fields.Datetime('Hold Date', readonly=True, states={'draft': [('readonly',False)]})

    state = fields.Selection(variables.BOOKING_STATE, 'State', default='draft')

    booked_uid = fields.Many2one('res.users', 'Booked by', readonly=True)
    booked_date = fields.Datetime('Booked Date', readonly=True)
    issued_uid = fields.Many2one('res.users', 'Issued by', readonly=True)
    issued_date = fields.Datetime('Issued Date', readonly=True)
    refund_uid = fields.Many2one('res.users', 'Refund by', readonly=True)
    refund_date = fields.Datetime('Refund Date', readonly=True)
    user_id = fields.Many2one('res.users', 'Create by', readonly=True)  # create_uid

    #utk adjustment
    res_model = fields.Char('Res Model', invisible=1, readonly=True)

    sid_booked = fields.Char('SID Booked', readonly=True)  # Signature generate sendiri

    booker_id = fields.Many2one('tt.customer','Booker', ondelete='restrict', readonly=True, states={'draft':[('readonly',False)]})
    contact_id = fields.Many2one('tt.customer', 'Contact Person', ondelete='restrict', readonly=True, states={'draft': [('readonly', False)]})

    contact_name = fields.Char('Contact Name',readonly=True)  # fixme oncreate later
    contact_title = fields.Char('Contact Title',readonly=True)
    contact_email = fields.Char('Contact Email',readonly=True)
    contact_phone = fields.Char('Contact Phone',readonly=True)

    display_mobile = fields.Char('Contact Person for Urgent Situation',
                                 readonly=True, states={'draft': [('readonly', False)]})

    elder = fields.Integer('Elder', default=0, readonly=True, states={'draft': [('readonly', False)]})
    adult = fields.Integer('Adult', default=1, readonly=True, states={'draft': [('readonly', False)]})
    child = fields.Integer('Child', default=0, readonly=True, states={'draft': [('readonly', False)]})
    infant = fields.Integer('Infant', default=0, readonly=True, states={'draft': [('readonly', False)]})

    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger', readonly=True)

    departure_date = fields.Char('Journey Date', readonly=True, states={'draft': [('readonly', False)]})  # , required=True
    return_date = fields.Char('Return Date', readonly=True, states={'draft': [('readonly', False)]})

    provider_type_id = fields.Many2one('tt.provider.type','Provider Type',readonly=True)

    adjustment_ids = fields.One2many('tt.adjustment','res_id','Adjustment',readonly=True)  # domain=[('res_model','=',lambda self: self._name)]
    refund_ids = fields.One2many('tt.refund','res_id','Refund',readonly=True)  # domain=[('res_model','=',lambda self: self._name)]
    error_msg = fields.Char('Error Message')
    notes = fields.Text('Notes for IT',default='')

    ##fixme tambahkan compute field nanti
    # display_provider_name = fields.Char(string='Provider', compute='_action_display_provider', store=True)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id.id)


    # total_fare = fields.Monetary(string='Total Fare', default=0, compute="_compute_total_booking", store=True)
    # total_tax = fields.Monetary(string='Total Tax', default=0, compute="_compute_total_booking", store=True)
    # total = fields.Monetary(string='Grand Total', default=0, compute="_compute_total_booking", store=True)
    # total_discount = fields.Monetary(string='Total Discount', default=0, compute="_compute_total_booking", store=True)
    # total_commission = fields.Monetary(string='Total Commission', default=0, compute="_compute_total_booking", store=True)
    # total_nta = fields.Monetary(string='NTA Amount', compute="_compute_total_booking", store=True)

    total_fare = fields.Monetary(string='Total Fare', default=0, compute="_compute_total_fare")
    total_tax = fields.Monetary(string='Total Tax', default=0, compute='_compute_total_tax')
    total = fields.Monetary(string='Grand Total', default=0, compute='_compute_grand_total')
    total_discount = fields.Monetary(string='Total Discount', default=0, readonly=True)
    total_commission = fields.Monetary(string='Total Commission', default=0, compute='_compute_total_commission')
    total_nta = fields.Monetary(string='NTA Amount',compute='_compute_total_nta')
    agent_nta = fields.Monetary(string='NTA Amount',compute='_compute_agent_nta')

    # yang jual
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True,
                               default=lambda self: self.env.user.agent_id,
                               readonly=True, states={'draft': [('readonly', False)]})
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id',readonly=True,
                                    store=True)

    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer', readonly=True, states={'draft': [('readonly', False)]},
                                   help='COR / POR')
    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Type', related='customer_parent_id.customer_parent_type_id',
                                        store=True, readonly=True)

    @api.model
    def create(self, vals_list):
        try:
            vals_list['name'] = self.env['ir.sequence'].next_by_code(self._name)
            vals_list['res_model'] = self._name
        except:
            pass
        return super(TtReservation, self).create(vals_list)

    def create_booker_api(self, vals, context):
        booker_obj = self.env['tt.customer'].sudo()
        get_booker_seq_id = util.get_without_empty(vals,'booker_seq_id')

        if get_booker_seq_id:
            booker_seq_id = vals['booker_seq_id']
            booker_rec = booker_obj.search([('seq_id','=',booker_seq_id)])
            update_value = {}
            if booker_rec:
                if vals.get('mobile'):
                    number_entered  = False
                    vals_phone_number = '%s%s' % (vals.get('calling_code', ''), vals['mobile'])
                    for phone in booker_rec.phone_ids:
                        if phone.phone_number == vals_phone_number:
                            number_entered = True
                            break

                    if not number_entered:
                        new_phone=[(0,0,{
                            'calling_code': vals.get('calling_code', ''),
                            'calling_number': vals.get('mobile', ''),
                            'phone_number': vals_phone_number
                        })]
                        update_value['phone_ids'] = new_phone
                update_value['email'] =vals.get('email', booker_rec.email)
                booker_rec.update(update_value)
                return booker_rec

        country = self.env['res.country'].sudo().search([('code', '=', vals.pop('nationality_code'))])
        agent_obj = self.env['tt.agent'].sudo().browse(context['co_agent_id'])

        vals.update({
            'agent_id': context['co_agent_id'],
            'nationality_id': country and country[0].id or False,
            'email': vals.get('email'),
            'phone_ids': [(0,0,{
                'calling_code': vals.get('calling_code',''),
                'calling_number': vals.get('mobile',''),
                'phone_number': '%s%s' % (vals.get('calling_code',''),vals.get('mobile','')),
                'country_id': country and country[0].id or False,
            })],
            'first_name': vals.get('first_name'),
            'last_name': vals.get('last_name'),
            'gender': vals.get('gender'),
            'marital_status': 'married' if vals.get('title') == 'MRS' else '',
            'customer_parent_ids': [(4,agent_obj.customer_parent_walkin_id.id )],
        })
        return booker_obj.create(vals)

    def create_contact_api(self, vals, booker, context):
        contact_obj = self.env['tt.customer'].sudo()
        get_contact_seq_id = util.get_without_empty(vals,'contact_seq_id',False)

        if get_contact_seq_id or vals.get('is_also_booker'):
            if get_contact_seq_id:
                contact_seq_id = get_contact_seq_id
            else:
                contact_seq_id = booker.seq_id

            contact_rec = contact_obj.search([('seq_id','=',contact_seq_id)])
            update_value = {}

            if contact_rec:
                if vals.get('mobile'):
                    number_entered = False
                    vals_phone_number = '%s%s' % (vals.get('calling_code', ''), vals['mobile'])
                    for phone in contact_rec.phone_ids:
                        if phone.phone_number == vals_phone_number:
                            number_entered = True
                            break
                    if not number_entered:
                        new_phone = [(0, 0, {
                            'calling_code': vals.get('calling_code', ''),
                            'calling_number': vals.get('mobile', ''),
                            'phone_number': vals_phone_number
                        })]
                        update_value['phone_ids'] = new_phone
                update_value['email'] =vals.get('email', contact_rec.email)

                contact_rec.update(update_value)
                return contact_rec

        country = self.env['res.country'].sudo().search([('code', '=', vals.pop('nationality_code'))])
        agent_obj = self.env['tt.agent'].sudo().browse(context['co_agent_id'])

        vals.update({
            'agent_id': context['co_agent_id'],
            'nationality_id': country and country[0].id or False,
            'email': vals.get('email'),
            'phone_ids': [(0,0,{
                'calling_code': vals.get('calling_code', ''),
                'calling_number': vals.get('mobile', ''),
                'phone_number': '%s%s' % (vals.get('calling_code',''),vals.get('mobile','')),
                'country_id': country and country[0].id or False,
            })],
            'first_name': vals.get('first_name'),
            'last_name': vals.get('last_name'),
            'marital_status': 'married' if vals.get('title') == 'MRS' else '',
            'customer_parent_ids': [(4, agent_obj.customer_parent_walkin_id.id)],
            'gender': vals.get('gender')
        })

        return contact_obj.create(vals)

    def create_customer_api(self,passengers,context,booker_seq_id=False,contact_seq_id=False):
        country_obj = self.env['res.country'].sudo()
        passenger_obj = self.env['tt.customer'].sudo()

        res_ids = []
        # identity_req = ['identity_number','identity_country_of_issued_id','identity_expdate','identity_type']

        for psg in passengers:
            country = country_obj.search([('code', '=', psg.pop('nationality_code'))])
            psg['nationality_id'] = country and country[0].id or False

            booker_contact_seq_id = ''
            if psg.get('is_also_booker'):
                booker_contact_seq_id = booker_seq_id
            elif psg.get('is_also_contact'):
                booker_contact_seq_id = contact_seq_id

            get_psg_seq_id = util.get_without_empty(psg, 'passenger_seq_id')

            if (get_psg_seq_id or booker_contact_seq_id) != '':
                current_passenger = passenger_obj.search([('seq_id','=',get_psg_seq_id or booker_contact_seq_id)])
                if current_passenger:
                    vals_for_update = {}
                    update_list = ['nationality_id', 'birth_date']

                    [vals_for_update.update({
                        key: psg[key]
                    }) for key in update_list if psg.get(key)]

                    current_passenger.update(vals_for_update)
                    if psg.get('identity'):
                        current_passenger.add_or_update_identity(psg['identity'])
                    res_ids.append(current_passenger)
                    continue

            util.pop_empty_key(psg)
            psg['agent_id'] = context['co_agent_id']
            agent_obj = self.env['tt.agent'].sudo().browse(context['co_agent_id'])
            psg.update({
                'customer_parent_ids': [(4, agent_obj.customer_parent_walkin_id.id)],
                'marital_status': 'married' if psg.get('title') == 'MRS' else '',
            })
            #if ada phone, kalau dari frontend cache passenger
            if psg.get('phone'):
                psg.update({
                    'phone_ids': [(0, 0, {
                        'calling_code': psg.get('phone_id', ''),
                        'calling_number': psg.get('phone', ''),
                        'phone_number': '%s%s' % (psg.get('phone_id', ''), psg.get('phone', '')),
                        'country_id': country and country[0].id or False,
                    })]
                })
            psg_obj = passenger_obj.create(psg)
            if psg.get('identity'):
                psg_obj.add_or_update_identity(psg['identity'])
            res_ids.append(psg_obj)

        return res_ids

    # passenger_obj di isi oleh self.env['']
    def create_passenger_api(self,list_customer,passenger_obj):
        list_passenger = []
        for rec in list_customer:
            vals = rec[0].copy_to_passenger()
            if rec[1]:
                vals.update(rec[1])
            list_passenger.append(passenger_obj.create(vals).id)
        return list_passenger

    def create_passenger_value_api_test(self,passenger):
        list_passenger_value = []
        country_obj = self.env['res.country'].sudo()
        for rec in passenger:
            nationality_id = country_obj.search([('code','=ilike',rec['nationality_code'])],limit=1).id
            identity = rec.get('identity')
            list_passenger_value.append((0,0,{
                'name': "%s %s" % (rec['first_name'],rec['last_name']),
                'first_name': rec['first_name'],
                'last_name': rec['last_name'],
                'gender': rec['gender'],
                'title': rec['title'],
                'birth_date': rec['birth_date'],
                'nationality_id': nationality_id,
                'identity_type': identity and identity['identity_type'] or '',
                'identity_number': identity and identity['identity_number'] or '',
                'identity_expdate': identity and identity['identity_expdate'] or False,
                'identity_country_of_issued_id': identity and country_obj.search([('code','=ilike',identity['identity_country_of_issued_code'])],limit=1).id or False,
                'sequence': rec['sequence']
            }))

        return list_passenger_value

    def _compute_total_fare(self):
        for rec in self:
            fare_total = 0
            for sale in rec.sale_service_charge_ids:
                if sale.charge_type == 'FARE':
                    fare_total += sale.total
            rec.total_fare = fare_total

    def _compute_total_tax(self):
        for rec in self:
            tax_total = 0
            for sale in rec.sale_service_charge_ids:
                if sale.charge_type in ['ROC', 'TAX']:
                    tax_total += sale.total
            rec.total_tax = tax_total

    def _compute_grand_total(self):
        for rec in self:
            grand_total = 0
            for sale in rec.sale_service_charge_ids:
                if sale.charge_type != 'RAC':
                    grand_total += sale.total
            rec.total = grand_total

    def _compute_total_commission(self):
        for rec in self:
            commission_total = 0
            for sale in rec.sale_service_charge_ids:
                if sale.charge_type == 'RAC':
                    commission_total += abs(sale.total)
            rec.total_commission = commission_total

    def _compute_total_nta(self):
        for rec in self:
            nta_total = 0
            for sale in rec.sale_service_charge_ids:
                nta_total += sale.total
            rec.total_nta = nta_total

    def _compute_agent_nta(self):
        for rec in self:
            agent_nta_total = 0
            for sale in rec.sale_service_charge_ids:
                if sale.charge_code == 'rac':
                    agent_nta_total += sale.total
            rec.agent_nta = agent_nta_total + rec.total

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
            'contact': {
                'title': self.contact_title,
                'name': self.contact_name,
                'email': self.contact_email,
                'phone': self.contact_phone
            },
            'booker': self.booker_id.to_dict(),
            'departure_date': self.departure_date and self.departure_date or '',
            'return_date': self.return_date and self.return_date or '',
            'provider_type': self.provider_type_id.code
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

    ##butuh field passenger_ids
    def channel_pricing_api(self,req,context):
        try:
            resv_obj = self.env['tt.reservation.%s' % (req['provider_type'])]
            book_obj = resv_obj.get_book_obj(req.get('book_id'), req.get('order_number'))
            if book_obj and book_obj.agent_id.id == context['co_agent_id']:
                for psg in req['passengers']:
                    book_obj.passenger_ids[psg['sequence']-1].create_channel_pricing(psg['pricing'])
            else:
                return ERR.get_error(1001)
        except Exception as e:
            _logger.error(str(e) + traceback.format_exc())
            return ERR.get_error(500, additional_message=str(e))
        return ERR.get_no_error()

    def action_failed_book(self):
        self.write({
            'state': 'fail_booked'
        })

    def action_failed_issue(self):
        self.write({
            'state': 'fail_issued'
        })

    ##override fungsi ini untuk melakukan action extra jika expired
    def action_expired(self):
        self.state = 'cancel2'
        try:
            for rec in self.provider_booking_ids.filtered(lambda x: x.state != 'cancel2'):
                rec.action_expired()
        except:
            _logger.error("provider type %s failed to expire vendor" % (self._name))

    def action_cancel(self):
        self.state = 'cancel'

    ## Digunakan untuk mengupdate PNR seluruh ledger untuk resv ini
    # Digunakan di hotel dan activity
    def update_ledger_pnr(self, new_pnr):
        for rec in self.ledger_ids:
            rec.update({'pnr': new_pnr})
