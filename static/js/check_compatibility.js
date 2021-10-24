odoo.define('custom_ezim.checkCompatibility', function(require){
"use strict";

    var Widget = require('web.Widget');
    var core = require('web.core');
    var _t = core._t;

    $(document).ready(function(){
        console.log('entereeeee!!!!!!!')
        var $adding = $(".check_comp");
        var message = _t('There was an error validating this imei.');


        $adding.click(function(ev){
        console.log('ev', ev)


            var imei = $('#imei').val()
//            var zip_code = $('#zip_value').val()

            console.log("imei", imei);
//            console.log("zip_code", zip_code);
            if (!imei){
                ev.preventDefault();
                ev.stopPropagation();
                alert('provide valid IMEI number or Zip Code');

            }
            if(imei.length > 15)
            {
                alert("Please enter a valid IMEI number")
                ev.preventDefault();
                return false;
            }
            else if(imei.length < 15)
            {
                alert("Please enter a valid IMEI number")
                ev.preventDefault();
                return false;
            }
        });
    });
    });
