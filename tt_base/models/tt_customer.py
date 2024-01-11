from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime,date
from dateutil.relativedelta import relativedelta
from odoo.tools import image
from ...tools import variables,util,ERR
from ...tools.api import Response
from ...tools.ERR import RequestException
import json,time
import logging,traceback
import random, string
import re

_logger = logging.getLogger(__name__)

class TtCustomer(models.Model):
    _inherit = 'tt.history'
    _name = 'tt.customer'
    _rec_name = 'name'
    _description = 'Tour & Travel - Customer'

    seq_id = fields.Char('Sequence ID', index=True,readonly=True)
    name = fields.Char(string='Name', compute='_compute_name', store=True)
    face_image_id = fields.Many2one('tt.upload.center','Face Image')
    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    gender = fields.Selection(variables.GENDER, string='Gender')
    marital_status = fields.Selection(variables.MARITAL_STATUS, 'Marital Status',default="single")
    religion = fields.Selection(variables.RELIGION, 'Religion')
    birth_date = fields.Date('Birth Date')
    nationality_id = fields.Many2one('res.country', 'Nationality')
    address_ids = fields.One2many('address.detail', 'customer_id', 'Address Detail')
    phone_ids = fields.One2many('phone.detail', 'customer_id', 'Phone Detail')
    social_media_ids = fields.One2many('social.media.detail', 'customer_id', 'Social Media Detail')
    email = fields.Char('Email')
    position = fields.Selection([('staff','Staff'),
                                 ('finance','Finance'),
                                 ('manager','Manager'),
                                 ('director','Director'),
                                 ('owner','Owner')],'Job Position')
    user_ids = fields.One2many('res.users', 'customer_id', 'User')
    # customer_bank_detail_ids = fields.One2many('customer.bank.detail', 'customer_id', 'Customer Bank Detail')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id.id)
    agent_id = fields.Many2one('tt.agent', 'Agent', default=lambda self: self.env.user.agent_id)  # , default=lambda self: self.env.user.agent_id
    agent_as_staff_id = fields.Many2one('tt.agent', 'Agent as Staff')  # , default=lambda self: self.env.user.agent_id
    # user_agent_id = fields.Many2one('tt.agent', 'Agent User', default=lambda self: self.env.user.agent_id)
    customer_parent_ids = fields.Many2many('tt.customer.parent','tt_customer_customer_parent_rel','customer_id','customer_parent_id','Customer Parent')
    # booker_parent_ids = fields.Many2many('tt.customer.parent', 'tt_customer_booker_customer_parent_rel', 'customer_id',
    #                                      'customer_parent_id', 'Booker Parent')
    customer_parent_booker_ids = fields.One2many('tt.customer.parent.booker.rel', 'customer_id', 'Booker Parent')

    active = fields.Boolean('Active', default=True)

    identity_ids = fields.One2many('tt.customer.identity','customer_id','Identity List')
    behavior_ids = fields.One2many('tt.customer.behavior', 'customer_id', 'Behavior List')
    frequent_flyer_ids = fields.One2many('tt.customer.frequent.flyer', 'customer_id', 'Frequent Flyer List')
    is_get_booking_from_vendor = fields.Boolean('Get Booking From Vendor')
    is_search_allowed = fields.Boolean("Search Allowed", default=True)

    riz_text = fields.Char('Endorsement Box (RIZ)')

    register_uid = fields.Many2one('res.users', 'Register UID', default=lambda self: self.env.user)

    @api.depends('first_name', 'last_name')
    def _compute_name(self):
        for rec in self:
            ## 2 apr 2022 IVAN KALAU LAST NAME KOSONG TIDAK TERISI FIRSTNAME dengan space
            rec_name_result = ''
            if rec.first_name:
                rec_name_result += rec.first_name
            if rec.last_name: ##ASUMSI FIRST NAME REQUIRED LASTNAME BOLEH KOSONG
                rec_name_result += " %s" % rec.last_name
            rec.name = rec_name_result
            # rec.name = "%s %s" % (rec.first_name and rec.first_name or '', rec.last_name and rec.last_name or '')

    @api.depends('logo')
    def _get_logo_image(self):
        for record in self:
            if record.logo:
                record.logo_thumb = image.crop_image(record.logo, type='center', ratio=(4, 3), size=(200, 200))
            else:
                record.logo_thumb = False

    @api.multi
    def set_history_message(self):
        for rec in self:
            body = "Message has been approved on %s", datetime.now()
            rec.message_post(body=body)


    @api.model
    def create(self, vals_list):
        util.pop_empty_key(vals_list,whitelist=[
            'is_search_allowed','is_get_booking_from_vendor','active'
        ])
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('tt.customer')
        if 'first_name' in vals_list:
            vals_list['first_name'] = vals_list['first_name'].strip()
        if 'last_name' in vals_list:
            vals_list['last_name'] = vals_list['last_name'].strip()
        cust_obj = super(TtCustomer, self).create(vals_list)
        cust_obj.customer_parent_ids = [(4, cust_obj.agent_id.customer_parent_walkin_id.id)]
        return cust_obj

    @api.multi
    def write(self, vals):
        util.pop_empty_key(vals,whitelist=[
            'is_search_allowed','is_get_booking_from_vendor','active','agent_as_staff_id','last_name'
        ])
        if 'first_name' in vals:
            vals['first_name'] = vals['first_name'].strip()
        if 'last_name' in vals:
            vals['last_name'] = vals['last_name'].strip()
        return super(TtCustomer, self).write(vals)

    @api.multi
    def unlink(self):
        if not ({self.env.ref('base.group_system').id, self.env.ref('tt_base.group_customer_level_5').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Action failed due to security restriction. Required Customer Level 5 permission.')
        return super(TtCustomer, self).unlink()

    def toggle_search_allowed(self):
        self.is_search_allowed = not self.is_search_allowed

    def to_dict(self,get_customer_parent=False):
        phone_list = []
        for rec in self.phone_ids:
            phone_list.append(rec.to_dict())
        is_id_alt_name = False
        cust_name = self.first_name
        if self.last_name:
            cust_name += ' %s' % self.last_name
        identity_dict = {}
        for rec in self.identity_ids:
            identity_dict.update(rec.to_dict())
            if not is_id_alt_name and rec.identity_first_name:
                id_name = '%s%s' % (rec.identity_first_name, rec.identity_last_name and ' ' + rec.identity_last_name or '')
                if id_name != cust_name:
                    is_id_alt_name = True

        behavior_dict = self.get_behavior()

        ff_list_dict = self.frequent_flyer_ids.to_dict()

        res = {
            'name': self.name,
            'first_name': self.first_name,
            'face_image': self.face_image_id and [self.face_image_id.url,self.face_image_id.seq_id, self.face_image_id.file_reference, self.face_image_id.create_date.strftime('%Y-%m-%d %H:%M:%S')] or [],
            'last_name': self.last_name and self.last_name or '',
            'gender': self.gender and self.gender or '',
            'birth_date': self.birth_date and self.birth_date.strftime('%Y-%m-%d') or '',
            'nationality_code': self.nationality_id and self.nationality_id.code or '',
            'nationality_name': self.nationality_id and self.nationality_id.name or '',
            'marital_status': self.marital_status and self.marital_status or '',
            'phones': phone_list,
            'email': self.email and self.email or '',
            'seq_id': self.seq_id,
            'identities': identity_dict,
            'behaviors': behavior_dict,
            'original_agent': self.agent_id and self.agent_id.name or '',
            'frequent_flyers': ff_list_dict,
            'is_id_alt_name': is_id_alt_name,
            'riz_text': self.riz_text if self.riz_text else ''
        }
        if get_customer_parent:
            customer_parent_list = []
            # for rec in self.booker_parent_ids:
            #     if rec.credit_limit != 0 and rec.state == 'done':
            #         customer_parent_list.append({
            #             'name': rec.name,
            #             'actual_balance': rec.actual_balance,
            #             'credit_limit': rec.credit_limit,
            #             'currency': rec.currency_id.name,
            #             'seq_id': rec.seq_id,
            #             'type': rec.customer_parent_type_id and rec.customer_parent_type_id.name or ''
            #         })

            for rec in self.customer_parent_booker_ids:
                cp_obj = rec.customer_parent_id
                if cp_obj.credit_limit != 0 and cp_obj.state == 'done':
                    customer_parent_list.append({
                        'name': cp_obj.name,
                        'actual_balance': cp_obj.actual_balance,
                        'credit_limit': cp_obj.credit_limit,
                        'currency': cp_obj.currency_id.name,
                        'seq_id': cp_obj.seq_id,
                        'type': cp_obj.customer_parent_type_id and cp_obj.customer_parent_type_id.name or ''
                    })
            res.update({
                'customer_parents': customer_parent_list
            })

        return res

    def get_behavior(self):
        behavior_dict = {}
        for rec in self.behavior_ids:
            rec_dict = rec.to_dict()
            if not behavior_dict.get(rec_dict['provider_type']):
                behavior_dict[rec_dict['provider_type']] = rec_dict['remark']
        return behavior_dict

    def copy_to_passenger(self):
        res = {
            'name': self.name,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'gender': self.gender,
            'birth_date': self.birth_date.strftime('%Y-%m-%d'),
            'nationality_id': self.nationality_id.id,
            'customer_id': self.id,
        }
        return res

    def create_or_update_customer_api(self,data,context):
        try:
            _logger.info('Create Customer API\n'+json.dumps(data))
            country_obj = self.env['res.country'].sudo()
            passenger_obj = self.env['tt.customer'].sudo()

            psg = data

            country = country_obj.search([('code', '=', psg.pop('nationality_code'))])
            psg['nationality_id'] = country and country[0].id or False

            get_psg_seq_id = util.get_without_empty(psg, 'seq_id','')
            if psg.get('face_image'):
                f_image = psg['face_image']
                if f_image[1] == 4:
                    image = self.env['tt.upload.center'].search([('seq_id','=',f_image[0])])
                    if image:
                        psg['face_image_id'] = image.id
                elif f_image[1] == 2:
                    psg['face_image_id'] = False

            if (get_psg_seq_id) != '':
                current_passenger = passenger_obj.search([('seq_id', '=', get_psg_seq_id)],limit=1)
                if current_passenger:
                    if psg.get('phone'):
                        [rec.update({'phone_number': '%s%s' % (rec['calling_code'],rec['calling_number']),
                                     'country_id': country and country[0].id or False})for rec in psg['phone']]
                        pop_phone_list = []
                        for phone in current_passenger.phone_ids:
                            phone_found = False
                            for idx,psg_phone in enumerate(psg['phone']):
                                if phone.phone_number == psg_phone:
                                    pop_phone_list.append(idx)
                                    phone_found = True
                            if not phone_found:
                                phone.unlink()
                        pop_phone_list.reverse()
                        for pop_index in pop_phone_list:
                            psg['phone'].pop(pop_index)

                        phone_list = []
                        for phone in psg['phone']:
                            phone_list.append((0,0,phone))
                        psg.pop('phone')
                        psg.update({'phone_ids':phone_list})
                    if 'face_image_id' in psg:
                        if current_passenger.face_image_id:
                            current_passenger.face_image_id.unlink()
                    if psg.get('title') == 'MRS':
                        psg['marital_status'] = 'married'

                    if psg.get('riz_text'):
                        psg['riz_text'] = psg['riz_text']

                    current_passenger.write(psg)
                    result_psg = current_passenger
                    if psg.get('identity'):
                        for key,identity in psg['identity'].items():
                            current_passenger.add_or_update_identity(identity)
                    if psg.get('ff_numbers'):
                        current_passenger.add_or_ff_number(psg['ff_numbers'])
                else:
                    raise RequestException(1024)
            else:
                util.pop_empty_key(psg)
                psg['ho_id'] = context['co_ho_id']
                psg['agent_id'] = context['co_agent_id']
                psg.update({
                    'customer_parent_ids': [(4, context.get('co_customer_parent_id'))] if context.get('co_customer_parent_id') else False,
                    'marital_status': 'married' if psg.get('title') == 'MRS' else '',
                })
                # if ada phone, kalau dari frontend cache passenger
                if psg.get('phone'):
                    phone_list = []
                    for phone in psg['phone']:
                        phone_list.append((0,0,{
                            'calling_code': phone['calling_code'],
                            'calling_number': phone['calling_number'],
                            'phone_number': '%s%s' % (phone['calling_code'], phone['calling_number']),
                            'country_id': country and country[0].id or False,
                            'ho_id': context['co_ho_id']
                        }))
                    psg.pop('phone')
                    psg.update({
                        'phone_ids': phone_list
                    })

                if psg.get('riz_text'):
                    psg.update({
                        'riz_text': psg['riz_text']
                    })

                psg_obj = passenger_obj.create(psg)
                result_psg = psg_obj
                if psg.get('identity'):
                    for identity_key, identity in psg['identity'].items():
                        if not identity.get('identity_first_name'):
                            identity.update({
                                'identity_first_name': psg['first_name'],
                                'identity_last_name': psg.get('last_name', '')
                            })
                        psg_obj.add_or_update_identity(identity)
                if psg.get('ff_numbers'):
                    psg_obj.add_or_ff_number(psg['ff_numbers'])

            return ERR.get_no_error(result_psg.to_dict())
        except:
            _logger.error(traceback.format_exc())
            return ERR.get_error(additional_message="Create or Update Customer Error")

    def get_customer_list_api(self,req,context):
        try:
            agent_id_list = [context['co_agent_id']]
            if context['co_agent_id'] == context['co_ho_id']:
                agent_id_list += self.env['tt.agent'].search([('is_share_cust_ho', '=', True)]).ids
            dom = [('agent_id','in',agent_id_list), ('is_search_allowed','=',True)]

            is_cor_login = util.get_without_empty(context,'co_customer_parent_id')
            cust_id_list_obj = []
            if util.get_without_empty(req,'name'):
                if util.get_without_empty(req,'search_type') == 'cor_name' and not is_cor_login:
                    cust_booker_objs = self.env['tt.customer.parent.booker.rel'].search([('customer_parent_id.name', 'ilike', req['name'])])
                    cust_dom_ids = []
                    for rec_book in cust_booker_objs:
                        if rec_book.customer_id.id not in cust_dom_ids:
                            cust_dom_ids.append(rec_book.customer_id.id)
                    dom.append(('id', 'in', cust_dom_ids))
                elif util.get_without_empty(req,'search_type') == 'seq_id':
                    dom.append(('seq_id', '=', req['name']))
                elif util.get_without_empty(req,'search_type') == 'mobile':
                    dom.append(('phone_ids.phone_number', '=', req['name']))
                elif util.get_without_empty(req,'search_type') == 'email':
                    dom.append(('email', '=', req['name']))
                elif util.get_without_empty(req,'search_type') == 'identity_type':
                    dom.append(('identity_ids.identity_number', '=', req['name']))
                elif util.get_without_empty(req,'search_type') == 'birth_date':
                    dom.append(('birth_date', '=', datetime.strptime(req['name'],'%Y-%m-%d')))
                else:
                    cust_id_list_obj = self.env['tt.customer.identity'].search(
                        [('identity_name', 'ilike', req['name'])])
                    dom.append(('name','ilike',req['name']))
            if req.get('email'):
                dom.append(('email','=',req['email']))
            if req.get('cust_code'):
                dom.append(('seq_id','=',req['cust_code']))
            if is_cor_login:
                cust_booker_objs = self.env['tt.customer.parent.booker.rel'].search([('customer_parent_id', '=', context['co_customer_parent_id'])])
                cust_dom_ids = []
                for rec_book in cust_booker_objs:
                    if rec_book.customer_id.id not in cust_dom_ids:
                        cust_dom_ids.append(rec_book.customer_id.id)
                dom.append('|')
                dom.append(('customer_parent_ids','=',context['co_customer_parent_id']))
                # dom.append(('booker_parent_ids','=',context['co_customer_parent_id']))
                dom.append(('id','in',cust_dom_ids))
            # customer_list_obj = self.search(dom,limit=100)
            customer_list_obj = self.search(dom)
            ## CASE IN TIDAK KELUAR TETAPI INF KELUAR
            ## KARENA RECORD YG INF TIDAK MASUK KE CUSTOMER_LIST_OBJ, KENA LIMIT JADI RECORD
            customer_list = []

            if req.get('departure_date'):
                upper = datetime.strptime(req['departure_date'], '%Y-%m-%d').date() - relativedelta(years=req.get('upper',200))
                lower = datetime.strptime(req['departure_date'], '%Y-%m-%d').date() - relativedelta(years=req.get('lower', 12))
            else:
                upper = date.today() - relativedelta(years=req.get('upper', 200))
                lower = date.today() - relativedelta(years=req.get('lower', 12))

            def filter_cust_age(cust_obj):
                ###fixme kalau tidak pbirth_date gimana? di asumsikan adult?
                if cust_obj.birth_date:
                    if not (upper <= cust_obj.birth_date <= lower):
                        return {}
                else:
                    if req.get('type') == 'psg' and req['upper'] <= 12:
                        return {}
                return cust_obj.to_dict(get_customer_parent=True)

            cust_blacklist_ids = []
            for cust in customer_list_obj:
                values = filter_cust_age(cust)
                if values:
                    cust_blacklist_ids.append(cust.id)
                    customer_list.append(values)
            for cust_id_obj in cust_id_list_obj:
                if cust_id_obj.customer_id.id not in cust_blacklist_ids:
                    values = filter_cust_age(cust_id_obj.customer_id)
                    if values:
                        cust_blacklist_ids.append(cust_id_obj.customer_id.id)
                        customer_list.append(values)
            return ERR.get_no_error(customer_list)
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error()

    def get_customer_customer_parent_list_api(self,req,context):
        try:
            dom = [('agent_id','=',context['co_agent_id']),
                   ('is_get_booking_from_vendor','=',False),
                   ('seq_id','=',req.get('seq_id'))]

            cust_obj = self.search(dom,limit=1)

            c_parent_list = []
            if cust_obj:
                if cust_obj.customer_parent_ids:
                    for rec in cust_obj.customer_parent_ids:
                        if rec.credit_limit != 0 and rec.state == 'done':
                            c_parent_list.append({
                                'name': rec.name,
                                'actual_balance': rec.actual_balance,
                                'credit_limit': rec.credit_limit,
                                'currency': rec.currency_id.name,
                                'seq_id': rec.seq_id,
                            })

            _logger.info(json.dumps(c_parent_list))
            return ERR.get_no_error(c_parent_list)
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error()

    def test_vals_cleaner(self):
        self.write({
            'nationality_id': 101,
            'gender': 'male',
            'email': 'twesting@gmail.com'
        })

    def add_or_ff_number(self, ff_list):
        not_exist = True
        error_msg = ''
        for idx, rec_ff in enumerate(ff_list):
            try:
                number = util.get_without_empty(rec_ff, 'ff_number', False)
                code = util.get_without_empty(rec_ff, 'ff_code', False)
            except:
                raise RequestException(1023, additional_message="Missing key ff.")

            for customer_ff in self.frequent_flyer_ids:
                if customer_ff.loyalty_program_id.code == code:
                    not_exist = False
                    break

            if not_exist:
                ## create new
                loyalty_program = self.env['tt.loyalty.program'].search([('code', '=', code)])
                loyalty_program_id = loyalty_program and loyalty_program[0].id or False
                if loyalty_program_id:
                    create_vals = {
                        'ff_number': number,
                        'loyalty_program_id': loyalty_program_id,
                        'customer_id': self.id,
                    }
                    self.env['tt.customer.frequent.flyer'].create(create_vals)
            else:
                ## update jika ada pasti di customer_ff karena di break
                customer_ff.update({
                    "ff_number": number
                })

    def add_or_update_identity(self,data):
        not_exist = True
        try:
            number = data['identity_number']
            type = data['identity_type']
            first_name = util.get_without_empty(data,'identity_first_name', '')
            last_name = util.get_without_empty(data,'identity_last_name', '')
            expdate = util.get_without_empty(data,'identity_expdate',False)
            c_issued_id = util.get_without_empty(data,'identity_country_of_issued_code',False)
            image_seqs = data.get('identity_image',[])
        except:
            raise RequestException(1023,additional_message="Missing key.")

        for identity in self.identity_ids:
            if identity.identity_type == type:
                not_exist = False
                exixting_identity = identity
                break

        if c_issued_id:
            country = self.env['res.country'].search([('code', '=', c_issued_id)])
            c_issued_id = country and country[0].id or False
            if not c_issued_id:
                raise RequestException(1023,additional_message="Country not found.")

        #convet seq_id to id
        image_ids = []
        if image_seqs:
            for seq in image_seqs:
                action = False
                ##supaya tidak di inject action aneh dari luar
                if seq[1] == 4:
                    action = 4
                elif seq[1] == 3:
                    action = 3
                elif seq[1] == 2:
                    action = 2
                if not action:
                    raise RequestException(1023,additional_message="Wrong Upload Action")
                image_obj = self.env['tt.upload.center'].search([('seq_id', '=', seq[0])], limit=1)
                try:
                    image_obj.create_date
                    image_ids.append((action,image_obj.id))
                except:
                    _logger.error("Error linking Customer Identity Image, UPC not found")

        if not_exist:
            create_vals = {
                'identity_type': type,
                'identity_number': number,
                'identity_first_name': first_name,
                'identity_last_name': last_name,
                'identity_country_of_issued_id': c_issued_id,
                'identity_expdate': expdate,
                'customer_id': self.id,
            }
            if image_ids:
                create_vals.update({'identity_image_ids':image_ids})
            self.env['tt.customer.identity'].create(create_vals)
        else:
            update_vals = {}
            if number != exixting_identity.identity_number:
                update_vals.update({
                    'identity_number': number
                })
            if c_issued_id != exixting_identity.identity_country_of_issued_id.id:
                update_vals.update({
                    'identity_country_of_issued_id': c_issued_id
                })
            if expdate != exixting_identity.identity_expdate:
                update_vals.update({
                    'identity_expdate': expdate
                })
            if first_name and first_name != exixting_identity.identity_first_name:
                update_vals.update({
                    'identity_first_name': first_name
                })
            # cek first_name supaya bisa hapus last_name
            if first_name and last_name != exixting_identity.identity_last_name:
                update_vals.update({
                    'identity_last_name': last_name
                })
            if image_ids:
                update_vals.update({'identity_image_ids':image_ids})
            exixting_identity.write(update_vals)

    @api.model
    def customer_action_view_customer(self):
        action = self.env.ref('tt_base.tt_customer_action_view').read()[0]
        action['context'] = {
            'form_view_ref': 'tt_base.tt_customer_form_view_customer',
            'tree_view_ref': 'tt_base.tt_customer_tree_view_customer',
            'default_agent_id': self.env.user.agent_id.id
        }
        action['domain'] = [('agent_id', '=', self.env.user.agent_id.id)]
        return action
        # return {
        #     'name': 'Customer',
        #     'type': 'ir.actions.act_window',
        #     'view_type': 'form',
        #     'view_mode': 'tree,form',
        #     'res_model': 'tt.customer',
        #     'views': [(self.env.ref('tt_base.tt_customer_tree_view_customer').id, 'tree'),
        #               (self.env.ref('tt_base.tt_customer_form_view_customer').id, 'form')],
        #     'context': {
        #         'default_agent_id': self.env.user.agent_id.id
        #     },
        #     'domain': [('agent_id', '=', self.env.user.agent_id.id)]
        # }

    def create_customer_user_api(self, data, context):
        try:
            # Create Agent B2C
            name = (data['first_name'] or '') + ' ' + (data.get('last_name') or '')
            ho_parent_obj = self.env['tt.agent'].browse(int(context['co_ho_id']))
            vals_list = {
                'ho_id': ho_parent_obj.id,
                'agent_type_id': ho_parent_obj.btc_agent_type_id.id,
                'parent_agent_id': context['co_ho_id'],
                'name': name,
                'email': data.get('email'),
                'is_send_email_cust': True
            }
            agent_id = self.env['tt.agent'].create(vals_list)

            # Load Template User B2C
            user_dict = self.env.ref('tt_base.template_btc_agent_user').read()
            # user id vals
            vals = {
                'name': name,
                'login': data.get('email'),
                'email': data.get('email'),
                'password': ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16)),
                'ho_id': ho_parent_obj.id,
                'agent_id': agent_id.id
            }

            # Set Groups & Frontend Security
            if user_dict:
                vals.update({
                    'groups_id': [(6, 0, user_dict[0]['groups_id'])],
                    'frontend_security_ids': [(6, 0, user_dict[0]['frontend_security_ids'])]
                })

            # Create User
            user_res = self.create_user_res(vals)
            if user_res['error_code'] != 0:
                raise RequestException(500, additional_message=user_res['error_msg'])

            # Create User B2C
            res = ERR.get_no_error()
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            res = Response().get_error(str(e), 500)
        return res

    def create_user_res(self, vals):
        login_exists = self.env['res.users'].search([('login', '=', vals.get('login'))])
        if login_exists:
            return {
                'error_code': 500,
                'error_msg': 'Create user error. User exists.'
            }
        if 'login' not in vals:
            return {
                'error_code': 500,
                'error_msg': 'Create User Error. You must input an email.'
            }
        if 'password' not in vals:
            return {
                'error_code': 500,
                'error_msg': 'Create User Error. You must input a password.'
            }
        user_id = self.env['res.users'].create(vals)
        res = Response().get_no_error(user_id)
        return res

    def compute_darmo_customer(self):
        self.compute_register_uid(8)

    def compute_ptc_customer(self):
        self.compute_register_uid(155)

    def compute_japro_b_customer(self):
        self.compute_register_uid(5)

    def compute_register_uid(self,agent_id):
        customers_obj = self.search([('agent_id','=',agent_id)])
        for rec in customers_obj:
            #airline

            _logger.info("#Airline\nCustomer OBJ : " + str(rec.id))
            psg_air_obj = self.env['tt.reservation.passenger.airline'].search([('customer_id','=',rec.id)],order= 'id asc')
            _logger.info("Passenger IDS : " + str(psg_air_obj.ids))
            psg_air_obj = psg_air_obj.filtered(lambda x: x.booking_id.id != False)
            _logger.info("Passenger IDS : " + str(psg_air_obj.ids))

            if psg_air_obj:
                user_id = psg_air_obj[0].booking_id.user_id
                _logger.info("Set Register UID to : %s\n\n" % (user_id.name) )
                rec.register_uid = user_id.id
            else:
                _logger.info("Skip Register UID, no Transaction\n\n")

            _logger.info("#Train\nCustomer OBJ : " + str(rec.id))
            psg_air_obj = self.env['tt.reservation.passenger.train'].search([('customer_id','=',rec.id)],order= 'id asc')
            _logger.info("Passenger IDS : " + str(psg_air_obj.ids))
            psg_air_obj = psg_air_obj.filtered(lambda x: x.booking_id.id != False)
            _logger.info("Passenger IDS : " + str(psg_air_obj.ids))

            if psg_air_obj:
                user_id = psg_air_obj[0].booking_id.user_id
                _logger.info("Set Register UID to : %s\n\n" % (user_id.name) )
                rec.register_uid = user_id.id
            else:
                _logger.info("Skip Register UID, no Transaction\n\n")

    def create_or_update_customer_bitrix(self, data, context):
        return ERR.get_no_error()

    def add_behavior(self, provider_type, remark='', is_need_delete=False):
        try:
            if remark or is_need_delete:
                is_behavior_found = False
                for behavior_obj in self.behavior_ids:
                    if provider_type.lower() == behavior_obj.provider_type_id.code.lower(): ## di lower mungkin ada data lama agar tidak error
                        behavior_obj.update({
                            "remark": remark,
                        })
                        is_behavior_found = True

                if not is_behavior_found:
                    self.env['tt.customer.behavior'].create({
                        "customer_id": self.id,
                        "provider_type_id": self.env['tt.provider.type'].search([('code','=',provider_type)],limit=1).id,
                        "remark": remark
                    })
        except Exception as e:
            _logger.error("%s, %s" % (str(e), traceback.format_exc()))

class TtCustomerIdentityNumber(models.Model):
    _name = "tt.customer.identity"
    _description = "Customer Identity Type"
    _rec_name = "identity_type"

    identity_first_name = fields.Char('First Name')
    identity_last_name = fields.Char('Last Name')
    identity_name = fields.Char('Name', compute='_compute_identity_name', store=True)
    identity_type = fields.Selection(variables.IDENTITY_TYPE,'Type',required=True)
    identity_number = fields.Char('Number',required=True)
    identity_expdate = fields.Date('Expire Date')
    identity_country_of_issued_id = fields.Many2one('res.country','Issued Country')
    identity_image_ids = fields.Many2many('tt.upload.center','tt_customer_identity_upload_center_rel','identity_id','upload_id','Uploads')

    customer_id = fields.Many2one('tt.customer','Owner',required=True)

    def create(self, vals_list):
        new_identity = super(TtCustomerIdentityNumber, self).create(vals_list)
        ##validator tidak kembar
        if len(new_identity.ids) >1:
            identity = new_identity[0]
        else:
            identity = new_identity

        identity_list = identity.customer_id.identity_ids
        for id1 in identity_list:
            for id2 in identity_list:
                if id1.identity_type == id2.identity_type and id1.id != id2.id:
                    raise UserError ('%s|%s Already Exists.' % (id1.id,id1.identity_type))

        return new_identity

    @api.depends('identity_first_name', 'identity_last_name')
    def _compute_identity_name(self):
        for rec in self:
            rec.identity_name = '%s%s' % (rec.identity_first_name, rec.identity_last_name and ' ' + rec.identity_last_name or '')

    def to_dict(self):
        image_list = [(rec.url,rec.seq_id,rec.file_reference, rec.create_date.strftime('%Y-%m-%d %H:%M:%S')) for rec in self.identity_image_ids]
        return {
            self.identity_type:{
                'identity_number': self.identity_number,
                'identity_first_name': self.identity_first_name and self.identity_first_name or '',
                'identity_last_name': self.identity_last_name and self.identity_last_name or '',
                'identity_expdate': self.identity_expdate and self.identity_expdate.strftime('%Y-%m-%d') or '',
                'identity_country_of_issued_name': self.identity_country_of_issued_id and self.identity_country_of_issued_id.name or '',
                'identity_country_of_issued_code': self.identity_country_of_issued_id and self.identity_country_of_issued_id.code or '',
                'identity_images': image_list
            }
        }

class TtCustomerBehavior(models.Model):
    _name = "tt.customer.behavior"
    _description = "Customer Behavior"

    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')
    customer_id = fields.Many2one('tt.customer', 'Owner', required=True)
    remark = fields.Char('Additional Information')

    def to_dict(self):
        return {
            "provider_type": self.provider_type_id.code,
            "remark": self.remark
        }

class TtCustomerFrequentFlyer(models.Model):
    _name = "tt.customer.frequent.flyer"
    _description = "Customer Frequent Flyer"
    # _rec_name = "behavior_type"

    loyalty_program_id = fields.Many2one('tt.loyalty.program', 'Loyalty Program')
    ff_number = fields.Char('Frequent Flyer Number')
    customer_id = fields.Many2one('tt.customer', 'Owner', required=True)

    def to_dict(self):
        ff_list = []
        for rec in self:
            ff_list.append({
                "ff_code": rec.loyalty_program_id.code,
                "ff_number": rec.ff_number
            })
        return ff_list