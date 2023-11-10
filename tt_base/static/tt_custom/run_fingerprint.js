odoo.define('tt.fingerprint', function (require) {
'use strict';

    var base = require('web_editor.base');
    var platform = 'default';
    var machine_code = crypto.randomUUID();
    var browser = '';
    var timezone = '';
    $(document).ready(function() {
    //$("#kentng").click(function() {
        $(document).click(function() {
            if(typeof(localStorage.machine_code) !== 'undefined' || localStorage.machine_code == '' || typeof(localStorage.platform) === 'undefined' || typeof(localStorage.browser) !== 'undefined' || typeof(localStorage.timezone) !== 'undefined'){
                //console.log('XXX1');
                //const fpPromise = import('https://openfpcdn.io/fingerprintjs/v4').then(FingerprintJS => FingerprintJS.load())
                const fpPromise = import('/tt_base/static/tt_custom/fingerprint.js').then(FingerprintJS => FingerprintJS.load())
                // Get the visitor identifier when you need it.
                fpPromise.then(fp => fp.get()).then(result => {
                    // console.log(result);
                    // This is the visitor identifier:
                    platform = result.components.platform.value;
                    machine_code = result['visitorId'];
                    if(result.components.vendorFlavors.value.length > 0)
                        browser = result.components.vendorFlavors.value[0];
                    else if(result.components.webGlBasics.value.vendor)
                        browser = result.components.webGlBasics.value.vendor;
                    timezone = result.components.timezone.value;
                    localStorage.platform = platform;
                    localStorage.machine_code = machine_code;
                    localStorage.browser = browser;
                    localStorage.timezone = timezone;
                });

                if(localStorage.hasOwnProperty('platform'))
                    platform = localStorage.platform;
                else
                    platform = '';

                if(localStorage.hasOwnProperty('browser'))
                    browser = localStorage.browser;
                else
                    browser = '';

                if(localStorage.hasOwnProperty('timezone'))
                    timezone = localStorage.timezone;
                else
                    timezone = '';

                if(localStorage.hasOwnProperty('machine_code'))
                    machine_code = localStorage.machine_code;
                else{
                    localStorage.machine_code = machine_code;
                }
            }else{
                platform = localStorage.platform;
                machine_code = localStorage.machine_code;
                browser = localStorage.browser;
                timezone = localStorage.timezone;
            }
            $("#platform").val(platform);
            $("#machine_code").val(machine_code);
            $("#browser").val(browser);
            $("#timezone").val(timezone);
        });
    });
});

