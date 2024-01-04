# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'tt_reservation_request',
    'version' : 'beta',
    'summary': 'Reservation Request',
    'sequence': 60,
    'description': """
TT_TRANSPORT
""",
    'category': 'booking',
    'website': '',
    'images' : [],
    'depends' : ['tt_base'],
    'data': [
        'views/menu_item_base.xml',

        'data/ir_sequence_data.xml',
        'data/ir_send_email.xml',
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',

        'views/tt_reservation_request_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
