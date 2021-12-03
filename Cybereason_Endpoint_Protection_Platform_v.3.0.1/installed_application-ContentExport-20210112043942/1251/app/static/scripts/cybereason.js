function alert_popups_blocked()
{
    alert("Your browser is configured to block pop-ups. Please disable this feature to continue.");
}

function open_malop_details(result) {
    // console.log("Hey, I am entered into Cybereason UI");
    // console.log(result);
    var lookup_form = window.open(result.context, "Cybereason Malop Information", "status=1,toolbar=1,resizeable=1,scrollbars=1,width=1000,height=500"
    );
    if (!!lookup_form)
        lookup_form.focus();
    else
        alert_popups_blocked();
}

function open_affected_machines_and_users_details(result) {
    // console.log(result);
    application_id = 0;
    if (typeof(CURRENT_SCOPE) == "undefined") {
        throw new Error("Unable to determine application id");
    } else {
        application_id = CURRENT_SCOPE;
    }
    // console.log("Hey, I am entered into cs_update_detection_status");
    var lookup_form = window.open("/console/plugins/" + result.app_id + "/app_proxy/open_affected_machines_and_users_details?server="+result.server+"&&malop_id="+result.malop_id+"&&detection_engine="+result.detection_engine,
    "Affected Machines and Users",
    "width=720,height=380,resizable=no,scrollbars=no,status=yes,toolbar=no,location=no,menubar=no"
    );
    if (!!lookup_form)
        lookup_form.focus();
    else
        alert_popups_blocked();
}

function open_connection_details(result) {
    // console.log(result);
    application_id = 0;
    if (typeof(CURRENT_SCOPE) == "undefined") {
        throw new Error("Unable to determine application id");
    } else {
        application_id = CURRENT_SCOPE;
    }
    console.log("Hey, I am entered into open_connection_details");
    var lookup_form = window.open("/console/plugins/" + application_id + "/app_proxy/open_connection_details?server="+result.server+"&&malop_id="+result.malop_id,
    "Connection Data",
    "width=720,height=380,resizable=no,scrollbars=no,status=yes,toolbar=no,location=no,menubar=no"
    );
    if (!!lookup_form)
        lookup_form.focus();
    else
        alert_popups_blocked();
}

function cr_malop_status(result) {
    // console.log(result);
    application_id = 0;
    if (typeof(CURRENT_SCOPE) == "undefined") {
        throw new Error("Unable to determine application id");
    } else {
        application_id = CURRENT_SCOPE;
    }
    // console.log("Hey, I am entered into cs_update_detection_status");
    var lookup_form = window.open("/console/plugins/" + application_id + "/app_proxy/cr_update_malop_status?server="+result.server+"&&malop_id="+result.malop_id,
    "Cybereason Malop Status",
    "width=720,height=380,resizable=no,scrollbars=no,status=yes,toolbar=no,location=no,menubar=no"
    );
    if (!!lookup_form)
        lookup_form.focus();
    else
        alert_popups_blocked();
}