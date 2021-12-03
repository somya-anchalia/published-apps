
var error_count = 0;

function validate() {
	error_count = 0;
	if($('#server').val() == "" || $('#port').val() == "" ||
		$('#username').val() == "" || $('#password').val() == "") {
		if($('#home-tab:has(small)').length == 0)
			$('.nav-tabs').find('a[href^="#home"]').append(' <small class="required">***</small>');
		error_count = error_count + 1;
		$('#home input').each(function () {
			
			if($("#"+this.id).val() == "") {
				$("#"+this.id).addClass("error");
			}
			if($("#"+this.id).val() != "") {
				$("#"+this.id).removeClass("error");
			}
		});
	}
	else {
		$('#home-tab').find('small').remove();
		$('#home input').each(function () {
			if($("#"+this.id).val() != "") {
				$("#"+this.id).removeClass("error");
			}
		});
	}

	if($('#malop_escalation_interval').val() == "" || $('#malop_escalation_interval').val() == "0") {
		error_count = error_count + 1;
		$('#malop_escalation_interval').addClass("error");
	}
	else {
		$('#malop_escalation_interval').removeClass("error");
	}

	if($('#malop_back_days').val() == "" || $('#malop_back_days').val() == "0") {
		error_count = error_count + 1;
		$('#malop_back_days').addClass("error");
	}
	else {
		$('#malop_back_days').removeClass("error");
	}

	if($('#malware_escalation_interval').val() == "" || $('#malware_escalation_interval').val() == "0") {
		error_count = error_count + 1;
		$('#malware_escalation_interval').addClass("error");
	}
	else {
		$('#malware_escalation_interval').removeClass("error");
	}

	if($('#malware_back_days').val() == "" || $('#malware_back_days').val() == "0") {
		error_count = error_count + 1;
		$('#malware_back_days').addClass("error");
	}
	else {
		$('#malware_back_days').removeClass("error");
	}

	if($('#chkProxy').prop("checked") == true){
		if($('#proxy_ip').val() == "" || $('#proxy_port').val() == ""){
			if($('#proxy-tab:has(small)').length == 0)
				$('.nav-tabs').find('a[href^="#proxy"]').append(' <small class="required">***</small>');
			error_count = error_count + 1;
			if($("#proxy_ip").val() == "") {
				$("#proxy_ip").addClass("error");
			}
			if($("#proxy_ip").val() != "") {
				$("#proxy_ip").removeClass("error");
			}

			if($("#proxy_port").val() == "") {
				$("#proxy_port").addClass("error");
			}
			if($("#proxy_port").val() != "") {
				$("#proxy_port").removeClass("error");
			}
		}
		else{
			$('#proxy-tab').find('small').remove();
			$("#proxy_ip").removeClass("error");
			$("#proxy_port").removeClass("error");
		}
	}
	else{
		$("#proxy_ip").removeClass("error");
		$("#proxy_port").removeClass("error");
	}

	if($('#chkProxyAuth').prop("checked") == true){
		if($('#proxy_user').val() == "" || $('#proxy_pass').val() == ""){
			if($('#proxy-tab:has(small)').length == 0)
				$('.nav-tabs').find('a[href^="#proxy"]').append(' <small class="required">***</small>');
			error_count = error_count + 1;
			if($("#proxy_user").val() == "") {
				$("#proxy_user").addClass("error");
			}
			if($("#proxy_user").val() != "") {
				$("#proxy_user").removeClass("error");
			}

			if($("#proxy_pass").val() == "") {
				$("#proxy_pass").addClass("error");
			}
			if($("#proxy_pass").val() != "") {
				$("#proxy_pass").removeClass("error");
			}

		}
		else {
			$('#proxy-tab').find('small').remove();
			$("#proxy_user").removeClass("error");
			$("#proxy_pass").removeClass("error");
		}
	}
	else {
		$("#proxy_user").removeClass("error");
		$("#proxy_pass").removeClass("error");
	}

	if($('#chkProxyAuth').prop("checked") == false && $('#chkProxy').prop("checked") == false){
		$('#proxy-tab').find('small').remove();
	}

	if(error_count > 0) {
		return false;
	}
	return true;
}