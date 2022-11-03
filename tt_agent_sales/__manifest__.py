# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Sales',
    'version': '2.0',
    'category': 'Billing',
    'summary': 'Agent Sales Module',
    'sequence': 20,
    'description': """
Tour & Travel - Agent Sales
===========================
Key Features
------------
    """,
    'author': "PT Roda Express Sukses Mandiri",
    'website': "rodextravel.tours",
    'depends': ['base', 'base_setup', 'tt_base','tt_accounting', 'tt_payment'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',

        'data/ir_sequence_data.xml',
        'data/tt_dynamic_selection_data.xml',
        'views/menu_item_base.xml',
        'wizard/tt_agent_invoice.xml',
        'wizard/tt_split_wizard_view.xml',
        'wizard/tt_merge_wizard_view.xml',
        'views/tt_agent_invoice_line.xml',
        'views/tt_agent_invoice.xml',
        'views/tt_ho_invoice_line.xml',
        'views/tt_ho_invoice.xml',
        'views/tt_ledger.xml',
        'views/tt_payment.xml',
        'data/ir_cron_data.xml'

    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}