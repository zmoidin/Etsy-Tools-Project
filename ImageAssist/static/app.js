document.addEventListener('DOMContentLoaded', () => {
    // Nav Logic
    const navBtns = document.querySelectorAll('.nav-btn');
    const views = document.querySelectorAll('.view');
    const title = document.getElementById('tool-title');
    const desc = document.getElementById('tool-desc');

    const descriptions = {
        'auto-process': 'Automatically detect objects, slice, resize, and pad your clipart sheet to 3000x3000.',
        'image-resizer': 'Resize a single image to multiple dimensions and download a ZIP archive containing all resized versions.',
        'format-clipart': 'Format images for Etsy clipart (remove BG, 3000x3000px padding, 300 DPI)',
        'bulk-renamer': 'Sequentially rename files in a folder using a custom text pattern.'
    };

    navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            navBtns.forEach(b => b.classList.remove('active'));
            views.forEach(v => v.classList.remove('active'));
            
            btn.classList.add('active');
            const target = btn.getAttribute('data-target');
            document.getElementById(target).classList.add('active');
            
            title.textContent = btn.textContent.trim();
            desc.textContent = descriptions[target];
        });
    });

    const canvasColorSelect = document.getElementById('canvas-color-select');
    const canvasColorPicker = document.getElementById('canvas-color-picker');
    if (canvasColorSelect && canvasColorPicker) {
        canvasColorSelect.addEventListener('change', (e) => {
            if (e.target.value === 'custom') {
                canvasColorPicker.style.display = 'inline-block';
            } else {
                canvasColorPicker.style.display = 'none';
            }
        });
    }

    // Dropzone Logic
    const setupDropZone = (zoneId, inputId, onFileCallback) => {
        const zone = document.getElementById(zoneId);
        const input = document.getElementById(inputId);
        
        zone.addEventListener('click', () => input.click());
        
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('dragover');
        });
        
        zone.addEventListener('dragleave', () => {
            zone.classList.remove('dragover');
        });
        
        const traverseFileTree = async (item, path, filesArray) => {
            path = path || "";
            if (item.isFile) {
                return new Promise((resolve) => {
                    item.file((file) => {
                        filesArray.push(file);
                        resolve();
                    });
                });
            } else if (item.isDirectory) {
                const dirReader = item.createReader();
                return new Promise((resolve) => {
                    dirReader.readEntries(async (entries) => {
                        for (let i = 0; i < entries.length; i++) {
                            await traverseFileTree(entries[i], path + item.name + "/", filesArray);
                        }
                        resolve();
                    });
                });
            }
        };
        
        zone.addEventListener('drop', async (e) => {
            e.preventDefault();
            zone.classList.remove('dragover');
            
            const files = [];
            if (e.dataTransfer.items) {
                for (let i = 0; i < e.dataTransfer.items.length; i++) {
                    const item = e.dataTransfer.items[i].webkitGetAsEntry();
                    if (item) {
                        await traverseFileTree(item, '', files);
                    }
                }
            } else {
                for (let i = 0; i < e.dataTransfer.files.length; i++) {
                    files.push(e.dataTransfer.files[i]);
                }
            }
            
            if (files.length) {
                handleFiles(zone, files, onFileCallback);
            }
        });

        input.addEventListener('change', () => {
            if (input.files.length) {
                const filesArray = [];
                for(let i=0; i<input.files.length; i++){
                    filesArray.push(input.files[i]);
                }
                handleFiles(zone, filesArray, onFileCallback);
            }
        });
    };

    const handleFiles = (zone, files, callback) => {
        if(files.length > 1) {
            zone.querySelector('h3').textContent = `${files.length} files selected`;
        } else {
            zone.querySelector('h3').textContent = files[0].name;
        }
        zone.classList.add('has-file');
        
        if(callback) callback(files);
    };

    const showLoading = (text) => {
        document.getElementById('loading-text').textContent = text;
        document.getElementById('loading-overlay').classList.remove('hidden');
    };

    const hideLoading = () => {
        document.getElementById('loading-overlay').classList.add('hidden');
    };

    const showToast = (msg) => {
        const toast = document.getElementById('toast');
        toast.textContent = msg;
        toast.classList.remove('hidden');
        setTimeout(() => toast.classList.add('show'), 10);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.classList.add('hidden'), 400);
        }, 4000);
    };

    // Auto Process execution
    setupDropZone('drop-auto-process', 'file-auto-process', (files) => {
        if(!files.length) return;
        
        if (files.length > 1) {
            alert("Error: Please drop a single image file, not multiple files or a folder!");
            return;
        }
        
        if (!files[0].type.startsWith('image/')) {
            alert("Error: You dragged a folder or an invalid file. Please drop a single image file!");
            return;
        }
        
        const formData = new FormData();
        formData.append('file', files[0]);
        
        const bgType = document.getElementById('bg-type-select').value;
        formData.append('bg_type', bgType);
        
        let canvasColor = document.getElementById('canvas-color-select').value;
        if (canvasColor === 'custom') {
            canvasColor = document.getElementById('canvas-color-picker').value;
        }
        formData.append('canvas_color', canvasColor);
        
        showLoading("Slicing and processing image...");
        fetch('/api/auto-process', { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                hideLoading();
                if(data.success) showToast(data.message);
                else alert("Error: " + data.error);
            });
    });

    // Format Clipart execution
    setupDropZone('drop-format-clipart', 'file-format-clipart', (files) => {
        if(!files.length) return;
        
        const formData = new FormData();
        for(let i=0; i<files.length; i++) {
            formData.append('files[]', files[i]);
        }
        
        showLoading("Formatting clipart folder...");
        fetch('/api/format-clipart', { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                hideLoading();
                if(data.success) showToast(data.message);
                else alert("Error: " + data.error);
            });
    });

    // Image Resizer Logic
    let resizeImageFile = null;
    const container = document.getElementById('dimension-rows-container');

    setupDropZone('drop-resize-image', 'file-resize-image', (files) => {
        if (files && files.length) {
            resizeImageFile = files[0];
        }
    });

    // Helper to manage dynamic rows
    const updatePlusButtonVisibility = () => {
        const rows = container.querySelectorAll('.dimension-row');
        const firstRowBtn = container.querySelector('.dimension-row:first-child .add-dim-btn');
        if (firstRowBtn) {
            if (rows.length >= 5) {
                firstRowBtn.style.display = 'none';
            } else {
                firstRowBtn.style.display = 'flex';
            }
        }
    };

    // Listen for click on the first row's '+' button
    container.addEventListener('click', (e) => {
        if (e.target.classList.contains('add-dim-btn')) {
            const rows = container.querySelectorAll('.dimension-row');
            if (rows.length >= 5) return;

            // Create new row
            const newRow = document.createElement('div');
            newRow.className = 'dimension-row';
            newRow.innerHTML = `
                <input type="number" class="dim-width" placeholder="Width (px)" required min="1">
                <span class="dim-separator">×</span>
                <input type="number" class="dim-height" placeholder="Height (px)" required min="1">
                <button type="button" class="remove-dim-btn" title="Remove this size">×</button>
            `;
            container.appendChild(newRow);
            updatePlusButtonVisibility();
        } else if (e.target.classList.contains('remove-dim-btn')) {
            // Remove row
            const row = e.target.closest('.dimension-row');
            if (row) {
                row.remove();
                updatePlusButtonVisibility();
            }
        }
    });

    document.getElementById('btn-run-resize').addEventListener('click', () => {
        if (!resizeImageFile) {
            alert("Error: Please select or drop a target PNG image file first!");
            return;
        }

        const widthInputs = container.querySelectorAll('.dim-width');
        const heightInputs = container.querySelectorAll('.dim-height');
        
        const widths = [];
        const heights = [];
        
        for (let i = 0; i < widthInputs.length; i++) {
            const wVal = parseInt(widthInputs[i].value);
            const hVal = parseInt(heightInputs[i].value);
            
            if (isNaN(wVal) || wVal <= 0 || isNaN(hVal) || hVal <= 0) {
                alert("Error: Please fill in a valid width and height (positive integers) for all dimension rows!");
                return;
            }
            
            widths.push(wVal);
            heights.push(hVal);
        }

        const formData = new FormData();
        formData.append('file', resizeImageFile);
        widths.forEach(w => formData.append('widths[]', w));
        heights.forEach(h => formData.append('heights[]', h));

        showLoading("Resizing image to requested sizes...");
        
        fetch('/api/image-resizer', { method: 'POST', body: formData })
            .then(res => {
                if (!res.ok) {
                    return res.json().then(err => { throw new Error(err.error || 'Server error'); });
                }
                const contentDisposition = res.headers.get('Content-Disposition');
                let filename = 'resized_images.zip';
                if (contentDisposition) {
                    const match = contentDisposition.match(/filename="?([^"]+)"?/);
                    if (match) filename = match[1];
                }
                return res.blob().then(blob => ({ blob, filename }));
            })
            .then(({ blob, filename }) => {
                hideLoading();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
                showToast("Images resized and ZIP downloaded!");
            })
            .catch(err => {
                hideLoading();
                alert("Error: " + err.message);
            });
    });

    // Bulk Renamer logic
    document.getElementById('btn-run-rename').addEventListener('click', () => {
        const folderPath = document.getElementById('rename-folder-path').value.trim();
        const baseText = document.getElementById('rename-base-text').value.trim();
        
        if (!folderPath || !baseText) {
            alert("Error: Folder path and base rename text are both required!");
            return;
        }
        
        showLoading("Renaming files in folder...");
        
        fetch('/api/bulk-renamer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ folder_path: folderPath, base_text: baseText })
        })
        .then(res => res.json())
        .then(data => {
            hideLoading();
            if (data.success) {
                showToast(data.message);
            } else {
                alert("Error: " + data.error);
            }
        })
        .catch(err => {
            hideLoading();
            alert("Error: " + err.message);
        });
    });
});
