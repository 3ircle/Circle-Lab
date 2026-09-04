// Utility functions & Interactive behaviors for Data Platform Template

document.addEventListener('DOMContentLoaded', function () {
    // Tooltip initialization
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // File Upload Drag and Drop Simulation
    const dropzone = document.getElementById('uploadDropzone');
    const fileInput = document.getElementById('datasetFileInput');
    const fileInfo = document.getElementById('selectedFileInfo');

    if (dropzone && fileInput) {
        dropzone.addEventListener('click', () => fileInput.click());

        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });

        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('dragover');
        });

        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                updateFileInfo(e.dataTransfer.files[0]);
            }
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length) {
                updateFileInfo(fileInput.files[0]);
            }
        });
    }

    function updateFileInfo(file) {
        if (fileInfo) {
            const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
            fileInfo.innerHTML = `
                <div class="alert alert-success d-flex align-items-center justify-content-between mt-3 bg-opacity-10 border-success text-success" role="alert">
                    <div class="d-flex align-items-center">
                        <i class="bi bi-file-earmark-spreadsheet-fill fs-4 me-2"></i>
                        <div>
                            <strong>${file.name}</strong> (${fileSizeMB} MB)
                        </div>
                    </div>
                    <i class="bi bi-check-circle-fill"></i>
                </div>
            `;
        }
    }

    // AI Chat Prompt Quick Insertion
    const promptButtons = document.querySelectorAll('.prompt-suggestion');
    const chatInput = document.getElementById('chatInputField');

    if (promptButtons && chatInput) {
        promptButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                chatInput.value = btn.innerText.trim();
                chatInput.focus();
            });
        });
    }
});
