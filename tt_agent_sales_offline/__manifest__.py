# -*- coding: utf-8 -*-
{
    'name': "tt_agent_sales_offline",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Skytors",
    'website': "http://www.skytors.id",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Tour and Travel',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'tt_agent_sales', 'tt_reservation_offline'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/tt_reservation_offline_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [],
}