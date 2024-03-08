# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Accounting',
    'version': '2.0',
    'category': 'Transaction',
    'sequence': 10,
    'summary': 'Accounting Module',
    'description': """
Tour & Travel - Accounting
==========================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['base', 'base_setup', 'tt_base', 'tt_in_api_connector'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'data/refund_type_data.xml',
        'data/admin_fee_data.xml',
        'data/admin_fee_line_data.xml',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'data/ir_send_email.xml',

        'views/ir_ui_menu_views.xml',
        'views/tt_reimburse_commission_tier_views.xml',
        'wizard/tt_change_admin_fee_wizard_view.xml',
        'wizard/tt_refund_extend_wizard_view.xml',
        'wizard/tt_reimburse_commission_wizard_view.xml',
        'views/tt_refund_type_views.xml',
        'views/tt_master_admin_fee_views.xml',
        'views/tt_master_admin_fee_views_transaction.xml',
        'views/tt_ledger_views.xml',
        'views/tt_ledger_queue_views.xml',
        'views/tt_adjustment_views.xml',
        'wizard/tt_adjustment_wizard_view.xml',
        'views/tt_refund_views.xml',
        'wizard/tt_refund_wizard_view.xml',
        'views/tt_agent_views.xml',
        'views/tt_top_up_views.xml',
        'views/tt_customer_parent_views.xml',
        'views/tt_pnr_quota_views.xml',
        'views/tt_reimburse_commission_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
