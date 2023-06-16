# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Tour & Travel - Reservation Train',
    'version': '2.0',
    'category': 'Reservation',
    'sequence': 60,
    'summary': 'Reservation Train Module',
    'description': """
Tour & Travel - Reservation Train
=================================
Key Features
------------
    """,
    'author': 'PT Orbis Daya Asia',
    'website': 'orbisway.com',
    'depends' : ['base_setup','tt_base','tt_reservation','base_address_city'],
    'data': [
        'data/ir_sequence_data.xml',
        'data/tt_provider_type_data.xml',
        'data/tt_provider_train.xml',
        'data/tt_destination_kai.xml',
        'data/tt_transport_carrier_train.xml',
        'data/tt_api_monitor_rule_data.xml',
        'data/ir_send_email.xml',
        'data/tt_pnr_quota_price_list_train_data.xml',
        'data/tt_pricing_agent_train_data.xml',

        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',

        'wizard/force_issued_wizard_views.xml',

        'views/menu_item_base.xml',
        'views/tt_reservation_train.xml',
        'views/tt_provider_views.xml',
        'views/tt_journey_views.xml',
        'views/tt_service_charge_views.xml',
        'views/tt_reservation_passenger_train_form_views.xml'

    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
