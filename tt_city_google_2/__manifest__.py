# -*- coding: utf-8 -*-
{
    'name': "Google State and City Code",

    'summary': """
        Data City from google code Part 2
    """,

    'description': """
        Data City from google code, need to update external code for better understandable meaning
    """,

    'author': "Rodex Travel and Tour",
    'website': "http://www.rodextrip.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base_address_city', 'tt_city_google_1',
    ],

    # always loaded
    'data': [
        'data/res.city.csv',
    ],
}