$('#add').click(function() {
    var new_chq_no = parseInt($('#total_chq').val()) + 1;
    var new_input = '<input id="new_' + new_chq_no + '" class="w3-input w3-border" name="candidate_name' + new_chq_no + '" type="text" placeholder="Candidate Name ' + new_chq_no + '">';

    $('#new_chq').append(new_input);

    $('#total_chq').val(new_chq_no);
});

$('#remove').click(function() {
    var last_chq_no = $('#total_chq').val();

    if (last_chq_no > 2)
    {
        $('#new_' + last_chq_no).remove();
        $('#total_chq').val(last_chq_no - 1);
    }
});