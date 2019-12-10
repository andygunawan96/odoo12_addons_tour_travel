from odoo import http
from odoo.http import request
import json
import datetime

class TtVoucher(http.Controller):
    @http.route('/test_voucher_discount', type='http', auth='public', csrf=False, method=['POST'])
    def test_voucher_discount(self):
        # data = {
        #     voucher reference
        #     date to be issued
        #     provider_type
        #     provider_id
        #     agent_type
        #     agent_id
        # }
        data = {
            'voucher_reference': 'TEST001.TESTED',
            'date': datetime.datetime.strptime('2019-12-01', '%Y-%m-%d').date(),
            'agent_type': 1,
            'agent': 3,
            'provider_type': 2,
            'provider': 6
        }
        voucher = request.env['tt.voucher.detail'].use_voucher(data)
        return 0

    @http.route('/test_voucher_percent', type='http', auth='public', csrf=False, method=['POST'])
    def tet_voucher_percent(self):
        data = {
            'voucher_reference': 'TEST001.TESTED',
            'date': datetime.datetime.today(),
            'agent_type': 1,
            'agent': 3,
            'provider_type': 2,
            'provider': 6
        }
        voucher = request.env['tt.voucher.detail'].use_voucher(data)
        return 0

    @http.route('/test_get_voucher', type='http', auth='public', csrf=False, method=['POST'])
    def get_voucher_details(self):
        data = {
            'provider_type_id': 2,
            'provider_id': -1,
            'start_date': datetime.datetime.today(),
            'end_date': datetime.datetime.today(),
            'reference_code': '-1'
        }
        context = {}
        voucher = request.env['tt.voucher'].get_voucher(data, context)
        print(voucher)
        return 0

    @http.route('/test_use_voucher', type='http', auth='public', csrf=False, method=['POST'])
    def use_voucher_test(self):
        data = {
            'voucher_reference': 'TEST001.TESTED',
            'provider_type_id': 2,
            'provider_id': 6,
            'date': datetime.datetime.today(),
            'purchase_amount': 500000.00
        }
        context = {"uid": 7, "user_name": "gateway user", "user_login": "mob.it@rodextravel.tours", "agent_id": 4, "agent_name": "SKYTORS.ID", "agent_type_id": 1, "agent_type_name": "HO", "agent_type_code": "ho", "agent_frontend_security": ["ticketing", "top_up", "admin", "login"], "api_role": "admin", "device_type": "general", "host_ips": [], "configs": {"visa": {"provider_access": "all", "providers": {}}, "agent_registration": {"provider_access": "all", "providers": {}}, "offline": {"provider_access": "all", "providers": {}}}, "co_uid": 6, "co_user_name": "Ivan", "co_user_login": "ivankai", "co_agent_id": 3, "co_agent_name": "rodex travel", "co_agent_type_id": 2, "co_agent_type_name": "Agent Citra", "co_agent_type_code": "citra", "co_agent_frontend_security": ["ticketing", "top_up", "admin", "login"], "sid": "0d7a5c2c318370ec0cb080b9ead9ba06ce9ff12a", "signature": "24f4b2d6dac445f8a2b3b8574e9e5614", "expired_date": "2019-12-04 02:19:10"}
        voucher = request.env['tt.voucher.detail'].use_voucher(data,context)
        print(voucher)
        return 0

    @http.route('/test_activate_voucher', type='http', auth='public', csrf=False, method=['POST'])
    def activating_voucher(self):
        voucher = request.env['tt.voucher.detail'].activate_voucher()
        print(voucher)
        return 0

    @http.route('/test_expire_voucher', type='http', auth='public', csrf=False, method=['POST'])
    def expiring_voucher(self):
        voucher = request.env['tt.voucher.detail'].expire_voucher()
        print(voucher)
        return 0

    @http.route('/test_simulate_voucher', type='http', auth='public', csrf=False, method=['POST'])
    def simulate_vouchers(self):
        data = {
            'voucher_reference': 'TEST001.TESTED',
            'provider_type_id': 2,
            'provider_id': 6,
            'date': datetime.datetime.today(),
        }
        context = {"uid": 7, "user_name": "gateway user", "user_login": "mob.it@rodextravel.tours", "agent_id": 4, "agent_name": "SKYTORS.ID", "agent_type_id": 1, "agent_type_name": "HO", "agent_type_code": "ho", "agent_frontend_security": ["ticketing", "top_up", "admin", "login"], "api_role": "admin", "device_type": "general", "host_ips": [], "configs": {"visa": {"provider_access": "all", "providers": {}}, "agent_registration": {"provider_access": "all", "providers": {}}, "offline": {"provider_access": "all", "providers": {}}}, "co_uid": 6, "co_user_name": "Ivan", "co_user_login": "ivankai", "co_agent_id": 3, "co_agent_name": "rodex travel", "co_agent_type_id": 2, "co_agent_type_name": "Agent Citra", "co_agent_type_code": "citra", "co_agent_frontend_security": ["ticketing", "top_up", "admin", "login"], "sid": "0d7a5c2c318370ec0cb080b9ead9ba06ce9ff12a", "signature": "24f4b2d6dac445f8a2b3b8574e9e5614", "expired_date": "2019-12-04 02:19:10"}
        voucher = request.env['tt.voucher.detail'].simulate_voucher(data,context)
        print(voucher)
        return 0