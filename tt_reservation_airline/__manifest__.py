# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'tt_reservation_airline',
    'version' : 'beta',
    'summary': 'transport dummy airline',
    'sequence': 2,
    'description': """
TT_TRANSPORT
""",
    'category': 'booking',
    'website': '',
    'images' : [],
    'depends' : ['base_setup','tt_base','tt_reservation','base_address_city','tt_in_api_connector'],
    'data': [
        'data/ir_sequence_data.xml',
        'data/tt_provider_type_data.xml',
        'data/tt_provider_airline.xml',
        'data/tt_destination_airline.xml',
        'data/tt_transport_carrier_airline.xml',
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',

        'views/menu_item_base.xml',
        'views/tt_reservation_airline.xml',
        'views/tt_provider_views.xml',
        'views/tt_journey_views.xml',
        'views/tt_segment_views.xml',
        'views/tt_leg_views.xml',
        'views/tt_service_charge_views.xml'

    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
