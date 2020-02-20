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
    'depends': ['base', 'hr', 'base_setup', 'base_address_city', 'mail', 'payment'],
    'data': [
        'data/ir_sequence_data.xml',
        'data/ir_module_category_data.xml',
        'data/frontend_security.xml',
        'data/res_groups_data.xml',
        'data/agent_type_rodex_data.xml',
        'data/customer_parent_type_rodex_data.xml',
        'data/tt_agent_ho_data.xml',
        'data/agent_b2c_data.xml',
        'data/skipped_history_data.xml',
        'data/tt.bank.csv',
        'data/tt.error.api.csv',
        'data/ir_cron_data.xml',
        'data/user_template.xml',
        'data/res.social.media.type.csv',
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'data/payment_acquirer_ho_data.xml',
        'data/tt_pnr_quota_price_list.xml',
        'views/menu_item_base.xml',

        'wizard/tt_upload_center_wizard_view.xml',
        'wizard/create_customer_parent_wizard_view.xml',

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
        'views/customer_bank_detail_views.xml',
        'views/customer_parent_type_views.xml',
        'views/tt_provider_views.xml',
        'views/tt_provider_code_views.xml',
        'views/tt_provider_type_views.xml',
        'views/transport_carrier_views.xml',
        'views/search_transport_carrier_views.xml',
        'views/tt_agent_views.xml',
        'views/tt_agent_views_customer.xml',
        'views/tt_agent_type_views.xml',
        'views/res_employee_views.xml',
        'views/tt_customer_views.xml',
        'views/tt_customer_views_customer.xml',
        'views/res_currency_views.xml',
        'views/res_rate_views.xml',
        'views/res_user_views.xml',
        'views/social_media_detail_views.xml',
        'views/res_social_media_type_views.xml',
        'views/templates.xml',
        'views/tt_destination_views.xml',
        'views/tt_skipped_keys_views.xml',
        'views/tt_customer_parent_views.xml',
        'views/tt_customer_parent_views_customer.xml',
        'views/tt_routes_views.xml',
        'views/error_api_views.xml',
        'views/tt_ssr_views.xml',
        # 'views/tt_cabin_class_views.xml',
        # 'views/tt_product_class_views.xml',
        # 'views/tt_fare_rules_views.xml',
        'views/tt_frontend_security.xml',
        'views/tt_ban_user.xml',
        'views/tt_pnr_quota.xml',
        'views/tt_pnr_quota_price_list.xml',
        'views/tt_pnr_quota_usage.xml',

        'wizard/tt_upload_center_wizard_view.xml',
        'wizard/create_user_wizard_view.xml',
        'wizard/notification_pop_up_wizard.xml',
        'views/tt_upload_center_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
