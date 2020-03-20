# -*- coding: utf-8 -*-
{
    'name': "tt_hotel_provider_data",

    'summary': """
        Data Provider Hotel
    """,

    'description': """
        Data Provider Hotel, Must install tt_base and tt_reservation_hotel first before install
    """,

    'author': "Rodex Travel and Tour",
    'website': "http://www.rodextrip.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [],

    # always loaded
    'data': [
        'data/tt.provider.code.csv',
    ],
}