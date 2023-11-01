odoo.define('tt.fingerprint', function (require) {
'use strict';

    var base = require('web_editor.base');
    var platform = '';
    var unique_id = crypto.randomUUID();
    var web_vendor = '';
    var timezone = '';
    $(document).ready(function() {
    //$("#kentng").click(function() {
        $(document).click(function() {
            if(typeof(localStorage.platform) === 'undefined'){
                //console.log('XXX1');
                //const fpPromise = import('https://openfpcdn.io/fingerprintjs/v4').then(FingerprintJS => FingerprintJS.load())
                //const fpPromise = import('/web/static/src/js/tt_custom/fingerprint.js').then(FingerprintJS => FingerprintJS.load())
                const fpPromise = import('/tt_base/static/tt_custom/fingerprint.js').then(FingerprintJS => FingerprintJS.load())
                // Get the visitor identifier when you need it.
                fpPromise.then(fp => fp.get()).then(result => {
                    // console.log(result);
                    // This is the visitor identifier:
                    platform = result.components.platform.value;
                    unique_id = result['visitorId'];
                    if(result.components.vendorFlavors.value.length > 0)
                        web_vendor = result.components.vendorFlavors.value[0];
                    else if(result.components.webGlBasics.value.vendor)
                        web_vendor = result.components.webGlBasics.value.vendor;
                    timezone = result.components.timezone.value;
                    localStorage.platform = platform;
                    localStorage.unique_id = unique_id;
                    localStorage.web_vendor = web_vendor;
                    localStorage.timezone = timezone;
                });
            }else{
                platform = localStorage.platform;
                unique_id = localStorage.unique_id;
                web_vendor = localStorage.web_vendor;
                timezone = localStorage.timezone;
            }
            $("#platform").val(platform);
            $("#machine_id").val(unique_id);
            $("#web_vendor").val(web_vendor);
            $("#tz").val(timezone);
        });
    });
});

