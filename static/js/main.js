document.addEventListener('DOMContentLoaded', function() {
  initializeUI();
});

function initializeUI() {
  fetchAndDisplayCandlestickData();
  fetchAndDisplayModels();

  setInterval(() => {
    fetchAndDisplayCandlestickData();
  }, 2000);

  document.getElementById('add-params').addEventListener('click', handleAddModelClick);
  document.getElementById('update-params').addEventListener('click', handleUpdateClick);
  document.getElementById('delete-model').addEventListener('click', handleDeleteClick);
  document.getElementById('sell-all').addEventListener('click', handleSellAllClick);
  document.getElementById('opt-out').addEventListener('click', handleOptOutClick);
}

function fetchAndDisplayCandlestickData() {
  fetch('/get_data').then(response => response.json()).then(data => {
    plotCandlestickChart(data);
  });
}

function plotCandlestickChart(data) {
  const trace = {
    x: data.map(row => new Date(row.datetime).toISOString()),
    close: data.map(row => row.close),
    decreasing: { line: { color: '#ff4136' } },
    high: data.map(row => row.high),
    increasing: { line: { color: '#2ecc40' } },
    low: data.map(row => row.low),
    open: data.map(row => row.open),
    type: 'candlestick',
    xaxis: 'x',
    yaxis: 'y'
  };

  const layout = {
    title: 'Candlestick Chart',
    autosize: true,
    height: window.innerHeight - document.getElementById('title-container').offsetHeight - 20,
    xaxis: {
      autorange: true,
      title: 'Time',
      rangeslider: { visible: false },
      tickformat: '%H:%M:%S',
      tickangle: -45,
      automargin: true,
      gridcolor: 'rgba(255, 255, 255, 0.1)'
    },
    yaxis: {
      autorange: true,
      title: 'Price',
      gridcolor: 'rgba(255, 255, 255, 0.1)'
    },
    paper_bgcolor: '#000',
    plot_bgcolor: '#000',
    font: {
      color: '#ffffff'
    }
  };

  Plotly.newPlot('graph-container', [trace], layout);
}

function fetchAndDisplayModels() {
  fetch('/get_models').then(response => response.json()).then(modelsInfo => {
    populateDropdown('model-dropdown', modelsInfo, 'params-container');
    fetchActiveModels(); // Fetch active models for the right panel
  });
}

function populateDropdown(dropdownId, models, paramsContainerId) {
  const dropdown = document.getElementById(dropdownId);
  dropdown.innerHTML = '';

  models.forEach(modelInfo => {
    let option = document.createElement('option');
    option.text = modelInfo.name;
    option.value = modelInfo.name;
    dropdown.add(option);
  });

  if (models.length > 0) {
    populateParameters(models[0], paramsContainerId);
  }

  // Add change event listener to update parameters when a new model is selected
  dropdown.onchange = function() {
    let selectedModel = models.find(model => model.name === this.value);
    if (selectedModel) {
      populateParameters(selectedModel, paramsContainerId);
    }
  };
}

function populateParameters(modelInfo, containerId) {
  const paramsContainer = document.getElementById(containerId);
  paramsContainer.innerHTML = '';

  for (const paramName in modelInfo.params) {
    let paramDiv = document.createElement('div');
    paramDiv.className = 'param';

    let label = document.createElement('label');
    label.innerText = `${paramName}:`;
    let input = document.createElement('input');
    input.type = 'text';
    input.value = modelInfo.params[paramName];

    paramDiv.appendChild(label);
    paramDiv.appendChild(input);
    paramsContainer.appendChild(paramDiv);
  }
}

function collectParams(containerId, isUpdate = false) {
  const params = {};
  const container = document.getElementById(containerId);
  const inputs = container.getElementsByTagName('input');
  let dropdown = document.getElementById('model-dropdown');
  let allValid = true;

  // If it's an update, we need to get the old name from the dropdown
  if (isUpdate) {
    let oldNameDropdown = document.getElementById('ava-model-dropdown');
    params['old_name'] = oldNameDropdown.options[oldNameDropdown.selectedIndex].value;
    dropdown = document.getElementById('ava-model-dropdown'); // Switch to the active models dropdown
  }

  for (let input of inputs) {
    const paramName = input.previousElementSibling.innerText.slice(0, -1);
    const value = input.value.trim();

    // If the parameter is 'name', allow it to be non-numeric
    if (paramName.toLowerCase() === 'name') {
      params[paramName] = value;
    } else if (isNaN(value) || Number(value) < 0) {
      input.classList.add('invalid-input');
      allValid = false;
    } else {
      input.classList.remove('invalid-input');
      params[paramName] = Number(value);
    }
  }

  if (allValid) {
    // For adding a new model, get the model name from the dropdown
    if (!isUpdate) {
      params['name'] = dropdown.options[dropdown.selectedIndex].value;
    }
    return params;
  } else {
    alert('Some parameters are invalid. Please correct them.');
    return null;
  }
}

function handleAddModelClick() {
  const params = collectParams('params-container');
  if (params) {
    addModel(params);
  }
}

function addModel(params) {
  fetch('/add_model', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(params)
  }).then(response => response.json()).then(data => {
    if (data.success) {
      alert('Model added successfully.');
      fetchAndDisplayModels(); // Fetch and display the models again, including the new one
    } else {
      alert('Error: ' + data.message);
    }
  }).catch(error => {
    console.error('Error adding model:', error);
    alert('Failed to add the model due to an error.');
  });
}

function fetchActiveModels() {
  fetch('/get_active_models').then(response => response.json()).then(activeModels => {
    populateDropdown('ava-model-dropdown', activeModels, 'ava-params-container');
  });
}


function handleUpdateClick() {
  const params = collectParams('ava-params-container', true);
  if (params) {
    updateModel(params);
  }
}

function updateModel(params) {
  fetch('/update_model', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(params)
  }).then(response => response.json()).then(data => {
    if (data.success) {
      alert('Model updated successfully.');
      fetchActiveModels(); // This should update the dropdown
      updateParametersDisplay(params.name); // Update the parameters display
    } else {
      alert('Error: ' + data.message);
    }
  }).catch(error => {
    console.error('Error updating model:', error);
    alert('Failed to update the model due to an error.');
  });
}

function updateParametersDisplay(updatedModelName) {
  // Fetch the updated model's parameters
  fetch(`/get_model_params?name=${encodeURIComponent(updatedModelName)}`)
    .then(response => response.json())
    .then(data => {
      populateParameters(data, 'ava-params-container'); // Update the parameters display
      updateDropdownSelection(updatedModelName); // Ensure dropdown is set to the updated model
    })
    .catch(error => {
      console.error('Error fetching updated model parameters:', error);
    });
}

function updateDropdownSelection(newModelName) {
  const dropdown = document.getElementById('ava-model-dropdown');
  for (let i = 0; i < dropdown.options.length; i++) {
    if (dropdown.options[i].value === newModelName) {
      dropdown.selectedIndex = i;
      break;
    }
  }
}

function handleDeleteClick() {
  const modelToDelete = document.getElementById('ava-model-dropdown').value;
  if (modelToDelete) {
    deleteModel(modelToDelete);
  }
}

function deleteModel(modelName) {
  fetch('/delete_model', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ name: modelName })
  }).then(response => response.json()).then(data => {
    if (data.success) {
      alert('Model deleted successfully.');
      fetchActiveModels(); // Refresh the list of active models
      clearParameters('ava-params-container'); // Clear the parameters display area
    } else {
      alert('Error: ' + data.message);
    }
  }).catch(error => {
    console.error('Error deleting model:', error);
    alert('Failed to delete the model due to an error.');
  });
}

function clearParameters(containerId) {
  const paramsContainer = document.getElementById(containerId);
  paramsContainer.innerHTML = ''; // Clear the inner HTML, removing parameter fields
}

function handleSellAllClick() {
  alert('Sell All functionality not implemented.');
}

function handleOptOutClick() {
  alert('Opt Out functionality not implemented.');
}
