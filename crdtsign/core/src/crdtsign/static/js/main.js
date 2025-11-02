document.addEventListener("DOMContentLoaded", function () {
  // Tab switching functionality
  const tabButtons = document.querySelectorAll(".tab-button");
  const tabContents = document.querySelectorAll(".tab-content");

  tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      // Remove active class from all buttons and tabs
      tabButtons.forEach((btn) =>
        btn.classList.remove("bg-indigo-100", "text-indigo-700"),
      );
      tabButtons.forEach((btn) =>
        btn.classList.add("text-gray-500", "hover:text-gray-700"),
      );
      tabContents.forEach((content) => content.classList.remove("active"));

      // Add active class to clicked button and corresponding tab
      button.classList.add("bg-indigo-100", "text-indigo-700");
      button.classList.remove("text-gray-500", "hover:text-gray-700");
      const tabId = button.getAttribute("data-tab");
      document.getElementById(`${tabId}-tab`).classList.add("active");
    });
  });

  // Load signatures on page load
  loadSignatures();

  // Set up form submissions
  document
    .getElementById("sign-form")
    .addEventListener("submit", handleSignSubmit);
  document
    .getElementById("verify-form")
    .addEventListener("submit", handleVerifySubmit);

  // Set up modal close buttons
  document
    .getElementById("close-modal")
    .addEventListener("click", closeDetailsModal);
  document
    .getElementById("close-delete-modal")
    .addEventListener("click", closeDeleteModal);
  document
    .getElementById("cancel-delete-btn")
    .addEventListener("click", closeDeleteModal);

  // Refresh signatures view on tab button press
  document
    .getElementById("signatures-tab-btn")
    .addEventListener("click", loadSignatures);

  // Set default expiration date (10 minutes from now in local time)
  const expirationInput = document.getElementById("expiration-date");
  const now = new Date();
  now.setMinutes(now.getMinutes() + 10);

  // Format date in local timezone for the datetime-local input
  // YYYY-MM-DDThh:mm format required by datetime-local input
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  const hours = String(now.getHours()).padStart(2, "0");
  const minutes = String(now.getMinutes()).padStart(2, "0");

  expirationInput.value = `${year}-${month}-${day}T${hours}:${minutes}`;
});

// Add state management at the top of the file
const state = {
  isDeleting: false,
  currentDeleteId: null,
};

// Load signatures from the API
async function loadSignatures() {
  try {
    const response = await fetch("/api/signatures");
    const data = await response.json();
    formatSignaturesTable(data.signatures);

    // Remove existing event listeners by cloning and replacing the table
    const tableBody = document.getElementById("signatures-table");
    const newTableBody = tableBody.cloneNode(true);
    tableBody.parentNode.replaceChild(newTableBody, tableBody);

    // Add event listeners to the details, validate and delete buttons
    document.querySelectorAll(".view-details").forEach((btn) => {
      btn.addEventListener("click", () => {
        const sigId = btn.getAttribute("data-id");
        // Fetch the signature details from the API
        fetch(`/api/signatures/${sigId}`)
          .then((response) => {
            if (!response.ok) {
              throw new Error(
                `HTTP ${response.status}: ${response.statusText}`,
              );
            }
            return response.json();
          })
          .then((data) => {
            if (data.signature) {
              showSignatureDetails(data.signature);
            } else {
              alert("Error: Signature not found");
            }
          })
          .catch((error) => {
            console.error("Error fetching signature details:", error);
            alert(`Error fetching signature details: ${error.message}`);
          });
      });
    });

    document.querySelectorAll(".validate-btn").forEach((btn) => {
      btn.addEventListener("click", () =>
        validateSignature(btn.getAttribute("data-id")),
      );
    });

    document.querySelectorAll(".delete-btn").forEach((btn) => {
      btn.addEventListener("click", () =>
        showDeleteConfirmation(btn.getAttribute("data-id")),
      );
    });
  } catch (error) {
    console.error("Error loading signatures:", error);
  }
}

// Format the signatures table
function formatSignaturesTable(signatures) {
  const tableBody = document.getElementById("signatures-table");
  tableBody.innerHTML = "";

  if (signatures.length === 0) {
    tableBody.innerHTML = `
            <tr>
                <td colspan="5" class="px-6 py-4 text-center text-gray-500">No signatures found</td>
            </tr>
        `;
    return;
  }

  signatures.forEach((sig) => {
    const row = document.createElement("tr");

    // Format the date
    const signedDate = new Date(sig.signed_on);
    const formattedDate = signedDate.toLocaleString();

    // Format expiration date if it exists
    let expirationText = "No expiration";
    if (sig.expiration_date) {
      const expirationDate = new Date(sig.expiration_date);
      expirationText = expirationDate.toLocaleString();
    }

    // Use username if available, otherwise fall back to user_id
    const displayName = sig.username || sig.user_id;

    row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${sig.name}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${displayName}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${formattedDate}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${expirationText}</td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <button class="text-indigo-600 hover:text-indigo-900 mr-2 view-details" data-id="${sig.id}">Details</button>
                <button class="text-green-600 hover:text-green-900 mr-2 validate-btn" data-id="${sig.id}">Validate</button>
                <button class="text-red-600 hover:text-red-900 delete-btn" data-id="${sig.id}" ${state.isDeleting ? "disabled" : ""}>Delete</button>
            </td>
        `;

    tableBody.appendChild(row);
  });
}

// Handle sign form submission
async function handleSignSubmit(event) {
  event.preventDefault();

  const form = event.target;
  const fileInput = form.querySelector("#file-to-sign");
  const expirationInput = form.querySelector("#expiration-date");

  if (!fileInput.files.length) {
    showSignResult("Please select a file to sign.", false);
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  if (expirationInput.value) {
    formData.append(
      "expiration_date",
      new Date(expirationInput.value).toISOString(),
    );
  }

  try {
    const response = await fetch("/api/signatures", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (response.ok) {
      showSignResult(
        `File signed successfully! Signature: ${data.signature.substring(0, 20)}...`,
        true,
      );
      loadSignatures(); // Reload the signatures table
    } else {
      showSignResult(`Error: ${data.error || "Unknown error"}`, false);
    }
  } catch (error) {
    showSignResult(`Error: ${error.message}`, false);
  }
}

// Show sign result message
function showSignResult(message, isSuccess) {
  const resultDiv = document.getElementById("sign-result");
  resultDiv.innerHTML = message;
  resultDiv.classList.remove(
    "hidden",
    "bg-green-100",
    "text-green-800",
    "bg-red-100",
    "text-red-800",
  );

  if (isSuccess) {
    resultDiv.classList.add("bg-green-100", "text-green-800");
  } else {
    resultDiv.classList.add("bg-red-100", "text-red-800");
  }
}

// Handle verify form submission
async function handleVerifySubmit(event) {
  event.preventDefault();

  const form = event.target;
  const fileInput = form.querySelector("#file-to-verify");
  const signatureInput = form.querySelector("#signature");
  const publicKeyInput = form.querySelector("#public-key");

  if (!fileInput.files.length) {
    showVerifyResult("Please select a file to verify.", false);
    return;
  }

  if (!signatureInput.value.trim()) {
    showVerifyResult("Please enter a signature.", false);
    return;
  }

  if (!publicKeyInput.value.trim()) {
    showVerifyResult("Please enter a public key.", false);
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  formData.append("signature", signatureInput.value.trim());
  formData.append("public_key", publicKeyInput.value.trim());

  try {
    const response = await fetch("/api/verify", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (response.ok) {
      showVerifyResult(data.message, data.is_valid);
    } else {
      showVerifyResult(`Error: ${data.error || "Unknown error"}`, false);
    }
  } catch (error) {
    showVerifyResult(`Error: ${error.message}`, false);
  }
}

// Show verify result message
function showVerifyResult(message, isValid) {
  const resultDiv = document.getElementById("verify-result");
  resultDiv.innerHTML = message;
  resultDiv.classList.remove(
    "hidden",
    "bg-green-100",
    "text-green-800",
    "bg-red-100",
    "text-red-800",
  );

  if (isValid) {
    resultDiv.classList.add("bg-green-100", "text-green-800");
  } else {
    resultDiv.classList.add("bg-red-100", "text-red-800");
  }
}

// Validate a signature
async function validateSignature(signatureId) {
  try {
    const response = await fetch(`/api/validate/${signatureId}`);
    const data = await response.json();

    if (response.ok) {
      // Show toast notification instead of opening details modal
      const signature = data.signature;
      let validationMessage = "";
      let messageClass = "";

      // Convert expiration date to local time if present in the message
      let message = data.message;
      if (signature.expiration_date) {
        // Extract the ISO date from the message
        const isoDateMatch = message.match(
          /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[\+\-][\d:]+/,
        );
        if (isoDateMatch) {
          const isoDate = isoDateMatch[0];
          const localDate = new Date(isoDate).toLocaleString();
          message = message.replace(isoDate, localDate);
        }
      }

      if (data.is_valid) {
        validationMessage = `Signature for ${signature.name} is valid. ${message}`;
        messageClass = "bg-green-100 text-green-700";
      } else {
        validationMessage = `Signature for ${signature.name} is invalid. ${message}`;
        messageClass = "bg-red-100 text-red-700";
      }

      // Create a notification div
      const notification = document.createElement("div");
      notification.className = `p-4 rounded-md shadow-md ${messageClass} max-w-md`;
      notification.innerHTML = `
          <div class="flex justify-between items-center">
              <p class="font-medium">${validationMessage}</p>
              <button class="ml-4 text-gray-500 hover:text-gray-700 focus:outline-none">
                  <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
              </button>
          </div>
      `;

      // Add close button functionality
      notification
        .querySelector("button")
        .addEventListener("click", function () {
          notification.remove();
        });

      // Add to notification container and auto-remove after 5 seconds
      const container = document.getElementById("notification-container");
      container.appendChild(notification);
      setTimeout(() => {
        if (container.contains(notification)) {
          notification.remove();
        }
      }, 5000);
    } else {
      alert(`Error: ${data.error || "Unknown error"}`);
    }
  } catch (error) {
    alert(`Error: ${error.message}`);
  }
}

// Show signature details in modal
function showSignatureDetails(signature) {
  document.getElementById("modal-file-name").textContent = signature.name;
  document.getElementById("modal-file-hash").textContent = signature.hash;
  document.getElementById("modal-signature").textContent = signature.signature;

  const downloadBtn = document.getElementById("download-btn");
  downloadBtn.addEventListener(
    "click",
    async () => {
      try {
        const fileId = signature.id;
        const fileName = signature.name;

        if (!fileId) {
          console.error("Download Error: No file ID found in signature.");
          return;
        }

        const response = await fetch(`/api/download/${fileId}`);

        if (!response.ok) {
          throw new Error(
            `Network response was not ok: ${response.statusText}`,
          );
        }

        const blob = await response.blob();

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.style.display = "none";
        a.href = url;
        a.download = fileName;

        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } catch (error) {
        console.error("Download failed:", error);
        alert("Download failed. Please try again.");
      }
    },
    false,
  );

  // Show username if available, otherwise show user_id
  const displayName = signature.username || signature.user_id;
  document.getElementById("modal-user-id").textContent = displayName;

  const signedDate = new Date(signature.signed_on);
  document.getElementById("modal-signed-on").textContent =
    signedDate.toLocaleString();

  // Handle expiration date
  const expirationContainer = document.getElementById(
    "modal-expiration-container",
  );
  if (signature.expiration_date) {
    expirationContainer.classList.remove("hidden");
    const expirationDate = new Date(signature.expiration_date);
    document.getElementById("modal-expiration").textContent =
      expirationDate.toLocaleString();
  } else {
    expirationContainer.classList.add("hidden");
  }

  // Show validation status
  // const validationContainer = document.getElementById(
  //   "modal-validation-status-container",
  // );
  // const validationStatus = document.getElementById("modal-validation-status");
  //
  const dataRetentionWarningContainer = document.getElementById(
    "modal-data-retention-warning-container",
  );
  if (signature.flag_data_retention) {
    const dataRetentionWarningText = document.getElementById(
      "modal-data-retention-warning-text",
    );
    dataRetentionWarningText.innerHTML =
      "Warning: The assigned expiration date has been overriden by the data retention policy configured by the administrator.";
    dataRetentionWarningText.innerHTML += ` This signature will expire <strong>${signature.time_to_data_retention}</strong>.`;
    dataRetentionWarningContainer.classList.remove("hidden");
  }

  // Show the modal
  document.getElementById("signature-details-modal").classList.remove("hidden");
}

async function handleFileDownload(fileId) {
  const response = await fetch(`/api/download/${fileId}`);
  if (!response.ok) {
    throw new Error(`Network response was not ok: ${response.statusText}`);
  }

  return response.blob();
}

// Close the details modal
function closeDetailsModal() {
  document.getElementById("signature-details-modal").classList.add("hidden");
}

// Show delete confirmation
function showDeleteConfirmation(signatureId) {
  if (state.isDeleting) {
    return; // Prevent multiple delete operations
  }

  state.currentDeleteId = signatureId;

  // Get the signature details
  fetch(`/api/signatures/${signatureId}`)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data.signature) {
        document.getElementById("delete-file-name").textContent =
          `File: ${data.signature.name}`;
        document
          .getElementById("confirm-delete-btn")
          .setAttribute("data-id", signatureId);
        document
          .getElementById("delete-confirmation-modal")
          .classList.remove("hidden");

        // Remove any existing event listeners
        const confirmBtn = document.getElementById("confirm-delete-btn");
        const newConfirmBtn = confirmBtn.cloneNode(true);
        confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);

        // Add event listener to the confirm button
        newConfirmBtn.addEventListener("click", () => {
          deleteSignature(signatureId);
        });
      }
    })
    .catch((error) => {
      console.error("Error fetching signature details:", error);
      alert("Error fetching signature details");
      state.currentDeleteId = null;
    });
}

// Delete a signature
async function deleteSignature(signatureId) {
  if (state.isDeleting || state.currentDeleteId !== signatureId) {
    return; // Prevent multiple delete operations or deleting wrong signature
  }

  state.isDeleting = true;

  try {
    const response = await fetch(`/api/signatures/${signatureId}`, {
      method: "DELETE",
    });

    const data = await response.json();

    if (response.ok) {
      closeDeleteModal();
      alert("Signature deleted successfully");
      loadSignatures(); // Reload the signatures table
    } else {
      alert(`Error: ${data.error || "Unknown error"}`);
    }
  } catch (error) {
    alert(`Error: ${error.message}`);
  } finally {
    state.isDeleting = false;
    state.currentDeleteId = null;
  }
}

// Close the delete modal
function closeDeleteModal() {
  document.getElementById("delete-confirmation-modal").classList.add("hidden");
}
