# -*- coding: utf-8 -*-
{
    'name': "tt_base",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Andre",
    'website': "http://www.skytors.id",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Tour and Travel',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'base_setup', 'base_address_city', 'mail', 'hr', 'payment'],

    # always loaded
    'data': [
        'data/ir_module_category_data.xml',
        'data/res_groups_data.xml',
        'data/agent_type_rodex_data.xml',
        'security/ir.model.access.csv',

        'views/menu_item_base.xml',
        'views/res_country_views.xml',
        'views/res_country_state_views.xml',
        'views/res_country_city_views.xml',
        'views/res_country_district_views.xml',
        'views/res_country_sub_district_views.xml',
        'views/payment_acquirer_views.xml',
        'views/address_detail_views.xml',
        'views/phone_detail_views.xml',
        'views/res_bank_views.xml',
        'views/agent_bank_detail_views.xml',
        'views/company_bank_detail_views.xml',
        'views/customer_bank_detail_views.xml',
        'views/tt_company_views.xml',
        'views/tt_provider_views.xml',
        'views/tt_agent_views.xml',
        'views/tt_agent_type_views.xml',
        'views/res_employee_views.xml',
        'views/tt_customer_views.xml',
        'views/res_currency_views.xml',
        'views/res_rate_views.xml',
        'views/res_user_views.xml',
        'views/social_media_detail_views.xml',
        'views/res_social_media_type_views.xml',
        'views/templates.xml',
        'views/tt_destination_views.xml',
        'views/tt_skipped_keys_views.xml',

        'data/skipped_history_data.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}