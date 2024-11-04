async function uploadFile() {
    const formData = new FormData();
    const fileInput = document.getElementById('file');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('Please select a file to upload.');
        return;
    }

    formData.append('file', file);

    document.getElementById('loadingSpinner').style.display = 'block';
    document.getElementById('resultContainer').style.display = 'none';
    document.getElementById('errorMessage').style.display = 'none';
    document.getElementById('pieChartContainer').style.display = 'none';

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.status === 'success') {
            displayResults(result);
            displayPieChart(result.aggressive_percentage, result.contributions);
        } else {
            displayError(result.message);
        }
    } catch (error) {
        console.error('Error uploading file:', error);
        displayError('An error occurred while uploading the file.');
    } finally {
        document.getElementById('loadingSpinner').style.display = 'none';
    }
}

function displayResults(result) {
    const tableBody = document.getElementById('resultTableBody');
    tableBody.innerHTML = '';

    // Display only the first 5 rows
    const displayRows = result.result.slice(0, 5);

    displayRows.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${row.time}</td>
            <td>${row.SPD}</td>
            <td>${row.acceleration}</td>
            <td>${row.deceleration}</td>
            <td>${row.stop_frequency}</td>
            <td>${row.idle_time}</td>
            <td>${row.behavior_category}</td>
        `;
        tableBody.appendChild(tr);
    });

    document.getElementById('aggressivePercentage').textContent = `${result.aggressive_percentage.toFixed(2)}%`;

    document.getElementById('resultContainer').style.display = 'block';
}

function displayError(message) {
    const errorMessage = document.getElementById('errorMessage');
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
}

function displayPieChart(aggressivePercentage, contributions) {
    const normalPercentage = 100 - aggressivePercentage;

    // Labels for the pie chart sections
    const labels = ['Normal', 'Aggressive (SPD)', 'Aggressive (Acceleration)', 'Aggressive (Deceleration)', 'Aggressive (Stop Frequency)', 'Aggressive (Idle Time)'];
    const values = [
        normalPercentage,
        contributions['SPD'] * aggressivePercentage,
        contributions['acceleration'] * aggressivePercentage,
        contributions['deceleration'] * aggressivePercentage,
        contributions['stop_frequency'] * aggressivePercentage,
        contributions['idle_time'] * aggressivePercentage
    ];

    const ctx = document.getElementById('behaviorPieChart').getContext('2d');
    if (window.myPieChart) {
        window.myPieChart.destroy();
    }
    window.myPieChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                label: 'Behavior Categories',
                data: values,
                backgroundColor: [
                    'rgb(54, 162, 235)',    // Normal
                    'rgb(255, 99, 132)',   // Aggressive (SPD)
                    'rgb(255, 159, 64)',   // Aggressive (Acceleration)
                    'rgb(75, 192, 192)',   // Aggressive (Deceleration)
                    'rgb(153, 102, 255)',  // Aggressive (Stop Frequency)
                    'rgb(255, 205, 86)'    // Aggressive (Idle Time)
                ],
                borderColor: [
                    'rgb(54, 162, 235)',   // Normal
                    'rgb(255, 99, 132)',   // Aggressive (SPD)
                    'rgb(255, 159, 64)',   // Aggressive (Acceleration)
                    'rgb(75, 192, 192)',   // Aggressive (Deceleration)
                    'rgb(153, 102, 255)',  // Aggressive (Stop Frequency)
                    'rgb(255, 205, 86)'    // Aggressive (Idle Time)
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: ${context.raw.toFixed(2)}%`;
                        }
                    }
                }
            }
        }
    });

    document.getElementById('pieChartContainer').style.display = 'block';
}
