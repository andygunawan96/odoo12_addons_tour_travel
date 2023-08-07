# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - All Complete Install',
    'version': '2.0',
    'category': 'Tour & Travel',
    'summary': 'Completely Install All Tour & Travel Features',
    'sequence': 32,
    'description': """
Tour & Travel - All Complete Install
====================================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['base', 'base_setup','web_m2x_options',
                'tt_api_management',
                'tt_reschedule',
                'tt_merge_record',

                'tt_frontend_banner',
                'tt_search_result_banner',
                'tt_bank_transaction',
                'tt_billing_statement',

                'tt_reservation_report_airline',
                'tt_agent_registration',
                
                'tt_agent_sales_activity',
                'tt_agent_sales_airline',
                'tt_agent_sales_event',
                'tt_agent_sales_hotel',
                'tt_agent_sales_offline',
                'tt_agent_sales_ppob',
                'tt_agent_sales_tour',
                'tt_agent_sales_train',
                'tt_agent_sales_visa',

                'tt_agent_report_balance',
                'tt_agent_report_billing',
                'tt_agent_report_invoice',
                'tt_agent_report_offline',
                'tt_agent_report_recap_reservation',
                'tt_agent_report_recap_transaction',
                'tt_agent_report_visa',

                'tt_customer_report_birthday',
                'tt_customer_report_performance',

                'tt_report_dashboard',
                'tt_report_selling',
                'tt_report_vendor_event',
                'tt_letter_guarantee_printout'
    ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}