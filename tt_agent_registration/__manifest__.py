# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Registration',
    'version': '2.0',
    'category': 'Tour & Travel',
    'summary': 'Agent Registration Module',
    'sequence': 3,
    'description': """
Tour & Travel - Agent Registration
==================================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['base', 'tt_base', 'tt_accounting', 'tt_report_common', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'data/ir_send_email.xml',
        'data/tt_agent_registration_promotion.xml',
        # 'data/tt_agent_registration_document.xml',
        # 'data/tt_provider_type_data.xml',
        'data/param_data.xml',
        'views/tt_agent_registration_views.xml',
        'views/tt_agent_registration_menuheader.xml',
        'views/tt_agent_registration_promotion_views.xml',
        'views/tt_agent_registration_customer_views.xml',
        'views/tt_agent_registration_address_views.xml',
        'views/tt_agent_registration_document_views.xml',
        'views/tt_agent_registration_payment_views.xml',
        'views/tt_document_type_views.xml',

        'report/printout_menu.xml',
        'report/printout_invoice_template.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}