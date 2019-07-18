from odoo import api, fields, models, _

TYPE = [
    ('cash', 'Cash'),
    ('transfer', 'Transfer'),
    ('installment', 'Installment'),
    ('va', 'Virtual Account')
]


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    type = fields.Selection(TYPE, 'Payment Type')
    provider_id = fields.Many2one('tt.provider', 'Provider')
    agent_id = fields.Many2one('tt.agent', 'Agent')
    bank_id = fields.Many2one('tt.bank', 'Bank')
    account_number = fields.Char('Account Number')
    account_name = fields.Char('Account Name')

    # FUNGSI
    def generate_unique_amount(self):
        random = randint(1, 999)
        return random

    def compute_fee(self, amount):
        fee = uniq= 0
        if self.type == 'transfer':
            uniq = self.generate_unique_amount()
        else:
            # TODO perhitungan per acquirer (Charge dari agent brapa, charge dari rodex brpa)
            fee = 5000
        return fee, uniq

    def acquirer_format(self, amount):
        # NB:  CASH /payment/cash/feedback?acq_id=41
        # NB:  BNI /payment/tt_transfer/feedback?acq_id=68
        # NB:  BCA /payment/tt_transfer/feedback?acq_id=27
        # NB:  MANDIRI /payment/tt_transfer/feedback?acq_id=28
        fee, uniq = self.compute_fee(amount)
        return {
            'id': self.id,
            'name': self.name,
            'account_name': self.account_name or '-',
            'account_number': self.account_number or '',
            'bank': {
                'name': self.bank_id.name,
                'code': self.bank_id.code,
            },
            'type': self.type,
            'provider_id': self.provider_id.id,
            'currency': 'IDR',
            'price_component': {
                'amount': amount,
                'fee': fee,
                'unique_amount': uniq,
            },
            'total_amount': amount + fee + uniq,
            'image': self.image,
            'return_url': '/payment/' + str(self.type) + '/feedback?acq_id=' + str(self.id)
        }

    def get_payment_acquirer(self, agent_id, tr_type, amount):
        agent_obj = self.env['tt.agent'].sudo().browse(agent_id)
        if not agent_obj:
            # Return Error jika agent_id tidak ditemukan
            return False
        dom = [('website_published', '=', True), ('company_id', '=', self.env.user.company_id.id)]
        # Ambil agent_id Parent nya (Citranya corpor tsb)
        # if agent_obj.agent_type_id.id in (self.env.ref('tt_base_rodex.agent_type_cor').id,
        #                                   self.env.ref('tt_base_rodex.agent_type_por').id):
        if tr_type == 'top_up':
            # Kalau top up Ambil agent_id HO
            dom.append(('agent_id', 'in', self.env['tt.agent'].sudo().search([('agent_type_id', '=', self.env.ref('tt_base.agent_type_ho').id )], limit=1) ))
        elif tr_type == 'billing':
            dom.append(('agent_id', '=', agent_id))

        values = {}
        for acq in self.sudo().search(dom):
            if not values.get(acq.type):
                values[acq.type] = []
            values[acq.type].append(acq.acquirer_format(amount))
        return values

    def test_payment(self):
        raise UserWarning(self.get_payment_acquirer(1, 'billing', 12000))