# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'tt_reservation_train',
    'version' : 'beta',
    'summary': 'transport train',
    'sequence': 2,
    'description': """
TT_TRANSPORT
""",
    'category': 'booking',
    'website': '',
    'images' : [],
    'depends' : ['base_setup','tt_base','tt_reservation','base_address_city'],
    'data': [
        # 'security/ir.model.access.csv',
        'security/ir.model.access.csv',
        
        'views/menu_item_base.xml',
        'views/tt_reservation_train.xml',
        'views/tb_provider_views.xml',
        'views/tb_segment_views.xml',
        'views/tb_leg_views.xml',
        'data/ir_sequence_data.xml',
        'data/tt_provider_type_data.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
