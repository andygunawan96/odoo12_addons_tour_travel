{
    'name': 'Tour & Travel - Base',
    'version': '2.0',
    'category': 'Tour & Travel',
    'sequence': 1,
    'summary': 'Core Module',
    'description': """
Tour & Travel - Base
====================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': ['base', 'base_setup', 'base_address_city', 'mail', 'payment'],
    'data': [
        'data/ir_mail_server.xml',
        'data/ir_sequence_data.xml',
        'data/ir_module_category_data.xml',
        'data/frontend_security.xml',
        'data/ir_config_parameter.xml',
        'data/res_groups_data.xml',
        'data/customer_parent_type_rodex_data.xml',
        'data/skipped_history_data.xml',
        'data/tt.bank.csv',
        'data/tt.error.api.csv',
        'data/ir_cron_data.xml',
        'data/ir_send_email.xml',

        'data/res.social.media.type.csv',
        'data/tt_pnr_quota_price_list.xml',
        'views/menu_item_base.xml',
        'views/tt_agent_views.xml',
        'data/agent_type_rodex_data.xml',
        'data/agent_b2c_data.xml',
        'data/tt_agent_ho_data.xml',
        'data/payment_acquirer_ho_data.xml',
        'data/user_template.xml',

        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',

        'wizard/res_users_duplicate_permissions_wizard_view.xml',
        'wizard/frontend_security_assign_wizard_view.xml',
        'wizard/tt_upload_center_wizard_view.xml',

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
        'views/tt_agent_views_customer.xml',
        'views/tt_agent_type_views.xml',
        'views/tt_employee_views.xml',
        'views/tt_customer_parent_booker_rel_views.xml',
        'views/tt_customer_job_position_views.xml',
        'views/tt_osi_corporate_code_views.xml',
        'views/tt_customer_views.xml',
        'views/tt_customer_views_customer.xml',
        'views/res_currency_views.xml',
        'views/res_rate_views.xml',
        'views/res_user_views.xml',
        'views/social_media_detail_views.xml',
        'views/res_social_media_type_views.xml',
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
        'views/tt_pnr_quota_views.xml',
        'views/tt_pnr_quota_price_list_views..xml',
        'views/tt_pnr_quota_usage_views.xml',
        'views/tt_pnr_quota_price_package_views.xml',
        'views/tt_email_queue_views.xml',
        'views/tt_agent_third_party_key.xml',

        'wizard/tt_upload_center_wizard_view.xml',
        'wizard/create_user_wizard_view.xml',
        'wizard/notification_pop_up_wizard.xml',
        'wizard/create_customer_parent_wizard_view.xml',
        'views/tt_upload_center_views.xml',
        'views/tt_vendor_views.xml',
        'views/ir_model_data_views.xml',
        'views/ir_mail_server_views.xml',

        'views/change_default_odoo.xml',
        'views/tt_loyalty_program_views.xml',
        'views/tt_public_holiday_views.xml',
        'views/tt_letter_guarantee_views.xml',
        'views/tt_letter_guarantee_lines_views.xml',
        'views/tt_agent_notification_views.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
