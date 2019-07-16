param_contact_data = {
        "city": "Surabaya",
        "first_name": "Edy",
        "last_name": "Kend",
        "home_phone": "8123574874",
        "nationality_code": "ID--62",
        "title": "MR",
        "mobile": "8123574874",
        "province_state": "Jawa Timur",
        "contact_id": "2",
        "work_phone": "6231-5662000",
        "postal_code": 0,
        "agent_id": "4",
        "country_code": "ID",
        "address": "Jl. Raya Darmo 177B",
        "other_phone": "6231-5662000",
        "email": "paleleh@gmail.com"
    }

param_passengers = [
        {
            "first_name": "Edy",
            "last_name": "Kend",
            "passenger_type": "ADT",
            "nationality_code": "ID",
            "title": "MR",
            "domicile": "ffsdfsdf",
            "visa_id": 869,
            "birth_date": "2000-03-04",
            "pricelist_id": 1,
            "passenger_id": "5"
        },
        {
            "first_name": "Edy",
            "last_name": "Kend",
            "passenger_type": "ADT",
            "nationality_code": "ID",
            "title": "MR",
            "domicile": "asdasd",
            "visa_id": 870,
            "birth_date": "2000-03-04",
            "pricelist_id": 1,
            "passenger_id": "5"
        }
    ]

param_service_charge_summary = [
    {
        "charge_type": "fare",
        "description": "Visa Japan",
        "charge_code": "fare",
        "amount": 1900000.0,
        "currency": "IDR",
        "foreign_currency": "IDR",
        "pax_count": 1,
        "passenger_type": "ADT",
        "pricelist_id": 1,
        "foreign_amount": 0
    },
    {
        "charge_type": "fare",
        "description": "Visa Japan",
        "charge_code": "fare",
        "amount": 1910000.0,
        "currency": "IDR",
        "foreign_currency": "IDR",
        "pax_count": 1,
        "passenger_type": "ADT",
        "pricelist_id": 1,
        "foreign_amount": 0,
        "visa_type": "Tourist",
        "entry_type": "Single",
    }
]

param_search_req = {
    "origin": "",
    "infant": 0,
    "uid": 1,
    "visa_ids": "869,870,",
    "departure_date": "2017-12-09",
    "destination": "",
    "country_id": "113",
    "direction": "OW",
    "search_type": "",
    "state": "draft",
    "transport_type": "visa",
    "adult": 1,
    "child": 0,
    "sid": "909a3a2f19050775964845ed83ce6a074b53a92c",
    "loaded": False,
    "class_of_service": "Y",
    "provider": "ALL",
    "return_date": False,
    "pax_count": "1,1,"
}

param_context = {
    "co_uid": 7  # co_uid akan menentukan agent yang membuat order visa
}

param_kwargs = {
    "force_issued": True
}

def create_booking_visa(self):
    contact_data = copy.deepcopy(self.param_contact_data)
    passengers = copy.deepcopy(self.param_passengers)
    service_charge_summary = copy.deepcopy(self.param_service_charge_summary)
    search_req = copy.deepcopy(self.param_search_req)
    context = copy.deepcopy(self.param_context)
    kwargs = copy.deepcopy(self.param_kwargs)

    try:
        self._validate_visa(context, 'context')
        self._validate_visa(search_req, 'header')
        context = self.update_api_context(int(contact_data.get('agent_id')), context)

        # ========= Validasi agent_id ===========
        # TODO : Security Issue VERY HIGH LEVEL
        # 1. Jika BUKAN is_company_website, maka contact.contact_id DIABAIKAN
        # 2. Jika ADA contact.contact_id MAKA agent_id = contact.contact_id.agent_id
        # 3. Jika TIDAK ADA contact.contact_id MAKA agent_id = co_uid.agent_id

        # PRODUCTION - SV
        # self._validate_booking(context)
        user_obj = self.env['res.users'].sudo().browse(int(context['co_uid']))
        contact_data.update({
            'agent_id': user_obj.agent_id.id,
            'commercial_agent_id': user_obj.agent_id.id,
            'booker_type': 'FPO',
        })
        if user_obj.agent_id.agent_type_id.id == 3:  # 3 : COR
            if user_obj.agent_id.parent_agent_id:
                contact_data.update({
                    'commercial_agent_id': user_obj.agent_id.parent_agent_id.id,
                    'booker_type': 'COR',
                })

        if user_obj.agent_id.agent_type_id.id == 9:  # 9 : POR
            if user_obj.agent_id.parent_agent_id:
                contact_data.update({
                    'commercial_agent_id': user_obj.agent_id.parent_agent_id.id,
                    'booker_type': 'POR',
                })

        # if not context['agent_id']:
        #     raise Exception('ERROR Create booking, Customer or User, not have Agent (Agent ID)\n'
        #                     'Please contact Administrator, to complete the data !')

        header_val = self._visa_header_normalization(search_req)
        contact_obj = self._create_contact(contact_data, context)

        print('Agent Context : ' + str(context['agent_id']))

        psg_ids = self._evaluate_passenger_info(passengers, contact_obj.id, context['agent_id'])
        ssc_ids = self._create_service_charge_sale_visa(service_charge_summary)

        to_psg_ids = self._create_visa_order(passengers)

        header_val.update({
            'contact_id': contact_obj.id,
            'passenger_ids': [(6, 0, psg_ids)],
            'sale_service_charge_ids': [(6, 0, ssc_ids)],
            'to_passenger_ids': [(6, 0, to_psg_ids)],
            'state': 'booked',
            'agent_id': context['agent_id'],
            'user_id': context['co_uid'],
        })

        print('Agent Header : ' + str(header_val['agent_id']))

        doc_type = header_val.get('transport_type')

        # create header & Update SUB_AGENT_ID
        book_obj = self.sudo().create(header_val)
        book_obj.sub_agent_id = contact_data['agent_id']

        book_obj.action_booked_visa(context, doc_type)
        if kwargs.get('force_issued'):
            book_obj.action_issued_visa(context, doc_type)

        self.env.cr.commit()
        return {
            'error_code': 0,
            'error_msg': 'Success',
            'response': {
                'order_id': book_obj.id,
                'order_number': book_obj.name,
                'status': book_obj.state,
                'state_visa': book_obj.state_visa,
            }
        }
    except Exception as e:
        self.env.cr.rollback()
        _logger.error(msg=str(e) + '\n' + traceback.format_exc())
        return {
            'error_code': 1,
            'error_msg': str(e)
        }


def _validate_visa(self, data, type):
    list_data = []
    if type == 'context':
        list_data = ['co_uid']
    elif type == 'header':
        list_data = ['transport_type', 'departure_date', 'adult', 'child', 'infant', 'country_id']

    # masukkan semua data context / header dalam keys_data
    keys_data = []
    for rec in data.keys():
        keys_data.append(str(rec))

    # cek apabila key pada list_data ada pada keys_data
    for ls in list_data:
        if not ls in keys_data:
            raise Exception('ERROR Validate %s, key : %s' % (type, ls))
    return True


def update_api_context(self, sub_agent_id, context):
    context['co_uid'] = int(context['co_uid'])  # co_uid = 1
    user_obj = self.env['res.users'].sudo().browse(context['co_uid'])  # get res.users where co_uid = 1
    #if int(context['co_uid']) == 744:
    #    _logger.error('JUST Test : "Anta Utama" ' +  str(context))

    if 'is_company_website' not in context:
        # ===============================================
        # ====== Context dari API Client ( BTBO ) =======
        # ===============================================
        context.update({
            'agent_id': user_obj.agent_id.id,
            'sub_agent_id': user_obj.agent_id.id,
            'booker_type': 'FPO',
        })
    elif context['is_company_website']:
        #============================================
        #====== Context dari WEBSITE/FRONTEND =======
        #============================================
        if user_obj.agent_id.agent_type_id.id == 3 or 9:
            # ===== COR/POR User ===== CORPOR LOGIN SENDIRI
            context.update({
                'agent_id': user_obj.agent_id.parent_agent_id.id,
                'sub_agent_id': user_obj.agent_id.id,
                'booker_type': 'COR/POR',
            })
        elif sub_agent_id:
            # ===== COR/POR in Contact ===== DARMO YANG LOGIN
            context.update({
                'agent_id': user_obj.agent_id.id,
                'sub_agent_id': sub_agent_id,
                'booker_type': 'COR/POR',
            })
        else:
            # ===== FPO in Contact =====
            context.update({
                'agent_id': user_obj.agent_id.id,
                'sub_agent_id': user_obj.agent_id.id,
                'booker_type': 'FPO',
            })
    else:
        # ===============================================
        # ====== Context dari API Client ( BTBO ) =======
        # ===============================================
        context.update({
            'agent_id': user_obj.agent_id.id,
            'sub_agent_id': user_obj.agent_id.id,
            'booker_type': 'FPO',
        })
    return context


# memisahkan antara variabel integer dan char
def _visa_header_normalization(self, data):
    res = {}
    str_key_att = ['transport_type', 'departure_date']
    int_key_att = ['adult', 'child', 'infant', 'country_id']

    for rec in str_key_att:
        res.update({
            rec: data[rec]
        })

    for rec in int_key_att:
        res.update({
            rec: int(data[rec])
        })

    return res


def _create_contact(self, vals, context):
    country_obj = self.env['res.country'].sudo()
    contact_obj = self.env['tt.customer'].sudo()
    if vals.get('contact_id'):
        vals['contact_id'] = int(vals['contact_id'])
        contact_rec = contact_obj.browse(vals['contact_id'])
        if contact_rec:
            contact_rec.update({
                'email': vals.get('email', contact_rec.email),
                # 'mobile': vals.get('mobile', contact_rec.phone_ids[0]),
            })
        return contact_rec

    # country = country_obj.search([('code', '=', vals.pop('nationality_code'))])
    # vals['nationality_id'] = country and country[0].id or False

    if context['booker_type'] in ['COR', 'POR']:
        vals['passenger_on_partner_ids'] = [(4, context['sub_agent_id'])]

    country = country_obj.search([('code', '=', vals.pop('country_code'))])
    vals.update({
        'booker_mobile': vals.get('mobile', ''),
        'commercial_agent_id': context['agent_id'],
        'agent_id': context['agent_id'],
        'country_id': country and country[0].id or False,
        'passenger_type': 'ADT',
        'bill_to': '<span><b>{title} {first_name} {last_name}</b> <br>Phone: {mobile}</span>'.format(**vals),
        'mobile_orig': vals.get('mobile', ''),
        'email': vals.get('email', vals['email']),
        'mobile': vals.get('mobile', vals['mobile']),
    })
    return contact_obj.create(vals)


def _evaluate_passenger_info(self, passengers, contact_id, agent_id):
    res = []
    country_obj = self.env['res.country'].sudo()
    psg_obj = self.env['tt.customer'].sudo()
    passenger_count = 0
    for psg in passengers:
        passenger_count += 1
        p_id = psg.get('passenger_id')
        if p_id:
            p_object = psg_obj.browse(int(p_id))
            if p_object:
                res.append(int(p_id))
                if psg.get('passport_number'):
                    p_object['passport_number'] = psg['passport_number']
                if psg.get('passport_expdate'):
                    p_object['passport_expdate'] = psg['passport_expdate']
                if psg.get('country_of_issued_id'):
                    p_object['country_of_issued_id'] = psg['country_of_issued_id']
                print('Passenger Type : ' + str(psg['passenger_type']))
                p_object.write({
                    'domicile': psg.get('domicile'),
                    # 'mobile': psg.get('mobile')
                })
        else:
            country = country_obj.search([('code', '=', psg.pop('nationality_code'))])
            psg['nationality_id'] = country and country[0].id or False
            if psg.get('country_of_issued_code'):
                country = country_obj.search([('code', '=', psg.pop('country_of_issued_code'))])
                psg['country_of_issued_id'] = country and country[0].id or False
            if not psg.get('passport_expdate'):
                psg.pop('passport_expdate')

            psg.update({
                'contact_id': contact_id,
                'passenger_id': False,
                'agent_id': agent_id
            })
            psg_res = psg_obj.create(psg)
            psg.update({
                'passenger_id': psg_res.id,
            })
            res.append(psg_res.id)
    return res


def _create_service_charge_sale_visa(self, service_charge_summary):
    pricelist_env = self.env['tt.reservation.visa.pricelist'].sudo()
    res = []
    ssc_obj = self.env['tt.service.charge'].sudo()
    for rec in service_charge_summary:
        pricelist_obj = pricelist_env.browse(rec['pricelist_id'])
        sc_obj_fare = ssc_obj.create(rec)
        sc_obj_fare.update({
            'pax_type': rec['passenger_type']
        })
        res.append(sc_obj_fare.id)
        rec2 = rec.copy()
        rec2.update({
            'charge_code': 'r.ac',
            'pax_type': rec['passenger_type'],
            'amount': pricelist_obj.commission_price * -1,
        })
        sc_obj_commission = ssc_obj.create(rec2)
        res.append(sc_obj_commission.id)
    return res


def _create_visa_order(self, passengers):
    pl_env = self.env['tt.reservation.visa.pricelist'].sudo()
    # to_env = self.env['tt.traveldoc.order'].sudo()
    to_psg_env = self.env['tt.reservation.visa.order.passengers'].sudo()
    to_req_env = self.env['tt.reservation.visa.order.requirements'].sudo()

    # to_obj = to_env.create({})
    to_psg_res = []
    for psg in passengers:
        pl_obj = pl_env.browse(psg['pricelist_id'])
        psg_vals = {
            'passenger_id': psg['passenger_id'],
            'passenger_type': psg['passenger_type'],
            'pricelist_id': psg['pricelist_id'],
        }
        to_psg_obj = to_psg_env.create(psg_vals)

        to_req_res = []
        for req in pl_obj.requirement_ids:
            req_vals = {
                'to_passenger_id': to_psg_obj.id,
                'requirement_id': req.id,
            }
            to_req_obj = to_req_env.create(req_vals)
            to_req_res.append(to_req_obj.id)

        print(to_req_res)
        to_psg_obj.write({
            'to_requirement_ids': [(6, 0, to_req_res)]
        })

        to_psg_res.append(to_psg_obj.id)
    # to_obj.write({
    #     'to_passenger_ids': [(6, 0, to_psg_res)]
    # })
    return to_psg_res


def _get_pricelist_ids(self, service_charge_summary):
    res = []
    for rec in service_charge_summary:
        res.append(rec['pricelist_id'])
    return res


def action_booked_visa(self, api_context=None, doc_type=''):
    if not api_context:  # Jika dari call from backend
        api_context = {
            'co_uid': self.env.user.id
        }
    vals = {}
    if self.name == 'New':
        vals.update({
            'name': self.env['ir.sequence'].next_by_code('visa.number'),
            # .with_context(ir_sequence_date=self.date[:10])
            'state': 'partial_booked',
        })

    vals.update({
        'state': 'booked',
        'booked_uid': api_context and api_context['co_uid'],
        # 'pnr': False,
        'booked_date': datetime.now(),
        # 'hold_date': False,
        # 'expired_date': False,
    })
    self.write(vals)