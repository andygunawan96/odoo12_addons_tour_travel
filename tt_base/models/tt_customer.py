from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime,date
from dateutil.relativedelta import relativedelta
from odoo.tools import image
from ...tools import variables,util,ERR
from ...tools.ERR import RequestException
import json,time
import logging,traceback

_logger = logging.getLogger(__name__)

class TtCustomer(models.Model):
    _inherit = 'tt.history'
    _name = 'tt.customer'
    _rec_name = 'name'
    _description = 'Tour & Travel - Customer'

    seq_id = fields.Char('ID', index=True,readonly=True)
    name = fields.Char(string='Name', compute='_compute_name', store=True)
    face_image_id = fields.Many2one('tt.upload.center','Face Image')
    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    gender = fields.Selection(variables.GENDER, string='Gender')
    marital_status = fields.Selection(variables.MARITAL_STATUS, 'Marital Status')
    religion = fields.Selection(variables.RELIGION, 'Religion')
    birth_date = fields.Date('Birth Date')
    nationality_id = fields.Many2one('res.country', 'Nationality')
    address_ids = fields.One2many('address.detail', 'customer_id', 'Address Detail')
    phone_ids = fields.One2many('phone.detail', 'customer_id', 'Phone Detail')
    social_media_ids = fields.One2many('social.media.detail', 'customer_id', 'Social Media Detail')
    email = fields.Char('Email')
    user_ids = fields.One2many('res.users', 'customer_id', 'User')
    customer_bank_detail_ids = fields.One2many('customer.bank.detail', 'customer_id', 'Customer Bank Detail')
    agent_id = fields.Many2one('tt.agent', 'Agent')  # , default=lambda self: self.env.user.agent_id
    # user_agent_id = fields.Many2one('tt.agent', 'Agent User', default=lambda self: self.env.user.agent_id)
    customer_parent_ids = fields.Many2many('tt.customer.parent','tt_customer_customer_parent_rel','customer_id','customer_parent_id','Customer Parent')

    active = fields.Boolean('Active', default=True)

    identity_ids = fields.One2many('tt.customer.identity','customer_id','Identity List')

    @api.depends('first_name', 'last_name')
    def _compute_name(self):
        for rec in self:
            rec.name = "%s %s" % (rec.first_name and rec.first_name or '', rec.last_name and rec.last_name or '')

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
        util.pop_empty_key(vals_list)
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('tt.customer')
        return super(TtCustomer, self).create(vals_list)

    def to_dict(self):
        phone_list = []
        for rec in self.phone_ids:
            phone_list.append(rec.to_dict())
        identity_dict = {}
        for rec in self.identity_ids:
            identity_dict.update(rec.to_dict())

        res = {
            'name': self.name,
            'first_name': self.first_name,
            'face_image': self.face_image_id and [self.face_image_id.url,self.face_image_id.seq_id] or [],
            'last_name': self.last_name and self.last_name or '',
            'gender': self.gender and self.gender or '',
            'birth_date': self.birth_date and self.birth_date.strftime('%Y-%m-%d') or '',
            'nationality_code': self.nationality_id and self.nationality_id.code or '',
            'nationality_name': self.nationality_id and self.nationality_id.name or '',
            'marital_status': self.marital_status and self.marital_status or '',
            'phones': phone_list,
            'email': self.email and self.email or '',
            'seq_id': self.seq_id,
            'identities': identity_dict
        }
        return res

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
                            for idx,psg_phone in enumerate(psg['phone']):
                                if phone.phone_number == psg_phone:
                                    pop_phone_list.append(idx)
                                    continue
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
                    current_passenger.write(psg)
                    result_psg = current_passenger
                    if psg.get('identity'):
                        for key,identity in psg['identity'].items():
                            current_passenger.add_or_update_identity(identity)
                else:
                    raise RequestException(1024)
            else:
                util.pop_empty_key(psg)
                psg['agent_id'] = context['co_agent_id']
                agent_obj = self.env['tt.agent'].sudo().browse(context['co_agent_id'])
                psg.update({
                    'customer_parent_ids': [(4, agent_obj.customer_parent_walkin_id.id)],
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
                        }))
                    psg.pop('phone')
                    psg.update({
                        'phone_ids': phone_list
                    })
                psg_obj = passenger_obj.create(psg)
                result_psg = psg_obj
                if psg.get('identity'):
                    for identity_key, identity in psg['identity'].items():
                        psg_obj.add_or_update_identity(identity)

            return ERR.get_no_error(result_psg.to_dict())
        except:
            _logger.error(traceback.format_exc())
            return ERR.get_error(additional_message="Create or Update Customer Error")

    def get_customer_list_api(self,req,context):
        try:
            print("request teropong\n"+json.dumps((req))+json.dumps(context))
            dom = [('agent_id','=',context['co_agent_id'])]

            if util.get_without_empty(req,'name'):
                dom.append(('name','ilike',req['name']))
            if req.get('email'):
                dom.append(('email','=',req['email']))
            if req.get('cust_code'):
                dom.append(('seq_id','=',req['cust_code']))

            customer_list_obj = self.search(dom)

            customer_list = []
            lower = date.today() - relativedelta(years=req.get('lower',12))
            upper = date.today() - relativedelta(years=req.get('upper',200))

            for cust in customer_list_obj:
                ###fixme kalau tidak pbirth_date gimana? di asumsikan adult?
                if cust.birth_date:
                    if not (upper <= cust.birth_date <= lower):
                        continue
                else:
                    if req.get('type') == 'psg' and req['lower']<12:
                        continue
                values = cust.to_dict()
                customer_list.append(values)
            _logger.info(json.dumps(customer_list))
            return ERR.get_no_error(customer_list)
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error()

    def add_identity_button(self):
        self.add_or_update_identity('sim',time.time(),157,'2024-09-01')

    def test_vals_cleaner(self):
        self.write({
            'nationality_id': 101,
            'gender': 'male',
            'email': 'twesting@gmail.com'
        })
        # self.add_or_update_identity('sim','BBBBB',157,'2024-09-01')

    def add_or_update_identity(self,data):
        not_exist =True
        try:
            number = data['identity_number']
            type = data['identity_type']
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
                image_ids.append((action,self.env['tt.upload.center'].search([('seq_id','=',seq[0])],limit=1).id))

        if not_exist:
            create_vals = {
                'identity_type': type,
                'identity_number': number,
                'identity_country_of_issued_id': c_issued_id,
                'identity_expdate': expdate,
                'customer_id': self.id,
            }
            if image_ids:
                create_vals.update({'identity_image_ids':image_ids})
            self.env['tt.customer.identity'].create(create_vals)
        else:
            update_vals = {
                'identity_number': number,
                'identity_country_of_issued_id': c_issued_id,
                'identity_expdate': expdate
            }
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



class TtCustomerIdentityNumber(models.Model):
    _name = "tt.customer.identity"
    _description = "Customer Identity Type"
    _rec_name = "identity_type"

    identity_type = fields.Selection(variables.IDENTITY_TYPE,'Type',required=True)
    identity_number = fields.Char('Number',required=True)
    identity_expdate = fields.Date('Expire Date')
    identity_country_of_issued_id = fields.Many2one('res.country','Issued  Country')
    identity_image_ids = fields.Many2many('tt.upload.center','tt_customer_identity_upload_center_rel','identity_id','upload_id','Uploads')

    customer_id = fields.Many2one('tt.customer','Owner')

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
    
    def write(self, vals):
        # util.vals_cleaner(vals,self)
        super(TtCustomerIdentityNumber, self).write(vals)
        
    def to_dict(self):
        image_list = [(rec.url,rec.seq_id) for rec in self.identity_image_ids]
        return {
            self.identity_type:{
                'identity_number': self.identity_number,
                'identity_expdate': self.identity_expdate and self.identity_expdate.strftime('%Y-%m-%d') or '',
                'identity_country_of_issued_name': self.identity_country_of_issued_id and self.identity_country_of_issued_id.name or '',
                'identity_country_of_issued_code': self.identity_country_of_issued_id and self.identity_country_of_issued_id.code or '',
                'identity_images': image_list
            }
        }