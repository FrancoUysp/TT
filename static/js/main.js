document.addEventListener('DOMContentLoaded', function() {
  fetchModelsAndParams();
  setInterval(updateUI, 2000);
});

function updateUI() {

  // Fetch and update ROI values
  fetch('/get_roi_day').then(response => response.json()).then(data => {
    document.getElementById('roi-day').innerText = `Daily ROI: ${data.daily_roi}`;
  });

  fetch('/get_data').then(response => response.json()).then(data => {
    const trace = {
      x: data.map(row => {
        let date = new Date(row.datetime);
        return date.toISOString();
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

}
function fetchModelsAndParams() {
  fetch('/get_models').then(response => response.json()).then(modelsInfo => {
    console.log("Received models info:", modelsInfo); // Debug: log the received modelsInfo

    const modelDropdown = document.getElementById('model-dropdown');
    const paramsContainer = document.getElementById('params-container');

    modelDropdown.innerHTML = '';
    paramsContainer.innerHTML = '';

    modelsInfo.forEach(modelInfo => {
      console.log("Processing model:", modelInfo.name); // Debug: log the current model being processed

      let option = new Option(modelInfo.name, modelInfo.name);
      modelDropdown.add(option);

      let paramsSection = document.createElement('section');
      paramsSection.id = `${modelInfo.name}-params`;
      paramsSection.style.display = 'none';

      for (const [paramName, paramDetails] of Object.entries(modelInfo.params)) {
        console.log(`Processing param: ${paramName}`, paramDetails); // Shows the details of param

        if (paramDetails instanceof Object) {
          for (const [detailName, detailValue] of Object.entries(paramDetails)) {
            let paramDiv = document.createElement('div');
            paramDiv.className = 'param';
            paramDiv.style.display = 'flex'; // Use flexbox for layout
            paramDiv.style.justifyContent = 'space-between'; // Space between label and input
            paramDiv.style.alignItems = 'center'; // Align items vertically
            paramDiv.style.marginBottom = '5px'; // Reduced space between items

            let label = document.createElement('label');
            label.setAttribute('for', `${modelInfo.name}-${paramName}-${detailName}`);
            label.innerText = `${detailName}:`;
            label.style.flexBasis = '40%'; // Label takes up 40% of the div

            let input = document.createElement('input');
            input.type = 'text';
            input.id = `${modelInfo.name}-${paramName}-${detailName}`;
            input.name = `${modelInfo.name}-${paramName}-${detailName}`;
            input.value = detailValue;
            input.style.flexBasis = '60%'; // Input takes up 60% of the div

            paramDiv.appendChild(label);
            paramDiv.appendChild(input);
            paramsSection.appendChild(paramDiv);
          }
        } else {
          // If paramDetails is not an object, handle as a primitive value
          let paramDiv = document.createElement('div');
          paramDiv.className = 'param';

          let label = document.createElement('label');
          label.setAttribute('for', `${modelInfo.name}-${paramName}`);
          label.innerText = `${paramName}:`;

          let input = document.createElement('input');
          input.type = 'text';
          input.id = `${modelInfo.name}-${paramName}`;
          input.name = `${modelInfo.name}-${paramName}`;
          input.value = paramDetails;

          paramDiv.appendChild(label);
          paramDiv.appendChild(input);
          paramsSection.appendChild(paramDiv);
        }
      }

      paramsContainer.appendChild(paramsSection);
    });

    modelDropdown.addEventListener('change', function() {
      document.querySelectorAll('#params-container > section').forEach(section => {
        section.style.display = 'none';
      });
      let selectedModel = this.value;
      document.getElementById(`${selectedModel}-params`).style.display = 'block';
    });

    modelDropdown.dispatchEvent(new Event('change'));

    let addButton = document.getElementById('add-params');
    if (!addButton) {
      // 'Set' button does not exist, create it.
      addButton = document.createElement('button');
      addButton.id = 'add-params';
      addButton.className = 'action-button';
      addButton.innerText = 'Add';
      addButton.addEventListener('click', setModelParams); // Ensure the event listener is added
      paramsContainer.appendChild(addButton);
    } else {
      // 'Set' button exists, update the event listener if necessary
      addButton.removeEventListener('click', setModelParams); // Remove the old event listener
      addButton.addEventListener('click', setModelParams); // Add the new event listener
    }
  });

}

function setModelParams() {
  let allValid = true; // Flag to track validation status
  const params = {};

  console.log("Setting parameters...");

  // Iterate through each parameter input and validate
  document.querySelectorAll('#params-container .param input').forEach(input => {
    const name = input.name;
    const value = input.value.trim();

    console.log(`Validating param: ${name}, Value: ${value}`);

    // Remove previous invalid class if any
    input.classList.remove('invalid-input');

    // Check if the value is a number and non-negative
    if (!isNaN(value) && Number(value) >= 0) {
      params[name] = Number(value);
    } else {
      // Add invalid input class and set the flag to false
      input.classList.add('invalid-input');
      console.log(`Invalid param: ${name}`);
      allValid = false;
    }
  });

  if (!allValid) {
    alert('Some parameters are invalid. Please correct them.');
    return; // Exit the function if there are any invalid params
  }

  // Confirm with the user
  if (confirm('Are you sure you want to set these parameters?')) {
    // Make a POST request to set the parameters
    fetch('/set_params', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(params)
    })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          alert(data.message);
        } else {
          alert('There was an error setting the parameters.');
        }
      })
      .catch(error => {
        console.error('Error:', error);
        alert('Failed to set parameters.');
      });
  }
}

function addModelParams() {
  const params = {};
  let allValid = true;

  // Collect all the parameters from the input fields
  document.querySelectorAll('#params-container .param input').forEach(input => {
    const name = input.name;
    const value = input.value.trim();
    if (!isNaN(value) && Number(value) >= 0) {
      params[name] = Number(value);
    } else {
      allValid = false;
    }
  });

  // If all parameters are valid, send them to the server
  if (allValid) {
    fetch('/add_model', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(params)
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        alert('Model added successfully.');
      } else {
        alert('Failed to add the model.');
      }
    })
    .catch(error => {
      console.error('Error:', error);
      alert('Failed to add the model.');
    });
  } else {
    alert('Some parameters are invalid. Please correct them before adding the model.');
  }
}
