(function (){
    // console.log(context)
    $.each(context.groups, function (idx, group) {
        $.ajax({
            type: 'post',
            url: group.nsid,
            data: {
                group: group,
                csrfmiddlewaretoken: context.csrf_token
            },
            success: ajax_success,
            dataType: 'html'
        });
    });
}())

function ajax_success(data, textStatus, jqXHR) {
    $('#groups').append(data)
}
