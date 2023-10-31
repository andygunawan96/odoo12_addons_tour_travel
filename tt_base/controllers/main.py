# -*- coding: utf-8 -*-
##############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2017-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Niyas Raphy(<https://www.cybrosys.com>)
#    you can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    GENERAL PUBLIC LICENSE (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo.addons.web.controllers import main
from odoo.http import request
from odoo.exceptions import Warning
import odoo
import odoo.modules.registry
from odoo.tools.translate import _
from odoo import http

from uuid import getnode as get_mac


class Home(main.Home):

    @http.route('/web/login', type='http', auth="public")
    def web_login(self, redirect=None, **kw):
        main.ensure_db()
        request.params['login_success'] = False
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return http.redirect_with_hash(redirect)

        if not request.uid:
            request.uid = odoo.SUPERUSER_ID

        values = request.params.copy()
        try:
            values['databases'] = http.db_list()
        except odoo.exceptions.AccessDenied:
            values['databases'] = None
        if request.httprequest.method == 'POST':
            old_uid = request.uid

            if request.params['login']:
                user_rec = request.env['res.users'].sudo().search([('login', '=', request.params['login'])])
                if user_rec.is_using_otp:
                    need_otp = user_rec.check_need_otp_user_api({
                        'machine_code': request.params['machine_id'],
                        'otp': request.params.get('otp_data'),
                        'platform': request.params['platform'],
                        'browser': request.params['web_vendor'],
                        'timezone': request.params['tz'],
                    })
                    if not need_otp: #Return True, False or Expired time
                        try:
                            uid = request.session.authenticate(request.session.db, request.params['login'], request.params['password'])
                            request.params['login_success'] = True
                            return http.redirect_with_hash(self._login_redirect(uid, redirect=redirect))
                        except odoo.exceptions.AccessDenied as e:
                            request.uid = old_uid
                            if e.args == odoo.exceptions.AccessDenied().args:
                                values['error'] = _("Wrong login/password")
                            else:
                                values['error'] = e.args[0]
                    else:
                        if isinstance(need_otp, bool):
                            values['error'] = _("Wrong OTP")
                        else: #Jika tipe data ne String (Timelimit)
                            values['error'] = _("Send OTP, Please check your email")
                        request.uid = old_uid
                        values['is_need_otp'] = True
                else:
                    try:
                        uid = request.session.authenticate(request.session.db, request.params['login'], request.params['password'])
                        request.params['login_success'] = True
                        return http.redirect_with_hash(self._login_redirect(uid, redirect=redirect))
                    except odoo.exceptions.AccessDenied as e:
                        request.uid = old_uid
                        if e.args == odoo.exceptions.AccessDenied().args:
                            values['error'] = _("Wrong login/password")
                        else:
                            values['error'] = e.args[0]

        return request.render('web.login', values)
