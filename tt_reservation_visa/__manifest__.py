# -*- coding: utf-8 -*-
{
    'name': "tt_reservation_visa",

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
    'depends': ['base', 'tt_base', 'tt_traveldoc', 'tt_reservation'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'data/ir_sequence_data.xml',
        'data/tt_provider_type_data.xml',
        'views/tt_reservation_visa_menuheader.xml',
        'views/tt_reservation_visa_views.xml',
        'views/tt_reservation_visa_order_passengers_views.xml',
        'views/tt_reservation_visa_pricelist_views.xml',
        'views/tt_reservation_visa_service_charge_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}