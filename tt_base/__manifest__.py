{
    'name': 'Tour & Travel - Base',
    'version': '1.1',
    'category': 'Tour & Travel',
    'sequence': 1,
    'summary': 'Tour & Travel - Base',
    'description': """
Tour & Travel - Base
====================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': ['base', 'base_setup', 'base_address_city', 'mail', 'hr', 'payment'],
    'data': [
        'data/ir_module_category_data.xml',
        'data/res_groups_data.xml',
        'data/agent_type_rodex_data.xml',
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',

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
        'views/tt_provider_type_views.xml',
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
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
