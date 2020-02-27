# -*- coding: utf-8 -*-
{
    'name': "All complete install",

    'summary': """
        Completely install all feature of TORS""",

    'description': """
        Long description of module's purpose
    """,

    'author': "PT. Roda Express Sukses Mandiri",
    'website': "http://rodextrip.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Tour & Travel',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'base_setup',

    ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
    ],
    # only loaded in demonstration mode
    'demo': [],
}