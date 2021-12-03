/*
 asa_init.js
 '''
 Written by Aplura, LLC
 Copyright (C) 2016-2020 Aplura, ,LLC

 This program is free software; you can redistribute it and/or
 modify it under the terms of the GNU General Public License
 as published by the Free Software Foundation; either version 2
 of the License, or (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
 '''
 */
require([
    "jquery",
    "asa_config",
    "splunkjs/ready!",
    "splunkjs/mvc/simplexml/ready!" ,
   "asa_mi_cybereason",
   "asa_mi_cybereason_users", 
 "asa_proxy", 
 "asa_credential", 
 "asa_readme", 
 "asa_eventgen", 
 "asa_z_appconfig_special"
], function ($,
             configManager,
             mvc,
             ignored , 
    asa_mi_cybereason,
    asa_mi_cybereason_users,
    asa_proxy,
    asa_credential,
    asa_readme,
    asa_eventgen,
    asa_z_appconfig_special
) {
    var configMan = new configManager();
    
 var miMan = new asa_mi_cybereason();
 var miMan = new asa_mi_cybereason_users();
    var appConfig_asa_proxy = new asa_proxy(); 
    var appConfig_asa_credential = new asa_credential(); 
    var appConfig_asa_readme = new asa_readme(); 
    var appConfig_asa_eventgen = new asa_eventgen(); 
    var appConfig_asa_z_appconfig_special = new asa_z_appconfig_special(); 



    var tryfunc = function() {
    if (!$(".clickable_mod_input.enablement a, .clickable.delete a").length) {
      window.requestAnimationFrame(tryfunc);
    }else {
      $(".clickable_mod_input.enablement a, .clickable.delete a").tooltip({position: {collision: "flip"}});
     }
  };
    tryfunc();
});