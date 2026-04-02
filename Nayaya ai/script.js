// Function to update the label when a file is picked
function updateFileName() {
    const fileInput = document.getElementById('evidenceFile');
    const display = document.getElementById('fileNameDisplay');
    if (fileInput.files.length > 0) {
        display.innerText = fileInput.files[0].name;
        display.classList.add('text-blue-600', 'font-medium');
    }
}

// Function to handle the actual upload
async function handleEvidenceUpload() {
    const firNo = document.getElementById('evidenceFirNo').value;
    const fileInput = document.getElementById('evidenceFile');
    
    if (!firNo || fileInput.files.length === 0) {
        alert("Please provide both an FIR number and a file.");
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const response = await fetch(`/upload_evidence/${encodeURIComponent(firNo)}`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.success) {
            alert("Evidence successfully secured in locker.");
            fileInput.value = ""; // Reset
            document.getElementById('fileNameDisplay').innerText = "Select Evidence File";
        } else {
            alert("Upload failed: " + result.error);
        }
    } catch (error) {
        console.error("Error:", error);
    }
}

function handleSearch() {
    const input = document.getElementById('userInput').value;
    if (input.trim() !== "") {
        // Here you would normally redirect or update the UI
        alert("Connecting to Nyaya AI for: " + input);
        
        /* In a real app, you would use:
        window.location.href = `chat.html?query=${encodeURIComponent(input)}`;
        */
    } else {
        alert("Please enter a legal query.");
    }
}

// Add Enter key support
document.getElementById('userInput')?.addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        handleSearch();
    }
});