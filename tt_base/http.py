import odoo
import werkzeug
from odoo.service import security

request = odoo.http.request

class OpenERPSessionInh(odoo.http.OpenERPSession):

    def authenticate(self, db, login=None, password=None, uid=None):
        """
        Authenticate the current user with the given db, login and
        password. If successful, store the authentication parameters in the
        current session and request.

        :param uid: If not None, that user id will be used instead the login
                    to authenticate the user.
        """
        if isinstance(uid,dict) or uid is None: #We substitute UID as OTP PARAMS
            wsgienv = request.httprequest.environ
            env = dict(
                base_location=request.httprequest.url_root.rstrip('/'),
                HTTP_HOST=wsgienv['HTTP_HOST'],
                REMOTE_ADDR=wsgienv['REMOTE_ADDR'],
            )
            uid = odoo.registry(db)['res.users'].authenticate(db, login, password, env, otp_params=uid)
        else:
            security.check(db, uid, password)
        self.rotate = True
        self.db = db
        self.uid = uid
        self.login = login
        self.session_token = uid and security.compute_session_token(self, request.env)
        request.uid = uid
        request.disable_db = False

        if uid: self.get_context()
        return uid

odoo.http.OpenERPSession.authenticate = OpenERPSessionInh.authenticate