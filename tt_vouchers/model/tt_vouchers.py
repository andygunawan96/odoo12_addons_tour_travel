from odoo import api, models, fields
from odoo.exceptions import UserError

from ...tools import variables
from datetime import datetime, date, timedelta
import base64
import logging,traceback
import json
from ...tools.ERR import RequestException
from ...tools import ERR

_logger = logging.getLogger(__name__)


class TtVoucher(models.Model):
    _name = "tt.voucher"
    _inherit = 'tt.history'
    _description = 'Voucher Model'
    _rec_name = 'voucher_reference_code'

    name = fields.Char("Voucher Name", required=True, default='Voucher', readonly=True, states={'draft': [('readonly', False)]})
    voucher_reference_code = fields.Char("Reference Code", required=True, readonly=True, states={'draft': [('readonly', False)]})
    voucher_coverage = fields.Selection([("all", "All"), ("product", "Specified Product"), ("provider", "Specified Provider")], default='all', readonly=True, states={'draft': [('readonly', False)]})
    voucher_type = fields.Selection([("percent", "Percentage"), ("amount", "Some Amount")], default='amount', readonly=True, states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one("res.currency", required=True, readonly=True, states={'draft': [('readonly', False)]})
    voucher_value = fields.Monetary("Voucher value", default=0, readonly=True, states={'draft': [('readonly', False)]})
    voucher_maximum_cap = fields.Float("Voucher Cap", readonly=True, states={'draft': [('readonly', False)]})
    voucher_minimum_purchase = fields.Float('Voucher Minimum Purchase', default=0, readonly=True, states={'draft': [('readonly', False)]})
    voucher_detail_ids = fields.One2many("tt.voucher.detail", "voucher_id", "Voucher Detail", readonly=True, states={'draft': [('readonly', False)]})
    voucher_author_id = fields.Many2one('res.users', 'author')   # voucher maker

    voucher_effect_all = fields.Boolean("Total", default=True, readonly=True, states={'draft': [('readonly', False)]})
    voucher_effect_base_fare = fields.Boolean("Base Fare", readonly=True, states={'draft': [('readonly', False)]})

    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'), ('not-active', 'Not Active'), ('done', 'Done')], default="draft")
    agent_type_access_type = fields.Selection([("all", "ALL"), ("allow", "Allowed"), ("restrict", "Restricted")], 'Agent Type Access Type', default='all', readonly=True, states={'draft': [('readonly', False)]})
    voucher_agent_type_eligibility_ids = fields.Many2many("tt.agent.type", "tt_agent_type_tt_voucher_rel", "tt_voucher_id", "tt_agent_type_id", "Agent Type", readonly=True, states={'draft': [('readonly', False)]})      #type of user that are able to use the voucher
    agent_access_type = fields.Selection([("all", "ALL"), ("allow", "Allowed"), ("restrict", "Restricted")], 'Agent Access Type', default='all', readonly=True, states={'draft': [('readonly', False)]})
    voucher_agent_eligibility_ids = fields.Many2many('tt.agent', "tt_agent_tt_voucher_rel", "tt_voucher_id", "tt_agent_id", "Agent ID", readonly=True, states={'draft': [('readonly', False)]})                                        # who can use the voucher
    provider_type_access_type = fields.Selection([("all", "ALL"), ("allow", "Allowed"), ("restrict", "Restricted")], 'Provider Type Access Type', default='all', readonly=True, states={'draft': [('readonly', False)]})
    voucher_provider_type_eligibility_ids = fields.Many2many("tt.provider.type", "tt_provider_type_tt_voucher_rel", "tt_voucher_id", "tt_provider_type_id", "Provider Type", readonly=True, states={'draft': [('readonly', False)]})                         # what product this voucher can be applied
    provider_access_type = fields.Selection([("all", "ALL"), ("allow", "Allowed"), ("restrict", "Restricted")], 'Provider Access Type', default='all', readonly=True, states={'draft': [('readonly', False)]})
    voucher_provider_eligibility_ids = fields.Many2many('tt.provider', "tt_provider_tt_voucher_rel", "tt_voucher_id", "tt_provier_id", "Provider ID", readonly=True, states={'draft': [('readonly', False)]})                                  # what provider this voucher can be applied

    #add-ons
    voucher_multi_usage = fields.Boolean("Voucher Multi Usage", readonly=True, states={'draft': [('readonly', False)]})
    voucher_usage_value = fields.Monetary("Voucher usage", readonly=True)
    voucher_customer_id = fields.Many2one('tt.customer', 'Customer', domain=[], readonly=True, states={'draft': [('readonly', False)]})
    is_customer_exclusive = fields.Boolean('Is Customer Exclusive', readonly=True, states={'draft': [('readonly', False)]})
    terms_conditions = fields.Html('Terms and Conditions', readonly=True, states={'draft': [('readonly', False)]})
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)])

    @api.onchange('agent_access_type', 'voucher_agent_eligibility_ids')
    def agent_eligibility_change(self):
        if self.agent_access_type == 'allow':
            domain = [('agent_id', 'in', self.voucher_agent_eligibility_ids.ids)]
        elif self.agent_access_type == 'restrict':
            domain = [('agent_id', 'not in', self.voucher_agent_eligibility_ids.ids)]
        else:
            domain = []
        return {'domain': {
            'voucher_customer_id': domain
        }}

    @api.model
    def create(self, vals):
        if type(vals.get('voucher_reference_code')) == str:
            vals['voucher_reference_code'] = vals['voucher_reference_code'].upper()
        res = super(TtVoucher, self).create(vals)
        return res

    # function for cron
    def expire_voucher(self):
        voucher = self.env['tt.voucher'].search([('state', '=', 'confirm')])
        for voucher_obj in voucher:
            expired = True
            for voucher_detail_obj in voucher_obj.voucher_detail_ids:
                if voucher_detail_obj.voucher_expire_date.strftime("%Y-%m-%d") < datetime.today().strftime("%Y-%m-%d"):
                    voucher_detail_obj.write({
                        'state': 'expire'
                    })
                if voucher_detail_obj.state != 'active':
                    expired = False
            if expired:
                voucher_obj.state = 'done'

        return 0

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
            'voucher_product_eligibility_ids': data['voucher_product_eligibility'],
            'voucher_multi_use': data['voucher_multi_use'],
            'voucher_customer_id': data['customer_id']
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

    # is product eligible responsible to check if the voucher allowed to effect product given
    # andy yang nge code
    def is_product_eligible(self, data):
        # search voucher by id
        voucher = self.env['tt.voucher'].search([('id', "=", data['voucher_id'])])

        # set default to false, since if everything goes wrong, then the voucher will not be use
        is_provider_type_eligible = False

        # check if voucher covers all product type then
        if voucher.provider_type_access_type == 'all':
            # set to true
            is_provider_type_eligible = True
        elif voucher.provider_type_access_type == 'allow':
            if int(data['provider_type_id']) in voucher.voucher_provider_type_eligibility_ids.ids:
                is_provider_type_eligible = True
        else:
            if int(data['provider_type_id']) not in voucher.voucher_provider_type_eligibility_ids.ids:
                is_provider_type_eligible = True

        is_provider_eligible = False
        if voucher.provider_access_type == 'all':
            is_provider_eligible = True
        elif voucher.provider_access_type == 'allow':
            if int(data['provider_id']) in voucher.voucher_provider_eligibility_ids.ids:
                is_provider_eligible = True
        else:
            if int(data['provider_id']) not in voucher.voucher_provider_eligibility_ids.ids:
                is_provider_eligible = True

        return is_provider_type_eligible and is_provider_eligible

    def add_usage_value(self, usage):
        self.voucher_usage_value += usage
        return True

    #update
    # is product eligible responsible to check if the voucher allowed to effect agent given
    # andy yang ngecode
    def is_agent_eligible(self, data):
        #search voucher by id
        voucher = self.env['tt.voucher'].search([('id', "=", data['voucher_id'])])

        is_agent_type_eligible = False
        if voucher.agent_type_access_type == 'all':
            is_agent_type_eligible = True
        elif voucher.agent_type_access_type == 'allow':
            if int(data['agent_type_id']) in voucher.voucher_agent_type_eligibility_ids.ids:
                is_agent_type_eligible = True
        else:
            if int(data['agent_type_id']) not in voucher.voucher_agent_type_eligibility_ids.ids:
                is_agent_type_eligible = True

        is_agent_eligible = False
        if voucher.agent_access_type == 'all':
            is_agent_eligible = True
        elif voucher.agent_access_type == 'allow':
            if int(data['agent_id']) in voucher.voucher_agent_eligibility_ids.ids:
                is_agent_eligible = True
        else:
            if int(data['agent_id']) not in voucher.voucher_agent_eligibility_ids.ids:
                is_agent_eligible = True

        return is_agent_type_eligible and is_agent_eligible

    def is_purchase_allowed(self, data):
        voucher = self.env['tt.voucher'].search([('voucher_reference_code', '=', data['voucher_reference'])])
        is_eligible = False
        if data['purchase'] >= voucher.voucher_minimum_purchase:
            is_eligible = True

        return is_eligible

    @api.onchange('agent_type_access_type', 'voucher_agent_type_eligibility_ids')
    def _onchange_action_agent_type(self):
        if self.agent_type_access_type == 'all':
            domain = {
                'voucher_agent_eligibility_ids': [('id', '!=', False)]
            }
        elif self.agent_type_access_type == 'allow':
            self.voucher_agent_eligibility_ids = False
            domain = {
                'voucher_agent_eligibility_ids': [('agent_type_id', 'in', self.voucher_agent_type_eligibility_ids.ids)]
            }
        else:
            self.voucher_agent_eligibility_ids = False
            domain = {
                'voucher_agent_eligibility_ids': [('agent_type_id', 'not in', self.voucher_agent_type_eligibility_ids.ids)]
            }
        return {'domain': domain}

    @api.onchange('provider_type_access_type', 'voucher_provider_type_eligibility_ids')
    def _onchange_action_provider_type(self):
        if self.provider_type_access_type == 'all':
            domain = {
                'voucher_provider_eligibility_ids': [('id', '!=', False)]
            }
        elif self.provider_type_access_type == 'allow':
            self.voucher_provider_eligibility_ids = False
            domain = {
                'voucher_provider_eligibility_ids': [('provider_type_id', 'in', self.voucher_provider_type_eligibility_ids.ids)]
            }
        else:
            self.voucher_provider_eligibility_ids = False
            domain = {
                'voucher_provider_eligibility_ids': [('provider_type_id', 'not in', self.voucher_provider_type_eligibility_ids.ids)]
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

    @api.onchange('agent_access_type', 'voucher_agent_eligibility_ids')
    def _onchange_action_agent(self):
        if self.agent_access_type == 'all':
            domain = {
                'voucher_customer_id': [('id', '!=', False)]
            }
        elif self.agent_access_type == 'allow':
            self.voucher_customer_id = False
            domain = {
                'voucher_customer_id': [('agent_id', 'in', self.voucher_agent_eligibility_ids.ids)]
            }
        else:
            self.voucher_customer_id = False
            domain = {
                'voucher_customer_id': [('agent_id', 'not in', self.voucher_agent_eligibility_ids.ids)]
            }
        return {'domain': domain}

    def action_set_to_draft(self):
        if not self.env.user.has_group('tt_base.group_voucher_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 352')
        self.write({
            'state': 'draft'
        })

    def action_set_to_confirm(self):
        if not self.env.user.has_group('tt_base.group_voucher_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 353')
        self.write({
            'state': 'confirm'
        })

    def set_to_not_active(self):
        if not self.env.user.has_group('tt_base.group_voucher_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 354')
        self.write({
            'state': 'not-active'
        })


class TtVoucherDetail(models.Model):
    _name = "tt.voucher.detail"
    _inherit = 'tt.history'
    _description = 'Voucher Detail'
    _rec_name = 'display_name'

    voucher_id = fields.Many2one("tt.voucher")
    voucher_reference_code = fields.Char("Voucher Reference", related="voucher_id.voucher_reference_code", readonly=True)
    voucher_period_reference = fields.Char("Voucher Period Reference", required=True)
    voucher_start_date = fields.Datetime("Voucher valid from")
    voucher_expire_date = fields.Datetime("Voucher valid until")
    voucher_apply = fields.Integer("Voucher apply", help="Reservation booked")
    voucher_used = fields.Integer("Voucher use", help="Reservation Issued")
    voucher_quota = fields.Integer("Voucher quota")
    voucher_blackout_ids = fields.One2many("tt.voucher.detail.blackout", 'voucher_detail_id')
    voucher_used_ids = fields.One2many("tt.voucher.detail.used", "voucher_detail_id")
    state = fields.Selection([('not-active', 'Not Active'), ('active', 'Active'), ('expire', 'Expire'), ('done', 'Done')], default="active")
    display_name = fields.Char('Display Name', compute='_compute_display_name')
    is_agent = fields.Boolean("For Agent", default=False)
    printout_voucher_id = fields.Many2one('tt.upload.center', 'Printout Voucher', readonly=True)

    @api.depends('voucher_reference_code', 'voucher_period_reference')
    @api.onchange('voucher_reference_code', 'voucher_period_reference')
    def _compute_display_name(self):
        for rec in self:
            ref_code = rec.voucher_reference_code and rec.voucher_reference_code or ''
            per_ref = rec.voucher_period_reference and rec.voucher_period_reference or ''
            rec.display_name = ref_code + '.' + per_ref

    @api.model
    def create(self, vals):
        if vals.get('voucher_period_reference'):
            if self.search([('voucher_period_reference','=',vals['voucher_period_reference'])]):
                raise UserError('Duplicate Reference Code')
        if type(vals.get('voucher_period_reference')) == str:
            vals['voucher_period_reference'] = vals['voucher_period_reference'].upper()
        return super(TtVoucherDetail, self).create(vals)

    def write(self, vals):
        if vals.get('voucher_period_reference'):
            if self.search([('voucher_period_reference','=',vals['voucher_period_reference'])]):
                raise UserError('Duplicate Reference Code')
        return super(TtVoucherDetail, self).write(vals)

    def create_voucher_created_email_queue(self):
        if not self.env.user.has_group('tt_base.group_voucher_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 355')
        self.create_voucher_email_queue('created')

    def create_voucher_email_queue(self, type):
        if self.voucher_id.voucher_multi_usage and self.voucher_id.voucher_customer_id:
            try:
                temp_data = {
                    'provider_type': 'voucher',
                    'ref_code': self.voucher_reference_code,
                    'period_code': self.voucher_period_reference,
                    'type': type,
                }
                temp_context = {
                    'co_agent_id': self.voucher_id.voucher_customer_id.agent_id.id
                }
                self.env['tt.email.queue'].create_email_queue(temp_data, temp_context)
            except Exception as e:
                _logger.info('Error Create Email Queue')

    def get_voucher_details_email(self):
        txt_detail = '<p>Reference Code: %s</p>' % (self.voucher_period_reference, )
        txt_detail += '<p>Value: %s %s</p>' % (self.voucher_id.currency_id.name, self.voucher_id.voucher_value)
        if self.voucher_start_date:
            txt_detail += '<p>Start Date: %s</p>' % (self.voucher_start_date.strftime('%d %b %Y %H:%M'), )
        else:
            txt_detail += '<p>Start Date: -</p>'

        if self.voucher_expire_date:
            txt_detail += '<p>Expired Date: %s</p>' % (self.voucher_expire_date.strftime('%d %b %Y %H:%M'), )
        else:
            txt_detail += '<p>Expired Date: -</p>'
        txt_detail += '<br/>'
        return txt_detail

    def get_voucher_remainder(self, voucher_id):
        voucher = self.env['tt.voucher.detail'].browse(int(voucher_id))
        return voucher.voucher_quota - voucher.voucher_used

    def get_voucher_detail_all(self):
        voucher = self.env['tt.voucher.detail'].search([])
        return voucher

    def get_voucher_detail(self, voucher_id):
        voucher = self.env['tt.voucher.detail'].browse(int(voucher_id)).read()
        voucher[0]['voucher_number'] = "%s.%s" % (voucher[0]['voucher_reference'], voucher[0]['voucher_period_reference'])
        return voucher

    #function for cron
    def activate_voucher(self):
        voucher = self.env['tt.voucher.detail'].search([('state', '=', 'not-active')])
        for i in voucher:
            if i.voucher_start_date.strftime("%Y-%m-%d") <= datetime.today().strftime("%Y-%m-%d"):
                i.write({
                    'state': 'active'
                })
        return 0

    #function for cron
    def expire_detail_voucher(self):
        voucher = self.env['tt.voucher.detail'].search([('state', '=', 'active')])
        for i in voucher:
            if i.voucher_expire_date.strftime("%Y-%m-%d") < datetime.today().strftime("%Y-%m-%d"):
                i.write({
                    'state': 'expire'
                })

        return 0

    def action_set_not_active(self):
        if not self.env.user.has_group('tt_base.group_voucher_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 356')
        self.write({
            'state': 'not-active'
        })

    def action_set_active(self):
        if not self.env.user.has_group('tt_base.group_voucher_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 357')
        self.write({
            'state': 'active'
        })

    def action_set_expire(self):
        if not self.env.user.has_group('tt_base.group_voucher_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 358')
        self.write({
            'state': 'expire'
        })

    # simulate voucher setelah order_obj created
    def new_simulate_voucher(self, data, context):
        # get the order object
        order_obj = self.env['tt.reservation.%s' % (data['provider_type'])].search([('name', '=', data['order_number'])])

        # get dependencies object
        dependencies_data = order_obj.provider_booking_ids

        ######################
        # check to see if voucher is exist
        #####################

        ##########################################
        # mark as old code
        # spliting voucher reference and detail reference by . (dot)
        # splits = data['voucher_reference'].split(".")
        ##########################################

        # extract the reference for the main voucher
        # adding the reference to the data
        # data['voucher_reference_code'] = splits[0]

        try:
            # get the detail reference code
            # data['voucher_reference_period'] = splits[1]
            data['voucher_reference_period'] = data['voucher_reference']
        except:
            # incase there's no detail reference code
            # write the error to logger
            _logger.error("%s doens't have period reference code" % data['voucher_reference'])

            # raise error
            return ERR.get_error(additional_message="must provide voucher period reference")

        # if voucher has reference and reference period
        # get the voucher data
        # voucher = self.env['tt.voucher'].search([('voucher_reference_code', '=', data['voucher_reference_code'])])

        # check if particular voucher do actually exist
        # if voucher.id == False:
        #     # if no known voucher data
        #     # write to logger
        #     _logger.error("%s voucher doesn't exist" % data['voucher_reference_code'])
        #
        #     # raise error
        #     return ERR.get_error(additional_message="Voucher doesn't exist")

        # if main voucher exist, lets try to get the voucher detail data
        # get voucher detail data
        # voucher_detail = voucher.voucher_detail_ids.filtered(lambda x: x['voucher_period_reference'] == data[
        #     'voucher_reference_period'])

        voucher_detail = self.env['tt.voucher.detail'].search([('voucher_period_reference', '=', data['voucher_reference_period'])])

        # check if voucher detail is actually exist
        if not voucher_detail:
            # if no known voucher detail
            # print to logger
            _logger.error("%s voucher doesn't exist" % data['voucher_reference'])

            # raise error
            return ERR.get_error(additional_message="Voucher doesn't exist")

        ######################
        # check to see if voucher is eligible
        #####################

        # check for voucher state
        if voucher_detail.voucher_id.state != 'confirm':
            # if voucher is not confirmed
            # print to logger
            _logger.error("%s voucher is either expired or inactive" % data['voucher_reference'])

            # raise error
            return ERR.get_error(additional_message="Voucher is either expired or inactive")

        # check for voucher state
        if voucher_detail.state != 'active':
            # if voucher is already expire
            # print to logger
            _logger.error("%s voucher is either expired or inactive" % data['voucher_reference'])

            # raise error
            return ERR.get_error(additional_message="Voucher is either expired or inactive")

        # check for voucher quota
        # check if voucher is multi_usage voucher
        if voucher_detail.voucher_id.voucher_multi_usage:
            # voucher is multi use
            # check if voucher value is up
            # if voucher value - voucher usage <= 0
            if voucher_detail.voucher_id.voucher_value - voucher_detail.voucher_id.voucher_usage_value <= 0:
                # voucher value is up
                # Print logger
                _logger.error("%s Voucher value is up" % data['voucher_reference'])

                # raise error
                return ERR.get_error("%s Voucher value is up" % data['voucher_reference'])
        else:
            # voucher is not multi use
            # check for quota
            # if voucher use is not bigger than quota, and quota is not -1
            # quota -1 = unlimited voucher
            if voucher_detail.voucher_used >= voucher_detail.voucher_quota and voucher_detail.voucher_quota != -1:
                # voucher is sold out, or used up
                # print in logger
                _logger.error("%s No more voucher" % data['voucher_reference'])

                # raise error
                return ERR.get_error(additional_message="No Voucher left %s" % data['voucher_reference'])

        # prepare data to check if voucher is able to be use by agent
        to_check = {
            'voucher_id': voucher_detail.voucher_id.id,
            'voucher_reference': data['voucher_reference'],
            'agent_type_id': context['co_agent_type_id'],
            'agent_id': context['co_agent_id']
        }

        # calling agent checker function
        agent_is_eligible = self.env['tt.voucher'].is_agent_eligible(to_check)
        # if value is false then the agent cannot use particular voucher
        if not agent_is_eligible:
            # agent cannot use the voucher
            # print logger
            _logger.error("%s, agent is not allowed to use voucher" % data['voucher_reference'])
            # raise error
            return ERR.get_error(additional_message="Agent is not allowed to use voucher %s" % data['voucher_reference'])

        # if is_customer_exclusive is True, check if customer is eligible to use the voucher
        if voucher_detail.voucher_id.is_customer_exclusive:
            cust_is_eligible = False
            for cust in order_obj.passenger_ids:
                if voucher_detail.voucher_id.voucher_customer_id.first_name == cust.first_name and voucher_detail.voucher_id.voucher_customer_id.last_name == cust.last_name:
                    cust_is_eligible = True
                    break

            if not cust_is_eligible:
                # agent cannot use the voucher
                # print logger
                _logger.error("%s, customer is not allowed to use voucher" % data['voucher_reference'])
                # raise error
                return ERR.get_error(additional_message="Customer is not allowed to use voucher %s" % data['voucher_reference'])

        # at this point it means the voucher is exist
        # voucher is not expired
        # agent can use the voucher
        # customer can use the voucher

        ######################
        # check voucher requirements
        #####################

        # check for minimum purchase
        if order_obj.total_fare < voucher_detail.voucher_id.voucher_minimum_purchase:
            # total fare is under the minimum_purchase
            # print logger
            _logger.error("%s, Order did not meet minimum purchase required" % order_obj['name'])

            # raise error
            return ERR.get_error("%s, Order did not meet minimum purchase required" % order_obj['name'])

        ######################
        # voucher process
        #####################

        # declare result array
        result_array = []

        # dependencies of voucher amount, and just to be safe
        voucher_remainder = voucher_detail.voucher_id.voucher_value - voucher_detail.voucher_id.voucher_usage_value
        voucher_usage = 0

        # iterate for every provider
        for i in dependencies_data:

            # declare some float
            provider_total_price = 0.0
            provider_total_discount = 0.0
            provider_final_total_price = 0.0

            # declare temp array for return value
            temp_array = []

            # create eligible provider
            if voucher_detail.voucher_id.voucher_coverage != 'all':
                # create data to check
                # since dependencies len is < 2
                temp_dict = {
                    'voucher_id': voucher_detail.voucher_id.id,
                    'voucher_reference': data['voucher_reference'],
                    'provider_type_id': i.provider_id.provider_type_id.id,
                    'provider_id': i.provider_id.id,
                    'provider_name': i.provider_id.code
                }

                # check if provider is cover by the voucher
                provider_is_eligible = self.env['tt.voucher'].is_product_eligible(temp_dict)
            else:
                provider_is_eligible = True

            if provider_is_eligible:
                # at this point provider within transaction is covered by voucher

                # check if voucher is multiusage and percent
                if voucher_detail.voucher_id.voucher_type == 'percent' and voucher_detail.voucher_id.voucher_multi_usage:
                    # voucher invalid
                    # no way multi use is percent will let it slide
                    _logger.error("Voucher logic is invalid, %s" % voucher_detail.voucher_id.voucher_reference_code)

                    # let the data pass
                    for j in i.cost_service_charge_ids:
                        # adding value to provider total
                        if j.charge_type != 'RAC' and j.charge_type != 'DISC':##DI TAMBAH CHARGE_TYPE DISC karena service charge minus nanti discount jadi hilang
                            provider_total_price += float(j.total)

                        # create result temp dict
                        result_temp = {
                            'charge_code': j.charge_code,
                            'charge_type': j.charge_type,
                            'start_amount': j.total,
                            'discount_value': 0.0,
                            'voucher_type': voucher_detail.voucher_id.voucher_type,
                            'discount_amount': 0.0,
                            'final_amount': j.total
                        }

                        # adding result to temp array
                        temp_array.append(result_temp)

                elif voucher_detail.voucher_id.voucher_type == 'percent' and not voucher_detail.voucher_id.voucher_multi_usage:
                    # voucher is percent
                    _logger.info(i.cost_service_charge_ids)
                    # iterate every cost
                    for j in i.cost_service_charge_ids:

                        # if voucher cover all pricing
                        if voucher_detail.voucher_id.voucher_effect_all:

                            # make sure charge type is not comission
                            if j.charge_type != 'RAC' and j.charge_type != 'DISC': ##DI TAMBAH CHARGE_TYPE DISC karena service charge minus nanti discount jadi hilang
                                _logger.info("Will be discount: %s, %s" % (j.charge_code, j.charge_type))
                                # charge_type is not RAC
                                # count the discount
                                discount_amount = float(j.total) * voucher_detail.voucher_id.voucher_value / 100

                                # SUM discount amount
                                final_amount = float(j.total) - float(discount_amount)

                                # adding the value to total price
                                provider_total_price += float(j.total)
                                provider_total_discount += float(discount_amount)

                                # creating result temp dict
                                result_temp = {
                                    'charge_code': j.charge_code,
                                    'charge_type': j.charge_type,
                                    'start_amount': j.total,
                                    'discount_value': voucher_detail.voucher_id.voucher_value,
                                    'voucher_type': voucher_detail.voucher_id.voucher_type,
                                    'discount_amount': float(discount_amount),
                                    'final_amount': float(final_amount)
                                }
                            else:
                                # charge_type is RAC
                                # nothing will happen
                                # RAC will not be affected by voucher

                                # create result temp dict
                                result_temp = {
                                    'charge_code': j.charge_code,
                                    'charge_type': j.charge_type,
                                    'start_amount': j.total,
                                    'discount_value': 0.0,
                                    'voucher_type': voucher_detail.voucher_id.voucher_type,
                                    'discount_amount': 0.0,
                                    'final_amount': j.total
                                }

                            # adding result to temp array
                            temp_array.append(result_temp)
                        else:

                            # voucher is percent
                            if j.charge_code == 'fare' or j.charge_code == 'FarePrice':
                                _logger.info("Will be discount: %s, %s" % (j.charge_code, j.charge_type))
                                # charge_type is not RAC
                                # count the discount
                                discount_amount = float(j.total) * voucher_detail.voucher_id.voucher_value / 100

                                # SUM discount amount
                                final_amount = float(j.total) - float(discount_amount)

                                # adding the value to total price
                                provider_total_price += float(j.total)
                                provider_total_discount += float(discount_amount)

                                # creating result temp dict
                                result_temp = {
                                    'charge_code': j.charge_code,
                                    'charge_type': j.charge_type,
                                    'start_amount': j.total,
                                    'discount_value': voucher_detail.voucher_id.voucher_value,
                                    'voucher_type': voucher_detail.voucher_id.voucher_type,
                                    'discount_amount': float(discount_amount),
                                    'final_amount': float(final_amount)
                                }
                            else:
                                # charge_type is RAC
                                # nothing will happen
                                # RAC will not be affected by voucher

                                # adding value to provider total
                                if j.charge_type != 'RAC' and j.charge_type != 'DISC': ##DI TAMBAH CHARGE_TYPE DISC karena service charge minus nanti discount jadi hilang
                                    provider_total_price += float(j.total)

                                # create result temp dict
                                result_temp = {
                                    'charge_code': j.charge_code,
                                    'charge_type': j.charge_type,
                                    'start_amount': j.total,
                                    'discount_value': 0.0,
                                    'voucher_type': voucher_detail.voucher_id.voucher_type,
                                    'discount_amount': 0.0,
                                    'final_amount': j.total
                                }

                            # adding result to temp array
                            temp_array.append(result_temp)
                else:
                    # voucher will be defaulted to amount

                    # check voucher remainderity
                    if voucher_remainder > 0:

                        _logger.info(i.cost_service_charge_ids)
                        # well count with the price
                        for j in i.cost_service_charge_ids:

                            # check if voucher check all
                            if voucher_detail.voucher_id.voucher_effect_all:
                                # check if price sector or voucher value is bigger
                                if j.charge_type != 'RAC' and j.charge_type != 'DISC': ##DI TAMBAH CHARGE_TYPE DISC karena service charge minus nanti discount jadi hilang
                                    _logger.info("Will be discount: %s, %s" % (j.charge_code, j.charge_type))
                                    # check if voucher value is bigger than fare
                                    if float(j.total) - voucher_remainder < 0:
                                        # total is smaller than voucher value
                                        temp_voucher_usage = float(j.total)

                                    else:
                                        # total is bigger than voucher value
                                        temp_voucher_usage = voucher_remainder

                                    # subtract voucher_remainder
                                    voucher_remainder -= temp_voucher_usage
                                    voucher_usage += temp_voucher_usage

                                    # create alles
                                    provider_total_price += float(j.total)
                                    provider_total_discount += float(temp_voucher_usage)

                                    # SUM discount amount
                                    final_amount = float(j.total) - float(temp_voucher_usage)

                                    # create result temp dict
                                    result_temp = {
                                        'charge_code': j.charge_code,
                                        'charge_type': j.charge_type,
                                        'start_amount': j.total,
                                        'discount_value': voucher_usage,
                                        'voucher_type': voucher_detail.voucher_id.voucher_type,
                                        'discount_amount': float(temp_voucher_usage),
                                        'final_amount': float(final_amount)
                                    }
                                    temp_array.append(result_temp)
                                else:
                                    # no error just let the data pass

                                    # create result_temp
                                    result_temp = {
                                        'charge_code': j.charge_code,
                                        'charge_type': j.charge_type,
                                        'start_amount': j.total,
                                        'discount_value': 0.0,
                                        'voucher_type': voucher_detail.voucher_id.voucher_type,
                                        'discount_amount': 0.0,
                                        'final_amount': j.total
                                    }

                                    # add to temp array
                                    temp_array.append(result_temp)
                            else:
                                # check if price sector or voucher value is bigger
                                if j.charge_code == 'fare' or j.charge_code == 'FarePrice':
                                    _logger.info("Will be discount: %s, %s" % (j.charge_code, j.charge_type))
                                    # check if voucher value is bigger than fare
                                    if float(j.total) - voucher_remainder < 0:
                                        # total is smaller than voucher value
                                        temp_voucher_usage = float(j.total)

                                    else:
                                        # total is bigger than voucher value
                                        temp_voucher_usage = voucher_remainder

                                    # subtract voucher_remainder
                                    voucher_remainder -= temp_voucher_usage
                                    voucher_usage += temp_voucher_usage

                                    # create alles
                                    provider_total_price += float(j.total)
                                    provider_total_discount += float(temp_voucher_usage)

                                    # SUM discount amount
                                    final_amount = float(j.total) - float(temp_voucher_usage)

                                    # create result temp dict
                                    result_temp = {
                                        'charge_code': j.charge_code,
                                        'charge_type': j.charge_type,
                                        'start_amount': j.total,
                                        'discount_value': voucher_usage,
                                        'voucher_type': voucher_detail.voucher_id.voucher_type,
                                        'discount_amount': float(temp_voucher_usage),
                                        'final_amount': float(final_amount)
                                    }
                                    temp_array.append(result_temp)
                                else:
                                    # no error just let the data pass
                                    # add to SUM variable
                                    if j.charge_type != 'RAC' and j.charge_type != 'DISC': ##DI TAMBAH CHARGE_TYPE DISC karena service charge minus nanti discount jadi hilang
                                        provider_total_price += float(j.total)

                                    # create result_temp
                                    result_temp = {
                                        'charge_code': j.charge_code,
                                        'charge_type': j.charge_type,
                                        'start_amount': j.total,
                                        'discount_value': 0.0,
                                        'voucher_type': voucher_detail.voucher_id.voucher_type,
                                        'discount_amount': 0.0,
                                        'final_amount': j.total
                                    }

                                    # add to temp array
                                    temp_array.append(result_temp)

                    else:
                        # let the data slide
                        for j in i.cost_service_charge_ids:
                            # adding value to provider total
                            if j.charge_type != 'RAC' and j.charge_type != 'DISC': ##DI TAMBAH CHARGE_TYPE DISC karena service charge minus nanti discount jadi hilang
                                provider_total_price += float(j.total)

                            # create result temp dict
                            result_temp = {
                                'charge_code': j.charge_code,
                                'charge_type': j.charge_type,
                                'start_amount': j.total,
                                'discount_value': 0.0,
                                'voucher_type': voucher_detail.voucher_id.voucher_type,
                                'discount_amount': 0.0,
                                'final_amount': j.total
                            }

                            # adding result to temp array
                            temp_array.append(result_temp)
            else:
                # let the data slide
                for j in i.cost_service_charge_ids:
                    # adding value to provider total
                    if j.charge_type != 'RAC' and j.charge_type != 'DISC': ##DI TAMBAH CHARGE_TYPE DISC karena service charge minus nanti discount jadi hilang
                        provider_total_price += float(j.total)

                    # create result temp dict
                    result_temp = {
                        'charge_code': j.charge_code,
                        'charge_type': j.charge_type,
                        'start_amount': j.total,
                        'discount_value': 0.0,
                        'voucher_type': voucher_detail.voucher_id.voucher_type,
                        'discount_amount': 0.0,
                        'final_amount': j.total
                    }

                    # adding result to temp array
                    temp_array.append(result_temp)

            # count the discount for particular provider
            provider_final_total_price = provider_total_price - provider_total_discount

            # if for some reason the voucher behave like its not suppose to, worse case 100% discount
            if provider_final_total_price < 0:
                provider_final_total_price = 0
                provider_total_discount = provider_total_price

            # create result dict
            result_dict = {
                'provider_type_code': i.provider_id.provider_type_id.code,
                'provider_code': i.provider_id.code,
                'provider_total_price': provider_total_price,
                'provider_total_discount': provider_total_discount,
                'provider_final_price': provider_final_total_price,
                'discount_detail': temp_array
            }

            # add result dict to result array
            result_array.append(result_dict)
        return ERR.get_no_error(result_array)

    # simulate voucher sebelum booked
    def simulate_voucher_api(self, data, context):
        # requirement of data
        # data = {
        #	voucher_reference,
        #	date 				<-- date voucher digunakan (today)
        #	provider_type
        #	provider 			--> list
        # }

        # create a return array
        result_array = []

        # split voucher reference
        # splits = data['voucher_reference'].split(".")
        # get the first index of split
        # data['voucher_reference_code'] = splits[0]
        # try to get the second half
        try:
            # data['voucher_reference_period'] = splits[1]
            data['voucher_reference_period'] = data['voucher_reference']
        except:
            # write to logger
            _logger.error("%s, voucher code is invalid" % data['voucher_reference'])
            # return error
            return ERR.get_error(additional_message="Voucher must have period reference")

        # at this point the voucher code is legal
        # check if the reference code voucher is actually exist
        # voucher = self.env['tt.voucher'].search([('voucher_reference_code', '=', data['voucher_reference_code'])])
        # if voucher.id == False:
        #     # no voucher found
        #     # write to logger
        #     _logger.error("%s voucher is not exist" % data['voucher_reference'])
        #     # return error
        #     return ERR.get_error(additional_message="Voucher is NOT exist")

        # okay so voucher is exist, but is the particular period voucher exist
        # voucher_detail = voucher.voucher_detail_ids.filtered(
        #     lambda x: x['voucher_period_reference'] == data['voucher_reference_period'])

        voucher_detail = self.env['tt.voucher.detail'].search([('voucher_period_reference', '=', data['voucher_reference_period'])])

        if not voucher_detail:
            # no voucher detail found
            # write to logger
            _logger.error("%s voucher is not exist" % data['voucher_reference'])
            # return error
            return ERR.get_error(additional_message="Voucher is NOT Exist")

        # voucher is exist hooray, now we'll check if the voucher could be use
        if voucher_detail.voucher_id.state != 'confirm':
            # voucher is expired dun dun dun
            # write log
            _logger.error("%s Voucher is either expired or inactive" % data['voucher_reference'])
            # return error
            return ERR.get_error(additional_message="Voucher is either expired or inactive")

        if voucher_detail.state != 'active':
            # voucher is expired dun dun dun
            # write log
            _logger.error("%s Voucher is either expired or inactive" % data['voucher_reference'])
            # return error
            return ERR.get_error(additional_message="Voucher is either expired or inactive")

        # voucher may not be expired at this point, but maybe just maybe voucher can only be use on certain date(s)
        if voucher_detail.voucher_start_date != False and voucher_detail.voucher_expire_date != False and voucher_detail.voucher_start_date.strftime("%Y-%m-%d") > data['date'] and voucher_detail.voucher_expire_date.strftime("%Y-%m-%d") < data['date'] or \
                voucher_detail.voucher_expire_date != False and voucher_detail.voucher_expire_date.strftime("%Y-%m-%d") < data['date']:
            # today's date (the day users pass to use the date) is not covered by the voucher #ouch!
            # write log
            _logger.error("%s Voucher cannot be use outside the designated date" % data['voucher_reference'])
            # return error
            return ERR.get_error(additional_message="Voucher cannot be use outside designated date")

        if voucher_detail.voucher_id.voucher_multi_usage:
            if voucher_detail.voucher_id.voucher_value - voucher_detail.voucher_id.voucher_usage_value <= 0:
                # o no the voucher is up
                # write to logger
                _logger.error("%s Voucher has no value left :(" % data['voucher_reference'])
                # return error
                return ERR.get_error(additional_message="Voucher has no value left")
        ### VOUCHER DAPAT DI APPLY BANYAK RESERVASI HANYA YG USE MENGIKUTI VOUCHER QUOTA
        # else:
        #     # okay okay so the voucher is there, the date is within the voucher date, then we should look f there's voucher left
        #     if voucher_detail.voucher_apply >= voucher_detail.voucher_quota:
        #         # o no the voucher is up
        #         # write to logger
        #         _logger.error("%s No More Voucher :(" % data['voucher_reference'])
        #         # return error
        #         return ERR.get_error(additional_message="Voucher sold out")

        # check agent
        agent_to_validate = {
            'voucher_id': voucher_detail.voucher_id.id,
            'voucher_reference': data['voucher_reference'],
            'agent_type_id': context['co_agent_type_id'],
            'agent_id': context['co_agent_id']
        }
        agent_eligible = self.env['tt.voucher'].is_agent_eligible(agent_to_validate)
        if not agent_eligible:
            # agent is not eligible to be use dun dun dun
            # write to log
            _logger.error('Agent ID %s cannot use voucher %s' % (context['co_agent_id'], data['voucher_reference']))
            # return error
            return ERR.get_error(additional_message="Agent cannot user the voucher")

        # if is_customer_exclusive is True, check if customer is eligible to use the voucher
        if voucher_detail.voucher_id.is_customer_exclusive:
            cust_is_eligible = False
            filtered_cust = filter(lambda x: x['first_name'] == voucher_detail.voucher_id.voucher_customer_id.first_name and x['last_name'] == voucher_detail.voucher_id.voucher_customer_id.last_name, data['passenger_list'])
            for cust in filtered_cust:
                if cust:
                    cust_is_eligible = True
                    break

            if not cust_is_eligible:
                # agent cannot use the voucher
                # print logger
                _logger.error("%s, customer is not allowed to use voucher" % data['voucher_reference'])
                # raise error
                return ERR.get_error(
                    additional_message="Customer is not allowed to use voucher %s" % data['voucher_reference'])

        # check provider
        if type(data['provider']) is list:
            # if provider list pass is list type
            # provider can be list, if particular order is multi provider
            # if multi provider, then we need to make sure only provider eligible for voucher, get the discount
            for i in data['provider']:
                # search the exact prvider
                provider = self.env['tt.provider'].search([('code', '=', i)], limit=1)
                provider_type_id = self.env['tt.provider.type'].search([('code', '=', data['provider_type'])], limit=1)
                # create data to check if current iteration provider is eligible for voucher discount
                to_check = {
                    'voucher_id': voucher_detail.voucher_id.id,
                    'provider_type_id': provider_type_id.id,
                    'provider_id': provider.id,
                    'provider_name': i,
                    'voucher_reference': data['voucher_reference']
                }

                # run the code to check
                is_eligible = self.env['tt.voucher'].is_product_eligible(to_check)
                # if provider is eligible
                if is_eligible:
                    to_return = {
                        'provider_type': data['provider_type'],
                        'provider': i,
                        'able_to_use': True
                    }
                else:
                # if not
                    to_return = {
                        'provider_type': data['provider_type'],
                        'provider': i,
                        'able_to_use': False
                    }
                result_array.append(to_return)
        else:
            provider = self.env['tt.provider'].search([('code', '=', data['provider'])])
            to_check = {
                'provider_type_id': provider.provider_type_id.id,
                'provider_id': provider.id,
                'provider_name': data['provider'],
                'voucher_reference': data['voucher_reference']
            }
            is_eligible = self.env['tt.voucher'].is_product_eligible(to_check)
            if is_eligible:
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

        # at this point the voucher can be use and will be use (?)
        # okay do something about the voucher
        if voucher_detail.voucher_id.voucher_multi_usage:
            voucher_value = voucher_detail.voucher_id.voucher_value - voucher_detail.voucher_id.voucher_usage_value
        else:
            voucher_value = voucher_detail.voucher_id.voucher_value

        # maximum_cap
        if voucher_detail.voucher_id.voucher_maximum_cap < 1:
            maximum_cap = False
        else:
            maximum_cap = voucher_detail.voucher_id.voucher_maximum_cap

        # minimum purchase
        if voucher_detail.voucher_id.voucher_minimum_purchase < 1:
            minimum_purchase = False
        else:
            minimum_purchase = voucher_detail.voucher_id.voucher_minimum_purchase

        result = {
            'reference_code': data['voucher_reference'],
            'voucher_type': voucher_detail.voucher_id.voucher_type,
            'voucher_value': voucher_value,
            'voucher_currency': voucher_detail.voucher_id.currency_id.name,
            'voucher_cap': maximum_cap,
            'voucher_minimum_purchase': minimum_purchase,
            'voucher_effect_all': voucher_detail.voucher_id.voucher_effect_all,
            'date_expire': '' if voucher_detail.voucher_expire_date == False else voucher_detail.voucher_expire_date.strftime("%Y-%m-%d"),
            'provider_type': data['provider_type'],
            'provider': result_array,
            'is_agent': voucher_detail.is_agent
        }

        ##TAMBAHKAN SERVICE CHARGE DISCOUNT KE RESERVASI
        if data.get('order_number'):
            book_obj = self.env['tt.reservation.%s' % (data['provider_type'])].search([('name','=',data['order_number'])],limit=1)
            if book_obj:
                book_obj.add_voucher(data['voucher_reference'], context)
        return ERR.get_no_error(result)

    def create_voucher_detail(self, data):
        self.env['tt.voucher.detail'].create({
            'voucher_id': data['voucher_id'],
            'voucher_period_reference': data['voucher_period_reference'],
            'voucher_start_date': data['start_date'],
            'voucher_expire_date': data['end_date'],
            'voucher_used': 0,
            'voucher_quota': int(data['voucher_quota']),
            'state': 'not-activate'
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
        corresponding_voucher = self.env['tt.voucher.detail'].search([('voucher_reference', '=', data['voucher_reference'])])
        if corresponding_voucher.id == False:
            _logger.error('Voucher is not exist')
            return ERR.get_error(additional_message="voucher is not exist")

        if corresponding_voucher.state == 'expire':
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

    ###############################################
    # Main function that's being called for voucher
    # well other than simulate_voucher_api, that's being called before order being booked
    ###############################################
    def use_voucher_new(self, data, context, type):
        try:
            # check if there's data being pass from frontend/gateway
            if data == None:
                return ERR.get_error()
            # data = {
            #   voucher_reference
            #   order_code
            #   date
            #   provider_type
            # }

            # called simulate voucher (basically who runs the validator and return how many discount the voucher will give)
            simulate = self.new_simulate_voucher(data, context)

            # if it success
            if simulate['error_code'] == 0:
                # okay so the purpose of this if logic is to built and trim data for return

                # splits = data['voucher_reference'].split(".")
                # data['voucher_reference'] = splits[0]

                # first get the voucher reference
                data['voucher_reference_period'] = data['voucher_reference']

                # search directly to voucher detail, since we'll not be using voucher (parent) reference
                voucher_detail = self.env['tt.voucher.detail'].search([('voucher_period_reference', '=', data['voucher_reference'])])
                # get all of necessary data
                provider_type = self.env['tt.provider.type'].search([('code', '=', simulate['response'][0]['provider_type_code'])], limit=1)
                provider = self.env['tt.provider'].search([('code', '=', simulate['response'][0]['provider_code'])], limit=1)
                voucher = self.env['tt.voucher'].search([('id', '=', voucher_detail.voucher_id.id)], limit=1)

                # set discount total variable, this variable will be very useful
                # especially if order contains more than one provider
                # for sum of course
                discount_total = 0

                # count all of discount
                for i in simulate['response']:
                    discount_total += i['provider_total_discount']

                # create data to add to voucher usage
                # a.k.a tracking record of particular voucher, maybe in the future the data can be use
                # better to record than sorry
                use_voucher_data = {
                    'voucher_detail_id': voucher_detail.id,
                    'voucher_date_use': data['date'],
                    'voucher_agent_type': context['co_agent_type_id'],
                    'voucher_agent': context['co_agent_id'],
                    'voucher_provider_type': provider_type.id,
                    'voucher_provider': provider.id,
                    'currency': voucher.currency_id.id,
                    'voucher_usage': discount_total,
                    'order_number': data['order_number'],
                    'type': type
                }

                # create used voucher data
                res = self.env['tt.voucher.detail.used'].add_voucher_used_detail(use_voucher_data)

                # if for some reason the usage failed to add, then return error
                if res.id == False:
                    return ERR.get_error(additional_message="voucher usage failed")
                else:
                    # if it's success, check if voucher is multi usage type
                    # multi usage voucher acct like digital currency
                    # so the voucher will not be burned after one use
                    # in order to do that, we keep track how much value the user had use
                    if voucher.voucher_multi_usage:
                        # adding the value to voucher usage
                        # like finalizing value of usage
                        voucher.voucher_usage_value += discount_total
                        if voucher.voucher_usage_value >= voucher.voucher_value:
                            for voucher_detail_obj in voucher.voucher_detail_ids:
                                voucher_detail_obj.state = 'done'
                            voucher.state = 'done'
                    else:
                        # assuming other voucher are normal boring voucher
                        # then we'll add number of usage for that particular voucher
                        # number_of_use = voucher_detail.voucher_used + 1

                        voucher_detail.write({
                            'voucher_apply': len(voucher_detail.voucher_used_ids),
                            'voucher_used': len(voucher_detail.voucher_used_ids.filtered(lambda x: x.type == 'use'))
                        })
                        if voucher_detail.voucher_used >= voucher_detail.voucher_quota:
                            voucher_detail.state = 'done'
                        update_state = True
                        for voucher_detail_obj in voucher.voucher_detail_ids:
                            if voucher_detail_obj.state != 'done':
                                update_state = False
                        if update_state:
                            voucher.state = 'done'

                    try:
                        voucher_detail.create_voucher_email_queue('used')
                    except Exception as e:
                        _logger.info('Error Create Voucher Usage Email Queue')

            # if failed then return the error from simulate
            else:
                return simulate
            return simulate
        except Exception as e:
            _logger.error(str(e) + traceback.format_exc())

    def print_voucher(self):
        datas = {
            'ids': self.env.context.get('active_ids', []),
            'model': self._name,
        }
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        voucher_printout_action = self.env.ref('tt_report_common.action_report_printout_voucher')
        if not self.printout_voucher_id:
            co_agent_id = self.env.user.agent_id.id
            co_uid = self.env.user.id

            pdf_report = voucher_printout_action.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = voucher_printout_action.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Voucher %s.pdf' % (self.voucher_reference_code),
                    'file_reference': 'Voucher Printout %s' % (self.voucher_reference_code),
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid,
                }
            )
            upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            self.printout_voucher_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': self.printout_voucher_id.url,
        }
        return url


class TtVoucherusedDetail(models.Model):
    _name = "tt.voucher.detail.used"
    _description = "Voucher Detail Used"

    voucher_detail_id = fields.Many2one("tt.voucher.detail", readonly=True)
    voucher_date_use = fields.Datetime("Date use")
    voucher_agent_type_id = fields.Many2one("tt.agent.type", "Agent Type")
    voucher_ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)])
    voucher_agent_id = fields.Many2one("tt.agent", "Agent ID")
    voucher_provider_type_id = fields.Many2one("tt.provider.type", "Provider Type")
    voucher_provider_id = fields.Many2one("tt.provider", "Provider ID")
    order_number = fields.Char('Order Number')

    currency_id = fields.Many2one('res.currency', 'Currency')
    voucher_usage = fields.Monetary('Voucher Usage', readonly=True)
    voucher_remainder = fields.Monetary('Voucher Remainder', readonly=True)
    type = fields.Selection([('use', 'Use'), ('apply', 'Apply')])

    def add_voucher_used_detail(self, data):
        result = self.env['tt.voucher.detail.used'].create({
            'voucher_detail_id': int(data['voucher_detail_id']),
            'voucher_date_use': data['voucher_date_use'],
            'voucher_agent_type_id': int(data['voucher_agent_type']),
            'voucher_agent_id': int(data['voucher_agent']),
            'voucher_provider_type_id': int(data['voucher_provider_type']),
            'voucher_provider_id': int(data['voucher_provider']),
            'currency_id': int(data['currency']),
            'voucher_usage': data['voucher_usage'],
            'order_number': data['order_number'],
            'type': data['type']
        })

        return result

class TtVoucherBlackout(models.Model):
    _name = "tt.voucher.detail.blackout"
    _description = "Voucher Detail Blackout"

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