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

    voucher_reference_code = fields.Char("Reference Code")
    voucher_coverage = fields.Selection([("all", "All"), ("product", "Specified Product"), ("provider", "Specified Provider")])
    voucher_type = fields.Selection([("percent", "Percentage"), ("discount", "Discount")])
    currency_id = fields.Many2one("res.currency")
    voucher_value = fields.Float("Voucher value")
    voucher_maximum_cap = fields.Float("Voucher Cap")
    voucher_minimum_purchase = fields.Float('Voucher Minimum Purchase')
    voucher_detail_ids = fields.One2many("tt.voucher.detail", "voucher_id", "Voucher Detail")
    voucher_author_id = fields.Many2one('res.users', 'author')   # voucher maker
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
        #     reference_code        = '-1'
        #     start_date            = '-1'
        #     end_date              = '-1'
        #     provider_type_id      = -1
        #     provider_id           = -1
        # }
        #   -1 = all
        error_list = ""

        searched_filter = []
        try:
            if data['provider_type_id'] != -1:
                searched_filter.append('|')
                searched_filter.append(('voucher_coverage', '=', 'all'))
                searched_filter.append(('voucher_provider_type_eligibility_ids', '=', data['provider_type_id']))
        except:
            error_list += "Must include provider type id \n"

        try:
            if data['provider_id'] != -1:
                if data['provider_type_id'] != -1:
                    searched_filter.append('|')
                    searched_filter.append(('voucher_coverage', '=', 'all'))
                searched_filter.append(('voucher_provider_eligibility_ids', '=', data['provider_id']))
        except:
            error_list += "Must include provider id \n"

        try:
            if data['reference_code'] != '-1':
                splits = data['voucher_reference'].split(".")
                data['voucher_reference'] = splits[0]
                searched_filter.append(('voucher_reference_code', '=', data['voucher_reference']))
                try:
                    data['voucher_reference_period'] = splits[1]
                    searched_filter.append(('voucher_detail_ids.voucher_reference_period', '=', data['voucher_reference_period']))
                except:
                    pass
        except:
            error_list += "Must include reference code \n"

        try:
            searched_filter.append(('voucher_agent_type_eligibility_ids', '=', context['co_agent_type_id']))
            searched_filter.append(('voucher_agent_eligibility_ids', '=', context['co_agent_id']))
        except:
            _logger.error('search voucher without context')
            pass

        try:
            if data['start_date'] != '-1':
                searched_filter.append(('voucher_detail_ids.voucher_start_date', '<=', data['start_date']))
        except:
            error_list += "Must include start_date \n"

        try:
            if data['end_date'] != '-1':
                searched_filter.append(('voucher_detail_ids.voucher_expire_date', '>=', data['end_date']))
        except:
            error_list += "Must include voucher end date"

        if error_list == "":
            voucher = self.env['tt.voucher'].search(searched_filter).read()
            result = []
            for i in voucher:
                i.update({
                    'voucher_detail_ids': self.env['tt.voucher.detail'].search([('voucher_id', '=', i['id'])]).read()
                })

                if i['voucher_maximum_cap'] < 1:
                    i['voucher_maximum_cap'] = False

                if i['voucher_coverage'] == 'all':
                    description = i['voucher_coverage']
                else:
                    temp_list = []
                    for j in i['voucher_provider_type_eligibility_ids']:
                        provider_type = self.env['tt.provider.type'].browse(int(j))
                        temp_list.append(provider_type.name)
                    description = (",").join(temp_list)

                for j in i['voucher_detail_ids']:
                    voucher_data = {
                        'reference_code': "%s.%s" % (i['voucher_reference_code'], j['voucher_period_reference']),
                        'voucher_type': i['voucher_type'],
                        'voucher_coverage': description,
                        'voucher_value': i['voucher_value'],
                        'maximum_cap': i['voucher_maximum_cap'],
                        'voucher_end_date': j['voucher_expire_date'].strftime("%Y-%m-%d"),
                        'left': int(j['voucher_quota'] - j['voucher_used'])
                    }
                    result.append(voucher_data)
        else:
            _logger.error(error_list)
            return ERR.get_error(error_list)

        return ERR.get_no_error(result)

    def is_product_eligible(self, data):
        voucher = self.env['tt.voucher'].search([('voucher_reference_code', "=", data['voucher_reference'])])
        is_eligible = False
        if voucher.voucher_coverage == 'all':
            is_eligible = True
        else:
            for i in voucher.voucher_provider_type_eligibility_ids:
                if data['provider_type_id'] == i.id:
                    is_eligible = True

        return is_eligible

    def is_agent_eligible(self, data):
        voucher = self.env['tt.voucher'].search([('voucher_reference_code', "=", data['voucher_reference'])])
        is_eligible = False
        for i in voucher.voucher_agent_type_eligibility_ids:
            if data['agent_type_id'] == i.id:
                is_eligible = True

        return is_eligible

    def is_purchase_allowed(self, data):
        voucher = self.env['tt.voucher'].search([('voucher_reference_code', '=', data['voucher_reference'])])
        is_eligible = False
        if data['purchase'] >= voucher.voucher_minimum_purchase:
            is_eligible = True

        return is_eligible

    @api.onchange('voucher_agent_type_eligibility_ids')
    def _onchange_action(self):
        domain = {'voucher_agent_eligibility_ids': []}
        if self.voucher_agent_type_eligibility_ids != False:
            self.voucher_agent_eligibility_ids = False
            domain = {
                'voucher_agent_eligibility_ids': [('agent_type_id', 'in', self.voucher_agent_type_eligibility_ids.ids)]
            }
        return {'domain': domain}

    @api.onchange('voucher_provider_type_eligibility_ids')
    def _onchange_action(self):
        domain = {'voucher_provider_eligibility_ids': []}
        if self.voucher_provider_type_eligibility_ids != False:
            self.voucher_provider_eligibility_ids = False
            domain = {
                'voucher_provider_eligibility_ids': [('provider_type_id', 'in', self.voucher_provider_type_eligibility_ids.ids)]
            }
        return {'domain': domain}

class TtVoucherDetail(models.Model):
    _name = "tt.voucher.detail"

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

    def activate_voucher(self):
        voucher = self.env['tt.voucher.detail'].search([('voucher_detail_state', '=', 'not-active')])
        for i in voucher:
            if i.voucher_start_date.strftime("%Y-%m-%d") <= datetime.today().strftime("%Y-%m-%d"):
                i.write({
                    'voucher_detail_state': 'active'
                })
        return 0

    def expire_voucher(self):
        voucher = self.env['tt.voucher.detail'].search([('voucher_detail_state', '=', 'active')])
        for i in voucher:
            if i.voucher_expire_date.strftime("%Y-%m-%d") < datetime.today().strftime("%Y-%m-%d"):
                i.write({
                    'voucher_detail_state': 'expire'
                })

        return 0

    def get_voucher_detail(self, voucher_id):
        voucher = self.env['tt.voucher.detail'].browse(int(voucher_id)).read()
        voucher[0]['voucher_number'] = "%s.%s" % (voucher[0]['voucher_reference_code'], voucher[0]['voucher_period_reference'])
        return voucher

    def simulate_voucher(self, data, context):
        # requirement of data
        # data = {
        #     voucher_reference
        #     date          <-- date vouchernya digunakan (today)
        #     provider_type_id
        #     provider_id
        #     purchase_amount
        # }
        splits = data['voucher_reference'].split(".")
        data['voucher_reference'] = splits[0]
        try:
            data['voucher_reference_period'] = splits[1]
        except:
            return ERR.get_error(7000, "Voucher must have period reference")
        data['agent_type_id'] = context['co_agent_type_id']

        voucher_detail = self.env['tt.voucher.detail'].search([('voucher_reference_code', '=', data['voucher_reference']),('voucher_period_reference', '=', data['voucher_reference_period'])])
        if voucher_detail == False:
            _logger.error('Voucher is not exist')
            return ERR.get_error(7000, "Voucher is not Exist")

        if voucher_detail.voucher_used >= voucher_detail.voucher_quota:
            _logger.error('Voucher sold out')
            return ERR.get_error(400, "Voucher sold out")

        data['voucher_detail_id'] = voucher_detail['id']

        able_to_use = self.voucher_validator(data)
        if able_to_use['error_code'] == 0:
            voucher = self.env['tt.voucher'].search([('voucher_reference_code', '=', data['voucher_reference'])])
            # if voucher[0]['voucher_type'] == 'discount':
            #     discount_amount = (voucher[0]['voucher_value'] / 100.0) * float(data['purchaase_amount'])
            #     total = float(data['purchase_amount']) - discount_amount
            # else:
            #     discount_amount = 0
            #     total = data['purchase_amount']
            if voucher[0]['voucher_maximum_cap'] < 1:
                voucher[0]['voucher_maximum_cap'] = False
            voucher_data = {
                # 'start_amount': data['purchase_amount'],
                'voucher_type': voucher[0]['voucher_type'],
                'voucher_currency': voucher[0]['currency_id'],
                'voucher_value': voucher[0]['voucher_value'],
                'voucher_cap': voucher[0]['voucher_maximum_cap'],
                'voucher_minimum_purchase': voucher[0]['voucher_minimum_purchase'],
                # 'discount': discount_amount,
                # 'final_amount': total
            }
            # voucher_data = {
            #     'error_code': 0,
            #     'error_m'
            # }
        else :
            return able_to_use

        return ERR.get_no_error(voucher_data)

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

    def voucher_validator(self, data):
        # requirement of data
        # data = {
        #     voucher reference
        #     date to be issued
        #     provider_type
        #     provider_id
        #     agent_type
        #     agent_id
        # }

        #corresponding voucher is within date
        corresponding_voucher = self.env['tt.voucher.detail'].search([('voucher_reference_code', '=', data['voucher_reference'])])
        if corresponding_voucher.id == False:
            _logger.error('Voucher is not exist')
            return ERR.get_error(7000, "voucher is not exist")

        if corresponding_voucher.voucher_detail_state == 'expire':
            _logger.error('Voucher is no longer works (expired)')
            return ERR.get_error(7001, "voucher is already expired")

        if data['date'] <= corresponding_voucher.voucher_start_date.strftime("%Y-%m-%d") or data['date'] > corresponding_voucher.voucher_expire_date.strftime("%Y-%m-%d"):
            _logger.error('Voucher is unusable outside designated date')
            return ERR.get_error(7002, "Voucher is unusable outside designated date")

        # check if voucher is able to be use by agent
        is_agent_eligible = self.env['tt.voucher'].is_agent_eligible(data)
        if not is_agent_eligible:
            _logger.error('Agent is not eligible to use this voucher')
            return ERR.get_error(7003, "Agent is not eligible to use this voucher")

        # check if voucher is eligible for specified product/product type
        is_product_eligible = self.env['tt.voucher'].is_product_eligible(data)
        if not is_product_eligible:
            _logger.error('Voucher is not eligible for selected type/product(s)')
            return ERR.get_error(7004, "Voucher is not eligible for selected")

        # check if voucher is eligible for required date(s)
        is_blackout = self.env['tt.voucher.detail.blackout'].is_blackout(data)
        if not is_blackout:
            _logger.error('Voucher is not applicable for selected date')
            return ERR.get_error(7005, 'Selected date are not covered by the voucher', "Blackout Dates")

        return {
            'error_code': 0,
            'error_msg': "voucher is eligible to be use",
            'response': ''
        }

    def use_voucher(self, data, context):
        # requirement of data
        # data = {
        #     voucher_reference
        #     voucher_date
        #     provider_type_id
        #     provider_id
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
            raise Exception ("Voucher is not exist.")

        #check if voucher quota is still available
        if voucher_date_detail.voucher_used >= voucher_date_detail.voucher_quota:
            _logger.error('Voucher sold out')
            raise Exception ("Voucher sold out")

        data['voucher_detail_id'] = voucher_date_detail['id']

        #check if voucher is eligible to use
        able_to_use = self.voucher_validator(data)

        if able_to_use['error_code'] == 0:
            # check if the purchase data is passed to this function
            try:
                voucher = self.env['tt.voucher'].search([('voucher_reference_code', '=', data['voucher_reference'])])
                if voucher[0]['voucher_type'] == 'discount':
                    discount_amount = (voucher[0]['voucher_value'] / 100.0) * float(data['purchaase_amount'])
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
        return voucher_data

class TtVoucherusedDetail(models.Model):
    _name = "tt.voucher.detail.used"

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

        print(result)

        return 0

class TtVoucherBlackout(models.Model):
    _name = "tt.voucher.detail.blackout"

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