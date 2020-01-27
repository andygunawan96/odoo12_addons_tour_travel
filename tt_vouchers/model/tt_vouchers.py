from odoo import api, models, fields
from ...tools import variables
from datetime import datetime
import logging,traceback
import json
from ...tools.ERR import RequestException
from ...tools import ERR

_logger = logging.getLogger(__name__)

class TtVoucher(models.Model):
    _name = "tt.voucher"
    _description = 'Rodex Model Voucher'
    voucher_reference_code = fields.Char("Reference Code")
    voucher_coverage = fields.Selection([("all", "All"), ("product", "Specified Product"), ("provider", "Specified Provider")])
    voucher_type = fields.Selection([("percent", "Percentage"), ("amount", "Some Amount")])
    currency_id = fields.Many2one("res.currency")
    voucher_value = fields.Float("Voucher value")
    voucher_maximum_cap = fields.Float("Voucher Cap")
    voucher_minimum_purchase = fields.Float('Voucher Minimum Purchase')
    voucher_detail_ids = fields.One2many("tt.voucher.detail", "voucher_id", "Voucher Detail")
    voucher_author_id = fields.Many2one('res.users', 'author')   # voucher maker

    voucher_effect_all = fields.Boolean("Total", default=True)
    voucher_effect_base_fare = fields.Boolean("Base Fare")

    voucher_state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'), ('not-active', 'Not Active')], default="draft")
    voucher_agent_type_eligibility_ids = fields.Many2many("tt.agent.type", "tt_agent_type_tt_voucher_rel", "tt_voucher_id", "tt_agent_type_id", "Agent Type")      #type of user that are able to use the voucher
    voucher_agent_eligibility_ids = fields.Many2many('tt.agent', "tt_agent_tt_voucher_rel", "tt_voucher_id", "tt_agent_id", "Agent ID")                                        # who can use the voucher
    voucher_provider_type_eligibility_ids = fields.Many2many("tt.provider.type", "tt_provider_type_tt_voucher_rel", "tt_voucher_id", "tt_provider_type_id", "Provider Type")                         # what product this voucher can be applied
    voucher_provider_eligibility_ids = fields.Many2many('tt.provider', "tt_provider_tt_voucher_rel", "tt_voucher_id", "tt_provier_id", "Provider ID")                                  # what provider this voucher can be applied

    #harus di cek sama dengan atasnya

    def create_voucher(self, data):
        result = self.env['tt.voucher'].create({
            'voucher_coverage': data['voucher_coverage'],
            'voucher_type': data['voucher_type'],
            'currency_id': data['currency_id'],
            'voucher_value': data['voucher_value'],
            'voucher_maximum_cap': data['voucher_maximum_cap'],
            'voucher_author_id': data['voucher_provider'],
            'voucher_eligibility_ids': data['voucher_eligibility'],
            'voucher_product_eligibility_ids': data['voucher_product_eligibility']
        })

        #create reference code
        if result.voucher_type == "percent":
            reference_code = "VCHS" + "01" + result.id
        else:
            reference_code = "VCHS" + "02" + result.id
        result.write({
            'reference_code': reference_code
        })

        return result

    def get_voucher(self, data, context):
        # data = {
        #     reference_code        = ''    '' --> for all
        #     start_date            = ''
        #     end_date              = ''
        #     provider_type         = ''    --> for multiple provider type list i.e ['airline', 'train']
        #     provider              = ''    --> for multiple provider use list i.e ['amadeus', 'garuda']
        # }

        error_list = ""
        searched_filter = []

        try:
            if data['reference_code'] != '':
                #split the reference code
                splits = data['reference_code'].split(".")
                data['voucher_reference'] = splits[0]
                searched_filter.append(('voucher_reference_code', '=', data['voucher_reference']))
                try:
                    data['voucher_reference_period'] = splits[1]
                except:
                    data['voucher_reference_period'] = ''

                # try:
                #     searched_filter.append(('voucher_agent_type_eligibility_ids', '=', context['co_agent_type_id']))
                #     searched_filter.append(('voucher_agent_eligibility_ids', '=', context['co_agent_id']))
                # except:
                #     _logger.error('search voucher without context')
                #     return ERR.get_error(additional_message="cannot search voucher without context")

                voucher_result = self.env['tt.voucher'].search(searched_filter)

                if len(voucher_result) < 1:
                    return ERR.get_error(additional_message="Voucher not found")

                #set voucher coverage return
                if voucher_result[0].voucher_coverage == 'all':
                    description = 'all'
                    provider_coverage = 'all'
                else:
                    temp_list = []
                    provider_list = []
                    for i in voucher_result[0].voucher_provider_type_eligibility_ids:
                        temp_list.append(i.name)
                    description = (",").join(temp_list)
                    for i in voucher_result[0].voucher_provider_eligibility_ids:
                        provider_list.append(i.name)
                    provider_coverage = (",").join(provider_list)

                #set_voucher_affecting
                if voucher_result[0]['voucher_effect_all']:
                    voucher_affecting = "Total"
                elif voucher_result[0]['voucher_effect_bas_fare']:
                    voucher_affecting = "Base Fare"
                else:
                    voucher_affecting = "Not Set"

                #set voucher detail within voucher reference period
                if data['voucher_reference_period'] != '':
                    voucher_detail = voucher_result[0].voucher_detail_ids.filtered(lambda x: x['voucher_reference_code'] == data['voucher_reference'] and x['voucher_period_reference'] == data['voucher_reference_period'])
                else:
                    voucher_detail = voucher_result[0].voucher_detail_ids[0]

                #set maximum cap to False if 0
                if voucher_result[0].voucher_maximum_cap < 1:
                    maximum_cap = False
                else:
                    maximum_cap = voucher_result[0].voucher_maximum_cap

                #set minimum requirement to False if 0
                if voucher_result[0].voucher_minimum_purchase < 1:
                    minimum_purchase = False
                else:
                    minimum_purchase = voucher_result[0].voucher_minimum_purchase

                voucher_data = {
                    'reference_code': "%s.%s" % (voucher_detail[0].voucher_reference_code, voucher_detail[0].voucher_period_reference),
                    'voucher_type': voucher_result[0].voucher_type,
                    'voucher_coverage': description,
                    'voucher_affecting': voucher_affecting,
                    'voucher_provider_coverage': provider_coverage,
                    'voucher_value': voucher_result[0].voucher_value,
                    'maximum_cap': maximum_cap,
                    'minimum_purchase': minimum_purchase,
                    'voucher_end_date': voucher_detail[0].voucher_expire_date.strftime("%Y-%m-%d"),
                    'left': int(voucher_detail[0].voucher_quota - voucher_detail[0].voucher_used)
                }

                return ERR.get_no_error(voucher_data)
        except:
            _logger.error('search voucher without reference code')
            pass

        ## if voucher search is without reference
        try:
            if data['provider_type'] != '':

                #check if provider_type is a list
                if type(data['provider_type']) is list:

                    # cooming soon feature
                    return ERR.get_error(additional_message="Cooming soon")

                #if provider_type is only string
                else:
                    provider_type = self.env['tt.provider.type'].search([('name', '=', data['provider_type'])])

                    searched_filter.append('|')
                    searched_filter.append(('voucher_coverage', '=', 'all'))
                    searched_filter.append(('voucher_provider_type_eligibility_ids', '=', provider_type.id))

        except:
            error_list += "Must include provider type\n"

        try:
            if data['provider'] != '':

                if type(data['provider']) is list:

                    # cooming soon feature
                    return ERR.get_error(additional_message="Cooming soon")

                else:
                    provider = self.env['tt.provider'].search([('name', '=', data['provider'])])

                    if data['provider_type'] == '':
                        searched_filter.append('|')
                        searched_filter.append(('voucher_coverage', '=', 'all'))
                    searched_filter.append(('voucher_provider_eligibility_ids', '=', provider.id))
        except:
            error_list += "Must include provider\n"

        # try:
        #     searched_filter.append(('voucher_agent_type_eligibility_ids', '=', context['co_agent_type_id']))
        #     searched_filter.append(('voucher_agent_eligibility_ids', '=', context['co_agent_id']))
        # except:
        #     _logger.error('search voucher without context')
        #     error_list += "cannot search voucher without context \n"

        final_voucher = []
        if error_list == '':
            #search voucher
            voucher_result = self.env['tt.voucher'].search(searched_filter)

            #if no voucher found
            if len(voucher_result) < 1:
                return ERR.get_error(additional_message="Voucher not found")

            for i in voucher_result:
                #set search party for date
                if data['start_date'] != '':
                    if data['end_date'] != '':
                        #start and end
                        voucher_detail = i.voucher_detail_ids.filtered(lambda x: x['voucher_start_date'].strftime("%Y-%m-%d") <= data['start_date'] and x['voucher_expire_date'].strftime("%Y-%m-%d") >= data['end_date'])
                    else:
                        #start only
                        voucher_detail = i.voucher_detail_ids.filtered(lambda x: x['voucher_start_date'].strftime("%Y-%m-%d") <= data['start_date'])
                else:
                    if data['end_date'] != '':
                        #end only
                        voucher_detail = i.voucher_detail_ids.filtered(lambda x: x['voucher_expire_date'].strftime("%Y-%m-%d") >= data['end_date'])
                    else:
                        voucher_detail = i.voucher_detail_ids

                #filtered voucher so only voucher within specific date
                for j in voucher_detail:
                    #set voucher coverage return
                    if j.voucher_id.voucher_coverage == 'all':
                        description = 'all'
                        provider_coverage = 'all'
                    else:
                        temp_list = []
                        provider_list = []
                        for k in j.voucher_id.voucher_provider_type_eligibility_ids:
                            temp_list.append(k.name)
                        description = (",").join(temp_list)
                        for k in j.voucher_id.voucher_provider_eligibility_ids:
                            provider_list.append(k.name)
                        provider_coverage = (",").join(provider_list)

                    # set maximum cap to False if 0
                    if j.voucher_id.voucher_maximum_cap < 1:
                        maximum_cap = False
                    else:
                        maximum_cap = j.voucher_id.voucher_maximum_cap

                    # set minimum requirement to False if 0
                    if j.voucher_id.voucher_minimum_purchase < 1:
                        minimum_purchase = False
                    else:
                        minimum_purchase = j.voucher_id.voucher_minimum_purchase

                    voucher_data = {
                        'reference_code': "%s.%s" % (j.voucher_reference_code, j.voucher_period_reference),
                        'voucher_type': j.voucher_id.voucher_type,
                        'voucher_coverage': description,
                        'voucher_provider_coverage': provider_coverage,
                        'voucher_value': j.voucher_id.voucher_value,
                        'maximum_cap': maximum_cap,
                        'minimum_purchase': minimum_purchase,
                        'voucher_end_date': j.voucher_expire_date.strftime("%Y-%m-%d"),
                        'left': int(j.voucher_quota - j.voucher_used)
                    }
                    final_voucher.append(voucher_data)
        else:
            _logger.error(error_list)
            return ERR.get_error(additional_message=error_list)

        return ERR.get_no_error(final_voucher)

    def is_product_eligible(self, data):
        voucher = self.env['tt.voucher'].search([('voucher_reference_code', "=", data['voucher_reference'])])
        is_eligible = False
        if voucher.voucher_coverage == 'all':
            is_eligible = True
        else:
            provider_type = voucher.voucher_provider_type_eligibility_ids.filtered(lambda x: x['id'] == data['provider_type_id'])
            if provider_type.id != False:
                is_eligible = True

            provider = voucher.voucher_provider_eligibility_ids.filtered(lambda x: x['id'] == data['provider_id'])
            if provider.id == False:
                is_eligible = False

        return is_eligible

    #update
    def is_agent_eligible(self, data):
        voucher = self.env['tt.voucher'].search([('voucher_reference_code', "=", data['voucher_reference'])])
        is_eligible = False
        is_empty = False
        if len(voucher.voucher_agent_type_eligibility_ids) < 1 and len(voucher.voucher_agent_eligibility_ids) < 1:
            is_empty = True
            is_eligible = True

        if not is_empty:
            agent_type = voucher.voucher_agent_type_eligibility_ids.filtered(lambda x: x['id'] == data['agent_type_id'])
            if agent_type.id != False:
                is_eligible = True

            agent = voucher.voucher_agent_eligibility_ids.filtered(lambda x: x['id'] == data['agent_id'])
            if agent.id != False:
                is_eligible = True
            else:
                is_eligible = False

        return is_eligible

    def is_purchase_allowed(self, data):
        voucher = self.env['tt.voucher'].search([('voucher_reference_code', '=', data['voucher_reference'])])
        is_eligible = False
        if data['purchase'] >= voucher.voucher_minimum_purchase:
            is_eligible = True

        return is_eligible

    @api.onchange('voucher_agent_type_eligibility_ids')
    def _onchange_action_agent_type(self):
        domain = {'voucher_agent_eligibility_ids': []}
        if self.voucher_agent_type_eligibility_ids != False:
            self.voucher_agent_eligibility_ids = False
            domain = {
                'voucher_agent_eligibility_ids': [('agent_type_id', 'in', self.voucher_agent_type_eligibility_ids.ids)]
            }
        return {'domain': domain}

    @api.onchange('voucher_provider_type_eligibility_ids')
    def _onchange_action_provider_type(self):
        domain = {'voucher_provider_eligibility_ids': []}
        if self.voucher_provider_type_eligibility_ids != False:
            self.voucher_provider_eligibility_ids = False
            domain = {
                'voucher_provider_eligibility_ids': [('provider_type_id', 'in', self.voucher_provider_type_eligibility_ids.ids)]
            }
        return {'domain': domain}

    @api.onchange('voucher_effect_all')
    def _onchange_action_total(self):
        if self.voucher_effect_all == True:
            self.voucher_effect_base_fare = False

    @api.onchange('voucher_effect_base_fare')
    def _onchange_action_base_fare(self):
        if self.voucher_effect_base_fare == True:
            self.voucher_effect_all = False

class TtVoucherDetail(models.Model):
    _name = "tt.voucher.detail"
    _description = 'Rodex Model Voucher Detail'

    voucher_id = fields.Many2one("tt.voucher")
    voucher_reference_code = fields.Char("Voucher Reference", related="voucher_id.voucher_reference_code")
    voucher_period_reference = fields.Char("Voucher Period Reference")
    voucher_start_date = fields.Datetime("voucher starts")
    voucher_expire_date = fields.Datetime("voucher end")
    voucher_used = fields.Integer("Voucher use")
    voucher_quota = fields.Integer("Voucher quota")
    voucher_blackout_ids = fields.One2many("tt.voucher.detail.blackout", 'voucher_detail_id')
    voucher_used_ids = fields.One2many("tt.voucher.detail.used", "voucher_detail_id")
    voucher_detail_state = fields.Selection([('not-active', 'Not Active'), ('active', 'Active'), ('expire', 'Expire')], default="not-active")

    def get_voucher_remainder(self, voucher_id):
        voucher = self.env['tt.voucher.detail'].browse(int(voucher_id))
        return voucher.voucher_quota - voucher.voucher_used

    def get_voucher_detail_all(self):
        voucher = self.env['tt.voucher.detail'].search([])
        return voucher

    def get_voucher_detail(self, voucher_id):
        voucher = self.env['tt.voucher.detail'].browse(int(voucher_id)).read()
        voucher[0]['voucher_number'] = "%s.%s" % (voucher[0]['voucher_reference_code'], voucher[0]['voucher_period_reference'])
        return voucher

    #function for cron
    def activate_voucher(self):
        voucher = self.env['tt.voucher.detail'].search([('voucher_detail_state', '=', 'not-active')])
        for i in voucher:
            if i.voucher_start_date.strftime("%Y-%m-%d") <= datetime.today().strftime("%Y-%m-%d"):
                i.write({
                    'voucher_detail_state': 'active'
                })
        return 0

    #function for cron
    def expire_voucher(self):
        voucher = self.env['tt.voucher.detail'].search([('voucher_detail_state', '=', 'active')])
        for i in voucher:
            if i.voucher_expire_date.strftime("%Y-%m-%d") < datetime.today().strftime("%Y-%m-%d"):
                i.write({
                    'voucher_detail_state': 'expire'
                })

        return 0

    def simulate_voucher(self, data, context):
        # requirement of data
        # data = {
        #     order_number
        #     voucher_reference
        #     date          <-- date vouchernya digunakan (today)
        #     provider_type
        # }

        #get order data
        order_obj = self.env['tt.reservation.%s' % (data['provider_type'])].search([('name', '=', data['order_number'])])
        dependencies_data = order_obj.provider_booking_ids

        ####################################################################
        #   check if voucher is eligible to use
        ####################################################################
        splits = data['voucher_reference'].split(".")
        data['voucher_reference_code'] = splits[0]
        try:
            data['voucher_reference_period'] = splits[1]
        except:
            _logger.error("%s didn't give period reference code" % data['voucher_reference'])
            return ERR.get_error(additional_message="must provide voucher period reference")

        # check if voucher exist
        voucher = self.env['tt.voucher'].search([('voucher_reference_code', '=', data['voucher_reference_code'])])
        if voucher.id == False:
            _logger.error("%s, voucher is not exist" % data['voucher_reference'])
            return ERR.get_error(additional_message="Voucher is not exist")

        voucher_detail = voucher.voucher_detail_ids.filtered(lambda x: x['voucher_reference_code'] == data['voucher_reference_code'] and x['voucher_period_reference' == data['voucher_reference_period']])
        if voucher_detail.id == False:
            _logger.error("%s, voucher is not exist" % data['voucher_reference'])
            return ERR.get_error(additional_message="Voucher is not exist")

        if voucher_detail.voucher_detail_state == 'expire':
            _logger.error("%s, voucher is expired" % data['voucher_reference'])
            return ERR.get_error(additional_message="Voucher is Expired")

        if voucher_detail.voucher_used >= voucher_detail.voucher_quota and voucher_detail.voucher_quota != -1:
            _logger.error("%s, voucher Sold Out" % data['voucher_reference'])
            return ERR.get_error(additional_message="Voucher sold out")

        to_check = {
            'voucher_reference': data['voucher_reference_code'],
            'agent_type_id': context['co_agent_type_id'],
            'agent_id': context['co_agent_id']
        }
        agent_is_eligible = self.env['tt.voucher'].is_agent_eligible(to_check)
        if not agent_is_eligible:
            _logger.error("%s, agent cannot use the voucher" % data['voucher_reference'])
            return ERR.get_error(additional_message="Agent cannot use the voucher")

        #check for minimum purchase
        order_provider = order_obj.provider_name.split(",")

        result_array = []
        #check if provider is more than one
        if len(order_provider) < 2:
            # # # # # # # # # # # # # # # # # # # #
            #   only one provider                 #
            # # # # # # # # # # # # # # # # # # # #

            #check if voucher covers all provider
            if voucher.voucher_coverage == 'all':

                #check if minimum purchase is allowed
                order_purchase = order_obj.total_fare
                if order_purchase < voucher.voucher_minimum_purchase and voucher.voucher_minimum_purchase != -1:
                    #not meet required minimum purchase
                    _logger.error("%s cannot use the voucher, minimum purchase not meet" % data['order_number'])
                    return ERR.get_error(additional_message="Do not meet minimum purchase, cannot use voucher")

                #if allowed
                #count every provider booking
                if voucher.voucher_effect_all:
                    for i in dependencies_data:
                        provider_total_price = 0.0
                        provider_total_discount = 0.0
                        provider_final_total_price = 0.0
                        temp_array = []
                        for j in i.cost_service_charge_ids:
                            if j.charge_type != 'RAC':
                                # count the discount
                                discount_amount = float(j.total) * voucher.voucher_value / 100.0
                                final_amount = float(j.total) - float(discount_amount)

                                provider_total_price += float(j.total)
                                provider_total_discount += float(discount_amount)

                                result_temp = {
                                    'charge_code': j.charge_code,
                                    'charge_type': j.charge_type,
                                    'start_amount': j.total,
                                    'discount_value': voucher.voucher_value,
                                    'discount_amount': float(discount_amount),
                                    'final_amount': float(final_amount),
                                }
                            else:
                                #RAC will not be affected by voucher
                                provider_total_price += float(j.total)
                                result_temp = {
                                    'charge_code': j.charge_code,
                                    'charge_type': j.charge_type,
                                    'start_amount': j.total,
                                    'discount_value': 0,
                                    'discount_amount': 0,
                                    'final_amount': j.total,
                                }

                            temp_array.append(result_temp)

                        #set data to return
                        provider_final_total_price = provider_total_price - provider_total_discount
                        result_dict = {
                            'provider_type_code': i.provider_id.provider_type_id.code,
                            'provider_code': i.provider_id.code,
                            'provider_total_price': provider_total_price,
                            'provider_total_discount': provider_total_discount,
                            'provider_final_price': provider_final_total_price,
                            'discount_detail': temp_array
                        }
                        result_array.append(result_dict)

                # elif voucher.voucher_effect_base_fare:
                else:
                    for i in dependencies_data:
                        provider_total_price = 0.0
                        provider_total_discount = 0.0
                        temp_array = []
                        for j in i.cost_service_charge_ids:
                            if j.charge_code == 'fare' or j.charge_code == 'FarePrice':
                                # count the discount
                                discount_amount = float(j.total) * voucher.voucher_value / 100.0
                                final_amount = float(j.total) - float(discount_amount)

                                provider_total_price += float(j.total)
                                provider_total_discount += float(discount_amount)

                                result_temp = {
                                    'charge_code': j.charge_code,
                                    'charge_type': j.charge_type,
                                    'start_amount': j.total,
                                    'discount_value': voucher.voucher_value,
                                    'discount_amount': float(discount_amount),
                                    'final_amount': float(final_amount),
                                }
                            else:

                                #only fare affected by voucher
                                provider_total_price += float(j.total)
                                result_temp = {
                                    'charge_code': j.charge_code,
                                    'charge_type': j.charge_type,
                                    'start_amount': j.total,
                                    'discount_value': 0,
                                    'discount_amount': 0,
                                    'final_amount': j.total,
                                }

                            temp_array.append(result_temp)

                        #create data to return
                        provider_final_total_price = float(provider_total_price) - float(provider_total_discount)
                        result_dict = {
                            'provider_type_code': i.provider_id.provider_type_id.code,
                            'provider_code': i.provider_id.code,
                            'provider_total_price': provider_total_price,
                            'provider_total_discount': provider_total_discount,
                            'provider_final_price': provider_final_total_price,
                            'discount_detail': temp_array
                        }
                        result_array.append(result_dict)
            else:
                #check minimum purchase
                order_purchase = order_obj.total_fare
                if order_purchase < voucher.voucher_minimum_purchase and voucher.voucher_minimum_purchase != -1:
                    # not meet required minimum purchase
                    _logger.error("%s cannot use the voucher, minimum purchase not meet" % data['order_number'])
                    return ERR.get_error(additional_message="Do not meet minimum purchase, cannot use voucher")

                temp_dict = {
                    'voucher_reference': data['voucher_reference_code'],
                    'provider_type_id': dependencies_data.provider_id.provider_type_id.id,
                    'provider_id': dependencies_data.provider_id.id,
                    'provider_name': dependencies_data.provider_id.code
                }
                provider_is_eligible = self.env['tt.voucher'].is_product_eligible(temp_dict)
                if provider_is_eligible:

                    for i in dependencies_data:
                        provider_total_price = 0.0
                        provider_total_discount = 0.0
                #voucher not covers all provider

                        if voucher.voucher_effect_all:

                            temp_array = []
                            for j in i.cost_service_charge_ids:
                                if j.charge_type != 'RAC':
                                    # count the discount
                                    discount_amount = float(j.total) * voucher.voucher_value / 100.0
                                    final_amount = float(j.total) - float(discount_amount)

                                    provider_total_price += float(j.total)
                                    provider_total_discount += float(discount_amount)

                                    result_temp = {
                                        'charge_code': j.charge_code,
                                        'charge_type': j.charge_type,
                                        'start_amount': j.total,
                                        'discount_value': voucher.voucher_value,
                                        'discount_amount': float(discount_amount),
                                        'final_amount': float(final_amount),
                                    }
                                else:
                                    # RAC will not be affected by voucher
                                    provider_total_price += float(j.total)
                                    result_temp = {
                                        'charge_code': j.charge_code,
                                        'charge_type': j.charge_type,
                                        'start_amount': j.total,
                                        'discount_value': 0,
                                        'discount_amount': 0,
                                        'final_amount': j.total,
                                    }

                                temp_array.append(result_temp)

                            # set data to return
                            provider_final_total_price = provider_total_price - provider_total_discount
                            result_dict = {
                                'provider_type_code': i.provider_id.provider_type_id.code,
                                'provider_code': i.provider_id.code,
                                'provider_total_price': provider_total_price,
                                'provider_total_discount': provider_total_discount,
                                'provider_final_price': provider_final_total_price,
                                'discount_detail': temp_array
                            }
                            result_array.append(result_dict)

                        # elif voucher.voucher_effect_base_fare:
                        else:
                            temp_array = []
                            for j in i.cost_service_charge_ids:
                                if j.charge_code == 'fare' or j.charge_code == 'FarePrice':
                                    # count the discount
                                    discount_amount = float(j.total) * voucher.voucher_value / 100.0
                                    final_amount = float(j.total) - float(discount_amount)

                                    provider_total_price += float(j.total)
                                    provider_total_discount += float(discount_amount)

                                    result_temp = {
                                        'charge_code': j.charge_code,
                                        'charge_type': j.charge_type,
                                        'start_amount': j.total,
                                        'discount_value': voucher.voucher_value,
                                        'discount_amount': float(discount_amount),
                                        'final_amount': float(final_amount),
                                    }
                                else:
                                    # only fare affected by voucher
                                    provider_total_price += float(j.total)
                                    result_temp = {
                                        'charge_code': j.charge_code,
                                        'charge_type': j.charge_type,
                                        'start_amount': j.total,
                                        'discount_value': 0,
                                        'discount_amount': 0,
                                        'final_amount': j.total,
                                    }

                                temp_array.append(result_temp)

                            # create data to return
                            provider_final_total_price = float(provider_total_price) - float(provider_total_discount)
                            result_dict = {
                                'provider_type_code': i.provider_id.provider_type_id.code,
                                'provider_code': i.provider_id.code,
                                'provider_total_price': provider_total_price,
                                'provider_total_discount': provider_total_discount,
                                'provider_final_price': provider_final_total_price,
                                'discount_detail': temp_array
                            }
                            result_array.append(result_dict)
                else:
                    _logger.error("%s provider cannot use the voucher %s" % (dependencies_data.provider_id, data['voucher_reference']))
                    return ERR.get_error(additional_message="Provider cannot use voucher %s" % data['voucher_reference'])
        else:
            # # # # # # # # # # # # # # # # # # # #
            #   multi provider                    #
            # # # # # # # # # # # # # # # # # # # #
            #for multi provider then you have to loop and count every price, then count and check.

            #check if voucher covers all provider
            if voucher.voucher_coverage == 'all':

                #check if minimum purchase is meet
                order_purchase = order_obj.total_fare
                if order_purchase < voucher.voucher_minimum_purchase:
                    _logger.error("%s cannot use the voucher, minimum purchase not meet" % data['order_number'])
                    return ERR.get_error(additional_message="Do not meet minimum purchase, cannot use voucher")

                #if voucher affecting all price
                if voucher.voucher_effect_all:
                    for i in dependencies_data:
                        temp_array = []
                        provider_total_price = 0.0
                        provider_total_discount = 0.0
                        for j in i.cost_service_charge_ids:
                            if j.charge_type != 'RAC':
                                # count the discount
                                discount_amount = float(j.total) * voucher.voucher_value / 100.0
                                final_amount = float(j.total) - float(discount_amount)

                                provider_total_price += float(j.total)
                                provider_total_discount += float(discount_amount)

                                result_temp = {
                                    'charge_code': j.charge_code,
                                    'charge_type': j.charge_type,
                                    'start_amount': j.total,
                                    'discount_value': voucher.voucher_value,
                                    'discount_amount': float(discount_amount),
                                    'final_amount': float(final_amount),
                                }
                            else:
                                provider_total_price += float(j.total)

                                result_temp = {
                                    'charge_code': j.charge_code,
                                    'charge_type': j.charge_type,
                                    'start_amount': j.total,
                                    'discount_value': 0,
                                    'discount_amount': 0,
                                    'final_amount': j.total,
                                }
                            temp_array.append(result_temp)

                #if voucher only affecting base fare
                # elif voucher.voucher_effect_base_fare:
                else:
                    for i in dependencies_data:
                        temp_array = []
                        provider_total_price = 0.0
                        provider_total_discount = 0.0

                        for j in i.cost_service_charge_ids:
                            if j.charge_code != 'fare' or j.charge_code == 'FarePrice':
                                # count the discount
                                discount_amount = float(j.total) * voucher.voucher_value / 100.0
                                final_amount = float(j.total) - float(discount_amount)

                                provider_total_price += float(j.total)
                                provider_total_discount += float(discount_amount)

                                result_temp = {
                                    'charge_code': j.charge_code,
                                    'charge_type': j.charge_type,
                                    'start_amount': j.total,
                                    'discount_value': voucher.voucher_value,
                                    'discount_amount': float(discount_amount),
                                    'final_amount': float(final_amount),
                                }
                            else:
                                provider_total_price += float(j.total)

                                result_temp = {
                                    'charge_code': j.charge_code,
                                    'charge_type': j.charge_type,
                                    'start_amount': j.total,
                                    'discount_value': 0,
                                    'discount_amount': 0,
                                    'final_amount': j.total,
                                }
                            temp_array.append(result_temp)
                        # create data to return
                        provider_final_total_price = float(provider_total_price) - float(provider_total_discount)
                        result_dict = {
                            'provider_type_code': i.provider_id.provider_type_id.code,
                            'provider_code': i.provider_id.code,
                            'pnr': i.pnr,
                            'provider_total_price': provider_total_price,
                            'provider_total_discount': provider_total_discount,
                            'provider_final_price': provider_final_total_price,
                            'discount_detail': temp_array
                        }
                        result_array.append(result_dict)
            else:
                ### if voucher is not cover all data
                #for every provider
                eligible_provider = []
                for i in order_provider:
                    temp_filter = dependencies_data.provider_booking_ids.filtered(lambda x: x['provider_id']['code'] == i)

                    #check if provider is allowed to use the voucher
                    temp_dict = {
                        'voucher_reference': data['voucher_reference_code'],
                        'provider_type_id': temp_filter.provider_id.provider_type_id.id,
                        'provider_id': temp_filter.provider_id.id,
                        'provider_name': temp_filter.provider_id.code
                    }
                    provider_is_eligible = self.env['tt.voucher'].is_product_eligible(temp_dict)
                    if provider_is_eligible:
                        eligible_provider.append(i)

                for i in dependencies_data:
                    temp_array = []
                    if i.provider_id.code in eligible_provider:
                        provider_total_price = 0.0
                        provider_total_discount = 0.0
                        ## provider is allowed to use the voucher
                        minimum_checker_provider = 0.0
                        for j in i.cost_service_charge_ids:
                            minimum_checker_provider += float(i.total)
                        if minimum_checker_provider <= voucher.voucher_minimum_purchase:
                            _logger.error("Purchase not meet minimum purchase")

                        for j in i.cost_service_charge_ids:
                            if j.charge_code == 'fare' or j.charge_code == 'FarePrice':
                                # count the discount
                                discount_amount = float(j.total) * voucher.voucher_value / 100.0
                                final_amount = float(j.total) - float(discount_amount)

                                provider_total_price += float(j.total)
                                provider_total_discount += float(discount_amount)

                                result_temp = {
                                    'charge_code': j.charge_code,
                                    'charge_type': j.charge_type,
                                    'start_amount': j.total,
                                    'discount_value': voucher.voucher_value,
                                    'discount_amount': float(discount_amount),
                                    'final_amount': float(final_amount),
                                }
                            else:
                                provider_total_price += float(j.total)

                                result_temp = {
                                    'charge_code': j.charge_code,
                                    'charge_type': j.charge_type,
                                    'start_amount': j.total,
                                    'discount_value': 0,
                                    'discount_amount': 0,
                                    'final_amount': j.total,
                                }
                            temp_array.append(result_temp)
                    else:
                        provider_total_price = 0.0
                        provider_total_discount = 0.0

                        for j in i.cost_service_charge_ids:
                            provider_total_price += float(j.total)

                            result_temp = {
                                'charge_code': j.charge_code,
                                'charge_type': j.charge_type,
                                'start_amount': j.total,
                                'discount_value': 0,
                                'discount_amount': 0,
                                'final_amount': j.total,
                            }
                            temp_array.append(result_temp)

                    # create data to return
                    provider_final_total_price = float(provider_total_price) - float(
                        provider_total_discount)
                    result_dict = {
                        'provider_type_code': i.provider_id.provider_type_id.code,
                        'provider_code': i.provider_id.code,
                        'pnr': i.pnr,
                        'provider_total_price': provider_total_price,
                        'provider_total_discount': provider_total_discount,
                        'provider_final_price': provider_final_total_price,
                        'discount_detail': temp_array
                    }
                    result_array.append(result_dict)

        return ERR.get_no_error(result_array)


    #done
    def simulate_voucher_api(self, data, context):
        # requirement of data
        # data = {
        #     voucher_reference
        #     date          <-- date vouchernya digunakan (today)
        #     provider_type
        #     provider          --> list
        # }

        result_array = []

        #seperate voucher reference code
        splits = data['voucher_reference'].split(".")
        data['voucher_reference_code'] = splits[0]
        try:
            data['voucher_reference_period'] = splits[1]
        except:
            return ERR.get_error(additional_message="Voucher must have period reference")

        #check if voucher exist
        voucher = self.env['tt.voucher'].search([('voucher_reference_code', '=', data['voucher_reference_code'])])
        if voucher.id == False:
            _logger.error('%s Voucher is not exist' % data['voucher_reference'])
            return ERR.get_error(additional_message="Voucher is NOT exist")

        voucher_detail = voucher.voucher_detail_ids.filtered(lambda x: x['voucher_period_reference'] == data['voucher_reference_period'])
        if voucher_detail.id == False:
            _logger.error('%s Voucher is not exist' % data['voucher_reference'])
            return ERR.get_error(additional_message="Voucher is NOT exist")

        #if voucher already expired
        if voucher_detail.voucher_detail_state == 'expire':
            _logger.error('%s Voucher can no longer be use (Expired)'% data['voucher_reference'])
            return ERR.get_error(additional_message="Voucher is already Expired")

        if voucher_detail.voucher_start_date.strftime("%Y-%m-%d") > data['date'] and voucher_detail.voucher_expire_date < data['date']:
            _logger.error("%s Voucher cannot be use outside designated date" % data['voucher_reference'])
            return ERR.get_error(additional_message="Voucher cannot be use outside designated date")

        #check if there are voucher left to be use
        if voucher_detail.voucher_used >= voucher_detail.voucher_quota:
            _logger.error("%s Voucher is used up (Sold out)" % data['voucher_reference'])
            return ERR.get_error(additional_message="Voucher sold out")

        #check agent
        agent_to_validate = {
            'voucher_reference': data['voucher_reference_code'],
            'agent_type_id': context['co_agent_type_id'],
            'agent_id': context['co_agent_id']
        }
        agent_eligible = self.env['tt.voucher'].is_agent_eligible(agent_to_validate)
        if not agent_eligible:
            _logger.error("Agent ID %s cannot use the %s voucher "% (context['co_agent_id'], data['voucher_reference']))
            return ERR.get_error(additional_message="Agent cannot use the voucher")

        #if voucher coverage == all
        if voucher.voucher_coverage == 'all':
            # check if voucher can be use to selected provider type
            provider_type = self.env['tt.provider.type'].search([('code', '=', data['provider_type'])])

            if type(data['provider']) is list:
                #for every data in list
                for i in data['provider']:

                    #check if given provider is actually part of povider_type
                    provider = self.env['tt.provider'].search([('code', '=', i)])
                    if provider.provider_type_id.id == provider_type.id:
                        to_return = {
                            'provider_type': data['provider_type'],
                            'provider': i,
                            'able_to_use': True
                        }
                    else:
                        to_return = {
                            'provider_type': data['provider_type'],
                            'provider': i,
                            'able_to_use': False
                        }
                    result_array.append(to_return)
            else:
                provider = self.env['tt.provider'].search([('code', '=', data['provider'])])
                if provider.provider_type_id.id == provider_type.id:
                    to_return = {
                        'provider_type': data['provider_type'],
                        'provider': data['provider'],
                        'able_to_use': True
                    }
                else:
                    to_return = {
                        'provider_type': data['provider_type'],
                        'provider': data['provider'],
                        'able_to_use': False
                    }
                result_array.append(to_return)
        else:
            #check if voucher can be use to selected provider type
            provider_type = voucher.voucher_provider_type_eligibility_ids.filtered(lambda x: x['code'] == data['provider_type'])

            if provider_type.id != False:
                if type(data['provider']) is list:
                    for i in data['provider']:
                        # check if given provider is actually part of povider_type
                        provider = self.env['tt.provider'].search([('code', '=', i)])
                        if provider.provider_type_id.id == provider_type.id:
                            to_return = {
                                'provider_type': data['provider_type'],
                                'provider': i,
                                'able_to_use': True
                            }
                        else:
                            to_return = {
                                'provider_type': data['provider_type'],
                                'provider': i,
                                'able_to_use': False
                            }
                        result_array.append(to_return)
                else:
                    provider = voucher.voucher_provider_eligibility_ids.filtered(lambda x: x['code'] == data['provider'])
                    if provider.id != False:
                        if provider.provider_type_id.id == provider_type.id:
                            to_return = {
                                'provider_type': data['provider_type'],
                                'provider': data['provider'],
                                'able_to_use': True
                            }
                        else:
                            to_return = {
                                'provider_type': data['provider_type'],
                                'provider': data['provider'],
                                'able_to_use': False
                            }
                    else:
                        to_return = {
                            'provider_type': data['provider_type'],
                            'provider': data['provider'],
                            'able_to_use': False
                        }
                    result_array.append(to_return)
            else:
                return ERR.get_error(additional_message="Voucher cannot be use on type %s" % data['provider_type'])

        #built to return

        #maximum_cap
        if voucher.voucher_maximum_cap < 1:
            maximum_cap = False
        else:
            maximum_cap = voucher.voucher_maximum_cap

        #minimum purchase
        if voucher.voucher_minimum_purchase < 1:
            minimum_purchase = False
        else:
            minimum_purchase = voucher.voucher_minimum_purchase

        result = {
            'reference_code': data['voucher_reference'],
            'voucher_type': voucher.voucher_type,
            'voucher_value': voucher.voucher_value,
            'voucher_currency': voucher.currency_id.name,
            'voucher_cap': maximum_cap,
            'voucher_minimum_purchase': minimum_purchase,
            'date_expire': voucher_detail.voucher_expire_date.strftime("%Y-%m-%d"),
            'provider_type': data['provider_type'],
            'provider': result_array
        }

        return ERR.get_no_error(result)

    def create_voucher_detail(self, data):
        self.env['tt.voucher.detail'].create({
            'voucher_id': data['voucher_id'],
            'voucher_period_reference': data['voucher_period_reference'],
            'voucher_start_date': data['start_date'],
            'voucher_expire_date': data['end_date'],
            'voucher_used': 0,
            'voucher_quota': int(data['voucher_quota']),
            'voucher_detail_state': 'not-activate'
        })

    #need revision
    def voucher_validator(self, data):
        # requirement of data
        # data = {
        #     voucher reference
        #     date to be issued
        #     provider_type
        #     provider
        #     agent_type_id
        #     agent_id
        # }

        #corresponding voucher is within date
        corresponding_voucher = self.env['tt.voucher.detail'].search([('voucher_reference_code', '=', data['voucher_reference'])])
        if corresponding_voucher.id == False:
            _logger.error('Voucher is not exist')
            return ERR.get_error(additional_message="voucher is not exist")

        if corresponding_voucher.voucher_detail_state == 'expire':
            _logger.error('Voucher is no longer works (expired)')
            return ERR.get_error(additional_message="voucher is already expired")

        if data['date'] <= corresponding_voucher.voucher_start_date.strftime("%Y-%m-%d") or data['date'] > corresponding_voucher.voucher_expire_date.strftime("%Y-%m-%d"):
            _logger.error('Voucher is unusable outside designated date')
            return ERR.get_error(additional_message="Voucher is unusable outside designated date")

        # check if voucher is able to be use by agent
        is_agent_eligible = self.env['tt.voucher'].is_agent_eligible(data)
        if not is_agent_eligible:
            _logger.error('Agent is not eligible to use this voucher')
            return ERR.get_error(additional_message="Agent is not eligible to use this voucher")

        # check if voucher is eligible for specified product/product type
        is_product_eligible = self.env['tt.voucher'].is_product_eligible(data)
        if not is_product_eligible:
            _logger.error('Voucher is not eligible for selected type/product(s)')
            return ERR.get_error(additional_message="Voucher is not eligible for selected")

        # check if voucher is eligible for required date(s)
        is_blackout = self.env['tt.voucher.detail.blackout'].is_blackout(data)
        if not is_blackout:
            _logger.error('Voucher is not applicable for selected date')
            return ERR.get_error(additional_message='Selected date are not covered by the voucher')

        return {
            'error_code': 0,
            'error_msg': "voucher is eligible to be use",
            'response': ''
        }

    def use_voucher_new(self, data, context):
        if data == None:
            return ERR.get_error()
        # data = {
        #   voucher_reference
        #   order_code
        #   date
        #   provider_type
        # }

        simulate = self.simulate_voucher(data, context)
        if simulate['error_code'] == 0:
            splits = data['voucher_reference'].split(".")
            data['voucher_reference_code'] = splits[0]
            data['voucher_reference_period'] = splits[1]

            voucher_detail = self.env['tt.voucher.detail'].search([('voucher_reference_code', '=', data['voucher_reference_code']), ('voucher_period_reference', '=', data['voucher_reference_period'])])
            provider_type = self.env['tt.provider.type'].search([('code', '=', simulate['response'][0]['provider_type_code'])])
            provider = self.env['tt.provider'].search([('code', '=', simulate['response'][0]['provider_code'])])

            use_voucher_data = {
                'voucher_detail_id': voucher_detail.id,
                'voucher_date_use': data['date'],
                'voucher_agent_type': context['co_agent_type_id'],
                'voucher_agent': context['co_agent_id'],
                'voucher_provider_type': provider_type.id,
                'voucher_provider': provider.id,
            }
            res = self.env['tt.voucher.detail.used'].add_voucher_used_detail(use_voucher_data)
            if res.id == False:
                return ERR.get_error(additional_message="voucher failed to be use")
            else:
                number_of_use = voucher_detail.voucher_used + 1
                voucher_detail.write({
                    'voucher_used': number_of_use
                })
        else:
            return simulate
        return simulate

    ### bellow dis is old function ###
    def use_voucher(self, data, context):
        # requirement of data
        # data = {
        #     voucher_reference
        #     voucher_date
        #     provider_type
        #     provider
        #     purchase_amount
        # }

        # split reference code
        splits = data['voucher_reference'].split(".")
        data['voucher_reference'] = splits[0]
        try:
            data['voucher_reference_period'] = splits[1]
        except:
            return ERR.get_error(7000, "Voucher not valid")
        data['agent_type_id'] = context['co_agent_type_id']

        #search the voucher
        voucher_date_detail = self.env['tt.voucher.detail'].search([('voucher_reference_code', '=', splits[0]), ('voucher_period_reference', '=', splits[1])])
        if voucher_date_detail == False:
            _logger.error('Voucher is not exist')
            return ERR.get_error("Voucher is not exist.")

        #check if voucher quota is still available
        if voucher_date_detail.voucher_used >= voucher_date_detail.voucher_quota:
            _logger.error('Voucher sold out')
            return ERR.get_error("Voucher sold out")

        data['voucher_detail_id'] = voucher_date_detail['id']

        # get provider id
        provider_type = self.env['tt.provider.type'].search([('code', '=', data['provider_type'])])
        provider = self.env['tt.provider'].search([('code', '=', data['provider'])])

        if provider_type.id:
            data['provider_type_id'] = provider_type.id
        else:
            return ERR.get_error(7020, "provider type not exist or there's a typo")

        if provider.id:
            data['provider_id'] = provider.id
        else:
            return ERR.get_error(7021, "provider not exist or there's a typo")

        #check if voucher is eligible to use
        able_to_use = self.voucher_validator(data)

        if able_to_use['error_code'] == 0:
            # check if the purchase data is passed to this function
            try:
                voucher = self.env['tt.voucher'].search([('voucher_reference_code', '=', data['voucher_reference'])])
                if voucher[0]['voucher_type'] == 'percent':
                    discount_amount = (voucher[0]['voucher_value'] / 100.0) * float(data['purchase_amount'])
                    total = float(data['purchase_amount']) - discount_amount
                else:
                    discount_amount = 0
                    total = data['purchase_amount']
                voucher_data = {
                    'start_amount': data['purchase_amount'],
                    'voucher_value': voucher[0]['voucher_value'],
                    'discount': discount_amount,
                    'final_amount': total
                }
            except:
                _logger.error("Purchase data must be included")
                return ERR.get_error(7000, "Purchase must be included")

            voucher = self.env['tt.voucher.detail'].browse(int(data['voucher_detail_id']))
            # log use voucher data
            used = {
                'voucher_detail_id': voucher.id,
                'voucher_date_use': datetime.today(),
                'voucher_agent_type': context['co_agent_type_id'],
                'voucher_agent': context['co_agent_id'],
                'voucher_provider_type': data['provider_type_id'],
                'voucher_provider': data['provider_id']
            }
            voucher_detail = self.env['tt.voucher.detail.used'].add_voucher_used_detail(used)

            number_of_use = voucher.voucher_used + 1
            voucher.write({
                'voucher_used': number_of_use
            })

        else:
            return able_to_use
        return ERR.get_no_error(voucher_data)
    ### above dis is old function ###

class TtVoucherusedDetail(models.Model):
    _name = "tt.voucher.detail.used"
    _description = "Rodex Model Voucher Detail Used"

    voucher_detail_id = fields.Many2one("tt.voucher.detail")
    voucher_date_use = fields.Datetime("Date use")
    voucher_agent_type_id = fields.Many2one("tt.agent_type", "Agent Type")
    voucher_agent_id = fields.Many2one("tt.agent", "Agent ID")
    voucher_provider_type_id = fields.Many2one("tt.provider.type", "Provider Type")
    voucher_provider_id = fields.Many2one("tt.provider", "Provider ID")

    def add_voucher_used_detail(self, data):
        result = self.env['tt.voucher.detail.used'].create({
            'voucher_detail_id': int(data['voucher_detail_id']),
            'voucher_date_use': data['voucher_date_use'],
            'voucher_agent_type_id': int(data['voucher_agent_type']),
            'voucher_agent_id': int(data['voucher_agent']),
            'voucher_provider_type_id': int(data['voucher_provider_type']),
            'voucher_provider_id': int(data['voucher_provider'])
        })

        return result

class TtVoucherBlackout(models.Model):
    _name = "tt.voucher.detail.blackout"
    _description = "Rodex Model Voucher Detail Blackout"

    voucher_detail_id = fields.Many2one("tt.voucher.detail", "Voucher Detail")
    voucher_blackout_start = fields.Datetime("Blackout Start")
    voucher_blackout_end = fields.Datetime("Blackout End")
    voucher_blackout_remark = fields.Char("Blackout Remark")

    def create_blackout(self, data):
        self.env['tt.voucher.detail.blackout'].create({
            'voucher_detail_id': data['voucher_detail_id'],
            'voucher_blackout_start': data['voucher_blackout_start'],
            'voucher_blackout_end': data['voucher_blackout_end'],
            'voucher_blackout_remark': data['voucher_blackout_remark']
        })

    def is_blackout(self, data):
        is_eligible = True
        blackouts = self.env['tt.voucher.detail.blackout'].search([('voucher_detail_id', '=', data['voucher_detail_id'])])
        for i in blackouts:
            if data['date'] >= i.voucher_blackout_start or data['date'] <= i.voucher_blackout_end:
                is_eligible = False

        return is_eligible