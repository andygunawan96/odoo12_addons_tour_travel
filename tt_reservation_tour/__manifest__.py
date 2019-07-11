# -*- coding: utf-8 -*-
{
    'name': "tt_reservation_tour",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'tt_reservation', 'survey', 'tt_base'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'views/tt_reservation_tour_menuheader.xml',
        'views/tt_reservation_tour_views.xml',
        # 'views/tour_booking_views_concept.xml',
        'views/tt_reservation_tour_package_quotation_views.xml',
        'views/tt_reservation_tour_pricelist_views.xml',
        'data/ir_sequence_data.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}