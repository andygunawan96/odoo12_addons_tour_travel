from odoo import models, fields, api
import datetime
import json
from num2words import num2words
import pytz
import odoo.tools as tools

static_url = tools.config.get('static_url','')


class PrintoutTicketForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_ticket'
    _description = 'Report Common Printout Ticket'

    # Dipindah ke tt_refund karena tt_refund, refund by api sma report perlu fungsi ini.
    def get_refund_fee_amount(self, agent_id):
        current_refund_env = self.env.ref('tt_accounting.admin_fee_refund_regular')
        refund_admin_fee_list = self.env['tt.master.admin.fee'].search([('after_sales_type', '=', 'refund')])
        for admin_fee in refund_admin_fee_list:
            if agent_id.id in admin_fee.agent_ids.ids:
                current_refund_env = admin_fee

        refund_fee = 0
        for line in current_refund_env.admin_fee_line_ids:
            refund_fee += line.amount
        return refund_fee

    def get_reschedule_fee_amount(self, agent_id):
        current_reschedule_env = self.env.ref('tt_accounting.admin_fee_reschedule')
        reschedule_admin_fee_list = self.env['tt.master.admin.fee'].search([('after_sales_type', '=', 'after_sales')])
        for admin_fee in reschedule_admin_fee_list:
            if agent_id.id in admin_fee.agent_ids.ids:
                current_reschedule_env = admin_fee

        reschedule_fee = 0
        for line in current_reschedule_env.admin_fee_line_ids:
            reschedule_fee += line.amount
        return reschedule_fee

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {}
            if internal_model_id == 1:
                data['context']['active_model'] = 'tt.reservation.airline'
            elif internal_model_id == 2:
                data['context']['active_model'] = 'tt.reservation.train'
            elif internal_model_id == 3:
                data['context']['active_model'] = 'tt.reservation.hotel'
            elif internal_model_id == 4:
                data['context']['active_model'] = 'tt.reservation.activity'
            elif internal_model_id == 5:
                data['context']['active_model'] = 'tt.reservation.tour'
            elif internal_model_id == 6:
                data['context']['active_model'] = 'tt.reservation.event'
            elif internal_model_id == 7:
                data['context']['active_model'] = 'tt.reservation.periksain'
            elif internal_model_id == 8:
                data['context']['active_model'] = 'tt.reservation.phc'
            elif internal_model_id == 9:
                data['context']['active_model'] = 'tt.reservation.medical'
            elif internal_model_id == 10:
                data['context']['active_model'] = 'tt.reservation.bus'
            elif internal_model_id == 11:
                data['context']['active_model'] = 'tt.reservation.insurance'
            elif internal_model_id == 12:
                data['context']['active_model'] = 'tt.reservation.mitrakeluarga'
            data['context']['active_ids'] = docids
        values = {}
        pnr_length = 0
        header_width = 90
        ssr_list = []
        refund_fee = 0
        reschedule_fee = 0
        agent_id = False
        price_breakdown = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            if rec.agent_id.is_btc_agent:
                is_break_down_price = rec.ho_id.is_btc_breakdown_price_printout
            else:
                is_break_down_price = rec.ho_id.is_agent_breakdown_price_printout
            values[rec.id] = []
            a = {}
            csc_pax_list = []
            for provider in rec.provider_booking_ids:
                a[provider.pnr] = []
                for pax in provider.ticket_ids:
                    price_target = {
                        'pnr': provider.pnr,
                        'passenger_id': pax.passenger_id,
                        'name': '%s %s' % (pax.passenger_id.title, pax.passenger_id.name),
                        'pax_type': pax.pax_type,
                        'ticket_number': pax.ticket_number,
                        'total_price': 0,
                    }
                    if hasattr(pax, 'loyalty_program_id'):
                        price_target.update({
                            'ff_obj': {
                                'name': pax.loyalty_program_id.name,
                                'ff_number': pax.ff_number,
                            }
                        })
                    for rec2 in pax.passenger_id.cost_service_charge_ids:
                        # if rec2.id in provider.cost_service_charge_ids.ids and rec2.charge_type.lower() in ['fare', 'roc', 'tax', 'disc', 'ssr', 'seat']:
                        if rec2.id in provider.cost_service_charge_ids.ids and rec2.charge_type.lower() in ['fare', 'roc', 'tax', 'disc']:
                            if is_break_down_price:
                                if rec2.charge_type not in price_breakdown:
                                    price_breakdown[rec2.charge_type] = 0
                                price_breakdown[rec2.charge_type] += rec2.amount
                            price_target['total_price'] += rec2.amount

                    for csc in pax.passenger_id.fee_ids:
                        if is_break_down_price:
                            if csc.category not in price_breakdown:
                                price_breakdown[csc.category] = 0
                            price_breakdown[csc.category] += csc.amount
                        price_target['total_price'] += csc.amount

                    # if pax.passenger_id.id not in csc_pax_list:
                    #     for scs in pax.passenger_id.channel_service_charge_ids:
                    #         price_target['total_price'] += scs.amount
                    #     csc_pax_list.append(pax.passenger_id.id)
                    a[provider.pnr].append(price_target)

            for ssr_per_pax in rec.passenger_ids:
                if hasattr(ssr_per_pax, 'fee_ids'):
                    ssr_obj = {
                        'name': ssr_per_pax.title + '. ' + ssr_per_pax.name,
                        'ssr': [],
                    }
                    for rec2 in ssr_per_pax.fee_ids:
                        ssr_obj['ssr'].append({
                            'name': rec2.name,
                            'amount': rec2.amount,
                            'category_icon': rec2.category_icon if hasattr(rec2, 'category_icon') else '',
                            'currency': rec2.currency_id.name,
                            'description': rec2.convert_json_to_str(rec2.description),
                            'pnr': rec2.provider_id.pnr
                        })
                    if ssr_obj['ssr']:
                        ssr_list.append(ssr_obj)
            values[rec.id] = [a[new_a] for new_a in a]
            pnr_length = len(rec.pnr)
            agent_id = rec.agent_id

            refund_fee = self.get_refund_fee_amount(agent_id)
            reschedule_fee = self.get_reschedule_fee_amount(agent_id)

        airline_ticket_footer = self.env['tt.report.common.setting'].get_footer('airline_ticket',agent_id)
        if data['context']['active_model'] == 'tt.reservation.periksain':
            airline_ticket_footer = self.env['tt.report.common.setting'].get_footer('periksain_ticket', agent_id)
        elif data['context']['active_model'] == 'tt.reservation.phc':
            airline_ticket_footer = self.env['tt.report.common.setting'].get_footer('phc_ticket', agent_id)
        elif data['context']['active_model'] == 'tt.reservation.medical':
            airline_ticket_footer = self.env['tt.report.common.setting'].get_footer('medical_ticket', agent_id)
        elif data['context']['active_model'] == 'tt.reservation.bus':
            airline_ticket_footer = self.env['tt.report.common.setting'].get_footer('bus_ticket', agent_id)
        elif data['context']['active_model'] == 'tt.reservation.insurance':
            airline_ticket_footer = self.env['tt.report.common.setting'].get_footer('insurance_ticket', agent_id)
        elif data['context']['active_model'] == 'tt.reservation.mitrakeluarga':
            airline_ticket_footer = self.env['tt.report.common.setting'].get_footer('mitrakeluarga_ticket', agent_id)

        ## printout
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()
        vals = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'price_lines': values,
            'price_breakdown': price_breakdown,
            'pnr_length': pnr_length,
            'header_width': str(header_width),
            'refund_fee': refund_fee,
            'reschedule_fee': reschedule_fee,
            'ssr_list': ssr_list,
            'airline_ticket_footer': airline_ticket_footer and airline_ticket_footer[0].html or '',
            'date_now': fields.Datetime.now(),
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');",
            'printout_tz': pytz.timezone('Asia/Jakarta'),
            'qr_code_data': False
        }
        if 'is_with_price' in data:
            vals.update({
                'with_price': data.get('is_with_price') or False,
            })
        elif 'is_with_price' in data.get('data', {}):
            vals.update({
                'with_price': data['data'].get('is_with_price') or False,
            })
        else:
            vals.update({
                'with_price': False,
            })

        if 'is_hide_agent_logo' in data:
            vals.update({
                'is_hide_agent_logo': data.get('is_hide_agent_logo') or False,
            })
        elif 'is_hide_agent_logo' in data.get('data', {}):
            vals.update({
                'is_hide_agent_logo': data['data'].get('is_hide_agent_logo') or False
            })
        else:
            vals.update({
                'is_hide_agent_logo': False
            })

        if data['context']['active_model'] in ['tt.reservation.medical', 'tt.reservation.mitrakeluarga']:
            booking_obj = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
            # qr_dict = {
            #     'order_number': to_dict['order_number'],
            #     'pnr': to_dict['pnr'],
            #     'state': to_dict['state_description'],
            #     'hold_date': to_dict['hold_date'],
            #     'pax': {
            #         'YCD': to_dict['YCD'],
            #         'ADT': to_dict['ADT'],
            #         'CHD': to_dict['CHD'],
            #         'INF': to_dict['INF'],
            #     },
            # }
            pax_values = []
            for pax_obj in booking_obj.passenger_ids:
                pax_values.append('%s, %s, %s, %s, %s, %s\n\n' % (pax_obj.name,pax_obj.identity_number,pax_obj.birth_date,pax_obj.email,pax_obj.phone_number,pax_obj.address_ktp))
            if booking_obj.picked_timeslot_id.timeslot_type == 'drive_thru':
                if data['context']['active_model'] == 'tt.reservation.medical':
                    if booking_obj.provider_booking_ids[0].carrier_id.code in ['NHDTKPCRR', 'NHDTSPCRR', 'NHDTMPCRR']:
                        test_date = '%s (24 hours)' % booking_obj.test_datetime.strftime('%d %B %Y')
                    elif booking_obj.provider_booking_ids[0].provider_id.code == 'mitrakeluarga':
                        test_date = '%s (MON-SAT: 08.00 - 20.00 WIB / SUN: 08.00 - 17.00 WIB)' % booking_obj.test_datetime.strftime('%d %B %Y')
                    else:
                        test_date = '%s (MON-SUN: 08.00 - 20.00 WIB' % booking_obj.test_datetime.strftime('%d %B %Y')
                else:
                    test_date = '%s (MON-SAT: 08.00 - 20.00 WIB)' % booking_obj.test_datetime.strftime('%d %B %Y')
            else:
                test_date = booking_obj.test_datetime.strftime('%d %B %Y %H:%M')
            qr_values = "%s - PAID\n%s\n%s\n%s\n%s\n\n%s" % (booking_obj.name,test_date,booking_obj.contact_name,booking_obj.contact_phone,booking_obj.provider_booking_ids[0].carrier_id.name,'\n'.join(pax_values))
            vals.update({'qr_code_data': qr_values})
        return vals

class PrintoutTicketBusForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_bus_ticket'
    _description = 'Report Common Printout Bus Ticket'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            # internal_model_id = docids.pop(0)
            data['context'] = {}
            data['context']['active_model'] = 'tt.reservation.bus'
            data['context']['active_ids'] = docids
        values = {}
        agent_id = False
        price_breakdown = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            if rec.agent_id.is_btc_agent:
                is_break_down_price = rec.ho_id.is_btc_breakdown_price_printout
            else:
                is_break_down_price = rec.ho_id.is_agent_breakdown_price_printout
            values[rec.id] = []
            a = {}
            for rec2 in rec.sale_service_charge_ids:
                if rec2.pax_type not in a.keys():
                    a[rec2.pax_type] = {
                        'pax_type': rec2.pax_type,
                        'fare': 0,
                        'tax': 0,
                        'qty': 0,
                    }
                if rec2.charge_type.lower() == 'fare':
                    a[rec2.pax_type]['fare'] += rec2.amount
                    a[rec2.pax_type]['qty'] = rec2.pax_count
                elif rec2.charge_type.lower() in ['roc', 'tax']:
                    a[rec2.pax_type]['tax'] += rec2.amount
                if is_break_down_price:
                    if rec2.charge_type not in price_breakdown:
                        price_breakdown[rec2.charge_type] = 0
                    price_breakdown[rec2.charge_type] += rec2.amount
            values[rec.id] = [a[new_a] for new_a in a]
            agent_id = rec.agent_id
        train_ticket_footer = self.env['tt.report.common.setting'].get_footer('bus_ticket', agent_id)
        ## printout
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()
        vals = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'price_lines': values,
            'price_breakdown': price_breakdown,
            'train_ticket_footer': train_ticket_footer and train_ticket_footer[0].html or '',
            'date_now': fields.Datetime.now(),
            'base_color': base_color,
            'static_url': static_url
        }
        if 'is_with_price' in data:
            vals.update({
                'with_price': data.get('is_with_price') or False,
            })
        elif 'is_with_price' in data.get('data',''):
            vals.update({
                'with_price': data['data'].get('is_with_price') or False,
            })
        else:
            vals.update({
                'with_price': False,
            })

        if 'is_hide_agent_logo' in data:
            vals.update({
                'is_hide_agent_logo': data.get('is_hide_agent_logo') or False,
            })
        elif 'is_hide_agent_logo' in data.get('data', {}):
            vals.update({
                'is_hide_agent_logo': data['data'].get('is_hide_agent_logo') or False
            })
        else:
            vals.update({
                'is_hide_agent_logo': False
            })

        return vals


class PrintoutTicketTrainForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_train_ticket'
    _description = 'Report Common Printout Train Ticket'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            # internal_model_id = docids.pop(0)
            data['context'] = {}
            data['context']['active_model'] = 'tt.reservation.train'
            data['context']['active_ids'] = docids
        values = {}
        agent_id = False
        price_breakdown = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            if rec.agent_id.is_btc_agent:
                is_break_down_price = rec.ho_id.is_btc_breakdown_price_printout
            else:
                is_break_down_price = rec.ho_id.is_agent_breakdown_price_printout
            values[rec.id] = []
            a = {}
            for rec2 in rec.sale_service_charge_ids:
                if rec2.pax_type not in a.keys():
                    a[rec2.pax_type] = {
                        'pax_type': rec2.pax_type,
                        'fare': 0,
                        'tax': 0,
                        'qty': 0,
                    }
                if rec2.charge_type.lower() == 'fare':
                    a[rec2.pax_type]['fare'] += rec2.amount
                    a[rec2.pax_type]['qty'] = rec2.pax_count
                elif rec2.charge_type.lower() in ['roc', 'tax']:
                    a[rec2.pax_type]['tax'] += rec2.amount
                if is_break_down_price:
                    if rec2.charge_type not in price_breakdown:
                        price_breakdown[rec2.charge_type] = 0
                    price_breakdown[rec2.charge_type] += rec2.amount
            values[rec.id] = [a[new_a] for new_a in a]
            agent_id = rec.agent_id
        train_ticket_footer = self.env['tt.report.common.setting'].get_footer('train_ticket', agent_id)
        ## printout
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()
        vals = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'price_lines': values,
            'price_breakdown': price_breakdown,
            'train_ticket_footer': train_ticket_footer and train_ticket_footer[0].html or '',
            'date_now': fields.Datetime.now(),
            'base_color': base_color,
            'static_url': static_url
        }
        if 'is_with_price' in data:
            vals.update({
                'with_price': data.get('is_with_price') or False,
            })
        elif 'is_with_price' in data.get('data',''):
            vals.update({
                'with_price': data['data'].get('is_with_price') or False,
            })
        else:
            vals.update({
                'with_price': False,
            })

        if 'is_hide_agent_logo' in data:
            vals.update({
                'is_hide_agent_logo': data.get('is_hide_agent_logo') or False,
            })
        elif 'is_hide_agent_logo' in data.get('data', {}):
            vals.update({
                'is_hide_agent_logo': data['data'].get('is_hide_agent_logo') or False
            })
        else:
            vals.update({
                'is_hide_agent_logo': False
            })

        return vals

class PrintoutBoardingPassTrainForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_train_boarding_pass'
    _description = 'Report Common Printout Boarding Pass Train'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            # internal_model_id = docids.pop(0)
            data['context'] = {}
            data['context']['active_model'] = 'tt.reservation.train'
            data['context']['active_ids'] = docids
        values = {}
        agent_id = False
        price_breakdown = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            if rec.agent_id.is_btc_agent:
                is_break_down_price = rec.ho_id.is_btc_breakdown_price_printout
            else:
                is_break_down_price = rec.ho_id.is_agent_breakdown_price_printout
            values[rec.id] = []
            a = {}
            for rec2 in rec.sale_service_charge_ids:
                if rec2.pax_type not in a.keys():
                    a[rec2.pax_type] = {
                        'pax_type': rec2.pax_type,
                        'fare': 0,
                        'tax': 0,
                        'qty': 0,
                    }
                if rec2.charge_type.lower() == 'fare':
                    a[rec2.pax_type]['fare'] += rec2.amount
                    a[rec2.pax_type]['qty'] = rec2.pax_count
                elif rec2.charge_type.lower() in ['roc', 'tax']:
                    a[rec2.pax_type]['tax'] += rec2.amount
                if is_break_down_price:
                    if rec2.charge_type not in price_breakdown:
                        price_breakdown[rec2.charge_type] = 0
                    price_breakdown[rec2.charge_type] += rec2.amount
            values[rec.id] = [a[new_a] for new_a in a]
            agent_id = rec.agent_id
        train_ticket_footer = self.env['tt.report.common.setting'].get_footer('train_ticket', agent_id)
        ## printout
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()
        vals = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'price_lines': values,
            'price_breakdown': price_breakdown,
            'train_ticket_footer': train_ticket_footer and train_ticket_footer[0].html or '',
            'date_now': fields.Datetime.now(),
            'base_color': base_color,
            'static_url': static_url
        }
        if 'is_with_price' in data:
            vals.update({
                'with_price': data.get('is_with_price') or False,
            })
        elif 'is_with_price' in data.get('data',''):
            vals.update({
                'with_price': data['data'].get('is_with_price') or False,
            })
        else:
            vals.update({
                'with_price': False,
            })

        if 'is_hide_agent_logo' in data:
            vals.update({
                'is_hide_agent_logo': data.get('is_hide_agent_logo') or False,
            })
        elif 'is_hide_agent_logo' in data.get('data', {}):
            vals.update({
                'is_hide_agent_logo': data['data'].get('is_hide_agent_logo') or False
            })
        else:
            vals.update({
                'is_hide_agent_logo': False
            })

        return vals


class PrintoutTicketEventForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_event_ticket'
    _description = 'Report Common Printout Event Ticket'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            # internal_model_id = docids.pop(0)
            data['context'] = {}
            data['context']['active_model'] = 'tt.reservation.event'
            data['context']['active_ids'] = docids
        values = {}
        pnr_length = 0
        header_width = 90
        price_breakdown = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            if rec.agent_id.is_btc_agent:
                is_break_down_price = rec.ho_id.is_btc_breakdown_price_printout
            else:
                is_break_down_price = rec.ho_id.is_agent_breakdown_price_printout
            values[rec.id] = []
            a = {}
            csc_pax_list = []
            for provider in rec.provider_booking_ids:
                a[provider.pnr] = []
                for pax in provider.passenger_ids:
                    price_target = {
                        'pnr': provider.pnr,
                        'passenger_id': pax,
                        'name': pax.name,
                        'pax_type': pax.pax_type,
                        'total_price': 0
                    }
                    for rec2 in pax.cost_service_charge_ids:
                        if rec2.id in provider.cost_service_charge_ids.ids and rec2.charge_type.lower() in ['fare',
                                                                                                            'roc',
                                                                                                            'tax',
                                                                                                            'disc']:
                            if is_break_down_price:
                                if rec2.charge_type not in price_breakdown:
                                    price_breakdown[rec2.charge_type] = 0
                                price_breakdown[rec2.charge_type] += rec2.amount
                            price_target['total_price'] += rec2.amount

                    # if pax.id not in csc_pax_list:
                    #     for scs in pax.channel_service_charge_ids:
                    #         price_target['total_price'] += scs.amount
                    #     csc_pax_list.append(pax.id)
                    a[provider.pnr].append(price_target)

            values[rec.id] = [a[new_a] for new_a in a]
            pnr_length = len(rec.pnr)

        ## printout
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()
        vals = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'price_lines': values,
            'price_breakdown': price_breakdown,
            'pnr_length': pnr_length,
            'header_width': str(header_width),
            'date_now': fields.Datetime.now(),
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');",
        }
        if 'is_with_price' in data:
            vals.update({
                'with_price': data.get('is_with_price') or False,
            })
        elif 'is_with_price' in data.get('data', ''):
            vals.update({
                'with_price': data['data'].get('is_with_price') or False,
            })
        else:
            vals.update({
                'with_price': False,
            })

        if 'is_hide_agent_logo' in data:
            vals.update({
                'is_hide_agent_logo': data.get('is_hide_agent_logo') or False,
            })
        elif 'is_hide_agent_logo' in data.get('data', {}):
            vals.update({
                'is_hide_agent_logo': data['data'].get('is_hide_agent_logo') or False
            })
        else:
            vals.update({
                'is_hide_agent_logo': False
            })
        return vals


class PrintoutVoucherHotelForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_hotel_voucher'
    _description = 'Report Common Printout Hotel Voucher'

    # Dipindah ke tt_refund karena tt_refund, refund by api sma report perlu fungsi ini.
    def get_refund_fee_amount(self, agent_id):
        current_refund_env = self.env.ref('tt_accounting.admin_fee_refund_regular')
        refund_admin_fee_list = self.env['tt.master.admin.fee'].search([('after_sales_type', '=', 'refund')])
        for admin_fee in refund_admin_fee_list:
            if agent_id.id in admin_fee.agent_ids.ids:
                current_refund_env = admin_fee

        refund_fee = 0
        for line in current_refund_env.admin_fee_line_ids:
            refund_fee += line.amount
        return refund_fee

    def get_reschedule_fee_amount(self, agent_id):
        current_reschedule_env = self.env.ref('tt_accounting.admin_fee_reschedule')
        reschedule_admin_fee_list = self.env['tt.master.admin.fee'].search([('after_sales_type', '=', 'after_sales')])
        for admin_fee in reschedule_admin_fee_list:
            if agent_id.id in admin_fee.agent_ids.ids:
                current_reschedule_env = admin_fee

        reschedule_fee = 0
        for line in current_reschedule_env.admin_fee_line_ids:
            reschedule_fee += line.amount
        return reschedule_fee

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            # internal_model_id = docids.pop(0)
            data['context'] = {}
            data['context']['active_model'] = 'tt.reservation.hotel'
            data['context']['active_ids'] = docids
        values = {}
        pnr_length = 0
        header_width = 90
        agent_id = False
        price_breakdown = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            if rec.agent_id.is_btc_agent:
                is_break_down_price = rec.ho_id.is_btc_breakdown_price_printout
            else:
                is_break_down_price = rec.ho_id.is_agent_breakdown_price_printout
            values[rec.id] = []
            a = {}
            for rec2 in rec.sale_service_charge_ids:
                if rec2.pax_type not in a.keys():
                    a[rec2.pax_type] = {
                        'pax_type': rec2.pax_type,
                        'price_per_pax': 0,
                        'price_total': 0,
                        'qty': rec2.pax_count  # asumsi yang pertama fare, qtynya benar
                    }
                if rec2.charge_type.lower() in ['fare', 'roc', 'tax']:
                    if is_break_down_price:
                        if rec2.charge_type not in price_breakdown:
                            price_breakdown[rec2.charge_type] = 0
                        price_breakdown[rec2.charge_type] += rec2.amount
                    a[rec2.pax_type]['price_per_pax'] += rec2.amount
                    a[rec2.pax_type]['price_total'] += rec2.total
            # tidak ada ticket with price, dan tidak ada pax type
            # for rec2 in rec.passenger_ids:
            #     for rec3 in rec2.channel_service_charge_ids:
            #         if rec3.pax_type not in a.keys():
            #             a[rec3.pax_type] = {
            #                 'pax_type': rec3.pax_type,
            #                 'fare': 0,
            #                 'tax': 0,
            #                 'qty': 0,
            #             }
            #         a[rec3.pax_type]['tax'] += rec3.amount
            values[rec.id] = [a[new_a] for new_a in a]
            pnr_length = len(rec.pnr) if rec.pnr else len(rec.name)
            if pnr_length > 27:
                header_width += 3 * (abs(27 - pnr_length))
                if header_width > 105:
                    header_width = 105
            agent_id = rec.agent_id
        hotel_ticket_footer = self.env['tt.report.common.setting'].get_footer('hotel_ticket',agent_id)
        ## printout
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()
        vals = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'pnr_length': pnr_length,
            'price_lines': values,
            'price_breakdown': price_breakdown,
            'header_width': str(header_width),
            'date_now': fields.Datetime.now(),
            'refund_fee': self.get_refund_fee_amount(self.env[data['context']['active_model']].browse(data['context']['active_ids']).agent_id),
            'reschedule_fee': self.get_reschedule_fee_amount(self.env[data['context']['active_model']].browse(data['context']['active_ids']).agent_id),
            'hotel_ticket_footer': hotel_ticket_footer and hotel_ticket_footer[0].html or '',
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');",
        }
        if 'is_with_price' in data:
            vals.update({
                'with_price': data.get('is_with_price') or False,
            })
        elif 'is_with_price' in data.get('data',''):
            vals.update({
                'with_price': data['data'].get('is_with_price') or False,
            })
        else:
            vals.update({
                'with_price': False,
            })

        if 'is_hide_agent_logo' in data:
            vals.update({
                'is_hide_agent_logo': data.get('is_hide_agent_logo') or False,
            })
        elif 'is_hide_agent_logo' in data.get('data', {}):
            vals.update({
                'is_hide_agent_logo': data['data'].get('is_hide_agent_logo') or False
            })
        else:
            vals.update({
                'is_hide_agent_logo': False
            })
        return vals


class PrintoutPPOBBillsForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_ppob_bills'
    _description = 'Report Common Printout PPOB Bills'

    @staticmethod
    def format_token_number(token):
        token = token.replace(" ", "")
        return '-'.join(token[i:i+4] for i in range(0, len(token), 4))

    def get_pln_postpaid_values(self, rec, is_break_down_price):
        values = {}

        # Variables
        period = []
        admin_bank = 0
        before_meter = -1
        after_meter = -1
        total_tagihan_pln = 0
        price_breakdown = {}
        # Get PLN Postpaid Data
        if rec.provider_booking_ids:
            # Admin Bank (ambil dari ROC service charge)
            provider = rec.provider_booking_ids[0]
            for scs in provider.cost_service_charge_ids:
                if scs.charge_code in ['rfc', 'rrc']:
                    if is_break_down_price:
                        if scs.charge_type not in price_breakdown:
                            price_breakdown[scs.charge_type] = 0
                        price_breakdown[scs.charge_type] += scs.amount
                    admin_bank += scs.total

            if provider.ppob_bill_ids:
                for bill in provider.ppob_bill_ids:
                    # Period
                    if bill.period:
                        period.append(bill.period.strftime('%b %y'))
                    # Tarif & Denda
                    total_tagihan_pln += bill.fare_amount + bill.fine_amount
                    # Stand Meter
                    if bill.meter_history_ids:
                        for meter in bill.meter_history_ids:
                            if before_meter == -1:
                                before_meter = meter.before_meter
                            else:
                                if meter.before_meter < before_meter:
                                    before_meter = meter.before_meter
                            if after_meter == -1:
                                after_meter = meter.after_meter
                            else:
                                if meter.after_meter > after_meter:
                                    after_meter = meter.after_meter

        # Set Values
        values.update({
            'total': "{:,.0f}".format(rec.total),
            'total_tagihan_pln': "{:,.0f}".format(total_tagihan_pln),
            'before_meter': before_meter,
            'after_meter': after_meter,
            'period': ', '.join(period),
            'admin_bank': "{:,.0f}".format(admin_bank)
        })
        return values, price_breakdown

    def get_pln_prepaid_values(self, rec, is_break_down_price):
        values = {}

        # Variables
        tarif = 0
        stamp_fee = 0
        ppn = 0
        ppj = 0
        admin_bank = 0
        jumlah_kwh = 0
        installment = 0
        token_number = ''
        price_breakdown = {}

        # Get PLN Prepaid Data
        if rec.provider_booking_ids:
            # Admin Bank (ambil dari ROC service charge)
            provider = rec.provider_booking_ids[0]

            for scs in provider.cost_service_charge_ids:
                if scs.charge_code in ['rfc', 'rrc']:
                    if is_break_down_price:
                        if scs.charge_type not in price_breakdown:
                            price_breakdown[scs.charge_type] = 0
                        price_breakdown[scs.charge_type] += scs.amount
                    admin_bank += scs.total

            if provider.ppob_bill_ids:
                token_number = self.format_token_number(provider.ppob_bill_ids[0].token)
                for bill in provider.ppob_bill_ids:
                    # Tarif & Total Bayar
                    tarif += bill.fare_amount
                    stamp_fee += bill.stamp_fee
                    ppn += bill.ppn_tax_amount
                    ppj += bill.ppj_tax_amount
                    jumlah_kwh += bill.kwh_amount
                    installment += bill.installment

        # Set Values
        values.update({
            'token_number': token_number,
            'jumlah_kwh': jumlah_kwh,
            'total': "{:,.0f}".format(rec.total),
            'tarif': "{:,.2f}".format(tarif),
            'stamp_fee': "{:,.2f}".format(stamp_fee),
            'ppn': "{:,.2f}".format(ppn),
            'ppj': "{:,.2f}".format(ppj),
            'admin_bank': "{:,.0f}".format(admin_bank),
            'installment': "{:,.2f}".format(installment)
        })
        return values, price_breakdown

    def get_non_electricity_bills(self, rec, is_break_down_price):
        values = {}

        # Variables
        admin_bank = 0
        total_tagihan_pln = 0
        tgl_registrasi = ''
        price_breakdown = {}
        # Get Non Electricity Bills
        if rec.provider_booking_ids:
            # Admin Bank (ambil dari ROC service charge)
            provider = rec.provider_booking_ids[0]
            tgl_registrasi = provider.registration_date.strftime('%d %b %y')
            for scs in provider.cost_service_charge_ids:
                if scs.charge_code in ['rfc', 'rrc']:
                    if is_break_down_price:
                        if scs.charge_type not in price_breakdown:
                            price_breakdown[scs.charge_type] = 0
                        price_breakdown[scs.charge_type] += scs.amount
                    admin_bank += scs.total

            if provider.ppob_bill_ids:
                for bill in provider.ppob_bill_ids:
                    total_tagihan_pln += bill.fare_amount + bill.fine_amount + bill.admin_fee + bill.stamp_fee + bill.incentive + bill.ppn_tax_amount + bill.ppj_tax_amount

        values.update({
            'tgl_registrasi': tgl_registrasi,
            'total': "{:,.0f}".format(rec.total),
            'total_tagihan_pln': "{:,.0f}".format(total_tagihan_pln),
            'admin_bank': "{:,.0f}".format(admin_bank)
        })
        return values, price_breakdown

    def get_bpjs_kesehatan_values(self, rec, is_break_down_price):
        values = {}

        # Variables
        admin_fee = 0
        period = 0
        tarif = 0
        jumlah_peserta = 0
        unpaid_bill_display = 0
        date = ''
        price_breakdown = {}
        # Get BPJS Kesehatan Data
        if rec.provider_booking_ids:
            provider = rec.provider_booking_ids[0]
            unpaid_bill_display = provider.unpaid_bill_display
            date = provider.issued_date.strftime('%d-%m-%Y')

            for scs in provider.cost_service_charge_ids:
                if scs.charge_code in ['rfc', 'rrc']:
                    if is_break_down_price:
                        if scs.charge_type not in price_breakdown:
                            price_breakdown[scs.charge_type] = 0
                        price_breakdown[scs.charge_type] += scs.amount
                    admin_fee += scs.total

            if provider.ppob_bill_ids:
                for bill in provider.ppob_bill_ids:
                    period += bill.amount_of_month

            if provider.ppob_bill_detail_ids:
                jumlah_peserta = len(provider.ppob_bill_detail_ids)
                for bill_detail in provider.ppob_bill_detail_ids:
                    tarif += bill_detail.total

        values.update({
            'date': date,
            'period': str(period),
            'unpaid_bill_display': "{:,.0f}".format(unpaid_bill_display),
            'total': "{:,.0f}".format(rec.total),
            'tarif': "{:,.0f}".format(tarif),
            'admin_fee': "{:,.0f}".format(admin_fee),
            'jumlah_peserta': jumlah_peserta
        })
        return values, price_breakdown

    def get_mobile_prepaid_values(self, rec, is_break_down_price):
        values = {}
        price_breakdown = {}
        values.update({
            'total': "{:,.0f}".format(rec.total)
        })

        return values, price_breakdown

    def get_ppob_general_values(self, rec, is_break_down_price):
        values = {}
        price_breakdown = {}
        values.update({
            'total': "{:,.0f}".format(rec.total)
        })

        return values, price_breakdown

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            # internal_model_id = docids.pop(0)
            data['context'] = {}
            data['context']['active_model'] = 'tt.reservation.hotel'
            data['context']['active_ids'] = docids
        values = {}
        header_width = 90
        va_length = 0
        agent_id = False
        price_breakdown = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            if rec.agent_id.is_btc_agent:
                is_break_down_price = rec.ho_id.is_btc_breakdown_price_printout
            else:
                is_break_down_price = rec.ho_id.is_agent_breakdown_price_printout
            # Get PPOB Type & Values
            ppob_type = ''
            ppob_type_name = ''
            if rec.provider_booking_ids[0].carrier_id:
                # Carrier berguna untuk menentukan jenis tagihan
                ppob_carrier = rec.provider_booking_ids[0].carrier_id
                ppob_type = ppob_carrier.code
                ppob_type_name = ppob_carrier.name
                if ppob_type == self.env.ref('tt_reservation_ppob.tt_transport_carrier_ppob_bpjs').code:
                    values, price_breakdown = self.get_bpjs_kesehatan_values(rec, is_break_down_price)
                elif ppob_type == self.env.ref('tt_reservation_ppob.tt_transport_carrier_ppob_postpln').code:
                    values, price_breakdown = self.get_pln_postpaid_values(rec, is_break_down_price)
                elif ppob_type == self.env.ref('tt_reservation_ppob.tt_transport_carrier_ppob_prepln').code:
                    values, price_breakdown = self.get_pln_prepaid_values(rec, is_break_down_price)
                elif ppob_type == self.env.ref('tt_reservation_ppob.tt_transport_carrier_ppob_notaglispln').code:
                    values, price_breakdown = self.get_non_electricity_bills(rec, is_break_down_price)
                elif ppob_type == self.env.ref('tt_reservation_ppob.tt_transport_carrier_ppob_prepaidmobile').code:
                    values, price_breakdown = self.get_mobile_prepaid_values(rec, is_break_down_price)
                else:
                    values, price_breakdown = self.get_ppob_general_values(rec, is_break_down_price)

            if rec.provider_booking_ids[0].customer_number:
                va_number = rec.provider_booking_ids[0].customer_number
                va_length = len(va_number) if rec.pnr else len(va_number)
                if va_length > 27:
                    header_width += 3 * (abs(27 - va_length))
                    if header_width > 105:
                        header_width = 105

            values.update({
                'ppob_type': ppob_type,
                'ppob_type_name': ppob_type_name,
                'ppob_type_name_up': ppob_type_name.upper()
            })
            agent_id = rec.agent_id

        footer_ppob_bpjs = self.env['tt.report.common.setting'].get_footer('ppob_bpjs', agent_id)
        ## printout
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()
        vals = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'values': values,
            'price_breakdown': price_breakdown,
            'pnr_length': va_length,
            'header_width': str(header_width),
            'footer_ppob_bpjs': footer_ppob_bpjs and footer_ppob_bpjs[0].html or '',
            'date_now': fields.Datetime.now(),
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');",
        }

        if 'is_hide_agent_logo' in data:
            vals.update({
                'is_hide_agent_logo': data.get('is_hide_agent_logo') or False,
            })
        elif 'is_hide_agent_logo' in data.get('data', {}):
            vals.update({
                'is_hide_agent_logo': data['data'].get('is_hide_agent_logo') or False
            })
        else:
            vals.update({
                'is_hide_agent_logo': False
            })

        return vals


class PrintoutInvoiceVendor(models.AbstractModel):
    _name = 'report.tt_report_common.printout_invoice_vendor'
    _description = 'Report Common Printout Invoice Vendor'

    def get_invoice_data(self, rec, context, data):
        invoice_data = {}
        if rec.provider_booking_ids:
            for provider in rec.provider_booking_ids:
                pnr = provider.pnr if provider.pnr else '-'
                if not invoice_data.get(pnr):
                    invoice_data[pnr] = {'model': rec._name, 'pax_data': [], 'descs': [], 'provider_type': ''}
                invoice_data[pnr]['descs'].append(self.get_description(provider, data))
                invoice_data[pnr]['provider_type'] = rec.provider_type_id.name
                pax_dict = self.get_pax_dict(rec, provider)
                for psg in pax_dict:
                    invoice_data[pnr]['pax_data'].append(pax_dict[psg])
        return invoice_data

    def get_description(self, rec, data, line=None):
        desc = ''
        if data['context']['active_model'] == 'tt.reservation.event':
            desc += 'Event : ' + rec.event_id.name + '<br/>'
            desc += 'Location : ' + '<br/>'
            for location in rec.event_id.location_ids:
                desc += (location.name if location.name else '') + ', ' + \
                        (location.address if location.address else '') + ', ' + \
                        (location.city_id.name if location.city_id.name else '') + ', ' + \
                        (location.country_id.name if location.country_id.name else '') + '<br/>'
            desc += 'Booker : ' + (rec.booking_id.booker_id.name if rec.booking_id.booker_id.name else '') + '<br/>'
            desc += 'Contact Person : ' + (rec.booking_id.contact_title if rec.booking_id.contact_title else '') + '<br/>'
            desc += 'Contact Email : ' + (rec.booking_id.contact_email if rec.booking_id.contact_email else '') + '<br/>'
            desc += 'Contact Phone : ' + (rec.booking_id.contact_phone if rec.booking_id.contact_phone else '') + '<br/>'
        return desc

    def get_pax_dict(self, rec, provider, add=None):
        pax_dict = {}
        if rec._name == 'tt.reservation.event':
            for psg in rec.passenger_ids:
                pax_dict[psg.id] = {}
                pax_dict[psg.id]['name'] = psg.option_id.event_option_id.grade
                pax_dict[psg.id]['total'] = 0
                # for csc in psg.cost_service_charge_ids:
                #     pax_dict[psg.id]['total'] += csc.total
        return pax_dict

    def compute_terbilang_from_objs(self, recs, currency_str='rupiah'):
        a = {}
        for rec2 in recs:
            a.update({rec2.name: num2words(rec2.total) + ' Rupiah'})
        return a

    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {}
            if internal_model_id == 1:
                data['context']['active_model'] = 'tt.reservation.airline'
            elif internal_model_id == 2:
                data['context']['active_model'] = 'tt.reservation.train'
            elif internal_model_id == 3:
                data['context']['active_model'] = 'tt.reservation.hotel'
            elif internal_model_id == 4:
                data['context']['active_model'] = 'tt.reservation.activity'
            elif internal_model_id == 5:
                data['context']['active_model'] = 'tt.reservation.tour'
            data['context']['active_ids'] = docids
        values = {}
        pnr_length = 0
        header_width = 90
        ## BELUM TAHU PRICE BREAKDOWN AMBIL DIMANA ##
        price_breakdown = []
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            if rec.agent_id.is_btc_agent:
                is_break_down_price = rec.ho_id.is_btc_breakdown_price_printout
            else:
                is_break_down_price = rec.ho_id.is_agent_breakdown_price_printout
            values[rec.id] = []
            a = {}
            pax_data = self.get_invoice_data(rec, data.get('context'), data)
            values[rec.id].append(pax_data)
            pnr_length = len(rec.pnr) if rec.pnr else len(rec.name)

        ## printout
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()
        vals = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'doc_type': 'vendor_invoice',
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'price_lines': values,
            'price_breakdown': price_breakdown,
            'inv_lines': values,
            'pnr_length': pnr_length,
            'header_width': str(header_width),
            'terbilang': self.compute_terbilang_from_objs(self.env[data['context']['active_model']].browse(data['context']['active_ids'])),
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');",
        }
        return vals


class PrintoutInvoiceHO(models.AbstractModel):
    _name = 'report.tt_report_common.printout_invoice_ho'
    _description = 'Report Common Printout Invoice HO'

    def get_invoice_data(self, rec, context, data):
        a = {}
        if rec._name == 'tt.reservation.hotel':
            if rec.room_detail_ids:
                for idx, rec2 in enumerate(rec.room_detail_ids):
                    issued_name = rec2.issued_name if rec2.issued_name else '-'
                    if not a.get(issued_name):
                        a[issued_name] = {'model': rec._name, 'pax_data': [], 'descs': [],
                                          'provider_type': ''}
                    meal = rec2.meal_type or 'Room Only'
                    if idx == 0:
                        a[issued_name]['descs'].append(self.get_description(rec, data))
                    a[issued_name]['provider_type'] = rec.provider_type_id.name
                    a[issued_name]['pax_data'].append({
                        'name': rec2.room_name + ' (' + meal + ') ',
                        'total': rec2.sale_price
                    })
        elif rec._name == 'tt.reservation.offline':
            if rec.line_ids:
                for rec2 in rec.line_ids:
                    if rec.offline_provider_type != 'hotel':
                        pnr_same = True
                        pnr = rec2.pnr if rec2.pnr else '-'
                        if not a.get(pnr):
                            pnr_same = False
                            a[pnr] = {'model': rec._name, 'pax_data': [], 'descs': [],
                                      'provider_type': ''}
                        a[pnr]['descs'].append(self.get_description(rec, data, rec2))
                        a[pnr]['provider_type'] = rec.provider_type_id.name
                        if not pnr_same:
                            for provider in rec.provider_booking_ids:
                                if provider.pnr == pnr:
                                    div_amount = 0
                                    for line2 in rec.line_ids:
                                        if line2.pnr == pnr:
                                            div_amount += 1
                                    for psg in rec.passenger_ids:
                                        a[pnr]['pax_data'].append({
                                            'name': psg.passenger_id.name,
                                            'total': rec.total / len(rec.passenger_ids) / len(rec.line_ids) * div_amount,
                                        })
                    else:
                        pnr = rec2.pnr if rec2.pnr else '-'
                        qty = 0
                        for line in rec.line_ids:
                            qty += line.obj_qty

                        if not a.get(pnr):
                            a[pnr] = {'model': rec._name, 'pax_data': [], 'descs': [],
                                      'provider_type': ''}
                        a[pnr]['descs'].append(self.get_description(rec, data, rec2))
                        a[pnr]['provider_type'] = rec.provider_type_id.name
                        a[pnr]['pax_data'].append({
                            'name': (rec2.get_line_hotel_description() if rec2.get_line_hotel_description() else ''),
                            'total': rec.total / qty
                        })
            else:
                pnr = rec.pnr
                a[pnr] = {'model': rec._name, 'pax_data': [], 'descs': [], 'provider_type': ''}
                a[pnr]['descs'].append(rec.description)
                a[pnr]['provider_type'] = rec.provider_type_id.name
                for psg in rec.passenger_ids:
                    a[pnr]['pax_data'].append({
                        'name': psg.passenger_id.name,
                        'total': rec.total / len(rec.passenger_ids),
                    })
        elif rec._name in ['tt.reservation.periksain','tt.reservation.phc']:
            descs = []
            for timeslot_obj in rec.timeslot_ids:
                if timeslot_obj.timeslot_type == 'drive_thru':
                    descs.append('Est Date: ' + str(timeslot_obj.datetimeslot.astimezone(pytz.timezone('Asia/Jakarta')).strftime('%Y-%m-%d')) + ' (DRIVE THRU 08.00 - 17.00 WIB)')
                else:
                    descs.append('Est Date: ' + str(timeslot_obj.datetimeslot.astimezone(pytz.timezone('Asia/Jakarta')).strftime('%Y-%m-%d %H:%M')))
            descs.append(' ')
            descs.append('Address: ' + rec.test_address,)
            a[rec.name] = {
                'model': rec._name,
                'pax_data': [{
                    'name': rec2.title + ' ' + rec2.name,
                    'total': sum([rec3.total for rec3 in rec2.cost_service_charge_ids if rec3.charge_type != 'RAC'])
                } for rec2 in rec.passenger_ids],
                'descs': descs,
                'provider_type': rec.provider_type_id.name,
                'price_breakdown': []
            }
            # a[issued_name]['descs'].append(self.get_description(rec, data))
        else:
            if rec.provider_booking_ids:
                for provider in rec.provider_booking_ids:
                    pnr = provider.pnr if provider.pnr else '-'
                    if not a.get(pnr):
                        a[pnr] = {'model': rec._name, 'pax_data': [], 'descs': [], 'provider_type': ''}
                    a[pnr]['descs'].append(self.get_description(provider, data))
                    a[pnr]['provider_type'] = rec.provider_type_id.name
                    # untuk harga fare per passenger
                    pax_dict = self.get_pax_dict(rec, provider)
                    for psg in pax_dict:
                        a[pnr]['pax_data'].append(pax_dict[psg])
        return a

    def get_additional_dict(self, rec, provider, add=None):
        add_dict = {}
        if rec._name == 'tt.reservation.visa':
            add_dict[add.id] = {}
            add_dict[add.id]['name'] = ''
            if add.vendor_id.name:
                add_dict[add.id]['name'] += add.vendor_id.name
            add_dict[add.id]['name'] += ' - '
            if add.reference_number:
                add_dict[add.id]['name'] += add.reference_number
            add_dict[add.id]['total'] = add.amount
        return add_dict

    def get_pax_dict(self, rec, provider):
        pax_dict = {}
        for cost_charge in provider.cost_service_charge_ids:
            # if cost_charge.charge_type != 'RAC':
            if rec._name == 'tt.reservation.airline':
                for psg in cost_charge.passenger_airline_ids:
                    if psg.name not in pax_dict:
                        pax_dict[psg.name] = {}
                        pax_dict[psg.name]['name'] = '%s, %s' % (
                            ' '.join((psg.first_name or '', psg.last_name or '')), psg.title or '')
                        pax_dict[psg.name]['total'] = cost_charge.amount
                    else:
                        pax_dict[psg.name]['total'] += cost_charge.amount
            elif rec._name == 'tt.reservation.train':
                for psg in cost_charge.passenger_train_ids:
                    if psg.name not in pax_dict:
                        pax_dict[psg.name] = {}
                        pax_dict[psg.name]['name'] = '%s, %s' % (
                            ' '.join((psg.first_name or '', psg.last_name or '')), psg.title or '')
                        pax_dict[psg.name]['total'] = cost_charge.amount
                    else:
                        pax_dict[psg.name]['total'] += cost_charge.amount
            elif rec._name == 'tt.reservation.activity':
                for psg in cost_charge.passenger_activity_ids:
                    if psg.name not in pax_dict:
                        pax_dict[psg.name] = {}
                        pax_dict[psg.name]['name'] = '%s, %s' % (
                            ' '.join((psg.first_name or '', psg.last_name or '')), psg.title or '')
                        pax_dict[psg.name]['total'] = cost_charge.amount
                    else:
                        pax_dict[psg.name]['total'] += cost_charge.amount
            elif rec._name == 'tt.reservation.tour':
                for psg in cost_charge.passenger_tour_ids:
                    if psg.name not in pax_dict:
                        pax_dict[psg.name] = {}
                        pax_dict[psg.name]['name'] = '%s, %s' % (
                            ' '.join((psg.first_name or '', psg.last_name or '')), psg.title or '')
                        pax_dict[psg.name]['total'] = cost_charge.amount
                    else:
                        pax_dict[psg.name]['total'] += cost_charge.amount
            elif rec._name == 'tt.reservation.visa':
                for psg in cost_charge.passenger_visa_ids:
                    if psg.name not in pax_dict:
                        name = ''
                        name += (psg.first_name or '') + ' ' + (psg.last_name or '') + ', ' + (psg.title or '') + \
                                ' (' + (psg.passenger_type if psg.passenger_type else '') + ') ' + \
                                (psg.pricelist_id.entry_type.capitalize() if psg.pricelist_id.entry_type else '') + ' ' + \
                                (psg.pricelist_id.visa_type.capitalize() if psg.pricelist_id.visa_type else '') + ' ' + \
                                (psg.pricelist_id.process_type.capitalize() if psg.pricelist_id.process_type else '') + \
                                ' (' + str(psg.pricelist_id.duration if psg.pricelist_id.duration else '-') + ' days)'
                        pax_dict[psg.name] = {}
                        pax_dict[psg.name]['name'] = name
                        pax_dict[psg.name]['total'] = cost_charge.amount
                    else:
                        pax_dict[psg.name]['total'] += cost_charge.amount
            elif rec._name == 'tt.reservation.passport':
                for psg in cost_charge.passenger_passport_ids:
                    if psg.name not in pax_dict:
                        name = ''
                        name += (psg.first_name or '') + ' ' + (psg.last_name or '') + ', ' + (psg.title or '') + \
                                ' (' + (psg.passenger_type if psg.passenger_type else '') + ') ' + \
                                (psg.pricelist_id.apply_type.capitalize() if psg.pricelist_id.apply_type else '') + ' ' + \
                                (psg.pricelist_id.passport_type.capitalize() if psg.pricelist_id.passport_type else '') + ' ' + \
                                (psg.pricelist_id.process_type.capitalize() if psg.pricelist_id.process_type else '') + \
                                ' (' + str((psg.pricelist_id.duration if psg.pricelist_id.duration else '-')) + ' days)'
                        pax_dict[psg.name] = {}
                        pax_dict[psg.name]['name'] = name
                        pax_dict[psg.name]['total'] = cost_charge.amount
                    else:
                        pax_dict[psg.name]['total'] += cost_charge.amount
        if rec._name == 'tt.reservation.ppob':
            ppob_carrier = provider.carrier_id
            if ppob_carrier.code == self.env.ref('tt_reservation_ppob.tt_transport_carrier_ppob_bpjs').code:
                for bill_detail in provider.ppob_bill_detail_ids:
                    pax_dict[bill_detail.customer_number] = {}
                    pax_dict[bill_detail.customer_number]['name'] = bill_detail.customer_name
                    pax_dict[bill_detail.customer_number]['total'] = bill_detail.total
            elif ppob_carrier.code == self.env.ref('tt_reservation_ppob.tt_transport_carrier_ppob_postpln').code:
                for bill in provider.ppob_bill_ids:
                    period = bill.period.strftime('%d/%m/%Y')
                    pax_dict[period] = {}
                    pax_dict[period]['name'] = 'Periode ' + period
                    pax_dict[period]['total'] = bill.fare_amount + bill.fine_amount
            elif ppob_carrier.code == self.env.ref('tt_reservation_ppob.tt_transport_carrier_ppob_prepln').code:
                for bill in provider.ppob_bill_ids:
                    period = bill.period.strftime('%d/%m/%Y')
                    total = bill.fare_amount + bill.fine_amount + bill.admin_fee + bill.stamp_fee + \
                            + bill.incentive + bill.ppn_tax_amount + bill.ppj_tax_amount + bill.installment
                    pax_dict[period] = {}
                    pax_dict[period]['name'] = 'Periode ' + period
                    pax_dict[period]['total'] = total
            elif ppob_carrier.code == self.env.ref('tt_reservation_ppob.tt_transport_carrier_ppob_notaglispln').code:
                period = provider.registration_date.strftime('%d/%m/%y')
                pax_dict[period] = {}
                pax_dict[period]['name'] = provider.transaction_name
                pax_dict[period]['total'] = provider.ppob_bill_ids[0].fare_amount
        if rec._name == 'tt.reservation.event':
            for psg in rec.passenger_ids:
                pax_dict[psg.id] = {}
                pax_dict[psg.id]['name'] = psg.option_id.event_option_id.grade
                pax_dict[psg.id]['total'] = 0
                for csc in psg.cost_service_charge_ids:
                    if csc.charge_type == 'RAC':
                        if csc.charge_code == 'rac':
                            pax_dict[psg.id]['total'] += csc.total
                    else:
                        pax_dict[psg.id]['total'] += csc.total
        return pax_dict

    def compute_terbilang_from_objs(self, recs, currency_str='rupiah'):
        a = {}
        for rec2 in recs:
            a.update({rec2.name: num2words(rec2.total) + ' Rupiah'})
        return a

    def get_description(self, rec, data, line=None):
        desc = ''
        if data['context']['active_model'] == 'tt.reservation.airline':
            for journey in rec.journey_ids:
                desc += '%s(%s) - %s(%s), ' % (
                    (journey.origin_id.city if journey.origin_id.city else ''),
                    (journey.origin_id.code if journey.origin_id.code else ''),
                    (journey.destination_id.city if journey.destination_id.city else ''),
                    (journey.destination_id.code if journey.destination_id.code else ''))
                desc += '%s - %s\n ' % (journey.departure_date[:16], journey.arrival_date[:16])
        elif data['context']['active_model'] == 'tt.reservation.train':
            for journey in rec.journey_ids:
                desc += '%s(%s) - %s(%s),' % (
                    (journey.origin_id.city if journey.origin_id.city else ''),
                    (journey.origin_id.code if journey.origin_id.code else ''),
                    journey.destination_id.city if journey.destination_id.city else '',
                    journey.destination_id.code if journey.destination_id.code else '')
                desc += '%s - %s\n ' % (journey.departure_date[:16], journey.arrival_date[:16])
        elif data['context']['active_model'] == 'tt.reservation.activity':
            desc = ''
            for rec2 in rec.activity_detail_ids:
                desc += '%s (%s), ' % (
                    rec2.activity_id.name if rec2.activity_id.name else '',
                    rec2.activity_product_id.name if rec2.activity_product_id.name else '')
                desc += '%s ' % (rec2.visit_date if rec2.visit_date else '')
                if rec2.timeslot:
                    desc += '(%s) ' % rec2.timeslot
                desc += '\n '
            return desc
        elif data['context']['active_model'] == 'tt.reservation.tour':
            desc = ''
            desc += '%s' % (rec.tour_id.name if rec.tour_id.name else '')
            desc += '\n'
            desc += '%s - %s ' % (rec.departure_date if rec.departure_date else '',
                                  rec.arrival_date if rec.arrival_date else '')
            desc += '\n'
        elif data['context']['active_model'] == 'tt.reservation.visa':
            desc = 'Reservation Visa Country : ' + (rec.booking_id.country_id.name if rec.booking_id.country_id.name else '') + \
                   ' ' + 'Consulate : ' + (rec.booking_id.immigration_consulate if rec.booking_id.immigration_consulate else '') + ' ' + \
                   'Journey Date : ' + str(rec.booking_id.departure_date) if rec.booking_id.departure_date else ''
        elif data['context']['active_model'] == 'tt.reservation.passport':
            desc = ''
            desc = 'Reservation Passport Consulate : ' + (rec.booking_id.immigration_consulate if rec.booking_id.immigration_consulate else '')
        elif data['context']['active_model'] == 'tt.reservation.offline':
            desc = ''
            if rec.provider_type_id_name != 'hotel':
                desc += line.get_line_description()
            else:
                desc += 'Description : ' + (rec.description if rec.description else '')
        elif data['context']['active_model'] == 'tt.reservation.hotel':
            desc += 'Hotel : %s\n' % (rec.hotel_name)
            desc += 'Date  : %s - %s\n' % (str(rec.checkin_date)[:10], str(rec.checkout_date)[:10])
            desc += 'Guest :\n'
            for idx, guest in enumerate(rec.passenger_ids):
                desc += str(idx + 1) + '. ' + (guest.name if guest.name else '') + '\n'
            # spc = rec.special_request or '-'
            # desc += 'Special Request: ' + spc + '\n'
        elif data['context']['active_model'] == 'tt.reservation.ppob':
            ppob_carrier = rec.carrier_id
            desc += 'PPOB : ' + (ppob_carrier.name if ppob_carrier.name else '') + '<br/>'
            if ppob_carrier.code == self.env.ref('tt_reservation_ppob.tt_transport_carrier_ppob_bpjs').code:
                # desc += 'MKM Ref : ' + rec.session_id + '<br/>'
                desc += 'BPJS Ref : ' + (rec.pnr if rec.pnr else '') + '<br/>'
                desc += 'Nama : ' + (rec.customer_name if rec.customer_name else '') + '<br/>'
                desc += 'Jumlah Peserta : ' + (str(len(rec.ppob_bill_detail_ids)) if rec.ppob_bill_detail_ids else '') + '<br/>'
                desc += 'Jumlah Periode : ' + (str(len(rec.ppob_bill_ids)) if rec.ppob_bill_ids else '') + '<br/>'
            elif ppob_carrier.code == self.env.ref('tt_reservation_ppob.tt_transport_carrier_ppob_postpln').code:
                desc += 'IDPel : ' + (rec.customer_id_number if rec.customer_id_number else '') + '<br/>'
                desc += 'Nama : ' + (rec.customer_name if rec.customer_name else '') + '<br/>'
                desc += 'Tarif/Daya : ' + (rec.fare_type if rec.fare_type else '') + ' / ' + str(rec.power if rec.power else '') + 'VA <br/>'
            elif ppob_carrier.code == self.env.ref('tt_reservation_ppob.tt_transport_carrier_ppob_prepln').code:
                desc += 'No. Meter : ' + (rec.meter_number if rec.meter_number else '') + '<br/>'
                desc += 'IDPel : ' + (rec.customer_id_number if rec.customer_id_number else '') + '<br/>'
                desc += 'Nama : ' + (rec.customer_name if rec.customer_name else '') + '<br/>'
                desc += 'Tarif/Daya : ' + (rec.fare_type if rec.fare_type else '') + ' / ' + str(rec.power if rec.power else '') + 'VA <br/>'
            elif ppob_carrier.code == self.env.ref('tt_reservation_ppob.tt_transport_carrier_ppob_notaglispln').code:
                desc += 'Transaksi : ' + (rec.transaction_code if rec.transaction_code else '') + '<br/>'
                desc += 'No. Registrasi : ' + (rec.registration_number if rec.registration_number else '') + '<br/>'
                desc += 'Tgl. Registrasi : ' + rec.registration_date.strftime('%d/%m/%Y') if rec.registration_date else '' + '<br/>'
                desc += 'IDPel : ' + (rec.customer_id_number if rec.customer_id_number else '') + '<br/>'
                desc += 'Nama : ' + (rec.customer_name if rec.customer_name else '') + '<br/>'
            elif ppob_carrier.code == self.env.ref('tt_reservation_ppob.tt_transport_carrier_ppob_prepaidmobile').code:
                desc += 'Serial Number : ' + (rec.original_pnr if rec.original_pnr else '') + '<br/>'
                desc += 'Nomor HP : ' + (rec.customer_number if rec.customer_number else '') + '<br/>'
                desc += 'Transaksi : ' + (rec.transaction_code if rec.transaction_code else '') + '<br/>'
                desc += 'Produk Pulsa : ' + (rec.transaction_name if rec.transaction_name else '') + '<br/>'
                desc += 'Nama : ' + (rec.customer_name if rec.customer_name else '') + '<br/>'

        elif data['context']['active_model'] == 'tt.reservation.event':
            desc += 'Event : ' + rec.event_id.name + '<br/>'
            desc += 'Location : ' + '<br/>'
            for location in rec.event_id.location_ids:
                desc += (location.name if location.name else '') + ', ' + \
                        (location.address if location.address else '') + ', ' + \
                        (location.city_id.name if location.city_id.name else '') + ', ' + \
                        (location.country_id.name if location.country_id.name else '') + '<br/>'
            desc += 'Booker : ' + (rec.booking_id.booker_id.name if rec.booking_id.booker_id.name else '') + '<br/>'
            desc += 'Contact Person : ' + (rec.booking_id.contact_title if rec.booking_id.contact_title else '') + '<br/>'
            desc += 'Contact Email : ' + (rec.booking_id.contact_email if rec.booking_id.contact_email else '') + '<br/>'
            desc += 'Contact Phone : ' + (rec.booking_id.contact_phone if rec.booking_id.contact_phone else '') + '<br/>'
        return desc

    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {}
            if internal_model_id == 1:
                data['context']['active_model'] = 'tt.reservation.airline'
            elif internal_model_id == 2:
                data['context']['active_model'] = 'tt.reservation.train'
            elif internal_model_id == 3:
                data['context']['active_model'] = 'tt.reservation.hotel'
            elif internal_model_id == 4:
                data['context']['active_model'] = 'tt.reservation.activity'
            elif internal_model_id == 5:
                data['context']['active_model'] = 'tt.reservation.tour'
            data['context']['active_ids'] = docids
        values = {}
        pnr_length = 0
        header_width = 90
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            values[rec.id] = []
            a = {}
            pax_data = self.get_invoice_data(rec, data.get('context'), data)
            values[rec.id].append(pax_data)
            pnr_length = len(rec.pnr) if rec.pnr else len(rec.name)
            if pnr_length > 27:
                header_width += 3 * (abs(27 - pnr_length))
                if header_width > 105:
                    header_width = 105
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        ho_obj = False
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()
            ho_obj = data_object.agent_id.ho_id
        vals = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'doc_type': 'ho_invoice',
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'price_lines': values,
            'inv_lines': values,
            'pnr_length': pnr_length,
            'terbilang': self.compute_terbilang_from_objs(self.env[data['context']['active_model']].browse(data['context']['active_ids'])),
            'date_now': fields.Datetime.now(),
            'ho_obj': ho_obj,
            'header_width': str(header_width),
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');",
        }
        return vals


class PrintoutInvoice(models.AbstractModel):
    _name = 'report.tt_report_common.printout_invoice'
    _description = 'Report Common Printout Invoice'

    """Abstract Model for report template.
        for `_name` model, please use `report.` as prefix then add `module_name.report_name`.
    """
    def format_description(self, desc_str):
        # desc_str.replace('\n','&lt;br/&gt;')
        return desc_str

    def get_invoice_data(self, line, rec, inv, inc_details=[]):
        a = {}
        reduce_amt = 0
        apply_filter = True if inc_details else False
        if rec._name == 'tt.reservation.offline':
            a = {'descs': self.format_description(line.desc), 'pnr': inv.pnr.split(','), 'line_detail': [], 'total_after_tax': line.total_after_tax}
            # for provider in rec.provider_booking_ids:
            #     a['pnr'].append(provider.pnr)
            for line_detail in line.invoice_line_detail_ids:
                if apply_filter and line_detail.id not in inc_details:
                    reduce_amt += line_detail.price_subtotal
                    continue
                a['line_detail'].append({
                    'name': line_detail.desc,
                    'price': line_detail.price_unit,
                    'quantity': line_detail.quantity,
                    'amount': line_detail.price_subtotal
                })
            # if rec.line_ids:
            #     for rec2 in rec.line_ids:
            #         if rec.offline_provider_type != 'hotel':
            #             pnr_same = True
            #             pnr = rec2.pnr if rec2.pnr else '-'
            #             if not a.get(pnr):
            #                 pnr_same = False
            #                 a[pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [],
            #                           'provider_type': ''}
            #             if not pnr_same:
            #                 a[pnr]['descs'].append(rec2.get_line_description())
            #                 a[pnr]['provider_type'] = rec.provider_type_id.name
            #
            #                 for provider in rec.provider_booking_ids:
            #                     if provider.pnr == pnr:
            #                         div_amount = 0
            #                         for line2 in rec.line_ids:
            #                             if line2.pnr == pnr:
            #                                 div_amount += 1
            #                         for line_detail in line.invoice_line_detail_ids:
            #                             a[pnr]['pax_data'].append({
            #                                 'name': (line_detail.desc if line_detail.desc else ''),
            #                                 'total': (line_detail.price_subtotal/len(rec.line_ids)*div_amount if line_detail.price_subtotal else 0)
            #                             })
            #                         break
            #         else:
            #             pnr_same = True
            #             pnr = rec2.pnr if rec2.pnr else '-'
            #             if not a.get(pnr):
            #                 pnr_same = False
            #                 a[pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [],
            #                           'provider_type': ''}
            #             a[pnr]['descs'].append(line.desc if line.desc else '')
            #             a[pnr]['provider_type'] = rec.provider_type_id.name
            #             a[pnr]['pax_data'].append({
            #                 'name': (rec2.get_line_hotel_description() if rec2.get_line_hotel_description() else ''),
            #                 'total': rec.total / len(rec.line_ids)
            #             })
            # else:
            #     for rec2 in rec.provider_booking_ids:
            #         pnr = rec2.pnr if rec2.pnr else '-'
            #         if not a.get(pnr):
            #             a[pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': ''}
            #         a[pnr]['descs'].append(line.desc if line.desc else '')
            #         a[pnr]['provider_type'] = rec.provider_type_id.name
            #         for line_detail in line.invoice_line_detail_ids:
            #             a[pnr]['pax_data'].append({
            #                 'name': (line_detail.desc if line_detail.desc else ''),
            #                 'total': (line_detail.price_subtotal if line_detail.price_subtotal else '')
            #             })
        elif rec._name == 'tt.reservation.hotel':
            a = {'descs': self.format_description(line.desc), 'pnr': [], 'line_detail': [], 'total_after_tax': line.total_after_tax}
            for room in rec.room_detail_ids:
                if room.issued_name and room.issued_name not in a['pnr']:
                    a['pnr'].append(room.issued_name)
            for line_detail in line.invoice_line_detail_ids:
                if apply_filter and line_detail.id not in inc_details:
                    reduce_amt += line_detail.price_subtotal
                    continue
                a['line_detail'].append({
                    'name': line_detail.desc,
                    'price': line_detail.price_unit,
                    'quantity': line_detail.quantity,
                    'amount': line_detail.price_subtotal
                })
            # if rec.room_detail_ids:
            # for rec2 in rec.room_detail_ids:
            #     issued_name = rec2.issued_name if rec2.issued_name else '-'
            #     if not a.get(issued_name):
            #         a[issued_name] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [],
            #                           'provider_type': ''}
            #     a[issued_name]['descs'].append(line.desc if line.desc else '')
            #     a[issued_name]['provider_type'] = rec.provider_type_id.name
            #     for line_detail in line.invoice_line_detail_ids:
            #         a[issued_name]['pax_data'].append({
            #             'name': (line_detail.desc if line_detail.desc else ''),
            #             'total': (line_detail.price_subtotal if line_detail.price_subtotal else '')
            #         })
            # else:
            # issued_name = '-'
            # if not a.get(issued_name):
            #     a[issued_name] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [],
            #                       'provider_type': ''}
            # a[issued_name]['descs'].append(line.desc if line.desc else '')
            # a[issued_name]['provider_type'] = rec.provider_type_id.name
            # for line_detail in line.invoice_line_detail_ids:
            #     a[issued_name]['pax_data'].append({
            #         'name': (line_detail.desc if line_detail.desc else ''),
            #         'total': (line_detail.price_subtotal if line_detail.price_subtotal else '')
            #     })
        elif rec._name == 'tt.reschedule':
            a = {'descs': self.format_description(line.desc), 'pnr': [], 'line_detail': [], 'total_after_tax': line.total_after_tax}
            a['pnr'].append(rec.pnr or '-')
            for line_detail in line.invoice_line_detail_ids:
                if apply_filter and line_detail.id not in inc_details:
                    reduce_amt += line_detail.price_subtotal
                    continue
                a['line_detail'].append({
                    'name': line_detail.desc,
                    'price': line_detail.price_unit,
                    'quantity': line_detail.quantity,
                    'amount': line_detail.price_subtotal
                })
            # pnr = rec.pnr and rec.pnr or '-'
            # re_book_obj = self.env[rec.res_model].sudo().browse(int(rec.res_id))
            # if not a.get(pnr):
            #     a[pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': ''}
            # a[pnr]['descs'].append(line.desc if line.desc else '')
            # a[pnr]['provider_type'] = re_book_obj and re_book_obj.provider_type_id.name or 'Reschedule'
            # for line_detail in line.invoice_line_detail_ids:
            #     a[pnr]['pax_data'].append({
            #         'name': (line_detail.desc if line_detail.desc else ''),
            #         'total': (line_detail.price_subtotal if line_detail.price_subtotal else '')
            #     })
        else:
            a = {'descs': self.format_description(line.desc), 'pnr': line.pnr.split(',') if line.pnr else '', 'line_detail': [], 'total_after_tax': line.total_after_tax}
            for line_detail in line.invoice_line_detail_ids:
                if apply_filter and line_detail.id not in inc_details:
                    reduce_amt += line_detail.price_subtotal
                    continue
                a['line_detail'].append({
                    'name': line_detail.desc,
                    'price': line_detail.price_unit,
                    'quantity': line_detail.quantity,
                    'amount': line_detail.price_subtotal
                })
            # if rec.provider_booking_ids:
            #     for provider in rec.provider_booking_ids:
            #         pnr = provider.pnr if provider.pnr else '-'
            #         if not a.get(pnr):
            #             a[pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': ''}
            #         a[pnr]['descs'].append(line.desc if line.desc else '')
            #         a[pnr]['provider_type'] = rec.provider_type_id.name
            #         for line_detail in line.invoice_line_detail_ids:
            #             a[pnr]['pax_data'].append({
            #                 'name': (line_detail.desc if line_detail.desc else ''),
            #                 'total': (line_detail.price_subtotal if line_detail.price_subtotal else '')
            #             })
            # else:
            #     pnr = '-'
            #     if not a.get(pnr):
            #         a[pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': ''}
            #     a[pnr]['descs'].append(line.desc if line.desc else '')
            #     a[pnr]['provider_type'] = rec.provider_type_id.name
            #     for line_detail in line.invoice_line_detail_ids:
            #         a[pnr]['pax_data'].append({
            #             'name': (line_detail.desc if line_detail.desc else ''),
            #             'total': (line_detail.price_subtotal if line_detail.price_subtotal else '')
            #         })
        if reduce_amt:
            a.update({
                'reduce_amt': reduce_amt
            })
        return a

    def calc_segments(self, rec, paxs):
        a = {}
        if rec._name == 'tt.reservation.hotel':
            for rec2 in rec.room_detail_ids:
                if not a.get(rec2.issued_name):
                    a[rec2.issued_name] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'total': 0}
                a[rec2.issued_name]['descs'].append( 'Hotel: ' + rec.hotel_name + '; Room: ' + rec2.room_name + ' ' + str(rec2.room_type) )
                a[rec2.issued_name]['total'] += rec2.sale_price
            for psg in rec.passenger_ids:
                a[rec.pnr]['pax_data'].append({
                    'name': (psg.first_name if psg.first_name else '') + ' ' + (psg.last_name if psg.last_name else ''),
                })
        elif rec._name == 'tt.reservation.airline':
            for provider in rec.provider_booking_ids:
                if not a.get(provider.pnr):
                    a[provider.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'total': rec.total}
                for journey in provider.journey_ids:
                    a[provider.pnr]['descs'].append(journey.origin_id.name + ' - ' + journey.destination_id.name + '; ' +
                                                    journey.departure_date + ' - ' + journey.arrival_date + '; ' +
                                                    journey.carrier_id.name + ' ' + journey.name)
                for ticket in provider.ticket_ids:
                    a[provider.pnr]['pax_data'].append({
                        'name': ticket.passenger_id.first_name + ' ' + (ticket.passenger_id.last_name if ticket.passenger_id.last_name else ''),
                        'total': 0
                    })
                for pax in a[provider.pnr]['pax_data']:
                    if a[provider.pnr]['pax_data'].get('pax_type'):
                        for price in provider.cost_service_charge_ids:
                            if pax.get('pax_type') == price.pax_type:
                                pax['total'] += price.amount / price.pax_total
            # for rec2 in rec.segment_ids:
            #     if not a.get(rec2.pnr):
            #         a[rec2.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': 'airline', 'total': rec.total}
            #     a[rec2.pnr]['descs'].append(rec2.origin_id.name + ' - ' + rec2.destination_id.name + '; ' +
            #                                 rec2.departure_date + ' - ' + rec2.arrival_date + '; ' +
            #                                 rec2.carrier_id.name + ' ' + rec2.name)

        elif rec._name == 'tt.reservation.activity':
            for provider in rec.provider_booking_ids:
                if not a.get(provider.pnr):
                    a[provider.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'total': rec.total}
                temp_desc = (provider.activity_id.name if provider.activity_id.name else '') + ' - ' + \
                            (provider.activity_product_id.name if provider.activity_product_id.name else '') + '; ' + \
                            (str(provider.visit_date) if provider.visit_date else '')
                if rec.timeslot:
                    temp_desc += ' ' + str(rec.timeslot) + '; '
                else:
                    temp_desc += '; '
                a[provider.pnr]['descs'].append(temp_desc)
                for ticket in provider.ticket_ids:
                    a[provider.pnr]['pax_data'].append({
                        'name': ticket.passenger_id.first_name + ' ' + (
                            ticket.passenger_id.last_name if ticket.passenger_id.last_name else ''),
                        'total': 0
                    })
                for pax in a[provider.pnr]['pax_data']:
                    if a[provider.pnr]['pax_data'].get('pax_type'):
                        for price in provider.cost_service_charge_ids:
                            if pax.get('pax_type') == price.pax_type:
                                pax['total'] += price.amount / price.pax_total

                # if not a.get(rec.pnr):
                #     a[rec.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': 'activity', 'total': rec.total}
                # temp_desc = (rec.activity_id.name if rec.activity_id.name else '') + ' - ' + \
                #             (rec.activity_product_id.name if rec.activity_product_id.name else '') + '; ' + \
                #             (str(rec.visit_date) if rec.visit_date else '')
                # if rec.timeslot:
                #     temp_desc += ' ' + str(rec.timeslot) + '; '
                # else:
                #     temp_desc += '; '
                # a[rec.pnr]['descs'].append(temp_desc)
        elif rec._name == 'tt.reservation.visa':
            pnr = rec.provider_booking_ids[0].pnr
            for rec2 in rec.provider_booking_ids:
                if not a.get(rec2.pnr):
                    a[rec2.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': 'visa', 'total': rec.total}
                for pax in rec2.passenger_ids:
                    a[rec2.pnr]['descs'].append('Visa : ' + (pax.passenger_id.first_name if pax.passenger_id.first_name else '') + ' ' +
                                                (pax.passenger_id.last_name if pax.passenger_id.last_name else '') + ', ' +
                                                (pax.passenger_id.title if pax.passenger_id.title else '') + ' ' +
                                                '( ' + (pax.pax_type if pax.pax_type else '') + ' ) ' +
                                                (pax.pricelist_id.entry_type if pax.pricelist_id.entry_type else '') + ' ' +
                                                (pax.pricelist_id.visa_type if pax.pricelist_id.visa_type else '') + ' ' +
                                                (pax.pricelist_id.process_type if pax.pricelist_id.process_type else '') + ' ' +
                                                '(' + (str(pax.pricelist_id.duration) if pax.pricelist_id.duration else '') + ' days)')
                for psg in rec.passenger_ids:
                    a[rec2.pnr]['pax_data'].append({
                        'name': (psg.first_name if psg.first_name else '') + ' ' + (psg.last_name if psg.last_name else ''),
                        'total': psg.pricelist_id.sale_price
                    })
        elif rec._name == 'tt.reservation.tour':
            for provider in rec.provider_booking_ids:
                if not a.get(provider.pnr):
                    a[provider.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'total': rec.total}
                temp_desc = (provider.tour_id.name if provider.tour_id.name else '') + '; ' + (str(provider.departure_date)[:10] if provider.departure_date else '') + ' - ' + (str(provider.arrival_date)[:10] if provider.arrival_date else '') + '; '
                a[provider.pnr]['descs'].append(temp_desc)
                for ticket in provider.ticket_ids:
                    a[provider.pnr]['pax_data'].append({
                        'name': ticket.passenger_id.first_name + ' ' + (
                            ticket.passenger_id.last_name if ticket.passenger_id.last_name else ''),
                        'total': 0
                    })
                for pax in a[provider.pnr]['pax_data']:
                    if a[provider.pnr]['pax_data'].get('pax_type'):
                        for price in provider.cost_service_charge_ids:
                            if pax.get('pax_type') == price.pax_type:
                                pax['total'] += price.amount / price.pax_total
        elif rec._name == 'tt.reservation.offline':
            if rec.provider_type_id_name == 'hotel':
                for rec2 in rec.line_ids:
                    if not a.get(rec2.pnr):
                        a[rec2.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': 'hotel', 'total': rec.total}
                    a[rec2.pnr]['descs'].append('Hotel: ' + (rec2.hotel_name if rec2.hotel_name else '') +
                                                '; Room: ' + (rec2.room if rec2.room else '') + ' ' +
                                                str(rec2.meal_type if rec2.meal_type else ''))
                    for psg in rec.passenger_ids:
                        a[rec2.pnr]['pax_data'].append({
                            'name': (psg.first_name if psg.first_name else '') + ' ' + (psg.last_name if psg.last_name else ''),
                            'provider_type': 'hotel',
                            'total': 0
                        })
            elif rec.provider_type_id_name == 'airline':
                for rec2 in rec.line_ids:
                    if not a.get(rec2.pnr):
                        a[rec2.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': 'airline', 'total': rec.total}
                    a[rec2.pnr]['descs'].append((rec2.origin_id.name if rec2.origin_id.name else '') + ' - ' +
                                                (rec2.destination_id.name if rec2.destination_id.name else '') + '; ' +
                                                str(rec2.departure_date if rec2.departure_date else '') + ' - ' +
                                                str(rec2.arrival_date if rec2.arrival_date else '') + '; ' +
                                                (rec2.carrier_id.name if rec2.carrier_id.name else '') + ' ' +
                                                (rec2.carrier_code if rec2.carrier_code else '') + ' - ' +
                                                (rec2.carrier_number if rec2.carrier_number else '') + ' ')
                    for psg in rec.passenger_ids:
                        a[rec2.pnr]['pax_data'].append({
                            'name': (psg.first_name if psg.first_name else '') + ' ' + (psg.last_name if psg.last_name else ''),
                            'provider_type': 'airline',
                            'total': 0
                        })
                    for pax in a[rec2.pnr]['pax_data']:
                        pax['total'] = rec.total / len(rec.passenger_ids)
            elif rec.provider_type_id_name == 'activity':
                for rec2 in rec.line_ids:
                    if not a.get(rec2.pnr):
                        a[rec2.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': 'activity', 'total': rec.total}
                    temp_desc = (rec2.activity_name.name if rec2.activity_name.name else '') + ' - ' + \
                                (rec2.activity_package.name if rec2.activity_package.name else '') + '; ' + \
                                (str(rec2.check_in) if rec2.check_in else '')
                    if rec2.activity_timeslot:
                        temp_desc += ' ' + str(rec2.activity_timeslot) + '; '
                    else:
                        temp_desc += '; '
                    a[rec2.pnr]['descs'].append(temp_desc)
                    for psg in rec.passenger_ids:
                        a[rec2.pnr]['pax_data'].append({
                            'name': (psg.first_name if psg.first_name else '') + ' ' + (psg.last_name if psg.last_name else ''),
                            'total': 0
                        })
                    for pax in a[rec2.pnr]['pax_data']:
                        pax['total'] = rec.total / len(rec.passenger_ids)
        return a

    # Get Terbilang dkk di hapus
    def compute_terbilang_from_objs(self, recs, currency_str='rupiah'):
        a = {}
        for rec2 in recs:
            a.update({rec2.name: num2words(rec2.grand_total) + ' Rupiah'})
        return a

    def compute_terbilang_from_objs_dynamic(self, recs, reduce_amt, currency_str='rupiah'):
        a = {}
        for rec2 in recs:
            final_amt = reduce_amt.get(rec2.id) and rec2.grand_total - reduce_amt[rec2.id] or rec2.grand_total
            a.update({rec2.name: num2words(final_amt) + ' Rupiah'})
        return a

    @api.model
    def _get_report_values(self, docids, data=None):
        # Print dari BackEnd bisa digunakan untuk Resv maupun invoice
        if not data.get('context'):
            data['context'] = {
                'active_model': 'tt.reservation.airline',
                'active_ids': docids
            }
        add_data = data.get('data', {})
        values = {}
        reduce_amt = {}
        val = {}
        header_width = 90
        resv_obj = False
        agent_id = False
        doc_objs = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        is_dynamic_print = add_data.get('is_dynamic_print') and add_data['is_dynamic_print'] or False
        for rec in doc_objs:
            values[rec.id] = []
            reduce_amt[rec.id] = 0
            for rec2 in rec.invoice_line_ids:
                resv_obj = self.env[rec2.res_model_resv].browse(rec2.res_id_resv)
                if is_dynamic_print:
                    included_detail_ids = add_data.get('included_detail_ids') and add_data['included_detail_ids'] or []
                else:
                    included_detail_ids = []
                inv_line_data = self.get_invoice_data(rec2, resv_obj, rec, included_detail_ids)
                if inv_line_data.get('reduce_amt'):
                    reduce_amt[rec.id] += inv_line_data['reduce_amt']
                if is_dynamic_print and not inv_line_data.get('line_detail'):
                    continue
                values[rec.id].append(inv_line_data)
                # values[rec.id].append(self.calc_segments(resv_obj, resv_obj.passenger_ids))
            agent_id = rec.agent_id
        invoice_footer = self.env['tt.report.common.setting'].get_footer('agent_invoice', agent_id)
        if reduce_amt:
            terbilang = self.compute_terbilang_from_objs_dynamic(self.env[data['context']['active_model']].browse(data['context']['active_ids']), reduce_amt)
        else:
            terbilang = self.compute_terbilang_from_objs(self.env[data['context']['active_model']].browse(data['context']['active_ids']))

        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()
        val = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'docs': doc_objs,
            'inv_lines': values,
            'is_dynamic_print': is_dynamic_print,
            'reduce_amt': reduce_amt,
            'header_width': str(header_width),
            'terbilang': terbilang,
            'invoice_footer': invoice_footer and invoice_footer[0].html or '',
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');",
            'is_invoice': True
        }
        if resv_obj._name in ['tt.reservation.phc', 'tt.reservation.periksain', 'tt.reservation.medical', 'tt.reservation.mitrakeluarga']:
            val.update({
                'terms_conditions': resv_obj.get_terms_conditions_email()
            })
        if resv_obj._name in ['tt.reservation.medical', 'tt.reservation.mitrakeluarga']:
            val.update({
                'qr_code_data': resv_obj.to_dict()
            })
        return val


class PrintoutInvoiceHOINV(models.AbstractModel):
    _name = 'report.tt_report_common.printout_invoice_hoinv'
    _description = 'Report Common Printout HO Invoice'

    """Abstract Model for report template.
        for `_name` model, please use `report.` as prefix then add `module_name.report_name`.
    """
    def format_description(self, desc_str):
        # desc_str.replace('\n','&lt;br/&gt;')
        return desc_str

    def get_invoice_data(self, line, rec, inv):
        a = {}
        if rec._name == 'tt.reservation.offline':
            a = {'descs': self.format_description(line.desc), 'pnr': inv.pnr.split(','), 'line_detail': [], 'total_after_tax': line.total_after_tax}
            # for provider in rec.provider_booking_ids:
            #     a['pnr'].append(provider.pnr)
            for line_detail in line.invoice_line_detail_ids:
                a['line_detail'].append({
                    'name': line_detail.desc,
                    'price': line_detail.price_unit,
                    'quantity': line_detail.quantity,
                    'amount': line_detail.price_subtotal
                })
            # if rec.line_ids:
            #     for rec2 in rec.line_ids:
            #         if rec.offline_provider_type != 'hotel':
            #             pnr_same = True
            #             pnr = rec2.pnr if rec2.pnr else '-'
            #             if not a.get(pnr):
            #                 pnr_same = False
            #                 a[pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [],
            #                           'provider_type': ''}
            #             if not pnr_same:
            #                 a[pnr]['descs'].append(rec2.get_line_description())
            #                 a[pnr]['provider_type'] = rec.provider_type_id.name
            #
            #                 for provider in rec.provider_booking_ids:
            #                     if provider.pnr == pnr:
            #                         div_amount = 0
            #                         for line2 in rec.line_ids:
            #                             if line2.pnr == pnr:
            #                                 div_amount += 1
            #                         for line_detail in line.invoice_line_detail_ids:
            #                             a[pnr]['pax_data'].append({
            #                                 'name': (line_detail.desc if line_detail.desc else ''),
            #                                 'total': (line_detail.price_subtotal/len(rec.line_ids)*div_amount if line_detail.price_subtotal else 0)
            #                             })
            #                         break
            #         else:
            #             pnr_same = True
            #             pnr = rec2.pnr if rec2.pnr else '-'
            #             if not a.get(pnr):
            #                 pnr_same = False
            #                 a[pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [],
            #                           'provider_type': ''}
            #             a[pnr]['descs'].append(line.desc if line.desc else '')
            #             a[pnr]['provider_type'] = rec.provider_type_id.name
            #             a[pnr]['pax_data'].append({
            #                 'name': (rec2.get_line_hotel_description() if rec2.get_line_hotel_description() else ''),
            #                 'total': rec.total / len(rec.line_ids)
            #             })
            # else:
            #     for rec2 in rec.provider_booking_ids:
            #         pnr = rec2.pnr if rec2.pnr else '-'
            #         if not a.get(pnr):
            #             a[pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': ''}
            #         a[pnr]['descs'].append(line.desc if line.desc else '')
            #         a[pnr]['provider_type'] = rec.provider_type_id.name
            #         for line_detail in line.invoice_line_detail_ids:
            #             a[pnr]['pax_data'].append({
            #                 'name': (line_detail.desc if line_detail.desc else ''),
            #                 'total': (line_detail.price_subtotal if line_detail.price_subtotal else '')
            #             })
        elif rec._name == 'tt.reservation.hotel':
            a = {'descs': self.format_description(line.desc), 'pnr': [], 'line_detail': [], 'total_after_tax': line.total_after_tax}
            for room in rec.room_detail_ids:
                if room.issued_name and room.issued_name not in a['pnr']:
                    a['pnr'].append(room.issued_name)
            for line_detail in line.invoice_line_detail_ids:
                a['line_detail'].append({
                    'name': line_detail.desc,
                    'price': line_detail.price_unit,
                    'quantity': line_detail.quantity,
                    'amount': line_detail.price_subtotal
                })
            # if rec.room_detail_ids:
            # for rec2 in rec.room_detail_ids:
            #     issued_name = rec2.issued_name if rec2.issued_name else '-'
            #     if not a.get(issued_name):
            #         a[issued_name] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [],
            #                           'provider_type': ''}
            #     a[issued_name]['descs'].append(line.desc if line.desc else '')
            #     a[issued_name]['provider_type'] = rec.provider_type_id.name
            #     for line_detail in line.invoice_line_detail_ids:
            #         a[issued_name]['pax_data'].append({
            #             'name': (line_detail.desc if line_detail.desc else ''),
            #             'total': (line_detail.price_subtotal if line_detail.price_subtotal else '')
            #         })
            # else:
            # issued_name = '-'
            # if not a.get(issued_name):
            #     a[issued_name] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [],
            #                       'provider_type': ''}
            # a[issued_name]['descs'].append(line.desc if line.desc else '')
            # a[issued_name]['provider_type'] = rec.provider_type_id.name
            # for line_detail in line.invoice_line_detail_ids:
            #     a[issued_name]['pax_data'].append({
            #         'name': (line_detail.desc if line_detail.desc else ''),
            #         'total': (line_detail.price_subtotal if line_detail.price_subtotal else '')
            #     })
        elif rec._name == 'tt.reschedule':
            a = {'descs': self.format_description(line.desc), 'pnr': [], 'line_detail': [], 'total_after_tax': line.total_after_tax}
            a['pnr'].append(rec.pnr or '-')
            for line_detail in line.invoice_line_detail_ids:
                a['line_detail'].append({
                    'name': line_detail.desc,
                    'price': line_detail.price_unit,
                    'quantity': line_detail.quantity,
                    'amount': line_detail.price_subtotal
                })
            # pnr = rec.pnr and rec.pnr or '-'
            # re_book_obj = self.env[rec.res_model].sudo().browse(int(rec.res_id))
            # if not a.get(pnr):
            #     a[pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': ''}
            # a[pnr]['descs'].append(line.desc if line.desc else '')
            # a[pnr]['provider_type'] = re_book_obj and re_book_obj.provider_type_id.name or 'Reschedule'
            # for line_detail in line.invoice_line_detail_ids:
            #     a[pnr]['pax_data'].append({
            #         'name': (line_detail.desc if line_detail.desc else ''),
            #         'total': (line_detail.price_subtotal if line_detail.price_subtotal else '')
            #     })
        else:
            a = {'descs': self.format_description(line.desc), 'pnr': line.pnr.split(',') if line.pnr else '', 'line_detail': [], 'total_after_tax': line.total_after_tax}
            for line_detail in line.invoice_line_detail_ids:
                if not line_detail.commission_agent_id or line_detail.commission_agent_id.id == line.invoice_id.agent_id.id:
                    a['line_detail'].append({
                        'name': line_detail.desc,
                        'price': line_detail.price_unit,
                        'quantity': line_detail.quantity,
                        'amount': line_detail.price_subtotal
                    })
            # if rec.provider_booking_ids:
            #     for provider in rec.provider_booking_ids:
            #         pnr = provider.pnr if provider.pnr else '-'
            #         if not a.get(pnr):
            #             a[pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': ''}
            #         a[pnr]['descs'].append(line.desc if line.desc else '')
            #         a[pnr]['provider_type'] = rec.provider_type_id.name
            #         for line_detail in line.invoice_line_detail_ids:
            #             a[pnr]['pax_data'].append({
            #                 'name': (line_detail.desc if line_detail.desc else ''),
            #                 'total': (line_detail.price_subtotal if line_detail.price_subtotal else '')
            #             })
            # else:
            #     pnr = '-'
            #     if not a.get(pnr):
            #         a[pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': ''}
            #     a[pnr]['descs'].append(line.desc if line.desc else '')
            #     a[pnr]['provider_type'] = rec.provider_type_id.name
            #     for line_detail in line.invoice_line_detail_ids:
            #         a[pnr]['pax_data'].append({
            #             'name': (line_detail.desc if line_detail.desc else ''),
            #             'total': (line_detail.price_subtotal if line_detail.price_subtotal else '')
            #         })
        return a

    def calc_segments(self, rec, paxs):
        a = {}
        if rec._name == 'tt.reservation.hotel':
            for rec2 in rec.room_detail_ids:
                if not a.get(rec2.issued_name):
                    a[rec2.issued_name] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'total': 0}
                a[rec2.issued_name]['descs'].append( 'Hotel: ' + rec.hotel_name + '; Room: ' + rec2.room_name + ' ' + str(rec2.room_type) )
                a[rec2.issued_name]['total'] += rec2.sale_price
            for psg in rec.passenger_ids:
                a[rec.pnr]['pax_data'].append({
                    'name': (psg.first_name if psg.first_name else '') + ' ' + (psg.last_name if psg.last_name else ''),
                })
        elif rec._name == 'tt.reservation.airline':
            for provider in rec.provider_booking_ids:
                if not a.get(provider.pnr):
                    a[provider.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'total': rec.total}
                for journey in provider.journey_ids:
                    a[provider.pnr]['descs'].append(journey.origin_id.name + ' - ' + journey.destination_id.name + '; ' +
                                                    journey.departure_date + ' - ' + journey.arrival_date + '; ' +
                                                    journey.carrier_id.name + ' ' + journey.name)
                for ticket in provider.ticket_ids:
                    a[provider.pnr]['pax_data'].append({
                        'name': ticket.passenger_id.first_name + ' ' + (ticket.passenger_id.last_name if ticket.passenger_id.last_name else ''),
                        'total': 0
                    })
                for pax in a[provider.pnr]['pax_data']:
                    if a[provider.pnr]['pax_data'].get('pax_type'):
                        for price in provider.cost_service_charge_ids:
                            if pax.get('pax_type') == price.pax_type:
                                pax['total'] += price.amount / price.pax_total
            # for rec2 in rec.segment_ids:
            #     if not a.get(rec2.pnr):
            #         a[rec2.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': 'airline', 'total': rec.total}
            #     a[rec2.pnr]['descs'].append(rec2.origin_id.name + ' - ' + rec2.destination_id.name + '; ' +
            #                                 rec2.departure_date + ' - ' + rec2.arrival_date + '; ' +
            #                                 rec2.carrier_id.name + ' ' + rec2.name)

        elif rec._name == 'tt.reservation.activity':
            for provider in rec.provider_booking_ids:
                if not a.get(provider.pnr):
                    a[provider.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'total': rec.total}
                temp_desc = (provider.activity_id.name if provider.activity_id.name else '') + ' - ' + \
                            (provider.activity_product_id.name if provider.activity_product_id.name else '') + '; ' + \
                            (str(provider.visit_date) if provider.visit_date else '')
                if rec.timeslot:
                    temp_desc += ' ' + str(rec.timeslot) + '; '
                else:
                    temp_desc += '; '
                a[provider.pnr]['descs'].append(temp_desc)
                for ticket in provider.ticket_ids:
                    a[provider.pnr]['pax_data'].append({
                        'name': ticket.passenger_id.first_name + ' ' + (
                            ticket.passenger_id.last_name if ticket.passenger_id.last_name else ''),
                        'total': 0
                    })
                for pax in a[provider.pnr]['pax_data']:
                    if a[provider.pnr]['pax_data'].get('pax_type'):
                        for price in provider.cost_service_charge_ids:
                            if pax.get('pax_type') == price.pax_type:
                                pax['total'] += price.amount / price.pax_total

                # if not a.get(rec.pnr):
                #     a[rec.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': 'activity', 'total': rec.total}
                # temp_desc = (rec.activity_id.name if rec.activity_id.name else '') + ' - ' + \
                #             (rec.activity_product_id.name if rec.activity_product_id.name else '') + '; ' + \
                #             (str(rec.visit_date) if rec.visit_date else '')
                # if rec.timeslot:
                #     temp_desc += ' ' + str(rec.timeslot) + '; '
                # else:
                #     temp_desc += '; '
                # a[rec.pnr]['descs'].append(temp_desc)
        elif rec._name == 'tt.reservation.visa':
            pnr = rec.provider_booking_ids[0].pnr
            for rec2 in rec.provider_booking_ids:
                if not a.get(rec2.pnr):
                    a[rec2.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': 'visa', 'total': rec.total}
                for pax in rec2.passenger_ids:
                    a[rec2.pnr]['descs'].append('Visa : ' + (pax.passenger_id.first_name if pax.passenger_id.first_name else '') + ' ' +
                                                (pax.passenger_id.last_name if pax.passenger_id.last_name else '') + ', ' +
                                                (pax.passenger_id.title if pax.passenger_id.title else '') + ' ' +
                                                '( ' + (pax.pax_type if pax.pax_type else '') + ' ) ' +
                                                (pax.pricelist_id.entry_type if pax.pricelist_id.entry_type else '') + ' ' +
                                                (pax.pricelist_id.visa_type if pax.pricelist_id.visa_type else '') + ' ' +
                                                (pax.pricelist_id.process_type if pax.pricelist_id.process_type else '') + ' ' +
                                                '(' + (str(pax.pricelist_id.duration) if pax.pricelist_id.duration else '') + ' days)')
                for psg in rec.passenger_ids:
                    a[rec2.pnr]['pax_data'].append({
                        'name': (psg.first_name if psg.first_name else '') + ' ' + (psg.last_name if psg.last_name else ''),
                        'total': psg.pricelist_id.sale_price
                    })
        elif rec._name == 'tt.reservation.tour':
            for provider in rec.provider_booking_ids:
                if not a.get(provider.pnr):
                    a[provider.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'total': rec.total}
                temp_desc = (provider.tour_id.name if provider.tour_id.name else '') + '; ' + (str(provider.departure_date)[:10] if provider.departure_date else '') + ' - ' + (str(provider.arrival_date)[:10] if provider.arrival_date else '') + '; '
                a[provider.pnr]['descs'].append(temp_desc)
                for ticket in provider.ticket_ids:
                    a[provider.pnr]['pax_data'].append({
                        'name': ticket.passenger_id.first_name + ' ' + (
                            ticket.passenger_id.last_name if ticket.passenger_id.last_name else ''),
                        'total': 0
                    })
                for pax in a[provider.pnr]['pax_data']:
                    if a[provider.pnr]['pax_data'].get('pax_type'):
                        for price in provider.cost_service_charge_ids:
                            if pax.get('pax_type') == price.pax_type:
                                pax['total'] += price.amount / price.pax_total
        elif rec._name == 'tt.reservation.offline':
            if rec.provider_type_id_name == 'hotel':
                for rec2 in rec.line_ids:
                    if not a.get(rec2.pnr):
                        a[rec2.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': 'hotel', 'total': rec.total}
                    a[rec2.pnr]['descs'].append('Hotel: ' + (rec2.hotel_name if rec2.hotel_name else '') +
                                                '; Room: ' + (rec2.room if rec2.room else '') + ' ' +
                                                str(rec2.meal_type if rec2.meal_type else ''))
                    for psg in rec.passenger_ids:
                        a[rec2.pnr]['pax_data'].append({
                            'name': (psg.first_name if psg.first_name else '') + ' ' + (psg.last_name if psg.last_name else ''),
                            'provider_type': 'hotel',
                            'total': 0
                        })
            elif rec.provider_type_id_name == 'airline':
                for rec2 in rec.line_ids:
                    if not a.get(rec2.pnr):
                        a[rec2.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': 'airline', 'total': rec.total}
                    a[rec2.pnr]['descs'].append((rec2.origin_id.name if rec2.origin_id.name else '') + ' - ' +
                                                (rec2.destination_id.name if rec2.destination_id.name else '') + '; ' +
                                                str(rec2.departure_date if rec2.departure_date else '') + ' - ' +
                                                str(rec2.arrival_date if rec2.arrival_date else '') + '; ' +
                                                (rec2.carrier_id.name if rec2.carrier_id.name else '') + ' ' +
                                                (rec2.carrier_code if rec2.carrier_code else '') + ' - ' +
                                                (rec2.carrier_number if rec2.carrier_number else '') + ' ')
                    for psg in rec.passenger_ids:
                        a[rec2.pnr]['pax_data'].append({
                            'name': (psg.first_name if psg.first_name else '') + ' ' + (psg.last_name if psg.last_name else ''),
                            'provider_type': 'airline',
                            'total': 0
                        })
                    for pax in a[rec2.pnr]['pax_data']:
                        pax['total'] = rec.total / len(rec.passenger_ids)
            elif rec.provider_type_id_name == 'activity':
                for rec2 in rec.line_ids:
                    if not a.get(rec2.pnr):
                        a[rec2.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': 'activity', 'total': rec.total}
                    temp_desc = (rec2.activity_name.name if rec2.activity_name.name else '') + ' - ' + \
                                (rec2.activity_package.name if rec2.activity_package.name else '') + '; ' + \
                                (str(rec2.check_in) if rec2.check_in else '')
                    if rec2.activity_timeslot:
                        temp_desc += ' ' + str(rec2.activity_timeslot) + '; '
                    else:
                        temp_desc += '; '
                    a[rec2.pnr]['descs'].append(temp_desc)
                    for psg in rec.passenger_ids:
                        a[rec2.pnr]['pax_data'].append({
                            'name': (psg.first_name if psg.first_name else '') + ' ' + (psg.last_name if psg.last_name else ''),
                            'total': 0
                        })
                    for pax in a[rec2.pnr]['pax_data']:
                        pax['total'] = rec.total / len(rec.passenger_ids)
        return a

    # Get Terbilang dkk di hapus
    def compute_terbilang_from_objs(self, recs, currency_str='rupiah'):
        a = {}
        for rec2 in recs:
            a.update({rec2.name: num2words(rec2.grand_total) + ' Rupiah'})
        return a

    @api.model
    def _get_report_values(self, docids, data=None):
        # Print dari BackEnd bisa digunakan untuk Resv maupun invoice
        if not data.get('context'):
            data['context'] = {
                'active_model': 'tt.reservation.airline',
                'active_ids': docids
            }
        values = {}
        payment_values = {}
        pay_method = {}
        point_reward = {}
        val = {}
        header_width = 90
        resv_obj = False
        agent_id = False
        doc_objs = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        for rec in doc_objs:
            values[rec.id] = []
            payment_values[rec.id] = []
            point_reward[rec.id] = 0
            agent_id = rec.agent_id
            for rec2 in rec.invoice_line_ids:
                resv_obj = self.env[rec2.res_model_resv].browse(rec2.res_id_resv)
                temp_data = self.get_invoice_data(rec2, resv_obj, rec)

                line_detail = []
                for temp_data_line in temp_data['line_detail']:
                    if temp_data_line['name'] == 'Use Point Reward':
                        payment_values[rec.id].append({
                            'name': temp_data_line['name'],
                            'description': 'State: Confirm',
                            'amount': temp_data_line['amount'],
                        })
                        point_reward[rec.id] += temp_data_line['amount']
                    else:
                        line_detail.append(temp_data_line)
                temp_data['line_detail'] = line_detail
                values[rec.id].append(temp_data)

            # Ambil Payment Method STD
            pay_method[rec.id] = 'Credit Limit' if rec.is_use_credit_limit else 'Balance'
            for payment_line in rec.payment_ids:
                payment_values[rec.id].append({
                    'name': pay_method[rec.id],
                    'description': 'State: ' + payment_line.state,
                    'amount': payment_line.pay_amount,
                })
            pnr_length = len(rec.pnr) if rec.pnr else len(rec.name)
        invoice_footer = self.env['tt.report.common.setting'].get_footer('agent_invoice', agent_id)
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()
        val = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'doc_type': 'ho_invoice',
            'docs': doc_objs,
            'inv_lines': values,

            'payment_lines': payment_values,
            'pay_method': pay_method,
            'point_reward': point_reward,

            'pnr_length': pnr_length,
            'header_width': str(header_width),
            'terbilang': self.compute_terbilang_from_objs(self.env[data['context']['active_model']].browse(data['context']['active_ids'])),
            'invoice_footer': invoice_footer and invoice_footer[0].html or '',
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');",
            'ho_obj': resv_obj.ho_id or False,
            'is_invoice': True
        }
        if resv_obj._name in ['tt.reservation.phc', 'tt.reservation.periksain', 'tt.reservation.medical', 'tt.reservation.mitrakeluarga']:
            val.update({
                'terms_conditions': resv_obj.get_terms_conditions_email()
            })
        if resv_obj._name in ['tt.reservation.medical', 'tt.reservation.mitrakeluarga']:
            val.update({
                'qr_code_data': resv_obj.to_dict()
            })
        return val


class PrintoutKwintasi(models.AbstractModel):
    _name = 'report.tt_report_common.printout_kwitansi'
    _description = 'Report Common Printout Kwitansi'

    """Abstract Model for report template.
        for `_name` model, please use `report.` as prefix then add `module_name.report_name`.
    """
    def format_description(self, desc_str):
        # desc_str.replace('\n','&lt;br/&gt;')
        return desc_str

    def get_invoice_data(self, line, rec, inv):
        a = {}
        if rec._name == 'tt.reservation.offline':
            a = {'descs': self.format_description(line.desc), 'pnr': inv.pnr.split(','), 'line_detail': [], 'total_after_tax': line.total_after_tax}
            # for provider in rec.provider_booking_ids:
            #     a['pnr'].append(provider.pnr)
            for line_detail in line.invoice_line_detail_ids:
                a['line_detail'].append({
                    'name': line_detail.desc,
                    'price': line_detail.price_unit,
                    'quantity': line_detail.quantity,
                    'amount': line_detail.price_subtotal
                })
            # if rec.line_ids:
            #     for rec2 in rec.line_ids:
            #         if rec.offline_provider_type != 'hotel':
            #             pnr_same = True
            #             pnr = rec2.pnr if rec2.pnr else '-'
            #             if not a.get(pnr):
            #                 pnr_same = False
            #                 a[pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [],
            #                           'provider_type': ''}
            #             if not pnr_same:
            #                 a[pnr]['descs'].append(rec2.get_line_description())
            #                 a[pnr]['provider_type'] = rec.provider_type_id.name
            #
            #                 for provider in rec.provider_booking_ids:
            #                     if provider.pnr == pnr:
            #                         div_amount = 0
            #                         for line2 in rec.line_ids:
            #                             if line2.pnr == pnr:
            #                                 div_amount += 1
            #                         for line_detail in line.invoice_line_detail_ids:
            #                             a[pnr]['pax_data'].append({
            #                                 'name': (line_detail.desc if line_detail.desc else ''),
            #                                 'total': (line_detail.price_subtotal/len(rec.line_ids)*div_amount if line_detail.price_subtotal else 0)
            #                             })
            #                         break
            #         else:
            #             pnr_same = True
            #             pnr = rec2.pnr if rec2.pnr else '-'
            #             if not a.get(pnr):
            #                 pnr_same = False
            #                 a[pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [],
            #                           'provider_type': ''}
            #             a[pnr]['descs'].append(line.desc if line.desc else '')
            #             a[pnr]['provider_type'] = rec.provider_type_id.name
            #             a[pnr]['pax_data'].append({
            #                 'name': (rec2.get_line_hotel_description() if rec2.get_line_hotel_description() else ''),
            #                 'total': rec.total / len(rec.line_ids)
            #             })
            # else:
            #     for rec2 in rec.provider_booking_ids:
            #         pnr = rec2.pnr if rec2.pnr else '-'
            #         if not a.get(pnr):
            #             a[pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': ''}
            #         a[pnr]['descs'].append(line.desc if line.desc else '')
            #         a[pnr]['provider_type'] = rec.provider_type_id.name
            #         for line_detail in line.invoice_line_detail_ids:
            #             a[pnr]['pax_data'].append({
            #                 'name': (line_detail.desc if line_detail.desc else ''),
            #                 'total': (line_detail.price_subtotal if line_detail.price_subtotal else '')
            #             })
        elif rec._name == 'tt.reservation.hotel':
            a = {'descs': self.format_description(line.desc), 'pnr': [], 'line_detail': [], 'total_after_tax': line.total_after_tax}
            for room in rec.room_detail_ids:
                if room.issued_name and room.issued_name not in a['pnr']:
                    a['pnr'].append(room.issued_name)
            for line_detail in line.invoice_line_detail_ids:
                a['line_detail'].append({
                    'name': line_detail.desc,
                    'price': line_detail.price_unit,
                    'quantity': line_detail.quantity,
                    'amount': line_detail.price_subtotal
                })
            # if rec.room_detail_ids:
            # for rec2 in rec.room_detail_ids:
            #     issued_name = rec2.issued_name if rec2.issued_name else '-'
            #     if not a.get(issued_name):
            #         a[issued_name] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [],
            #                           'provider_type': ''}
            #     a[issued_name]['descs'].append(line.desc if line.desc else '')
            #     a[issued_name]['provider_type'] = rec.provider_type_id.name
            #     for line_detail in line.invoice_line_detail_ids:
            #         a[issued_name]['pax_data'].append({
            #             'name': (line_detail.desc if line_detail.desc else ''),
            #             'total': (line_detail.price_subtotal if line_detail.price_subtotal else '')
            #         })
            # else:
            # issued_name = '-'
            # if not a.get(issued_name):
            #     a[issued_name] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [],
            #                       'provider_type': ''}
            # a[issued_name]['descs'].append(line.desc if line.desc else '')
            # a[issued_name]['provider_type'] = rec.provider_type_id.name
            # for line_detail in line.invoice_line_detail_ids:
            #     a[issued_name]['pax_data'].append({
            #         'name': (line_detail.desc if line_detail.desc else ''),
            #         'total': (line_detail.price_subtotal if line_detail.price_subtotal else '')
            #     })
        elif rec._name == 'tt.reschedule':
            a = {'descs': self.format_description(line.desc), 'pnr': [], 'line_detail': [], 'total_after_tax': line.total_after_tax}
            a['pnr'].append(rec.pnr or '-')
            for line_detail in line.invoice_line_detail_ids:
                a['line_detail'].append({
                    'name': line_detail.desc,
                    'price': line_detail.price_unit,
                    'quantity': line_detail.quantity,
                    'amount': line_detail.price_subtotal
                })
            # pnr = rec.pnr and rec.pnr or '-'
            # re_book_obj = self.env[rec.res_model].sudo().browse(int(rec.res_id))
            # if not a.get(pnr):
            #     a[pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': ''}
            # a[pnr]['descs'].append(line.desc if line.desc else '')
            # a[pnr]['provider_type'] = re_book_obj and re_book_obj.provider_type_id.name or 'Reschedule'
            # for line_detail in line.invoice_line_detail_ids:
            #     a[pnr]['pax_data'].append({
            #         'name': (line_detail.desc if line_detail.desc else ''),
            #         'total': (line_detail.price_subtotal if line_detail.price_subtotal else '')
            #     })
        else:
            a = {'descs': self.format_description(line.desc), 'pnr': inv.pnr.split(','), 'line_detail': [], 'total_after_tax': line.total_after_tax}
            for line_detail in line.invoice_line_detail_ids:
                a['line_detail'].append({
                    'name': line_detail.desc,
                    'price': line_detail.price_unit,
                    'quantity': line_detail.quantity,
                    'amount': line_detail.price_subtotal
                })
            # if rec.provider_booking_ids:
            #     for provider in rec.provider_booking_ids:
            #         pnr = provider.pnr if provider.pnr else '-'
            #         if not a.get(pnr):
            #             a[pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': ''}
            #         a[pnr]['descs'].append(line.desc if line.desc else '')
            #         a[pnr]['provider_type'] = rec.provider_type_id.name
            #         for line_detail in line.invoice_line_detail_ids:
            #             a[pnr]['pax_data'].append({
            #                 'name': (line_detail.desc if line_detail.desc else ''),
            #                 'total': (line_detail.price_subtotal if line_detail.price_subtotal else '')
            #             })
            # else:
            #     pnr = '-'
            #     if not a.get(pnr):
            #         a[pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': ''}
            #     a[pnr]['descs'].append(line.desc if line.desc else '')
            #     a[pnr]['provider_type'] = rec.provider_type_id.name
            #     for line_detail in line.invoice_line_detail_ids:
            #         a[pnr]['pax_data'].append({
            #             'name': (line_detail.desc if line_detail.desc else ''),
            #             'total': (line_detail.price_subtotal if line_detail.price_subtotal else '')
            #         })
        return a

    def calc_segments(self, rec, paxs):
        a = {}
        if rec._name == 'tt.reservation.hotel':
            for rec2 in rec.room_detail_ids:
                if not a.get(rec2.issued_name):
                    a[rec2.issued_name] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'total': 0}
                a[rec2.issued_name]['descs'].append( 'Hotel: ' + rec.hotel_name + '; Room: ' + rec2.room_name + ' ' + str(rec2.room_type) )
                a[rec2.issued_name]['total'] += rec2.sale_price
            for psg in rec.passenger_ids:
                a[rec.pnr]['pax_data'].append({
                    'name': (psg.first_name if psg.first_name else '') + ' ' + (psg.last_name if psg.last_name else ''),
                })
        elif rec._name == 'tt.reservation.airline':
            for provider in rec.provider_booking_ids:
                if not a.get(provider.pnr):
                    a[provider.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'total': rec.total}
                for journey in provider.journey_ids:
                    a[provider.pnr]['descs'].append(journey.origin_id.name + ' - ' + journey.destination_id.name + '; ' +
                                                    journey.departure_date + ' - ' + journey.arrival_date + '; ' +
                                                    journey.carrier_id.name + ' ' + journey.name)
                for ticket in provider.ticket_ids:
                    a[provider.pnr]['pax_data'].append({
                        'name': ticket.passenger_id.first_name + ' ' + (ticket.passenger_id.last_name if ticket.passenger_id.last_name else ''),
                        'total': 0
                    })
                for pax in a[provider.pnr]['pax_data']:
                    if a[provider.pnr]['pax_data'].get('pax_type'):
                        for price in provider.cost_service_charge_ids:
                            if pax.get('pax_type') == price.pax_type:
                                pax['total'] += price.amount / price.pax_total
            # for rec2 in rec.segment_ids:
            #     if not a.get(rec2.pnr):
            #         a[rec2.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': 'airline', 'total': rec.total}
            #     a[rec2.pnr]['descs'].append(rec2.origin_id.name + ' - ' + rec2.destination_id.name + '; ' +
            #                                 rec2.departure_date + ' - ' + rec2.arrival_date + '; ' +
            #                                 rec2.carrier_id.name + ' ' + rec2.name)

        elif rec._name == 'tt.reservation.activity':
            for provider in rec.provider_booking_ids:
                if not a.get(provider.pnr):
                    a[provider.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'total': rec.total}
                temp_desc = (provider.activity_id.name if provider.activity_id.name else '') + ' - ' + \
                            (provider.activity_product_id.name if provider.activity_product_id.name else '') + '; ' + \
                            (str(provider.visit_date) if provider.visit_date else '')
                if rec.timeslot:
                    temp_desc += ' ' + str(rec.timeslot) + '; '
                else:
                    temp_desc += '; '
                a[provider.pnr]['descs'].append(temp_desc)
                for ticket in provider.ticket_ids:
                    a[provider.pnr]['pax_data'].append({
                        'name': ticket.passenger_id.first_name + ' ' + (
                            ticket.passenger_id.last_name if ticket.passenger_id.last_name else ''),
                        'total': 0
                    })
                for pax in a[provider.pnr]['pax_data']:
                    if a[provider.pnr]['pax_data'].get('pax_type'):
                        for price in provider.cost_service_charge_ids:
                            if pax.get('pax_type') == price.pax_type:
                                pax['total'] += price.amount / price.pax_total

                # if not a.get(rec.pnr):
                #     a[rec.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': 'activity', 'total': rec.total}
                # temp_desc = (rec.activity_id.name if rec.activity_id.name else '') + ' - ' + \
                #             (rec.activity_product_id.name if rec.activity_product_id.name else '') + '; ' + \
                #             (str(rec.visit_date) if rec.visit_date else '')
                # if rec.timeslot:
                #     temp_desc += ' ' + str(rec.timeslot) + '; '
                # else:
                #     temp_desc += '; '
                # a[rec.pnr]['descs'].append(temp_desc)
        elif rec._name == 'tt.reservation.visa':
            pnr = rec.provider_booking_ids[0].pnr
            for rec2 in rec.provider_booking_ids:
                if not a.get(rec2.pnr):
                    a[rec2.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': 'visa', 'total': rec.total}
                for pax in rec2.passenger_ids:
                    a[rec2.pnr]['descs'].append('Visa : ' + (pax.passenger_id.first_name if pax.passenger_id.first_name else '') + ' ' +
                                                (pax.passenger_id.last_name if pax.passenger_id.last_name else '') + ', ' +
                                                (pax.passenger_id.title if pax.passenger_id.title else '') + ' ' +
                                                '( ' + (pax.pax_type if pax.pax_type else '') + ' ) ' +
                                                (pax.pricelist_id.entry_type if pax.pricelist_id.entry_type else '') + ' ' +
                                                (pax.pricelist_id.visa_type if pax.pricelist_id.visa_type else '') + ' ' +
                                                (pax.pricelist_id.process_type if pax.pricelist_id.process_type else '') + ' ' +
                                                '(' + (str(pax.pricelist_id.duration) if pax.pricelist_id.duration else '') + ' days)')
                for psg in rec.passenger_ids:
                    a[rec2.pnr]['pax_data'].append({
                        'name': (psg.first_name if psg.first_name else '') + ' ' + (psg.last_name if psg.last_name else ''),
                        'total': psg.pricelist_id.sale_price
                    })
        elif rec._name == 'tt.reservation.tour':
            for provider in rec.provider_booking_ids:
                if not a.get(provider.pnr):
                    a[provider.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'total': rec.total}
                temp_desc = (provider.tour_id.name if provider.tour_id.name else '') + '; ' + (str(provider.departure_date)[:10] if provider.departure_date else '') + ' - ' + (str(provider.arrival_date)[:10] if provider.arrival_date else '') + '; '
                a[provider.pnr]['descs'].append(temp_desc)
                for ticket in provider.ticket_ids:
                    a[provider.pnr]['pax_data'].append({
                        'name': ticket.passenger_id.first_name + ' ' + (
                            ticket.passenger_id.last_name if ticket.passenger_id.last_name else ''),
                        'total': 0
                    })
                for pax in a[provider.pnr]['pax_data']:
                    if a[provider.pnr]['pax_data'].get('pax_type'):
                        for price in provider.cost_service_charge_ids:
                            if pax.get('pax_type') == price.pax_type:
                                pax['total'] += price.amount / price.pax_total
        elif rec._name == 'tt.reservation.offline':
            if rec.provider_type_id_name == 'hotel':
                for rec2 in rec.line_ids:
                    if not a.get(rec2.pnr):
                        a[rec2.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': 'hotel', 'total': rec.total}
                    a[rec2.pnr]['descs'].append('Hotel: ' + (rec2.hotel_name if rec2.hotel_name else '') +
                                                '; Room: ' + (rec2.room if rec2.room else '') + ' ' +
                                                str(rec2.meal_type if rec2.meal_type else ''))
                    for psg in rec.passenger_ids:
                        a[rec2.pnr]['pax_data'].append({
                            'name': (psg.first_name if psg.first_name else '') + ' ' + (psg.last_name if psg.last_name else ''),
                            'provider_type': 'hotel',
                            'total': 0
                        })
            elif rec.provider_type_id_name == 'airline':
                for rec2 in rec.line_ids:
                    if not a.get(rec2.pnr):
                        a[rec2.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': 'airline', 'total': rec.total}
                    a[rec2.pnr]['descs'].append((rec2.origin_id.name if rec2.origin_id.name else '') + ' - ' +
                                                (rec2.destination_id.name if rec2.destination_id.name else '') + '; ' +
                                                str(rec2.departure_date if rec2.departure_date else '') + ' - ' +
                                                str(rec2.arrival_date if rec2.arrival_date else '') + '; ' +
                                                (rec2.carrier_id.name if rec2.carrier_id.name else '') + ' ' +
                                                (rec2.carrier_code if rec2.carrier_code else '') + ' - ' +
                                                (rec2.carrier_number if rec2.carrier_number else '') + ' ')
                    for psg in rec.passenger_ids:
                        a[rec2.pnr]['pax_data'].append({
                            'name': (psg.first_name if psg.first_name else '') + ' ' + (psg.last_name if psg.last_name else ''),
                            'provider_type': 'airline',
                            'total': 0
                        })
                    for pax in a[rec2.pnr]['pax_data']:
                        pax['total'] = rec.total / len(rec.passenger_ids)
            elif rec.provider_type_id_name == 'activity':
                for rec2 in rec.line_ids:
                    if not a.get(rec2.pnr):
                        a[rec2.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': 'activity', 'total': rec.total}
                    temp_desc = (rec2.activity_name.name if rec2.activity_name.name else '') + ' - ' + \
                                (rec2.activity_package.name if rec2.activity_package.name else '') + '; ' + \
                                (str(rec2.check_in) if rec2.check_in else '')
                    if rec2.activity_timeslot:
                        temp_desc += ' ' + str(rec2.activity_timeslot) + '; '
                    else:
                        temp_desc += '; '
                    a[rec2.pnr]['descs'].append(temp_desc)
                    for psg in rec.passenger_ids:
                        a[rec2.pnr]['pax_data'].append({
                            'name': (psg.first_name if psg.first_name else '') + ' ' + (psg.last_name if psg.last_name else ''),
                            'total': 0
                        })
                    for pax in a[rec2.pnr]['pax_data']:
                        pax['total'] = rec.total / len(rec.passenger_ids)
        return a

    # Get Terbilang dkk di hapus
    def compute_terbilang_from_objs(self, recs, currency_str='rupiah'):
        a = {}
        for rec2 in recs:
            a.update({rec2.name: num2words(rec2.grand_total) + ' Rupiah'})
        return a

    @api.model
    def _get_report_values(self, docids, data=None):
        # Print dari BackEnd bisa digunakan untuk Resv maupun invoice
        if not data.get('context'):
            data['context'] = {
                'active_model': 'tt.reservation.airline',
                'active_ids': docids
            }
        values = {}
        val = {}
        header_width = 90
        resv_obj = False
        agent_id = False
        doc_objs = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        for rec in doc_objs:
            values[rec.id] = []
            for rec2 in rec.invoice_line_ids:
                resv_obj = self.env[rec2.res_model_resv].browse(rec2.res_id_resv)
                values[rec.id].append(self.get_invoice_data(rec2, resv_obj, rec))
                # values[rec.id].append(self.calc_segments(resv_obj, resv_obj.passenger_ids))
            agent_id = rec.agent_id
        invoice_footer = self.env['tt.report.common.setting'].get_footer('agent_invoice', agent_id)
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        ho_obj = False
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()
            ho_obj = data_object.agent_id.ho_id
        val = {
            'ho_obj': ho_obj,
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'docs': doc_objs,
            'inv_lines': values,
            'header_width': str(header_width),
            'terbilang': self.compute_terbilang_from_objs(self.env[data['context']['active_model']].browse(data['context']['active_ids'])),
            'invoice_footer': invoice_footer and invoice_footer[0].html or '',
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');",
            'is_invoice': False,
        }
        if resv_obj._name in ['tt.reservation.phc', 'tt.reservation.periksain']:
            val.update({
                'terms_conditions': resv_obj.get_terms_conditions_email()
            })
        return val


class PrintoutExpenses(models.AbstractModel):
    _name = 'report.tt_report_common.printout_expenses_invoice'
    _description = 'Report Common Printout Expenses Invoice'

    def get_invoice_data(self, rec, context, data):
        a = {}
        for rec in rec.vendor_ids:
            if rec.amount:
                create_date = rec.create_date.strftime('%d-%m-%Y')
                if not a.get(create_date):
                    a[create_date] = {'model': rec._name, 'create_date': create_date, 'vendor': [], 'ref_number': [], 'nta_amount': [], 'ho_amount': [], 'psg': []}
                a[create_date]['vendor'].append(rec.vendor_id.name)
                a[create_date]['ref_number'].append(rec.reference_number)
                a[create_date]['nta_amount'].append(rec.nta_amount)
                a[create_date]['ho_amount'].append(rec.amount)
                a[create_date]['psg'].append(rec.pax_to_dict())
        return a

    # Get Terbilang dkk di hapus
    def compute_terbilang_from_objs(self, recs, currency_str='rupiah'):
        a = {}
        for rec2 in recs:
            a.update({rec2.booking_id.name: num2words(rec2.total) + ' Rupiah'})
        return a

    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {}
            if internal_model_id == 1:
                data['context']['active_model'] = 'tt.reservation.airline'
            elif internal_model_id == 2:
                data['context']['active_model'] = 'tt.reservation.train'
            elif internal_model_id == 3:
                data['context']['active_model'] = 'tt.reservation.hotel'
            elif internal_model_id == 4:
                data['context']['active_model'] = 'tt.reservation.activity'
            elif internal_model_id == 5:
                data['context']['active_model'] = 'tt.reservation.tour'
            data['context']['active_ids'] = docids
        values = {}
        nta_amount = 0
        ho_amount = 0
        header_width = 90
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            values[rec.id] = []
            expenses_data = self.get_invoice_data(rec, data.get('context'), data)
            values[rec.id].append(expenses_data)
            for vendor in rec.vendor_ids:
                if vendor.amount:
                    nta_amount += vendor.nta_amount
                    ho_amount += vendor.amount
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()
        vals = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'doc_type': 'expenses',
            'price_lines': values,
            'inv_lines': values,
            'nta_amount': nta_amount,
            'ho_amount': ho_amount,
            'header_width': str(header_width),
            # 'terbilang': self.compute_terbilang_from_objs(
            #     self.env[data['context']['active_model']].browse(data['context']['active_ids'])),
            'date_now': fields.Datetime.now(),
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');"
        }
        return vals


class PrintoutIteneraryForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_itinerary'
    _description = 'Report Common Printout Itinerary'

    @api.model
    def _get_report_values_1(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {}
            if internal_model_id == 1:
                data['context']['active_model'] = 'tt.reservation.airline'
            elif internal_model_id == 2:
                data['context']['active_model'] = 'tt.reservation.train'
            elif internal_model_id == 3:
                data['context']['active_model'] = 'tt.reservation.hotel'
            elif internal_model_id == 4:
                data['context']['active_model'] = 'tt.reservation.activity'
            elif internal_model_id == 5:
                data['context']['active_model'] = 'tt.reservation.tour'
            else:
                data['context']['active_model'] = 'tt.agent.invoice'

            data['context']['active_ids'] = docids

        values = {}
        pnr_length = 0
        customer_grand_total = 0
        discount_value = 0
        header_width = 90
        agent_id = False
        price_breakdown = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            if rec.agent_id.is_btc_agent:
                is_break_down_price = rec.ho_id.is_btc_breakdown_price_printout
            else:
                is_break_down_price = rec.ho_id.is_agent_breakdown_price_printout
            values[rec.id] = []
            a = {}
            for rec2 in rec.sale_service_charge_ids:
                if rec2.pax_type not in a.keys():
                    a[rec2.pax_type] = {
                        'pax_type': rec2.pax_type,
                        'price_per_pax': 0,
                        'price_total': 0,
                        'qty': rec2.pax_count  # asumsi yang pertama fare, qtynya benar
                    }

                if rec2.charge_type.lower() in ['fare', 'roc', 'tax']:
                    if is_break_down_price:
                        if rec2.charge_type not in price_breakdown:
                            price_breakdown[rec2.charge_type] = 0
                        price_breakdown[rec2.charge_type] += rec2.total
                    a[rec2.pax_type]['price_per_pax'] += rec2.amount
                    a[rec2.pax_type]['price_total'] += rec2.total
                elif rec2.charge_type.lower() == 'disc':
                    discount_value += rec2.amount

            if discount_value:
                a.update({'DISC': {'pax_type': 'DISC', 'price_per_pax': discount_value, 'price_total': discount_value, 'qty': 1,}})

            # csc_found = []
            # for psg in rec.passenger_ids:
            #     pax_type = psg.cost_service_charge_ids[0].pax_type
                # Noted Mark Up Airline pakek tngan per org makane langsung di kali QTY
                # for csc in psg.channel_service_charge_ids:
                #     if pax_type not in csc_found:
                #         a[pax_type]['price_per_pax'] += csc.amount
                #         a[pax_type]['price_total'] += csc.amount * a[pax_type]['qty']
                #         csc_found.append(pax_type)

                # Add SSR cman karena ssr itu per pax maka smentara cman ku kasih di total
                # klo di tmbah ke per pax jadi slah jumlah
                # if hasattr(psg,'fee_ids'):
                #     for csc in psg.fee_ids:
                #         a[pax_type]['price_total'] += csc.amount

            for sc_key in a.keys():
                sc = a[sc_key]
                customer_grand_total += sc['price_total']

            values[rec.id] = [a[new_a] for new_a in a]
            pnr_length = len(rec.pnr)
            if pnr_length > 27:
                header_width += 3 * (abs(27 - pnr_length))
                if header_width > 105:
                    header_width = 105
            agent_id = rec.agent_id

        printout_itinerary_footer = self.env['tt.report.common.setting'].get_footer('printout_itinerary', agent_id)
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()
        vals = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'doc_type': 'itin',
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'pnr_length': pnr_length,
            'header_width': str(header_width),
            'price_lines': values, #Old format Here
            'price_breakdown': price_breakdown,
            'customer_grand_total': customer_grand_total,
            'printout_itinerary_footer': printout_itinerary_footer and printout_itinerary_footer[0].html or '',
            'date_now': fields.Datetime.now(),
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');"
        }
        if data.get('data') and 'is_with_price' in data['data']:
            vals.update({
                'with_price': data['data'].get('is_with_price') or False,
            })
        return vals

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {}
            if internal_model_id == 1:
                data['context']['active_model'] = 'tt.reservation.airline'
            elif internal_model_id == 2:
                data['context']['active_model'] = 'tt.reservation.train'
            elif internal_model_id == 3:
                data['context']['active_model'] = 'tt.reservation.hotel'
            else:
                data['context']['active_model'] = 'tt.agent.invoice'

            data['context']['active_ids'] = docids

        values = {}
        pnr_length = 0
        customer_grand_total = 0
        discount_value = 0
        header_width = 90
        agent_id = False
        price_breakdown = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            if rec.agent_id.is_btc_agent:
                is_break_down_price = rec.ho_id.is_btc_breakdown_price_printout
            else:
                is_break_down_price = rec.ho_id.is_agent_breakdown_price_printout
            values[rec.id] = []

            if data['context']['active_model'] == 'tt.reservation.airline':
                for psg in rec.passenger_ids:
                    total_price_pax = 0
                    pax_type = psg.cost_service_charge_ids[-1].pax_type # Notes Pax type bisa jadi slah first bisa di isi SSR
                    for cost_sc in psg.cost_service_charge_ids:
                        if cost_sc.charge_type.lower() in ['fare', 'roc', 'tax']:
                            if is_break_down_price:
                                if cost_sc.charge_type not in price_breakdown:
                                    price_breakdown[cost_sc.charge_type] = 0
                                price_breakdown[cost_sc.charge_type] += cost_sc.amount
                            total_price_pax += cost_sc.amount
                        elif cost_sc.charge_type.lower() == 'disc':
                            discount_value += cost_sc.amount

                    # for csc in psg.channel_service_charge_ids:
                    #     total_price_pax += csc.amount

                    inc_ssr_descs = []
                    for seg_id in rec.segment_ids:
                        for ssr_sc in seg_id.segment_addons_ids:
                            inc_ssr_descs.append({'name':str(ssr_sc.amount) + ' ' + ssr_sc.unit + ';' + ssr_sc.segment_id.origin_id.code + '-' + ssr_sc.segment_id.destination_id.code, 'value':ssr_sc.amount,'category_icon':""})

                    # Add SSR cman karena ssr itu per pax maka smentara cman ku kasih di total
                    # klo di tmbah ke per pax jadi slah jumlah
                    ssr_descs = []
                    if hasattr(psg, 'fee_ids'):
                        for ssr_sc in psg.fee_ids:
                            ssr_journey_code = ssr_sc.journey_code.split(';')
                            ssr_seg_applied = ';' + ssr_journey_code[0].split(',')[2] + '-' + ssr_journey_code[-1].split(',')[4] if len(ssr_journey_code) != 1 else ""
                            ssr_descs.append({'name': ssr_sc.name + ssr_seg_applied, 'value': ssr_sc.value, 'category_icon': ssr_sc.category_icon})
                            if is_break_down_price:
                                if ssr_sc.category not in price_breakdown:
                                    price_breakdown[ssr_sc.category] = 0
                                price_breakdown[ssr_sc.category] += ssr_sc.amount
                            total_price_pax += ssr_sc.amount

                    values[rec.id].append({
                        'name': psg.name,
                        'passenger_id': psg,
                        'pax_type': pax_type,
                        'inc_ssr': inc_ssr_descs, # Inc. SSR
                        'add_ssr': ssr_descs,  # Add SSR
                        'price_total': total_price_pax,
                    })
                    customer_grand_total += total_price_pax
            elif data['context']['active_model'] == 'tt.reservation.hotel':
                pax_type = 'ADT'
                total_price_pax = 0
                for sc in rec.sale_service_charge_ids:
                    if sc.charge_type.lower() in ['fare', 'roc', 'tax']:
                        if is_break_down_price:
                            if sc.charge_type not in price_breakdown:
                                price_breakdown[sc.charge_type] = 0
                            price_breakdown[sc.charge_type] += sc.amount
                        total_price_pax += sc.amount
                    elif sc.charge_type.lower() == 'disc':
                        discount_value += sc.amount

                # for psg in rec.passenger_ids:
                    # for csc in psg.channel_service_charge_ids:
                    #     total_price_pax += csc.amount

                    # customer_grand_total += total_price_pax

                values[rec.id].append({
                    'name': rec.passenger_ids[0].name,
                    'pax_type': pax_type,
                    'inc_ssr': "",  # Inc. SSR
                    'add_ssr': "",  # Add SSR
                    'price_total': customer_grand_total,
                })
            elif data['context']['active_model'] == 'tt.reservation.train':
                for psg in rec.passenger_ids:
                    total_price_pax = 0
                    pax_type = psg.cost_service_charge_ids[-1].pax_type # Notes Pax type bisa jadi slah first bisa di isi SSR
                    for cost_sc in psg.cost_service_charge_ids:
                        if cost_sc.charge_type.lower() in ['fare', 'roc', 'tax']:
                            if is_break_down_price:
                                if cost_sc.charge_type not in price_breakdown:
                                    price_breakdown[cost_sc.charge_type] = 0
                                price_breakdown[cost_sc.charge_type] += cost_sc.amount
                            total_price_pax += cost_sc.amount
                        elif cost_sc.charge_type.lower() == 'disc':
                            discount_value += cost_sc.amount

                    # for csc in psg.channel_service_charge_ids:
                    #     total_price_pax += csc.amount

                    inc_ssr_descs = []

                    # Add SSR cman karena ssr itu per pax maka smentara cman ku kasih di total
                    # klo di tmbah ke per pax jadi slah jumlah
                    ssr_descs = []

                    values[rec.id].append({
                        'name': psg.name,
                        'pax_type': pax_type,
                        'inc_ssr': inc_ssr_descs, # Inc. SSR
                        'add_ssr': ssr_descs,  # Add SSR
                        'price_total': total_price_pax,
                    })
                    customer_grand_total += total_price_pax

            pnr_length = len(rec.pnr)
            if pnr_length > 27:
                header_width += 3 * (abs(27 - pnr_length))
                if header_width > 105:
                    header_width = 105
            agent_id = rec.agent_id
        printout_itinerary_footer = self.env['tt.report.common.setting'].get_footer('printout_itinerary', agent_id)
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()
        vals = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'doc_type': 'itin',
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'pnr_length': pnr_length,
            'header_width': str(header_width),
            'price_lines': values,
            'discount_value': discount_value,
            'customer_grand_total': customer_grand_total + discount_value, #Disc value (-1)
            'price_breakdown': price_breakdown,
            'printout_itinerary_footer': printout_itinerary_footer and printout_itinerary_footer[0].html or '',
            'date_now': fields.Datetime.now(),
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');"
        }
        if data.get('data') and 'is_with_price' in data['data']:
            vals.update({
                'with_price': data['data'].get('is_with_price') or False,
            })
        return vals


class PrintoutActivityIteneraryForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_activity_itinerary'
    _description = 'Report Common Printout Activity Itinerary'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {}
            if internal_model_id == 1:
                data['context']['active_model'] = 'tt.reservation.airline'
            elif internal_model_id == 2:
                data['context']['active_model'] = 'tt.reservation.train'
            elif internal_model_id == 3:
                data['context']['active_model'] = 'tt.reservation.hotel'
            elif internal_model_id == 4:
                data['context']['active_model'] = 'tt.reservation.activity'
            elif internal_model_id == 5:
                data['context']['active_model'] = 'tt.reservation.tour'
            else:
                data['context']['active_model'] = 'tt.agent.invoice'

            data['context']['active_ids'] = docids
        values = {}
        pnr_length = 0
        customer_grand_total = 0
        discount_value = 0
        header_width = 90
        price_breakdown = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            if rec.agent_id.is_btc_agent:
                is_break_down_price = rec.ho_id.is_btc_breakdown_price_printout
            else:
                is_break_down_price = rec.ho_id.is_agent_breakdown_price_printout
            values[rec.id] = []
            a = {}
            for rec2 in rec.sale_service_charge_ids:
                if rec2.pax_type not in a.keys():
                    a[rec2.pax_type] = {
                        'pax_type': rec2.pax_type,
                        'price_per_pax': 0,
                        'price_total': 0,
                        'qty': rec2.pax_count  # asumsi yang pertama fare, qtynya benar
                    }

                if rec2.charge_type.lower() in ['fare', 'roc', 'tax']:
                    if is_break_down_price:
                        if rec2.charge_type not in price_breakdown:
                            price_breakdown[rec2.charge_type] = 0
                        price_breakdown[rec2.charge_type] += rec2.total
                    a[rec2.pax_type]['price_per_pax'] += rec2.amount
                    a[rec2.pax_type]['price_total'] += rec2.total
                elif rec2.charge_type.lower() == 'disc':
                    discount_value += rec2.amount

            if discount_value:
                a.update({
                    'DISC': {
                        'pax_type': 'DISC',
                        'price_per_pax': discount_value,
                        'price_total': discount_value,
                        'qty': 1,
                    }
                })

            # csc_found = []
            # for psg in rec.passenger_ids:
            #     pax_type = psg.cost_service_charge_ids[0].pax_type
                # for csc in psg.channel_service_charge_ids:
                #     if pax_type not in csc_found:
                #         a[pax_type]['price_per_pax'] += csc.amount
                #         a[pax_type]['price_total'] += csc.amount * a[pax_type]['qty']
                #         csc_found.append(pax_type)

            for sc_key in a.keys():
                sc = a[sc_key]
                customer_grand_total += sc['price_total']

            values[rec.id] = [a[new_a] for new_a in a]
            pnr_length = len(rec.pnr)
            if pnr_length > 27:
                header_width += 3 * (abs(27 - pnr_length))
                if header_width > 105:
                    header_width = 105
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()

        vals = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'doc_type': 'itin',
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'pnr_length': pnr_length,
            'header_width': str(header_width),
            'price_lines': values,
            'price_breakdown': price_breakdown,
            'customer_grand_total': customer_grand_total,
            'date_now': fields.Datetime.now(),
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');"
        }

        if data.get('data') and 'is_with_price' in data['data']:
            vals.update({
                'with_price': data['data'].get('is_with_price') or False,
            })
        return vals


class PrintoutEventIteneraryForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_event_itinerary'
    _description = 'Report Common Event Itinerary'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {}
            if internal_model_id == 1:
                data['context']['active_model'] = 'tt.reservation.airline'
            elif internal_model_id == 2:
                data['context']['active_model'] = 'tt.reservation.train'
            elif internal_model_id == 3:
                data['context']['active_model'] = 'tt.reservation.hotel'
            elif internal_model_id == 4:
                data['context']['active_model'] = 'tt.reservation.activity'
            elif internal_model_id == 5:
                data['context']['active_model'] = 'tt.reservation.tour'
            else:
                data['context']['active_model'] = 'tt.agent.invoice'

            data['context']['active_ids'] = docids
        values = {}
        pnr_length = 0
        customer_grand_total = 0
        discount_value = 0
        header_width = 90
        price_breakdown = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            if rec.agent_id.is_btc_agent:
                is_break_down_price = rec.ho_id.is_btc_breakdown_price_printout
            else:
                is_break_down_price = rec.ho_id.is_agent_breakdown_price_printout
            values[rec.id] = []
            a = {}
            for rec2 in rec.sale_service_charge_ids:
                if rec2.pax_type not in a.keys():
                    a[rec2.pax_type] = {
                        'pax_type': rec2.pax_type,
                        'price_per_pax': 0,
                        'price_total': 0,
                        'qty': rec2.pax_count  # asumsi yang pertama fare, qtynya benar
                    }

                if rec2.charge_type.lower() in ['fare', 'roc', 'tax']:
                    if is_break_down_price:
                        if rec2.charge_type not in price_breakdown:
                            price_breakdown[rec2.charge_type] = 0
                        price_breakdown[rec2.charge_type] += rec2.total
                    a[rec2.pax_type]['price_per_pax'] += rec2.amount
                    a[rec2.pax_type]['price_total'] += rec2.total
                elif rec2.charge_type.lower() == 'disc':
                    discount_value += rec2.amount

            if discount_value:
                a.update({
                    'DISC': {
                        'pax_type': 'DISC',
                        'price_per_pax': discount_value,
                        'price_total': discount_value,
                        'qty': 1,
                    }
                })

            # csc_found = []
            # for psg in rec.passenger_ids:
            #     pax_type = psg.cost_service_charge_ids[0].pax_type
                # for csc in psg.channel_service_charge_ids:
                #     if pax_type not in csc_found:
                #         a[pax_type]['price_per_pax'] += csc.amount
                #         a[pax_type]['price_total'] += csc.amount * a[pax_type]['qty']
                #         csc_found.append(pax_type)

            for sc_key in a.keys():
                sc = a[sc_key]
                customer_grand_total += sc['price_total']

            values[rec.id] = [a[new_a] for new_a in a]
            pnr_length = len(rec.pnr)
            if pnr_length > 27:
                header_width += 3 * (abs(27 - pnr_length))
                if header_width > 105:
                    header_width = 105
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()

        vals = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'doc_type': 'itin',
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'pnr_length': pnr_length,
            'header_width': str(header_width),
            'price_lines': values,
            'price_breakdown': price_breakdown,
            'customer_grand_total': customer_grand_total,
            'date_now': fields.Datetime.now(),
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');"
        }

        if data.get('data') and 'is_with_price' in data['data']:
            vals.update({
                'with_price': data['data'].get('is_with_price') or False,
            })

        return vals


class PrintoutTourIteneraryForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_tour_itinerary'
    _description = 'Report Common Printout Tour Itinerary'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {}
            if internal_model_id == 1:
                data['context']['active_model'] = 'tt.reservation.airline'
            elif internal_model_id == 2:
                data['context']['active_model'] = 'tt.reservation.train'
            elif internal_model_id == 3:
                data['context']['active_model'] = 'tt.reservation.hotel'
            elif internal_model_id == 4:
                data['context']['active_model'] = 'tt.reservation.activity'
            elif internal_model_id == 5:
                data['context']['active_model'] = 'tt.reservation.tour'
            else:
                data['context']['active_model'] = 'tt.agent.invoice'

            data['context']['active_ids'] = docids
        values = {}
        pnr_length = 0
        customer_grand_total = 0
        discount_value = 0
        header_width = 90
        price_breakdown = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            if rec.agent_id.is_btc_agent:
                is_break_down_price = rec.ho_id.is_btc_breakdown_price_printout
            else:
                is_break_down_price = rec.ho_id.is_agent_breakdown_price_printout
            values[rec.id] = []
            a = {}
            for rec2 in rec.sale_service_charge_ids:
                if rec2.pax_type not in a.keys():
                    a[rec2.pax_type] = {
                        'pax_type': rec2.pax_type,
                        'price_per_pax': 0,
                        'price_total': 0,
                        'qty': rec2.pax_count  # asumsi yang pertama fare, qtynya benar
                    }

                if rec2.charge_type.lower() in ['fare', 'roc', 'tax']:
                    if is_break_down_price:
                        if rec2.charge_type not in price_breakdown:
                            price_breakdown[rec2.charge_type] = 0
                        price_breakdown[rec2.charge_type] += rec2.total
                    a[rec2.pax_type]['price_per_pax'] += rec2.amount
                    a[rec2.pax_type]['price_total'] += rec2.total
                elif rec2.charge_type.lower() == 'disc':
                    discount_value += rec2.amount

            if discount_value:
                a.update({
                    'DISC': {
                        'pax_type': 'DISC',
                        'price_per_pax': discount_value,
                        'price_total': discount_value,
                        'qty': 1,
                    }
                })

            # csc_found = []
            # for psg in rec.passenger_ids:
            #     pax_type = psg.cost_service_charge_ids[0].pax_type
            #     for csc in psg.channel_service_charge_ids:
                    # if pax_type not in csc_found:
                    #     a[pax_type]['price_per_pax'] += csc.amount
                    #     a[pax_type]['price_total'] += csc.amount * a[pax_type]['qty']
                    #     csc_found.append(pax_type)

            for sc_key in a.keys():
                sc = a[sc_key]
                customer_grand_total += sc['price_total']

            values[rec.id] = [a[new_a] for new_a in a]
            pnr_length = len(rec.pnr)
            if pnr_length > 27:
                header_width += 3 * (abs(27 - pnr_length))
                if header_width > 105:
                    header_width = 105
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()

        vals = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'doc_type': 'itin',
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'pnr_length': pnr_length,
            'header_width': str(header_width),
            'price_lines': values,
            'price_breakdown': price_breakdown,
            'customer_grand_total': customer_grand_total,
            'date_now': fields.Datetime.now(),
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');"
        }

        if data.get('data') and 'is_with_price' in data['data']:
            vals.update({
                'with_price': data['data'].get('is_with_price') or False,
            })

        return vals


class PrintoutPassportItineraryForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_passport_itinerary'
    _description = 'Report Common Printout Passport Itinerary'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {}
            if internal_model_id == 1:
                data['context']['active_model'] = 'tt.reservation.airline'
            elif internal_model_id == 2:
                data['context']['active_model'] = 'tt.reservation.train'
            elif internal_model_id == 3:
                data['context']['active_model'] = 'tt.reservation.hotel'
            elif internal_model_id == 4:
                data['context']['active_model'] = 'tt.reservation.activity'
            elif internal_model_id == 5:
                data['context']['active_model'] = 'tt.reservation.tour'
            else:
                data['context']['active_model'] = 'tt.agent.invoice'

            data['context']['active_ids'] = docids
        values = {}
        pnr_length = 0
        customer_grand_total = 0
        discount_value = 0
        header_width = 90
        price_breakdown = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            if rec.agent_id.is_btc_agent:
                is_break_down_price = rec.ho_id.is_btc_breakdown_price_printout
            else:
                is_break_down_price = rec.ho_id.is_agent_breakdown_price_printout
            values[rec.id] = []
            a = {}
            for rec2 in rec.sale_service_charge_ids:
                if rec2.pax_type not in a.keys():
                    a[rec2.pax_type] = {
                        'pax_type': rec2.pax_type,
                        'price_per_pax': 0,
                        'price_total': 0,
                        'qty': rec2.pax_count  # asumsi yang pertama fare, qtynya benar
                    }

                if rec2.charge_type.lower() in ['fare', 'roc', 'tax']:
                    if is_break_down_price:
                        if rec2.charge_type not in price_breakdown:
                            price_breakdown[rec2.charge_type] = 0
                        price_breakdown[rec2.charge_type] += rec.total
                    a[rec2.pax_type]['price_per_pax'] += rec2.amount
                    a[rec2.pax_type]['price_total'] += rec2.total
                elif rec2.charge_type.lower() == 'disc':
                    discount_value += rec2.amount

            if discount_value:
                a.update({
                    'DISC': {
                        'pax_type': 'DISC',
                        'price_per_pax': discount_value,
                        'price_total': discount_value,
                        'qty': 1,
                    }
                })

            # csc_found = []
            # for psg in rec.passenger_ids:
            #     pax_type = psg.cost_service_charge_ids[0].pax_type
                # for csc in psg.channel_service_charge_ids:
                #     if pax_type not in csc_found:
                #         a[pax_type]['price_per_pax'] += csc.amount
                #         a[pax_type]['price_total'] += csc.amount * a[pax_type]['qty']
                #         csc_found.append(pax_type)

            for sc_key in a.keys():
                sc = a[sc_key]
                customer_grand_total += sc['price_total']

            values[rec.id] = [a[new_a] for new_a in a]
            pnr_length = len(rec.pnr)
            if pnr_length > 27:
                header_width += 3 * (abs(27 - pnr_length))
                if header_width > 105:
                    header_width = 105
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()

        vals = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'doc_type': 'itin',
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'pnr_length': pnr_length,
            'header_width': str(header_width),
            'price_lines': values,
            'price_breakdown': price_breakdown,
            'customer_grand_total': customer_grand_total,
            'date_now': fields.Datetime.now(),
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');"
        }

        if data.get('data') and 'is_with_price' in data['data']:
            vals.update({
                'with_price': data['data'].get('is_with_price') or False,
            })

        return vals


class PrintoutPPOBItineraryForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_ppob_itinerary'
    _description = 'Report Common Printout PPOB Itinerary'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {}
            if internal_model_id == 1:
                data['context']['active_model'] = 'tt.reservation.airline'
            elif internal_model_id == 2:
                data['context']['active_model'] = 'tt.reservation.train'
            elif internal_model_id == 3:
                data['context']['active_model'] = 'tt.reservation.hotel'
            elif internal_model_id == 4:
                data['context']['active_model'] = 'tt.reservation.activity'
            elif internal_model_id == 5:
                data['context']['active_model'] = 'tt.reservation.tour'
            else:
                data['context']['active_model'] = 'tt.agent.invoice'

            data['context']['active_ids'] = docids
        values = {}
        pnr_length = 0
        customer_grand_total = 0
        discount_value = 0
        header_width = 90
        price_breakdown = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            if rec.agent_id.is_btc_agent:
                is_break_down_price = rec.ho_id.is_btc_breakdown_price_printout
            else:
                is_break_down_price = rec.ho_id.is_agent_breakdown_price_printout
            values[rec.id] = []
            a = {}
            for rec2 in rec.sale_service_charge_ids:
                if rec2.pax_type not in a.keys():
                    a[rec2.pax_type] = {
                        'pax_type': rec2.pax_type,
                        'price_per_pax': 0,
                        'price_total': 0,
                        'qty': rec2.pax_count  # asumsi yang pertama fare, qtynya benar
                    }

                if rec2.charge_type.lower() in ['fare', 'roc', 'tax']:
                    if is_break_down_price:
                        if rec2.charge_type not in price_breakdown:
                            price_breakdown[rec2.charge_type] = 0
                        price_breakdown[rec2.charge_type] += rec2.total
                    a[rec2.pax_type]['price_per_pax'] += rec2.amount
                    a[rec2.pax_type]['price_total'] += rec2.total
                elif rec2.charge_type.lower() == 'disc':
                    discount_value += rec2.amount

            if discount_value:
                a.update({
                    'DISC': {
                        'pax_type': 'DISC',
                        'price_per_pax': discount_value,
                        'price_total': discount_value,
                        'qty': 1,
                    }
                })

            # csc_found = []
            # for psg in rec.passenger_ids:
            #     pax_type = psg.cost_service_charge_ids[0].pax_type
                # for csc in psg.channel_service_charge_ids:
                #     if pax_type not in csc_found:
                #         a[pax_type]['price_per_pax'] += csc.amount
                #         a[pax_type]['price_total'] += csc.amount * a[pax_type]['qty']
                #         csc_found.append(pax_type)

            for sc_key in a.keys():
                sc = a[sc_key]
                customer_grand_total += sc['price_total']

            values[rec.id] = [a[new_a] for new_a in a]
            if rec.pnr:
                pnr_length = len(rec.pnr)
            else:
                pnr_length = len(rec.provider_booking_ids[0].customer_number)
            if pnr_length > 27:
                header_width += 3 * (abs(27 - pnr_length))
                if header_width > 105:
                    header_width = 105
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()

        vals = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'doc_type': 'itin',
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'pnr_length': pnr_length,
            'header_width': str(header_width),
            'price_lines': values,
            'price_breakdown': price_breakdown,
            'customer_grand_total': customer_grand_total,
            'date_now': fields.Datetime.now(),
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');"
        }

        if data.get('data') and 'is_with_price' in data['data']:
            vals.update({
                'with_price': data['data'].get('is_with_price') or False,
            })

        return vals


class PrintoutVisaItineraryForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_visa_itinerary'
    _description = 'Report Common Printout Visa Itinerary'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {}
            if internal_model_id == 1:
                data['context']['active_model'] = 'tt.reservation.airline'
            elif internal_model_id == 2:
                data['context']['active_model'] = 'tt.reservation.train'
            elif internal_model_id == 3:
                data['context']['active_model'] = 'tt.reservation.hotel'
            elif internal_model_id == 4:
                data['context']['active_model'] = 'tt.reservation.activity'
            elif internal_model_id == 5:
                data['context']['active_model'] = 'tt.reservation.tour'
            else:
                data['context']['active_model'] = 'tt.agent.invoice'

            data['context']['active_ids'] = docids
        values = {}
        pnr_length = 0
        customer_grand_total = 0
        discount_value = 0
        header_width = 90
        price_breakdown = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            if rec.agent_id.is_btc_agent:
                is_break_down_price = rec.ho_id.is_btc_breakdown_price_printout
            else:
                is_break_down_price = rec.ho_id.is_agent_breakdown_price_printout
            values[rec.id] = []
            a = {}
            for rec2 in rec.sale_service_charge_ids:
                if rec2.pax_type not in a.keys():
                    a[rec2.pax_type] = {
                        'pax_type': rec2.pax_type,
                        'price_per_pax': 0,
                        'price_total': 0,
                        'qty': rec2.pax_count  # asumsi yang pertama fare, qtynya benar
                    }

                if rec2.charge_type.lower() in ['fare', 'roc', 'tax']:
                    if is_break_down_price:
                        if rec2.charge_type not in price_breakdown:
                            price_breakdown[rec2.charge_type] = 0
                        price_breakdown[rec2.charge_type] += rec2.total
                    a[rec2.pax_type]['price_per_pax'] += rec2.amount
                    a[rec2.pax_type]['price_total'] += rec2.total
                elif rec2.charge_type.lower() == 'disc':
                    discount_value += rec2.amount

            if discount_value:
                a.update({
                    'DISC': {
                        'pax_type': 'DISC',
                        'price_per_pax': discount_value,
                        'price_total': discount_value,
                        'qty': 1,
                    }
                })

            # csc_found = []
            # for psg in rec.passenger_ids:
            #     pax_type = psg.cost_service_charge_ids[0].pax_type
                # for csc in psg.channel_service_charge_ids:
                #     if pax_type not in csc_found:
                #         a[pax_type]['price_per_pax'] += csc.amount
                #         a[pax_type]['price_total'] += csc.amount * a[pax_type]['qty']
                #         csc_found.append(pax_type)

            for sc_key in a.keys():
                sc = a[sc_key]
                customer_grand_total += sc['price_total']

            values[rec.id] = [a[new_a] for new_a in a]
            pnr_length = len(rec.pnr)
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()
        vals =  {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'doc_type': 'itin',
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'pnr_length': pnr_length,
            'header_width': str(header_width),
            'price_lines': values,
            'price_breakdown': price_breakdown,
            'customer_grand_total': customer_grand_total,
            'date_now': fields.Datetime.now(),
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');"
        }

        if data.get('data') and 'is_with_price' in data['data']:
            vals.update({
                'with_price': data['data'].get('is_with_price') or False,
            })
        return vals


class PrintoutPeriksainItineraryForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_periksain_itinerary'
    _description = 'Report Common Printout Periksain Itinerary'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {}
            if internal_model_id == 1:
                data['context']['active_model'] = 'tt.reservation.airline'
            elif internal_model_id == 2:
                data['context']['active_model'] = 'tt.reservation.train'
            elif internal_model_id == 3:
                data['context']['active_model'] = 'tt.reservation.hotel'
            elif internal_model_id == 4:
                data['context']['active_model'] = 'tt.reservation.activity'
            elif internal_model_id == 5:
                data['context']['active_model'] = 'tt.reservation.tour'
            elif internal_model_id == 7:
                data['context']['active_model'] = 'tt.reservation.periksain'
            else:
                data['context']['active_model'] = 'tt.agent.invoice'

            data['context']['active_ids'] = docids
        values = {}
        pnr_length = 0
        customer_grand_total = 0
        discount_value = 0
        header_width = 90
        price_breakdown = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            if rec.agent_id.is_btc_agent:
                is_break_down_price = rec.ho_id.is_btc_breakdown_price_printout
            else:
                is_break_down_price = rec.ho_id.is_agent_breakdown_price_printout
            values[rec.id] = []
            a = {}
            for rec2 in rec.sale_service_charge_ids:
                if rec2.pax_type not in a.keys():
                    a[rec2.pax_type] = {
                        'pax_type': rec2.pax_type,
                        'price_per_pax': 0,
                        'price_total': 0,
                        'qty': rec2.pax_count  # asumsi yang pertama fare, qtynya benar
                    }

                if rec2.charge_type.lower() in ['fare', 'roc', 'tax']:
                    if is_break_down_price:
                        if rec2.charge_type not in price_breakdown:
                            price_breakdown[rec2.charge_type] = 0
                        price_breakdown[rec2.charge_type] += rec2.total
                    a[rec2.pax_type]['price_per_pax'] += rec2.amount
                    a[rec2.pax_type]['price_total'] += rec2.total
                elif rec2.charge_type.lower() == 'disc':
                    discount_value += rec2.amount

            if discount_value:
                a.update({
                    'DISC': {
                        'pax_type': 'DISC',
                        'price_per_pax': discount_value,
                        'price_total': discount_value,
                        'qty': 1,
                    }
                })

            # csc_found = []
            # for psg in rec.passenger_ids:
            #     pax_type = psg.cost_service_charge_ids[0].pax_type
                # for csc in psg.channel_service_charge_ids:
                #     if pax_type not in csc_found:
                #         a[pax_type]['price_per_pax'] += csc.amount
                #         a[pax_type]['price_total'] += csc.amount * a[pax_type]['qty']
                #         csc_found.append(pax_type)

            for sc_key in a.keys():
                sc = a[sc_key]
                customer_grand_total += sc['price_total']

            values[rec.id] = [a[new_a] for new_a in a]
            pnr_length = len(rec.pnr)
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()

        vals = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'doc_type': 'itin',
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'pnr_length': pnr_length,
            'header_width': str(header_width),
            'price_lines': values,
            'price_breakdown': price_breakdown,
            'customer_grand_total': customer_grand_total,
            'date_now': fields.Datetime.now(),
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');",
            'printout_tz': pytz.timezone('Asia/Jakarta')
        }

        if data.get('data') and 'is_with_price' in data['data']:
            vals.update({
                'with_price': data['data'].get('is_with_price') or False,
            })
        return vals


class PrintoutMedicalItineraryForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_medical_itinerary'
    _description = 'Report Common Printout Medical Itinerary'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {}
            if internal_model_id == 1:
                data['context']['active_model'] = 'tt.reservation.airline'
            elif internal_model_id == 2:
                data['context']['active_model'] = 'tt.reservation.train'
            elif internal_model_id == 3:
                data['context']['active_model'] = 'tt.reservation.hotel'
            elif internal_model_id == 4:
                data['context']['active_model'] = 'tt.reservation.activity'
            elif internal_model_id == 5:
                data['context']['active_model'] = 'tt.reservation.tour'
            elif internal_model_id == 7:
                data['context']['active_model'] = 'tt.reservation.periksain'
            elif internal_model_id == 8:
                data['context']['active_model'] = 'tt.reservation.phc'
            elif internal_model_id == 9:
                data['context']['active_model'] = 'tt.reservation.medical'
            else:
                data['context']['active_model'] = 'tt.agent.invoice'

            data['context']['active_ids'] = docids
        values = {}
        pnr_length = 0
        customer_grand_total = 0
        discount_value = 0
        header_width = 90
        price_breakdown = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            if rec.agent_id.is_btc_agent:
                is_break_down_price = rec.ho_id.is_btc_breakdown_price_printout
            else:
                is_break_down_price = rec.ho_id.is_agent_breakdown_price_printout
            values[rec.id] = []
            a = {}
            for rec2 in rec.sale_service_charge_ids:
                if rec2.pax_type not in a.keys():
                    a[rec2.pax_type] = {
                        'pax_type': rec2.pax_type,
                        'price_per_pax': 0,
                        'price_total': 0,
                        'qty': rec2.pax_count  # asumsi yang pertama fare, qtynya benar
                    }

                if rec2.charge_type.lower() in ['fare', 'roc', 'tax']:
                    if is_break_down_price:
                        if rec2.charge_type not in price_breakdown:
                            price_breakdown[rec2.charge_type] = 0
                        price_breakdown[rec2.charge_type] += rec2.total
                    a[rec2.pax_type]['price_per_pax'] += rec2.amount
                    a[rec2.pax_type]['price_total'] += rec2.total
                elif rec2.charge_type.lower() == 'disc':
                    discount_value += rec2.amount

            if discount_value:
                a.update({
                    'DISC': {
                        'pax_type': 'DISC',
                        'price_per_pax': discount_value,
                        'price_total': discount_value,
                        'qty': 1,
                    }
                })

            # csc_found = []
            # for psg in rec.passenger_ids:
            #     pax_type = psg.cost_service_charge_ids[0].pax_type
                # for csc in psg.channel_service_charge_ids:
                #     if pax_type not in csc_found:
                #         a[pax_type]['price_per_pax'] += csc.amount
                #         a[pax_type]['price_total'] += csc.amount * a[pax_type]['qty']
                #         csc_found.append(pax_type)

            for sc_key in a.keys():
                sc = a[sc_key]
                customer_grand_total += sc['price_total']

            values[rec.id] = [a[new_a] for new_a in a]
            pnr_length = len(rec.pnr)
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()

        vals = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'doc_type': 'itin',
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'pnr_length': pnr_length,
            'header_width': str(header_width),
            'price_lines': values,
            'price_breakdown': price_breakdown,
            'customer_grand_total': customer_grand_total,
            'date_now': fields.Datetime.now(),
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');",
            'printout_tz': pytz.timezone('Asia/Jakarta')
        }

        if data.get('data') and 'is_with_price' in data['data']:
            vals.update({
                'with_price': data['data'].get('is_with_price') or False,
            })
        return vals


class PrintoutBusItineraryForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_bus_itinerary'
    _description = 'Report Common Printout Bus Itinerary'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {}
            if internal_model_id == 1:
                data['context']['active_model'] = 'tt.reservation.airline'
            elif internal_model_id == 2:
                data['context']['active_model'] = 'tt.reservation.train'
            elif internal_model_id == 3:
                data['context']['active_model'] = 'tt.reservation.hotel'
            elif internal_model_id == 4:
                data['context']['active_model'] = 'tt.reservation.activity'
            elif internal_model_id == 5:
                data['context']['active_model'] = 'tt.reservation.tour'
            elif internal_model_id == 7:
                data['context']['active_model'] = 'tt.reservation.periksain'
            elif internal_model_id == 8:
                data['context']['active_model'] = 'tt.reservation.phc'
            elif internal_model_id == 9:
                data['context']['active_model'] = 'tt.reservation.medical'
            elif internal_model_id == 10:
                data['context']['active_model'] = 'tt.reservation.bus'
            else:
                data['context']['active_model'] = 'tt.agent.invoice'

            data['context']['active_ids'] = docids
        values = {}
        pnr_length = 0
        customer_grand_total = 0
        discount_value = 0
        header_width = 90
        price_breakdown = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            if rec.agent_id.is_btc_agent:
                is_break_down_price = rec.ho_id.is_btc_breakdown_price_printout
            else:
                is_break_down_price = rec.ho_id.is_agent_breakdown_price_printout
            values[rec.id] = []
            a = {}
            for rec2 in rec.sale_service_charge_ids:
                if rec2.pax_type not in a.keys():
                    a[rec2.pax_type] = {
                        'pax_type': rec2.pax_type,
                        'price_per_pax': 0,
                        'price_total': 0,
                        'qty': rec2.pax_count  # asumsi yang pertama fare, qtynya benar
                    }

                if rec2.charge_type.lower() in ['fare', 'roc', 'tax']:
                    if is_break_down_price:
                        if rec2.charge_type not in price_breakdown:
                            price_breakdown[rec2.charge_type] = 0
                        price_breakdown[rec2.charge_type] += rec2.total
                    a[rec2.pax_type]['price_per_pax'] += rec2.amount
                    a[rec2.pax_type]['price_total'] += rec2.total
                elif rec2.charge_type.lower() == 'disc':
                    discount_value += rec2.amount

            if discount_value:
                a.update({
                    'DISC': {
                        'pax_type': 'DISC',
                        'price_per_pax': discount_value,
                        'price_total': discount_value,
                        'qty': 1,
                    }
                })

            # csc_found = []
            # for psg in rec.passenger_ids:
            #     pax_type = psg.cost_service_charge_ids[0].pax_type
                # for csc in psg.channel_service_charge_ids:
                #     if pax_type not in csc_found:
                #         a[pax_type]['price_per_pax'] += csc.amount
                #         a[pax_type]['price_total'] += csc.amount * a[pax_type]['qty']
                #         csc_found.append(pax_type)

            for sc_key in a.keys():
                sc = a[sc_key]
                customer_grand_total += sc['price_total']

            values[rec.id] = [a[new_a] for new_a in a]
            pnr_length = len(rec.pnr)
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()
        vals = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'doc_type': 'itin',
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'pnr_length': pnr_length,
            'header_width': str(header_width),
            'price_lines': values,
            'price_breakdown': price_breakdown,
            'customer_grand_total': customer_grand_total,
            'date_now': fields.Datetime.now(),
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');",
            'printout_tz': pytz.timezone('Asia/Jakarta')
        }

        if data.get('data') and 'is_with_price' in data['data']:
            vals.update({
                'with_price': data['data'].get('is_with_price') or False,
            })

        return vals


class PrintoutInsuranceItineraryForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_insurance_itinerary'
    _description = 'Report Common Printout Insurance Itinerary'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {}
            if internal_model_id == 1:
                data['context']['active_model'] = 'tt.reservation.airline'
            elif internal_model_id == 2:
                data['context']['active_model'] = 'tt.reservation.train'
            elif internal_model_id == 3:
                data['context']['active_model'] = 'tt.reservation.hotel'
            elif internal_model_id == 4:
                data['context']['active_model'] = 'tt.reservation.activity'
            elif internal_model_id == 5:
                data['context']['active_model'] = 'tt.reservation.tour'
            elif internal_model_id == 7:
                data['context']['active_model'] = 'tt.reservation.periksain'
            elif internal_model_id == 8:
                data['context']['active_model'] = 'tt.reservation.phc'
            elif internal_model_id == 9:
                data['context']['active_model'] = 'tt.reservation.medical'
            elif internal_model_id == 10:
                data['context']['active_model'] = 'tt.reservation.bus'
            elif internal_model_id == 11:
                data['context']['active_model'] = 'tt.reservation.insurance'
            else:
                data['context']['active_model'] = 'tt.agent.invoice'

            data['context']['active_ids'] = docids
        values = {}
        pnr_length = 0
        customer_grand_total = 0
        discount_value = 0
        header_width = 90
        price_breakdown = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            if rec.agent_id.is_btc_agent:
                is_break_down_price = rec.ho_id.is_btc_breakdown_price_printout
            else:
                is_break_down_price = rec.ho_id.is_agent_breakdown_price_printout
            values[rec.id] = []
            a = {}
            for rec2 in rec.sale_service_charge_ids:
                if rec2.pax_type not in a.keys():
                    a[rec2.pax_type] = {
                        'pax_type': rec2.pax_type,
                        'price_per_pax': 0,
                        'price_total': 0,
                        'qty': rec2.pax_count  # asumsi yang pertama fare, qtynya benar
                    }

                if rec2.charge_type.lower() in ['fare', 'roc', 'tax']:
                    if is_break_down_price:
                        if rec2.charge_type not in price_breakdown:
                            price_breakdown[rec2.charge_type] = 0
                        price_breakdown[rec2.charge_type] += rec2.total
                    a[rec2.pax_type]['price_per_pax'] += rec2.amount
                    a[rec2.pax_type]['price_total'] += rec2.total
                elif rec2.charge_type.lower() == 'disc':
                    discount_value += rec2.amount

            if discount_value:
                a.update({
                    'DISC': {
                        'pax_type': 'DISC',
                        'price_per_pax': discount_value,
                        'price_total': discount_value,
                        'qty': 1,
                    }
                })

            # csc_found = []
            # for psg in rec.passenger_ids:
            #     pax_type = psg.cost_service_charge_ids[0].pax_type
                # for csc in psg.channel_service_charge_ids:
                #     if pax_type not in csc_found:
                #         a[pax_type]['price_per_pax'] += csc.amount
                #         a[pax_type]['price_total'] += csc.amount * a[pax_type]['qty']
                #         csc_found.append(pax_type)

            for sc_key in a.keys():
                sc = a[sc_key]
                customer_grand_total += sc['price_total']

            values[rec.id] = [a[new_a] for new_a in a]
            pnr_length = len(rec.pnr)
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()
        vals = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'doc_type': 'itin',
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'pnr_length': pnr_length,
            'header_width': str(header_width),
            'price_lines': values,
            'price_breakdown': price_breakdown,
            'customer_grand_total': customer_grand_total,
            'date_now': fields.Datetime.now(),
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');",
            'printout_tz': pytz.timezone('Asia/Jakarta')
        }

        if data.get('data') and 'is_with_price' in data['data']:
            vals.update({
                'with_price': data['data'].get('is_with_price') or False,
            })

        return vals


class PrintoutOfflineIteneraryForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_offline_itinerary'
    _description = 'Report Common Printout Offline Itinerary'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {}
            if internal_model_id == 1:
                data['context']['active_model'] = 'tt.reservation.airline'
            elif internal_model_id == 2:
                data['context']['active_model'] = 'tt.reservation.train'
            elif internal_model_id == 3:
                data['context']['active_model'] = 'tt.reservation.hotel'
            elif internal_model_id == 4:
                data['context']['active_model'] = 'tt.reservation.activity'
            elif internal_model_id == 5:
                data['context']['active_model'] = 'tt.reservation.tour'
            else:
                data['context']['active_model'] = 'tt.agent.invoice'

            data['context']['active_ids'] = docids
        values = {}
        pnr_length = 0
        customer_grand_total = 0
        discount_value = 0
        header_width = 90
        price_breakdown = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            if rec.agent_id.is_btc_agent:
                is_break_down_price = rec.ho_id.is_btc_breakdown_price_printout
            else:
                is_break_down_price = rec.ho_id.is_agent_breakdown_price_printout
            values[rec.id] = []
            a = {}
            for rec2 in rec.sale_service_charge_ids:
                if rec2.pax_type not in a.keys():
                    a[rec2.pax_type] = {
                        'pax_type': rec2.pax_type,
                        'price_per_pax': 0,
                        'price_total': 0,
                        'qty': rec2.pax_count  # asumsi yang pertama fare, qtynya benar
                    }

                if rec2.charge_type.lower() in ['fare', 'roc', 'tax']:
                    if is_break_down_price:
                        if rec2.charge_type not in price_breakdown:
                            price_breakdown[rec2.charge_type] = 0
                        price_breakdown[rec2.charge_type] += rec2.total
                    a[rec2.pax_type]['price_per_pax'] += rec2.amount
                    a[rec2.pax_type]['price_total'] += rec2.total
                elif rec2.charge_type.lower() == 'disc':
                    discount_value += rec2.amount

            if discount_value:
                a.update({
                    'DISC': {
                        'pax_type': 'DISC',
                        'price_per_pax': discount_value,
                        'price_total': discount_value,
                        'qty': 1,
                    }
                })

            # csc_found = []
            # for psg in rec.passenger_ids:
            #     pax_type = psg.cost_service_charge_ids[0].pax_type
                # for csc in psg.channel_service_charge_ids:
                #     if pax_type not in csc_found:
                #         a[pax_type]['price_per_pax'] += csc.amount
                #         a[pax_type]['price_total'] += csc.amount * a[pax_type]['qty']
                #         csc_found.append(pax_type)

            for sc_key in a.keys():
                sc = a[sc_key]
                customer_grand_total += sc['price_total']

            values[rec.id] = [a[new_a] for new_a in a]
            pnr_length = len(rec.pnr)
            if pnr_length > 27:
                header_width += 3 * (abs(27 - pnr_length))
                if header_width > 105:
                    header_width = 105
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()

        vals = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'doc_type': 'itin',
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'pnr_length': pnr_length,
            'header_width': str(header_width),
            'price_lines': values,
            'price_breakdown': price_breakdown,
            'customer_grand_total': customer_grand_total,
            'date_now': fields.Datetime.now(),
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');"
        }

        if data.get('data') and 'is_with_price' in data['data']:
            vals.update({
                'with_price': data['data'].get('is_with_price') or False,
            })
        return vals


class PrintoutJSONIteneraryForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_json_itinerary'
    _description = 'Report Common Printout JSON Itinerary'

    @api.model
    def _get_report_values(self, docids, data=None):
        '''
        values = {
            'type': 'hotel', ** hotel, activity**
            'line': [
                {** Hotel **
                    'resv': 'qwe123', ** PNR / Resv Code **
                    'checkin': '2019-10-24', ** YYYY-mm-DD **
                    'checkout': '2019-10-26',
                    'hotel_name': 'Hotel Mawar',
                    'room_name': 'Superior Room',
                    'meal_type': 'Room Only',
                },
                {** Activity **
                    'resv': 'qwe123', ** PNR / Resv Code **
                    'checkin': '2019-10-24', ** YYYY-mm-DD **
                    'time_slot': '09:30:00 - 13:30:00',
                    'activity_title': 'KidsSTOP Singapore E-voucher',
                    'product_type': 'Weekday Admission',
                },
            ],
            'passenger': [
                {
                    'ticket_number': '12345678', ** airline/train only **
                    'name': '', **Mr. F_name L_name**
                    'pax_type': 'Elder', **Elder, Adult, Child, Infant**
                    'birth_date': '1993-08-17', ** YYYY-mm-dd **
                    'additional_info': ['Room: 1'],
                        **klo airline: baggage**,
                        **klo hotel: room apa?**,
                }
            ],
            'price_detail': [
                {
                    'name': **Passenger Name**,
                    'pax_type': 'ADT' **ADT, CHD, INF, YCD**,
                    'fare': 0,
                    'tax': 0,
                    'total': 0, ** fare + tax **
                }
            ],
        }
        '''
        values = {}
        header_width = 90
        ## BELUM TAHU AMBIL BREAKDOWN DIMANA ##
        price_breakdown = {}
        if data.get('context'):
            values = json.loads(data['context']['json_content'])
            # values = [{
            #     'agent_id': 1,
            #     'type': 'hotel',
            #     'line': [
            #         {
            #             'resv': 'qwe123',
            #             'checkin': '2019-10-24',
            #             'checkout': '2019-10-26',
            #             'hotel_name': 'Hotel Mawar',
            #             'room_name': 'Superior Room',
            #             'meal_type': 'Room Only',
            #         },
            #     ],
            #     'passenger': [
            #         {
            #             'ticket_number': '',
            #             'name': 'Mr Vincentius Hadi',
            #             'pax_type': 'Adult',
            #             'birth_date': '1993-08-17',
            #             'additional_info': ['Room: 1', 'Special Req: Non Smoking Rooms'],
            #         }
            #     ],
            #     'price_detail': [
            #         {
            #             'name': 'Mr Vincentius Hadi',
            #             'pax_type': 'ADT',
            #             'fare': 50000,
            #             'tax': 1250,
            #             'total': 51250,
            #         }
            #     ],
            # }]

            values['agent_id'] = self.env['tt.agent'].search([('name', '=ilike', values['agent_name'])], limit=1)
        # data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        # if hasattr(data_object, 'agent_id'):
        if values.get('agent_id'):
            base_color = values['agent_id'].get_printout_agent_color()
        vals = {
            'doc_ids': False,
            'doc_model': 'tt.reservation.hotel',  # Can be set to as any model
            'doc_type': 'itin', #untuk judul report
            'docs': [values,],
            'price_breakdown': price_breakdown,
            'header_width': str(header_width),
            'date_now': fields.Datetime.now(),
            'currency_id': self.env.user.company_id.currency_id,
            'base_color': base_color,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');"
        }

        if data.get('data') and 'is_with_price' in data['data']:
            vals.update({
                'with_price': data['data'].get('is_with_price') or False,
            })

        return vals


class PrintoutBilling(models.AbstractModel):
    _name = 'report.tt_report_common.printout_billing'
    _description = 'Report Common Printout Billing'

    def compute_terbilang_from_objs(self, recs, currency_str='rupiah'):
        a = {}
        for rec2 in recs:
            a.update({rec2.name: num2words(rec2.amount_total) + ' Rupiah'})
        return a

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {
                'active_model': 'tt.billing.statement',
                'active_ids': docids
            }
        header_width = 90
        agent_id = False
        cust_parent_id = False
        ## TIDAK DI BREAKDOWN ##
        price_breakdown = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            if rec.agent_id.is_btc_agent:
                is_break_down_price = rec.ho_id.is_btc_breakdown_price_printout
            else:
                is_break_down_price = rec.ho_id.is_agent_breakdown_price_printout
            agent_id = rec.agent_id
            cust_parent_id = rec.customer_parent_id
        billing_footer = self.env['tt.report.common.setting'].get_footer('billing_statement', agent_id)
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        ho_obj = False
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()
            ho_obj = data_object.agent_id.ho_id
        vals = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'doc_type': 'ho_billing' if not cust_parent_id else '',
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'price_breakdown': price_breakdown,
            'terbilang': self.compute_terbilang_from_objs(
                self.env[data['context']['active_model']].browse(data['context']['active_ids'])),
            # 'last_billing': self.last_billing(
            #     self.env[data['context']['active_model']].browse(data['context']['active_ids'])),
            'header_width': str(header_width),
            'billing_footer': billing_footer and billing_footer[0].html or '',
            'base_color': base_color,
            'static_url': static_url,
            'ho_obj': ho_obj,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');"
        }

        if data.get('data') and 'is_with_price' in data['data']:
            vals.update({
                'with_price': data['data'].get('is_with_price') or False,
            })

        return vals


class PrintoutTopUp(models.AbstractModel):
    _name = 'report.tt_report_common.printout_topup'
    _description = 'Report Common Printout Topup'

    def compute_terbilang_from_objs(self, recs, currency_str='Rupiah'):
        a = {}
        for rec2 in recs:
            a.update({rec2.name: num2words(rec2.total) + ' ' + currency_str})
        return a

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {
                'active_model': 'tt.billing.statement',
                'active_ids': docids
            }
        values = {}
        agent_id = False
        ## TIDAK DI BREAKDOWN ##
        price_breakdown = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            values.update({
                'amount': rec.amount,
                'unique_amount': rec.unique_amount,
                'total': rec.total,
                'fees': rec.fees,
                'total_with_fees': rec.total_with_fees
            })
            agent_id = rec.agent_id
        top_up_footer = self.env['tt.report.common.setting'].get_footer('top_up', agent_id)
        header_width = 90
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        base_color = '#CDCDCD'
        ho_obj = False
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()
            ho_obj = data_object.agent_id.ho_id
        return {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'doc_type': 'top_up',
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'values': values,
            'price_breakdown': price_breakdown,
            'terbilang': self.compute_terbilang_from_objs(
                self.env[data['context']['active_model']].browse(data['context']['active_ids'])),
            'header_width': str(header_width),
            'ho_obj': ho_obj,
            'top_up_footer': top_up_footer and top_up_footer[0].html or '',
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');"
        }


class PrintoutRefund(models.AbstractModel):
    _name = 'report.tt_report_common.printout_refund'
    _description = 'Report Common Printout Refund'

    def compute_terbilang_from_objs(self, recs, is_ho=False, currency_str='rupiah'):
        a = {}
        for rec2 in recs:
            if is_ho:
                a.update({rec2.name: num2words(rec2.total_amount) + ' Rupiah'})
            else:
                a.update({rec2.name: num2words(rec2.total_amount_cust) + ' Rupiah'})
        return a

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {
                'active_model': 'tt.refund',
                'active_ids': docids
            }

        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        header_width = 90
        base_color = '#CDCDCD'
        ho_obj = False
        ## TIDAK DI BREAKDOWN ##
        price_breakdown = {}
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()
            ho_obj = data_object.agent_id.ho_id
        return_dat = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'docs': data_object,
            'price_breakdown': price_breakdown,
            'is_ho': data['data'].get('is_ho') and data['data']['is_ho'] or False,
            'is_agent': data['data'].get('is_agent') and data['data']['is_agent'] or False,
            'is_est': data['data'].get('is_est') and data['data']['is_est'] or False,
            'header_width': str(header_width),
            'terbilang': self.compute_terbilang_from_objs(
                self.env[data['context']['active_model']].browse(data['context']['active_ids']), data['data'].get('is_ho')),
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');"
        }

        if data['data'].get('is_ho') and ho_obj:
            return_dat.update({
                'ho_obj': ho_obj
            })

        return return_dat


class PrintoutReschedule(models.AbstractModel):
    _name = 'report.tt_report_common.printout_reschedule'
    _description = 'Report Common Printout Reschedule'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {
                'active_model': 'tt.refund',
                'active_ids': docids
            }

        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        header_width = 90
        base_color = '#CDCDCD'
        ## TIDAK DI BREAKDOWN ##
        price_breakdown = {}
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()
        return {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'docs': data_object,
            'price_breakdown': price_breakdown,
            'header_width': str(header_width),
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');"
        }


class PrintoutVoucher(models.AbstractModel):
    _name = 'report.tt_report_common.printout_voucher'
    _description = 'Report Common Printout Voucher'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {
                'active_model': 'tt.voucher.detail',
                'active_ids': docids
            }

        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        header_width = 90
        base_color = '#CDCDCD'
        ho_obj = False
        ## TIDAK DI BREAKDOWN ##
        price_breakdown = {}
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()
            ho_obj = data_object.agent_id.ho_id
        return {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'doc_type': 'voucher',
            'docs': data_object,
            'price_breakdown': price_breakdown,
            'doc_start_date': data_object.voucher_start_date and data_object.voucher_start_date.astimezone(pytz.timezone('Asia/Jakarta')) or False,
            'doc_expire_date': data_object.voucher_expire_date and data_object.voucher_expire_date.astimezone(pytz.timezone('Asia/Jakarta')) or False,
            'header_width': str(header_width),
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');",
            'ho_obj': ho_obj or False
        }


class PrintoutLetterOfGuarantee(models.AbstractModel):
    _name = 'report.tt_report_common.printout_letter_guarantee'
    _description = 'Report Common Printout Letter Guarantee'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {
                'active_model': 'tt.letter.guarantee',
                'active_ids': docids
            }
        agent_id = False
        data_object = self.env[data['context']['active_model']].browse(data['context']['active_ids'])
        header_width = 90
        # for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
        #     agent_id = rec.agent_id
        lg_po_footer = self.env['tt.report.common.setting'].get_footer('letter_guarantee_po', agent_id)
        lg_footer = self.env['tt.report.common.setting'].get_footer('letter_guarantee', agent_id)
        base_color = '#CDCDCD'
        ho_obj = False
        ## TIDAK DI BREAKDOWN ##
        price_breakdown = {}
        if hasattr(data_object, 'agent_id'):
            base_color = data_object.agent_id.get_printout_agent_color()
            ho_obj = data_object.agent_id.ho_id
        elif hasattr(data_object, 'ho_id'):
            base_color = data_object.ho_id.get_printout_agent_color()
            ho_obj = data_object.ho_id
        return {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'doc_type': 'letter_of_guarantee',
            'docs': data_object,
            'price_breakdown': price_breakdown,
            'lg_po_footer': lg_po_footer and lg_po_footer[0].html or '',
            'lg_footer': lg_footer and lg_footer[0].html or '',
            'header_width': str(header_width),
            'base_color': base_color,
            'static_url': static_url,
            'img_url': "url('/tt_report_common/static/images/background footer airline.jpg');",
            'provider_ho_obj': data_object.get_provider_ho_data(),
            'ho_obj': ho_obj or False
        }
