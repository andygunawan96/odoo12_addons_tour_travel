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
                'tt_api_management',
                'tt_reschedule',
                'tt_merge_record',
                'tt_report_selling',
                'tt_public_holiday',
                'tt_frontend_banner', 'tt_bank_transaction',
                'tt_billing_statement', 'tt_agent_report_billing',
                'tt_reservation_report_airline',
                'tt_agent_report_invoice', 'tt_agent_report_offline',
                'tt_agent_report_recap_reservation', 'tt_agent_report_recap_transaction',
                'tt_agent_sales_activity',
                # 'tt_agent_sales_agent_registration',
                'tt_agent_sales_airline', 'tt_agent_sales_hotel', 'tt_agent_sales_offline',
                'tt_agent_sales_passport', 'tt_agent_sales_tour',
                'tt_agent_sales_train', 'tt_agent_sales_visa', 'web_m2x_options',
                'tt_agent_report_balance', 'tt_agent_report_passport', 'tt_agent_report_visa'
    ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
    ],
    # only loaded in demonstration mode
    'demo': [],
}