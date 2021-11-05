# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Tour & Travel - Reservation Insurance',
    'version': '2.0',
    'category': 'Reservation',
    'sequence': 55,
    'summary': 'Reservation Insurance Module',
    'description': """
Tour & Travel - Reservation Insurance
=====================================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': ['base_setup','tt_base','tt_reservation','base_address_city'],
    'data': [
        'views/menu_item_base.xml',

        'data/tt_provider_type_data.xml',
        'data/tt_provider_insurance.xml',
        'data/tt_transport_carrier_insurance.xml',
        'data/ir_sequence_data.xml',

        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',

        'wizard/force_issued_wizard_views.xml',

        'views/tt_reservation_insurance.xml',
        'views/tt_provider_views.xml',
        'views/tt_service_charge_views.xml',
        'views/tt_reservation_passenger_insurance_form_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
