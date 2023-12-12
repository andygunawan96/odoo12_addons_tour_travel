from odoo import api, fields, models, _
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ManualGetBankTransactionWizard(models.TransientModel):
    _name = "manual.get.bank.transaction.wizard"
    _description = 'Manual Get Bank Transaction Wizard'

    bank_accounts_id = fields.Many2one('tt.bank.accounts','Bank Account', readonly=True, required=True)
    transaction_date = fields.Date('Transaction Date', required=True)

    def get_bank_mutation_wizard(self):
        transaction_date = self.transaction_date.strftime("%Y-%m-%d")
        data = {
            'account_id': self.bank_accounts_id.id,
            'account_number': self.bank_accounts_id.bank_account_number_without_dot,
            'provider': self.bank_accounts_id.bank_id.code,
            'startdate': transaction_date,
            'enddate': transaction_date
        }
        # called function to proceed data and input in bank transaction
        self.env['tt.bank.transaction'].get_data(data, self.bank_accounts_id.ho_id.id)