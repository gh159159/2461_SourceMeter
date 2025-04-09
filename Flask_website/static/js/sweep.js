$(document).ready(function() {
    $('#sweep-form').on('submit', function(event) {
        event.preventDefault();
        $.ajax({
            url: '/measure',
            type: 'POST',
            data: $(this).serialize(),
            success: function(response) {
                if (response.error) {
                    alert(response.error);
                } else {
                    const ctx = document.getElementById('sweep-chart').getContext('2d');
                    new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: response.voltages,
                            datasets: [{
                                label: 'Current (A)',
                                data: response.currents,
                                borderColor: 'rgba(75, 192, 192, 1)',
                                borderWidth: 1,
                                fill: false
                            }]
                        },
                        options: {
                            scales: {
                                x: {
                                    title: {
                                        display: true,
                                        text: 'Voltage (V)'
                                    }
                                },
                                y: {
                                    title: {
                                        display: true,
                                        text: 'Current (A)'
                                    }
                                }
                            }
                        }
                    });
                }
            }
        });
    });
});
