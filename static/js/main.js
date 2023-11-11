document.addEventListener('DOMContentLoaded', function() {
  // Update UI with fetched data
  function updateUI() {
    // Fetch and update models dropdown
    fetch('/get_models').then(response => response.json()).then(models => {
      const modelDropdown = document.getElementById('model-dropdown');
      models.forEach(model => {
        let option = new Option(model, model);
        modelDropdown.add(option);
      });
    });

    // Fetch and update ROI values
    fetch('/get_roi_day').then(response => response.json()).then(data => {
      document.getElementById('roi-day').innerText = `Daily ROI: ${data.daily_roi}`;
    });

    // Fetch and render graph
    fetch('/get_data').then(response => response.json()).then(data => {
      const trace = {
        //i only want the time
        x: data.map(row => {
          let date = new Date(row.datetime); // Parse the datetime string into a Date object
          date.setHours(date.getHours() - 2); // Add 2 hours to the time

          // Format the time to HH:MM:SS, ensuring that hours, minutes, and seconds are two digits
          let hours = String(date.getHours()).padStart(2, '0');
          let minutes = String(date.getMinutes()).padStart(2, '0');
          let seconds = String(date.getSeconds()).padStart(2, '0');

          return `${hours}:${minutes}:${seconds}`;
        }),
        close: data.map(row => row.close),
        decreasing: { line: { color: 'red' } },
        high: data.map(row => row.high),
        increasing: { line: { color: 'green' } },
        low: data.map(row => row.low),
        open: data.map(row => row.open),
        type: 'candlestick',
        xaxis: 'x',
        yaxis: 'y'
      };

      const layout = {
        title: 'Candlestick Chart',
        autosize: true, // This will cause the plot to resize to the container
        height: window.innerHeight - document.getElementById('title-container').offsetHeight - 20, // Adjust the height dynamically
        xaxis: {
          title: 'Time',
          rangeslider: { visible: false },
          gridcolor: 'rgba(255, 255, 255, 0.1)',
          tickformat: '%H:%M:%S', // This will ensure only the time is shown
          tickangle: -45, // Tilt the labels to prevent overlap
          automargin: true, // Automatically adjust margins to fit labels
          title: {
            text: 'Time',
            font: {
              color: '#ffffff'
            }
          }
        },
        yaxis: {
          gridcolor: 'rgba(255, 255, 255, 0.1)',
          title: 'Price'
        },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: {
          color: '#ffffff'
        }
      };

      Plotly.newPlot('graph-container', [trace], layout);

    });

    // ...fetch for monthly and all-time ROI
  }
  // Call the updateUI function to populate data on page load
  updateUI();
});
