# -*- coding: utf-8 -*-
{
    'name' : 'tt_reservation_tour',
    'version' : 'beta',
    'summary': 'transport dummy tour',
    'sequence': 2,

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'booking',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'tt_reservation', 'survey', 'tt_base'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'views/menu_item_base.xml',
        'views/tt_reservation_tour_views.xml',
        # 'views/tour_booking_views_concept.xml',
        'views/tt_master_tour_quotation_views.xml',
        'views/tt_master_tour_views.xml',
        'data/ir_sequence_data.xml',
        'data/tt_provider_type_data.xml',
        'data/tt_provider_tour.xml',
    ],
    # only loaded in demonstration mode
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
