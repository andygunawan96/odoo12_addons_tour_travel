# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'tt_reservation_ppob',
    'version' : 'beta',
    'summary': 'Reservation PPOB',
    'sequence': 2,
    'description': """
TT_TRANSPORT
""",
    'category': 'booking',
    'website': '',
    'images' : [],
    'depends' : ['base_setup','tt_base','tt_reservation','base_address_city','tt_in_api_connector'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'data/ir_sequence_data.xml',
        'data/tt_provider_type_data.xml',
        'data/tt_provider_ppob_data.xml',
        'data/tt_transport_carrier_ppob_data.xml',
        'data/ir_send_email.xml',
        'wizard/force_issued_wizard_views.xml',
        'views/menu_item_base.xml',
        'views/tt_bill_ppob_views.xml',
        'views/tt_provider_views.xml',
        'views/tt_reservation_passenger_ppob.xml',
        'views/tt_service_charge_views.xml',
        'views/tt_reservation_ppob.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
