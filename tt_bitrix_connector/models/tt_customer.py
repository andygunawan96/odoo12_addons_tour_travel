from odoo import models, fields, api
import logging,traceback
import json
from ...tools import variables,util,ERR
from ..bitrix_models.tt_bitrix_connector import BitrixContact

_logger = logging.getLogger(__name__)


class TtCustomer(models.Model):
    _inherit = 'tt.customer'

    @api.model
    def create(self, vals):
        cust_obj = super(TtCustomer, self).create(vals)
        if cust_obj.agent_id.is_using_bitrix and self.env['ir.config_parameter'].sudo().get_param('use.bitrix.contact') == 'True' and not vals.get('webhook_from_bitrix'):
            try:
                gender_conv = {
                    'male': 72,
                    'female': 73
                }

                marital_status_conv = {
                    'single': 27,
                    'married': 28,
                    'divorced': 29,
                    'widowed': 30,
                }

                religion_conv = {
                    'islam': 31,
                    'protestantism': 32,
                    'catholicism': 33,
                    'hinduism': 34,
                    'buddhism': 35,
                    'confucianism': 36,
                }

                identity_conv = {
                    'ktp': 38,
                    'sim': 39,
                    'passport': 131,
                    'other': 132,
                }

                first_name = vals.get('first_name') and vals['first_name'] or ''
                last_name = vals.get('last_name') and vals['last_name'] or ''
                agent = vals.get('agent_id') and self.env['tt.agent'].browse(int(vals['agent_id'])).name or ''

                emailfield = []
                emailvals = {
                    "VALUE": vals.get('email') and vals.get('email') or False,
                    "VALUE_TYPE": "WORK"
                }
                emailfield.append(emailvals)

                address_list = []
                for rec in cust_obj.address_ids:
                    temp_address = rec.address and rec.address or ''
                    if temp_address:
                        if rec.rt:
                            temp_address += ' RT ' + str(rec.rt)
                        if rec.rw:
                            temp_address += ' RW ' + rec.rw
                    address_list.append({
                        'address': temp_address,
                        'postal_code': rec.zip and rec.zip or '',
                        'city': rec.city_id and rec.city_id.name or '',
                        'state': rec.state_id and rec.state_id.name or '',
                        'country': rec.country_id and rec.country_id.name or '',
                        'country_code': rec.country_id and rec.country_id.code or '',
                    })

                phone_list = []
                for rec in cust_obj.phone_ids:
                    phone_type_conv = {
                        'work': 'WORK',
                        'home': 'HOME',
                        'other': 'OTHER'
                    }
                    phone_list.append({
                        'VALUE': (rec.calling_code and rec.calling_code or '') + (rec.calling_number and rec.calling_number or ''),
                        'VALUE_TYPE': rec.type and phone_type_conv[rec.type] or '',
                    })

                temp_identity_type = False
                temp_identity_num = ''
                identity_list = []
                for rec in cust_obj.identity_ids:
                    if rec.identity_type == 'ktp':
                        temp_identity_type = identity_conv[rec.identity_type]
                        temp_identity_num = rec.identity_number
                    identity_list.append({
                        'identity_type': identity_conv[rec.identity_type],
                        'identity_number': rec.identity_number
                    })

                if not temp_identity_type:
                    temp_identity_type = identity_list and identity_list[0]['identity_type'] or False,
                    temp_identity_num = identity_list and identity_list[0]['identity_number'] or ''

                gender = vals.get('gender') and gender_conv[vals['gender']] or False
                marital = vals.get('marital_status') and marital_status_conv[vals['marital_status']] or False
                religion = vals.get('religion') and religion_conv[vals['religion']] or False

                contact_fields = {
                    'NAME': first_name,
                    'LAST_NAME': last_name,
                    'ADDRESS': address_list and address_list[0]['address'] or '',
                    'ADDRESS_POSTAL_CODE': address_list and address_list[0]['postal_code'] or '',
                    'ADDRESS_CITY': address_list and address_list[0]['city'] or '',
                    'ADDRESS_PROVINCE': address_list and address_list[0]['state'] or '',
                    'ADDRESS_COUNTRY': address_list and address_list[0]['country'] or '',
                    'ADDRESS_COUNTRY_CODE': address_list and address_list[0]['country_code'] or '',
                    'UF_CRM_1529548344555': address_list and (address_list[0]['address'] + ' ' + address_list[0]['postal_code'] + ', ' + address_list[0]['city'] + ', ' + address_list[0]['state'] + ', ' + address_list[0]['country']) or '',
                    'BIRTHDATE': vals.get('birth_date') and vals['birth_date'].strftime('%Y-%m-%d') or False,
                    'EMAIL': emailfield,
                    'UF_CRM_1529549610946': vals.get('nationality_id') and self.env['res.country'].browse(int(vals['nationality_id'])).name or '',
                    'ASSIGNED_BY_ID': 97,
                    'PHONE': phone_list,
                    'UF_CRM_1586761168': cust_obj.id,
                    'UF_CRM_1586920969': cust_obj.seq_id and cust_obj.seq_id or '',
                    'UF_CRM_1532507009': agent,
                    'UF_CRM_5C3EB7BF2AD44': gender,
                    'UF_CRM_1529548076671': marital,
                    'UF_CRM_1529548307310': religion,
                    'UF_CRM_1529549538070': temp_identity_type,
                    'UF_CRM_1529549568200': temp_identity_num
                }
                bx = BitrixContact()
                req = {
                    'FIELDS': contact_fields,
                }
                bx.AddContact(req)

            except Exception as e:
                _logger.error('Error: Failed to create Bitrix Contact data. \n %s : %s' % (traceback.format_exc(), str(e)))
        return cust_obj

    @api.multi
    def write(self, vals):
        res = super(TtCustomer, self).write(vals)
        if self.agent_id.is_using_bitrix and self.env['ir.config_parameter'].sudo().get_param('use.bitrix.contact') == 'True' and not vals.get('webhook_from_bitrix'):
            try:
                gender_conv = {
                    'male': 72,
                    'female': 73
                }

                marital_status_conv = {
                    'single': 27,
                    'married': 28,
                    'divorced': 29,
                    'widowed': 30,
                }

                religion_conv = {
                    'islam': 31,
                    'protestantism': 32,
                    'catholicism': 33,
                    'hinduism': 34,
                    'buddhism': 35,
                    'confucianism': 36,
                }

                identity_conv = {
                    'ktp': 38,
                    'sim': 39,
                    'passport': 131,
                    'other': 132,
                }

                emailfield = []
                if self.email:
                    emailvals = {
                        "VALUE": self.email,
                        "VALUE_TYPE": "WORK"
                    }
                    emailfield.append(emailvals)

                address_list = []
                for rec in self.address_ids:
                    temp_address = rec.address and rec.address or ''
                    if temp_address:
                        if rec.rt:
                            temp_address += ' RT ' + str(rec.rt)
                        if rec.rw:
                            temp_address += ' RW ' + rec.rw
                    address_list.append({
                        'address': temp_address,
                        'postal_code': rec.zip and rec.zip or '',
                        'city': rec.city_id and rec.city_id.name or '',
                        'state': rec.state_id and rec.state_id.name or '',
                        'country': rec.country_id and rec.country_id.name or '',
                        'country_code': rec.country_id and rec.country_id.code or '',
                    })

                phone_list = []
                for rec in self.phone_ids:
                    phone_type_conv = {
                        'work': 'WORK',
                        'home': 'HOME',
                        'other': 'OTHER'
                    }
                    phone_list.append({
                        'VALUE': (rec.calling_code and rec.calling_code or '') + (
                                    rec.calling_number and rec.calling_number or ''),
                        'VALUE_TYPE': rec.type and phone_type_conv[rec.type] or '',
                    })

                temp_identity_type = False
                temp_identity_num = ''
                identity_list = []
                for rec in self.identity_ids:
                    if rec.identity_type == 'ktp':
                        temp_identity_type = identity_conv[rec.identity_type]
                        temp_identity_num = rec.identity_number
                    identity_list.append({
                        'identity_type': identity_conv[rec.identity_type],
                        'identity_number': rec.identity_number
                    })

                if not temp_identity_type:
                    temp_identity_type = identity_list and identity_list[0]['identity_type'] or False,
                    temp_identity_num = identity_list and identity_list[0]['identity_number'] or ''

                contact_fields = {
                    'NAME': self.first_name and self.first_name or '',
                    'LAST_NAME': self.last_name and self.last_name or '',
                    'ADDRESS': address_list and address_list[0]['address'] or '',
                    'ADDRESS_POSTAL_CODE': address_list and address_list[0]['postal_code'] or '',
                    'ADDRESS_CITY': address_list and address_list[0]['city'] or '',
                    'ADDRESS_PROVINCE': address_list and address_list[0]['state'] or '',
                    'ADDRESS_COUNTRY': address_list and address_list[0]['country'] or '',
                    'ADDRESS_COUNTRY_CODE': address_list and address_list[0]['country_code'] or '',
                    'UF_CRM_1529548344555': address_list and (address_list[0]['address'] + ' ' + address_list[0]['postal_code'] + ', ' + address_list[0]['city'] + ', ' + address_list[0]['state'] + ', ' + address_list[0]['country']) or '',
                    'BIRTHDATE': self.birth_date and self.birth_date.strftime('%Y-%m-%d') or '',
                    'EMAIL': emailfield,
                    'UF_CRM_1529549610946': self.nationality_id and self.nationality_id.name or '',
                    'PHONE': phone_list,
                    'UF_CRM_1586761168': self.id,
                    'UF_CRM_1586920969': self.seq_id,
                    'UF_CRM_1532507009': self.agent_id.name,
                    'UF_CRM_5C3EB7BF2AD44': self.gender and gender_conv[self.gender] or '',
                    'UF_CRM_1529548076671': self.marital_status and marital_status_conv[self.marital_status] or '',
                    'UF_CRM_1529548307310': self.religion and religion_conv[self.religion] or '',
                    'UF_CRM_1529549538070': temp_identity_type,
                    'UF_CRM_1529549568200': temp_identity_num
                }
                bx = BitrixContact()
                contact_params = {
                    'ORDER': {'ID': 'ASC'},
                    'FILTER': {'UF_CRM_1586761168': self.id},
                    'SELECT': ['ID', 'NAME', 'UF_CRM_1586761168'],
                }
                contacts = bx.SelectContact(contact_params)
                bitrix_con_id = 0
                if contacts['response']:
                    for rec in json.loads(contacts['response'])['result']:
                        bitrix_con_id = rec['ID']
                req = {
                    'ID': bitrix_con_id,
                    'FIELDS': contact_fields,
                }
                bx.UpdateContact(req)
            except Exception as e:
                _logger.error('Error: Failed to update Bitrix Contact data. \n %s : %s' % (traceback.format_exc(), str(e)))
        return res

    def create_or_update_customer_bitrix(self, data, context):
        try:
            gender_conv = {
                '72': 'male',
                '73': 'female'
            }

            marital_status_conv = {
                '27': 'single',
                '28': 'married',
                '29': 'divorced',
                '30': 'widowed',
            }

            religion_conv = {
                '31': 'islam',
                '32': 'protestantism',
                '33': 'catholicism',
                '34': 'hinduism',
                '35': 'buddhism',
                '36': 'confucianism',
            }

            identity_conv = {
                '38': 'ktp',
                '39': 'sim',
                '131': 'passport',
                '132': 'other',
            }

            bx = BitrixContact()
            contact_params = {
                'ORDER': {'ID': 'ASC'},
                'FILTER': {'ID': data['data[FIELDS][ID]']},
                'SELECT': ['ID', 'NAME', 'LAST_NAME', 'ADDRESS', 'ADDRESS_POSTAL_CODE',
                           'ADDRESS_CITY', 'ADDRESS_PROVINCE', 'ADDRESS_COUNTRY', 'ADDRESS_COUNTRY_CODE', 'BIRTHDATE',
                           'EMAIL', 'UF_CRM_1529549610946', 'PHONE', 'UF_CRM_1586761168', 'UF_CRM_1586920969',
                           'UF_CRM_1532507009', 'UF_CRM_5C3EB7BF2AD44', 'UF_CRM_1529548076671', 'UF_CRM_1529548307310',
                           'UF_CRM_1529549538070', 'UF_CRM_1529549568200'],
            }
            contacts = bx.SelectContact(contact_params)
            if contacts['response']:
                for rec in json.loads(contacts['response'])['result']:
                    vals = {
                        'webhook_from_bitrix': True,
                        'rdx_id': rec.get('UF_CRM_1586761168') and rec['UF_CRM_1586761168'] or False,
                        'first_name': rec.get('NAME') and rec['NAME'] or '',
                        'last_name': rec.get('LAST_NAME') and rec['LAST_NAME'] or '',
                        'birth_date': rec.get('BIRTHDATE') and rec['BIRTHDATE'] or False,
                        'email': rec.get('EMAIL') and rec['EMAIL'] or '',
                        'gender': rec.get('UF_CRM_5C3EB7BF2AD44') and gender_conv[str(rec['UF_CRM_5C3EB7BF2AD44'])] or '',
                        'marital_status': rec.get('UF_CRM_1529548076671') and marital_status_conv[str(rec['UF_CRM_1529548076671'])] or '',
                        'religion': rec.get('UF_CRM_1529548307310') and religion_conv[str(rec['UF_CRM_1529548307310'])] or '',
                    }
                    if data['event'] == 'ONCRMCONTACTADD' or not vals.get('rdx_id'):
                        vals.get('rdx_id') and vals.pop('rdx_id')
                        new_bitrix_cust = self.sudo().create(vals)
                        req = {
                            'ID': rec['ID'],
                            'FIELDS': {
                                'UF_CRM_1586761168': new_bitrix_cust.id,
                                'UF_CRM_1586920969': new_bitrix_cust.seq_id
                            },
                        }
                        bx.UpdateContact(req)
                    elif data['event'] == 'ONCRMCONTACTUPDATE':
                        cust_obj = self.sudo().browse(int(vals['rdx_id']))
                        vals.pop('rdx_id')
                        cust_obj.sudo().write(vals)
            return ERR.get_no_error()
        except:
            _logger.error(traceback.format_exc())
            return ERR.get_error(additional_message="Create or Update Customer Bitrix Error")
