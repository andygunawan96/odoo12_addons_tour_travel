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
        'data/tt_provider_type_data.xml',
        'data/tt_provider_ppob_data.xml',
        'data/tt_transport_carrier_ppob_data.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
