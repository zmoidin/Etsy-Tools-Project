document.addEventListener('DOMContentLoaded', () => {
    // Nav Logic
    const navBtns = document.querySelectorAll('.nav-btn');
    const views = document.querySelectorAll('.view');
    const title = document.getElementById('tool-title');
    const desc = document.getElementById('tool-desc');

    const descriptions = {
        'auto-process': 'Automatically detect objects, slice, resize, and pad your clipart sheet to 3000x3000.',
        'mockup-showcase': 'Automatically arrange all clipart pieces onto a single beautiful showcase listing image.',
        'format-clipart': 'Format images for Etsy clipart (remove BG, 3000x3000px padding, 300 DPI)'
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

    // Mockup Showcase logic
    let mockupClipartFiles = [];
    let mockupBgFile = null;

    setupDropZone('drop-mockup-clipart', 'file-mockup-clipart', (files) => {
        mockupClipartFiles = files;
    });
    
    setupDropZone('drop-mockup-bg', 'file-mockup-bg', (files) => {
        if (files && files.length) {
            mockupBgFile = files[0];
        }
    });

    document.getElementById('btn-run-mockup').addEventListener('click', () => {
        if(!mockupClipartFiles || !mockupClipartFiles.length) {
            alert("Please select a clipart folder first!");
            return;
        }

        const formData = new FormData();
        for(let i=0; i<mockupClipartFiles.length; i++) {
            formData.append('files[]', mockupClipartFiles[i]);
        }
        if(mockupBgFile) {
            formData.append('background', mockupBgFile);
        }

        showLoading("Generating drop shadows and arranging layout...");
        fetch('/api/mockup-showcase', { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                hideLoading();
                if(data.success) showToast(data.message);
                else alert("Error: " + data.error);
            });
    });
});
