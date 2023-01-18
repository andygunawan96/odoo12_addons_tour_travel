# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Tour & Travel - Reservation PPOB',
    'version': '2.0',
    'category': 'Reservation',
    'sequence': 58,
    'summary': 'Reservation PPOB Module',
    'description': """
Tour & Travel - Reservation PPOB
================================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends' : ['base_setup','tt_base','tt_reservation','base_address_city','tt_in_api_connector'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'data/ir_sequence_data.xml',
        'data/tt_provider_type_data.xml',
        'data/tt_provider_ppob_data.xml',
        'data/tt_transport_carrier_ppob_data.xml',
        'data/tt_master_voucher_ppob_data.xml',
        'data/ir_send_email.xml',
        'data/tt_pricing_agent_ppob_data.xml',

        'wizard/force_issued_wizard_views.xml',
        'views/menu_item_base.xml',
        'views/tt_master_voucher_ppob_views.xml',
        'views/tt_bill_ppob_views.xml',
        'views/tt_provider_views.xml',
        'views/tt_reservation_passenger_ppob.xml',
        'views/tt_service_charge_views.xml',
        'views/tt_reservation_ppob.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
