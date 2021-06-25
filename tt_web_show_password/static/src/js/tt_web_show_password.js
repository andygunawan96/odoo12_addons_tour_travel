odoo.define('tt_web_show_password.web_login_show_password', function(require) {
    "use strict";

    var base = require('web_editor.base');
    $(document).ready(function() {

        $('.oe_login_form').each(function(ev) {
            var oe_website_login_container = this;

            $(oe_website_login_container).on('click', 'div.input-group-append button.btn.btn-secondary', function() {
                var icon = $(this).find('i.fa.fa-eye').length
                if (icon == 1) {
                    $(this).find('i.fa.fa-eye').removeClass('fa-eye').addClass('fa-eye-slash');
                    $(this).parent().prev('input[type="password"]').prop('type', 'text');
                } else {
                    $(this).find('i.fa.fa-eye-slash').removeClass('fa-eye-slash').addClass('fa-eye');
                    $(this).parent().prev('input[type="text"]').prop('type', 'password');
                }
            });
        });
    });
});
