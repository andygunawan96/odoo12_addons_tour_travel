# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'tt_reservation_periksain',
    'version' : 'beta',
    'summary': 'Transport Reservation Periksain',
    'sequence': 10,
    'description': """
TT_TRANSPORT
""",
    'category': 'booking',
    'website': '',
    'images' : [],
    'depends' : ['base_setup','tt_base','tt_reservation','tt_in_api_connector'],
    'data': [
        'views/menu_item_base.xml',

        'data/ir_sequence_data.xml',
        'data/tt_provider_type_data.xml',
        'data/tt_destination_periksain.xml',
        'data/tt_transport_carrier_periksain.xml',
        'data/ir_send_email.xml',

        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',

        'views/tt_reservation_periksain_views.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
