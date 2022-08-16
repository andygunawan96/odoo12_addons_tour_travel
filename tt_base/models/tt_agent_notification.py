from dateutil.relativedelta import relativedelta
from odoo import api,models,fields
import json
from ...tools import variables,util,ERR
from datetime import datetime
from ...tools.ERR import RequestException

class TtReservationNotification(models.Model):
    _name = 'tt.agent.notification'
    _description = 'Agent Notification'

    _order = 'id desc'

    active = fields.Boolean('Is Active')
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True, default=lambda self: self.env.user.agent_id,readonly=True)
    is_read = fields.Boolean('Is Read', readonly=True)
    type = fields.Selection([('reservation','Reservation')], 'Type')
    name = fields.Char('Name')  ## untuk nomor AL, nomor TU, DLL
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')
    pnr = fields.Char('PNR')
    description = fields.Char('Description') ## action needs to do
    snooze_days = fields.Integer('Snooze In Days') ## next update


    def to_dict(self):
        return {
            "is_active": self.active,
            "is_read": self.is_read,
            "name": self.name,
            "pnr": self.pnr,
            "description": self.description,
            "agent_name": self.agent_id.name,
            "provider_type": self.provider_type_id.code
        }

    def get_notification_api(self, req, context):
        agent_obj = self.env['tt.agent'].browse(context['co_agent_id'])
        try:
            agent_obj.create_date
        except:
            raise RequestException(1008)
        user_obj = self.env['res.users'].browse(context['co_uid'])
        try:
            user_obj.create_date
        except:
            raise RequestException(1001)

        if self.env.ref('tt_base.group_tt_process_channel_bookings').id in user_obj.groups_id.ids:
            dom = []
        else:
            dom = [('agent_id', '=', agent_obj.id)]

        # req_provider = util.get_without_empty(req, 'provider_type')
        #
        # if req_provider:
        #     if (all(rec in variables.PROVIDER_TYPE for rec in req_provider)):
        #         types = req['provider_type']  # asumsi dari frontend dapat hanya 1 update 9 juli 2021
        #     else:
        #         raise Exception("Wrong provider type")
        # else:
        #     # types = variables.PROVIDER_TYPE
        dom.append(('active','=', True))
        types = ['airline'] ## baru nyala di airline

        res = []
        notification_book_objs = self.search(dom)
        for notification_book_obj in notification_book_objs:
            res.append(notification_book_obj.to_dict())
        return ERR.get_no_error(res)


    def set_notification_read_api(self, req, context):
        agent_obj = self.env['tt.agent'].browse(context['co_agent_id'])
        try:
            agent_obj.create_date
        except:
            raise RequestException(1008)
        user_obj = self.env['res.users'].browse(context['co_uid'])
        try:
            user_obj.create_date
        except:
            raise RequestException(1001)

        if self.env.ref('tt_base.group_tt_process_channel_bookings').id in user_obj.groups_id.ids:
            dom = []
        else:
            dom = [('agent_id', '=', agent_obj.id)]
        dom.append(('name','=',req['order_number']))
        dom.append(('description','=',req['description']))
        dom.append(('active','=',True))
        notif_list = self.search(dom, limit=1)
        if notif_list:
            if len(dom) == 4: ## agent yg read
                notif_list.is_read = True
            return ERR.get_no_error()
        return ERR.get_error(500, additional_message='Booking not found')

    def set_false_all_record(self):
        self.search([('active', '=', True)]).write({
            "active": False
        })

    def create_notification_record(self):
        self.set_false_all_record()
        ## create new notif yg booked
        for provider_type in variables.PROVIDER_TYPE:
            book_objs = self.env['tt.reservation.%s' % provider_type].search([('state', '=', 'booked')])
            for book_obj in book_objs:
                self.create({
                    "booking_id": book_obj.id,
                    "is_read": False,
                    "active": True,
                    "agent_id": book_obj.agent_id.id,
                    "type": 'reservation',
                    "name": book_obj.name,
                    "description": "Needs to Issued before %s" % book_obj.hold_date.strftime("%d %b %Y %H:%M"),
                    "provider_type_id": book_obj.provider_type_id.id,
                    "pnr": book_obj.pnr
                })
        ### NOTIF UNTUK INVALID IDENTITY
        provider_types = ['airline']
        for provider_type in provider_types:
            book_objs = self.env['tt.reservation.%s' % provider_type].search([('passenger_ids.is_valid_identity', '=', False), ('passenger_ids.identity_number', '=', 'P999999'),('state', 'not in', ['draft', 'cancel', 'cancel2'])])
            for book_obj in book_objs:
                self.create({
                    "booking_id": book_obj.id,
                    "is_read": False,
                    "active": True,
                    "agent_id": book_obj.agent_id.id,
                    "type": 'reservation',
                    "name": book_obj.name,
                    "description": "Needs to Update Identity",
                    "provider_type_id": book_obj.provider_type_id.id,
                    "pnr": book_obj.pnr
                })
        #### TOP UP
