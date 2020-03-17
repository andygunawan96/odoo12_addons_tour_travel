# -*- coding: utf-8 -*-
{
    'name': "tt_agent_registration",
    'version': 'beta',
    'summary': 'Agent Registration',
    'sequence': 5,
    'description': """
        Module for Agent Registration
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',

    # any module necessary for this one to work correctly
    'depends': ['base', 'tt_base', 'tt_accounting', 'tt_report_common', 'web'],

    # always loaded
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
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}