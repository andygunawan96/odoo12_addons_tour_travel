from dateutil.relativedelta import relativedelta
from odoo import api,models,fields
import json
from ...tools import variables,util,ERR
from datetime import datetime, timedelta
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
    description_msg = fields.Char('Description Message') ## action needs to do
    description_datetime = fields.Datetime('Description Datetime')
    snooze_days = fields.Integer('Snooze In Days', default=0) ## next update
    last_snooze_date = fields.Date('Last Snooze Date')


    def to_dict(self):
        return {
            "is_active": self.active,
            "is_read": self.is_read,
            "name": self.name,
            "pnr": self.pnr,
            "description": {
                "msg": self.description_msg,
                "datetime": self.description_datetime
            },
            "agent_name": self.agent_id.name,
            "provider_type": self.provider_type_id.code,
            "snooze_days": self.snooze_days,
            "create_date": self.create_date.strftime('%Y-%m-%d'),
            "last_snooze_date": self.last_snooze_date.strftime('%Y-%m-%d') if self.last_snooze_date else False
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
        res_snooze = [] ## agar urutan tidak berpindah - pindah
        notification_book_objs = self.search(dom, order='snooze_days asc, id desc') ## kalau pakai order by snooze_days urutan berubah - ubah jadi pakai 2 list nanti append jadi 1
        for notification_book_obj in notification_book_objs:
            if notification_book_obj.snooze_days != 0:
                res_snooze.append(notification_book_obj.to_dict())
            else:
                res.append(notification_book_obj.to_dict())
        for rec in res_snooze:
            res.append(rec)
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
        dom.append(('active','=',True))
        notif_list = self.search(dom, limit=1)
        if notif_list:
            if len(dom) == 3: ## agent yg read
                notif_list.is_read = True
            return ERR.get_no_error()
        return ERR.get_error(500, additional_message='Notification not found')

    def set_snooze_notification_api(self, req, context):
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
        dom.append(('active','=',True))
        notif_list = self.search(dom, limit=1)
        if notif_list:
            if len(dom) == 3: ## agent yg read
                notif_list.snooze_days = req['days']
            return ERR.get_no_error()
        return ERR.get_error(500, additional_message='Notification not found')

    def set_false_all_record(self):
        agent_notif_objs = self.search([('active', '=', True)])
        for agent_notif_obj in agent_notif_objs:
            if agent_notif_obj.snooze_days == 0 or datetime.now() > agent_notif_obj.create_date.replace(hour=0,minute=0,second=0,microsecond=0) + timedelta(days=agent_notif_obj.snooze_days):
                agent_notif_obj.write({
                    "active": False
                })

    def create_notification_record(self):
        self.set_false_all_record()
        ## create new notif yg booked
        for provider_type in variables.PROVIDER_TYPE:
            book_objs = self.env['tt.reservation.%s' % provider_type].search([('state', '=', 'booked')])
            for book_obj in book_objs:
                last_record_notif = self.search([('name','=',book_obj.name), ('active','=',True), ('snooze_days','!=', 0)],limit=1)
                create_record = True
                if last_record_notif.snooze_days > 0 and datetime.now() < last_record_notif.create_date.replace(hour=0,minute=0,second=0,microsecond=0) + timedelta(days=last_record_notif.snooze_days):
                    create_record = False
                if create_record:
                    self.create({
                        "is_read": False,
                        "active": True,
                        "agent_id": book_obj.agent_id.id,
                        "type": 'reservation',
                        "name": book_obj.name,
                        "description_msg": "Please Issued",
                        "description_datetime": "%s" % book_obj.hold_date.strftime("%Y-%m-%d %H:%M:%S"),
                        "provider_type_id": book_obj.provider_type_id.id,
                        "pnr": book_obj.pnr,
                        "last_snooze_date": book_obj.hold_date.strftime("%Y-%m-%d"),
                        "snooze_days": 0
                    })
        ### NOTIF UNTUK INVALID IDENTITY
        provider_types = ['airline']
        for provider_type in provider_types:
            book_objs = self.env['tt.reservation.%s' % provider_type].search([('passenger_ids.is_valid_identity', '=', False), ('passenger_ids.identity_number', '=', 'P999999'),('state', 'not in', ['draft', 'cancel', 'cancel2'])])
            for book_obj in book_objs:
                create_record = True
                last_record_notif = self.search([('name', '=', book_obj.name), ('active', '=', True), ('snooze_days', '!=', 0)], limit=1)
                if last_record_notif.snooze_days > 0 and datetime.now() < last_record_notif.create_date.replace(hour=0,minute=0,second=0) + timedelta(days=last_record_notif.snooze_days):
                    create_record = False
                if create_record:
                    last_snooze_date = False
                    if book_obj.provider_type_id.code in ['airline','train','bus']:
                        last_snooze_date = book_obj.departure_date - timedelta(days=30)
                        if datetime.now() > last_snooze_date:
                            last_snooze_date = False

                    self.create({
                        "is_read": False,
                        "active": True,
                        "agent_id": book_obj.agent_id.id,
                        "type": 'reservation',
                        "name": book_obj.name,
                        "description_msg": "Please Update Identity",
                        "description_datetime": last_snooze_date,
                        "provider_type_id": book_obj.provider_type_id.id,
                        "pnr": book_obj.pnr,
                        "last_snooze_date": last_snooze_date,
                        "snooze_days": 0
                    })
        #### TOP UP
