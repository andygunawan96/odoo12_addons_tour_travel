# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Tour & Travel - Reservation Bus',
    'version': '2.0',
    'category': 'Reservation',
    'sequence': 60,
    'summary': 'Reservation Bus Module',
    'description': """
Tour & Travel - Reservation Bus
=================================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends' : ['base_setup','tt_base','tt_reservation','base_address_city'],
    'data': [
        'data/ir_sequence_data.xml',
        'data/tt_provider_type_data.xml',
        'data/tt_provider_bus.xml',
        'data/tt_transport_carrier_bus.xml',
        'data/ir_send_email.xml',

        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',

        'wizard/force_issued_wizard_views.xml',

        'views/menu_item_base.xml',
        'views/tt_reservation_bus.xml',
        'views/tt_provider_views.xml',
        'views/tt_journey_views.xml',
        'views/tt_master_bus_views.xml',
        'views/tt_bus_sync_data_wizard.xml',
        'views/tt_service_charge_views.xml',
        'views/tt_reservation_passenger_bus_form_views.xml'

    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
