from odoo import api, fields, models, _
from ...tools import variables
from datetime import timedelta
from ...tools.repricing_tools import RepricingTools, RepricingToolsV2
from odoo.exceptions import UserError


class TtTicketGroupBooking(models.Model):
    _name = 'tt.ticket.groupbooking'
    _description = 'Ticket Group Booking'
    _order = "type asc"
    _rec_name = 'seq_id'

    seq_id = fields.Char('Sequence ID', readonly=True)
    booking_id = fields.Many2one('tt.reservation.groupbooking', 'Group Booking')
    type = fields.Selection([('departure', 'Departure'), ('return', 'Return')], string='Type')
    departure_date = fields.Datetime('Departure Date')
    arrival_date = fields.Datetime('Arrival Date')
    segment_ids = fields.One2many('tt.segment.groupbooking', 'ticket_id', string='Segment List')
    provider_id = fields.Many2one('tt.provider', 'Provider ID', readonly=False)
    amount_list = fields.Char('Amount List', compute='compute_amount_list')
    fare_ids = fields.One2many('tt.fare.groupbooking', 'ticket_id', string='Fare List')

    @api.model
    def create(self, vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('tt.ticket.groupbooking')
        if vals_list['segment_ids']:
            if vals_list['segment_ids'][0][2]['leg_ids']:
                vals_list.update({
                    'departure_date': vals_list['segment_ids'][0][2]['leg_ids'][0][2]['departure_date'],
                    'arrival_date': vals_list['segment_ids'][-1][2]['leg_ids'][-1][2]['arrival_date']
                })

        return super(TtTicketGroupBooking, self).create(vals_list)

    @api.onchange('segment_ids')
    @api.depends('segment_ids')
    def compute_amount_list(self):
        for rec in self:
            if rec.segment_obj:
                rec.departure_date = rec.segment_obj[0].departure_date
                rec.arrival_date = rec.segment_obj[-1].arrival_date

    def to_dict(self):
        segment_list = []
        fare_list = []
        for segment_obj in self.segment_ids:
            segment_list.append(segment_obj.to_dict())
        for fare_obj in self.fare_ids:
            fare_list.append(fare_obj.to_dict())
        return {
            'arrival_date': str(self.arrival_date),
            'departure_date': str(self.departure_date),
            'type': self.type,
            'segments': segment_list,
            'fare_list': fare_list
        }

    @api.onchange('segment_ids')
    @api.depends('segment_ids')
    def compute_amount_list(self):
        for rec in self:
            list_amount = []
            for fare_obj in rec.fare_ids:
                for pax_price_obj in fare_obj.pax_price_ids:
                    if pax_price_obj.pax_type == 'ADT':
                        list_amount.append(str(int(pax_price_obj.amount)))

            rec.amount_list = ','.join(list_amount)

            # rec.amount_list = ','.join([str(int(fare.amount)) for fare in rec.fare_ids])

class TtSegmentGroupBooking(models.Model):
    _name = 'tt.segment.groupbooking'
    _description = 'Segment Group Booking'

    ticket_id = fields.Many2one('tt.ticket.groupbooking', 'Ticket Group Booking')
    leg_ids = fields.One2many('tt.leg.groupbooking', 'segment_id', string='Leg List')
    carrier_code_id = fields.Many2one('tt.transport.carrier', 'Carrier Code')
    carrier_number = fields.Char('Carrier Number', required=True)
    origin_id = fields.Many2one('tt.destinations', 'Origin')
    destination_id = fields.Many2one('tt.destinations', 'Destination')
    departure_date = fields.Datetime('Departure Date')
    arrival_date = fields.Datetime('Arrival Date')

    @api.model
    def create(self, vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('tt.fare.groupbooking')
        if vals_list['leg_ids']:
            vals_list.update({
                'departure_date': vals_list['leg_ids'][0][2]['departure_date'],
                'arrival_date': vals_list['leg_ids'][-1][2]['arrival_date'],
                'origin_id': vals_list['leg_ids'][0][2]['origin_id'],
                'destination_id': vals_list['leg_ids'][-1][2]['destination_id']
            })
        return super(TtSegmentGroupBooking, self).create(vals_list)

    @api.onchange('leg_ids')
    @api.depends('leg_ids')
    def compute_amount_list(self):
        for rec in self:
            if rec.leg_ids:
                rec.departure_date = rec.leg_ids[0].departure_date
                rec.arrival_date = rec.leg_ids[-1].arrival_date
                rec.origin_id = rec.leg_ids[0].origin_id
                rec.destination_id = rec.leg_ids[-1].destination_id
                for leg_obj in rec.leg_ids:
                    leg_obj.carrier_number = rec.carrier_number

    def to_dict(self):
        leg_list = []
        for leg_obj in self.leg_ids:
            leg_list.append(leg_obj.to_dict())

        return {
            'carrier_code': self.carrier_code_id.code,
            'carrier_number': self.carrier_number,
            'carrier_name': "%s %s" % (self.carrier_code_id.code,self.carrier_number),
            'origin': self.origin_id.code,
            'destination': self.destination_id.code,
            'departure_date': str(self.departure_date),
            'arrival_date': str(self.arrival_date),
            'legs': leg_list,
        }

class TtLegGroupBooking(models.Model):
    _name = 'tt.leg.groupbooking'
    _description = 'Leg Group Booking'

    segment_id = fields.Many2one('tt.segment.groupbooking', 'Segment Group Booking')
    origin_id = fields.Many2one('tt.destinations', 'Origin', required=True)
    destination_id = fields.Many2one('tt.destinations', 'Destination', required=True)
    departure_date = fields.Datetime('Departure Date', required=True)
    arrival_date = fields.Datetime('Arrival Date', required=True)

    @api.model
    def create(self, vals_list):
        vals_list['carrier_number'] = vals_list['segment_id']
        return super(TtLegGroupBooking, self).create(vals_list)


    def to_dict(self):
        return {
            'origin': self.origin_id.code,
            'destination': self.destination_id.code,
            'departure_date': str(self.departure_date),
            'arrival_date': str(self.arrival_date),
        }

class TtFareGroupBooking(models.Model):
    _name = 'tt.fare.groupbooking'
    _description = 'Fare Group Booking'
    _rec_name = 'seq_id'

    ticket_id = fields.Many2one('tt.ticket.groupbooking', 'Ticket Segment Group Booking')
    pax_price_ids = fields.One2many('tt.paxprice.groupbooking', 'fare_id', string='Pax')
    seq_id = fields.Char('Sequence ID', readonly=True)
    type = fields.Char('Type', readonly=True)

    @api.model
    def create(self, vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('tt.fare.groupbooking')
        vals_list['type'] = self.ticket_id.type
        return super(TtFareGroupBooking, self).create(vals_list)

    @api.onchange('ticket_id')
    @api.depends('ticket_id')
    def compute_type(self):
        for rec in self:
            rec.type = rec.ticket_id.type

    def to_dict(self):
        pax_price = []
        for pax in self.pax_price_ids:
            pax_price.append(pax.to_dict())

        return {
            'fare_seq_id': self.seq_id,
            'price_list': pax_price
        }

    def get_fare_detail(self): #buat fare pick
        fare_obj = self.to_dict()
        ticket_obj = self.ticket_id.to_dict()
        ticket_obj.pop('fare_list')
        ticket_obj.update({
            'fare': fare_obj
        })
        return ticket_obj

class TtPaxPriceGroupBooking(models.Model):
    _name = 'tt.paxprice.groupbooking'
    _description = 'Pax Price Group Booking'

    fare_id = fields.Many2one('tt.fare.groupbooking', 'Fare Group Booking')
    pax_type = fields.Selection([('ADT', 'Adult'), ('CHD','Child'), ('INF', 'Infant')])
    amount = fields.Monetary('Amount', currency_field='currency_id')
    commission = fields.Monetary('Commission', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    cost_service_charge_ids = fields.One2many('tt.service.charge', 'paxprice_groupbooking_booking_id',
                                              'Cost Service Charges')

    @api.model
    def create(self, vals):
        new_book = super(TtPaxPriceGroupBooking, self).create(vals)
        csc = new_book.generate_sc_repricing_v2()
        service_chg_obj = self.env['tt.service.charge']
        for service_charge in csc:
            service_charge.update({
                'paxprice_groupbooking_booking_id': new_book.id,
                'description': new_book.fare_id.ticket_id.type
            })
            service_chg_obj.create(service_charge)

        return new_book

    def generate_sc_repricing_v2(self):
        context = self.env['tt.api.credential'].get_userid_credential({
            'user_id': self.fare_id.ticket_id.booking_id.user_id.id
        })
        if not context.get('error_code'):
            context = context['response']
        else:
            raise UserError('Failed to generate service charge, context user not found.')
        repr_tool = RepricingToolsV2('groupbooking', context)
        scs_dict = {
            'service_charges': []
        }
        sale_price = self.amount
        total_commission_amount = self.commission

        segment_count = 1
        route_count = 1
        pax_count = 1

        if pax_count > 0:
            scs_dict['service_charges'].append({
                'amount': sale_price,
                'charge_code': 'fare',
                'charge_type': 'FARE',
                'currency_id': self.currency_id.id,
                'pax_type': self.pax_type,
                'pax_count': pax_count,
                'total': sale_price,
            })
            scs_dict['service_charges'].append({
                'amount': total_commission_amount * -1,
                'charge_code': 'rac',
                'charge_type': 'RAC',
                'currency_id': self.currency_id.id,
                'pax_type': 'ADT',
                'pax_count': pax_count,
                'total': (total_commission_amount) * -1,
            })

        repr_tool.add_ticket_fare(scs_dict)
        carrier_code = ''

        agent_obj = self.fare_id.ticket_id.booking_id.agent_id
        ho_agent_obj = agent_obj.get_ho_parent_agent()

        context = {
            "co_ho_id": ho_agent_obj.id,
            "co_ho_seq_id": ho_agent_obj.seq_id
        }

        rule_param = {
            'provider': self.fare_id.ticket_id.provider_id.code,
            'carrier_code': self.fare_id.ticket_id.booking_id.carrier_code_id.code,
            'route_count': route_count,
            'segment_count': segment_count,
            'show_commission': True,
            'pricing_datetime': '',
            'context': context
        }
        repr_tool.calculate_pricing(**rule_param)

        return scs_dict['service_charges']

    def to_dict(self):
        return {
            'currency': self.currency_id.name,
            'pax_type': self.pax_type,
            'service_charges': self.get_service_charges()
        }

    def get_service_charges(self):
        sc_value = {}
        for p_sc in self.cost_service_charge_ids:
            p_charge_type = p_sc.charge_type
            if not sc_value.get(p_charge_type):
                sc_value[p_charge_type] = {}
                sc_value[p_charge_type].update({
                    'amount': 0,
                    'foreign_amount': 0,
                })

            if p_charge_type == 'RAC' and p_sc.charge_code != 'rac':
                continue

            sc_value[p_charge_type].update({
                'charge_code': p_sc.charge_code,
                'currency': p_sc.currency_id.name,
                'foreign_currency': p_sc.foreign_currency_id.name,
                'amount': sc_value[p_charge_type]['amount'] + p_sc.amount,
                # 'amount': p_sc.amount,
                'foreign_amount': sc_value[p_charge_type]['foreign_amount'] + p_sc.foreign_amount,
                'pax_type': p_sc.pax_type #untuk ambil pax type di to_dict
                # 'foreign_amount': p_sc.foreign_amount,
            })

        return sc_value