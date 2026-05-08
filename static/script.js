document.addEventListener('DOMContentLoaded', () => {
    const scrapeBtn = document.getElementById('scrapeBtn');
    const urlInput = document.getElementById('url');
    const promptInput = document.getElementById('prompt');
    const spinner = document.getElementById('spinner');
    const btnText = document.querySelector('.btn-text');
    const errorMsg = document.getElementById('errorMsg');
    const resultsSection = document.getElementById('resultsSection');
    const tableHeadRow = document.getElementById('tableHeadRow');
    const tableBody = document.getElementById('tableBody');
    const exportBtns = document.querySelectorAll('.export-btn');

    let currentData = null;

    scrapeBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        const prompt = promptInput.value.trim();

        if (!url) {
            showError("Please enter a valid URL.");
            return;
        }

        // Set Loading state
        hideError();
        scrapeBtn.disabled = true;
        spinner.classList.remove('hidden');
        btnText.textContent = "Scraping...";
        resultsSection.classList.add('hidden');

        try {
            const response = await fetch('/api/scrape', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, prompt })
            });

            const result = await response.json();

            if (result.success) {
                currentData = result.data;
                renderTable(result.data);
                resultsSection.classList.remove('hidden');
            } else {
                showError(result.error || "An unknown error occurred.");
            }
        } catch (err) {
            showError("Failed to connect to the server.");
            console.error(err);
        } finally {
            scrapeBtn.disabled = false;
            spinner.classList.add('hidden');
            btnText.textContent = "Scrape Data";
        }
    });

    exportBtns.forEach(btn => {
        btn.addEventListener('click', async () => {
            if (!currentData || currentData.length === 0) return;
            
            const format = btn.getAttribute('data-format');
            
            try {
                const response = await fetch('/api/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ data: currentData, format })
                });

                if (!response.ok) throw new Error("Download failed");
                
                // Trigger download
                const blob = await response.blob();
                const downloadUrl = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = downloadUrl;
                
                // Get filename from response header or default
                const cd = response.headers.get('Content-Disposition');
                let filename = `scraped_data.${format}`;
                if (cd && cd.includes('filename=')) {
                    filename = cd.split('filename=')[1].replace(/"/g, '');
                }
                
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(downloadUrl);
            } catch (err) {
                showError("Failed to download file.");
                console.error(err);
            }
        });
    });

    function renderTable(data) {
        tableHeadRow.innerHTML = '';
        tableBody.innerHTML = '';

        if (!data || data.length === 0) {
            tableHeadRow.innerHTML = '<th>No data found</th>';
            return;
        }

        // Get all unique keys for headers
        const keys = new Set();
        data.forEach(item => {
            if (typeof item === 'object' && item !== null) {
                Object.keys(item).forEach(k => keys.add(k));
            }
        });
        
        const headers = Array.from(keys);

        // Build Head
        headers.forEach(h => {
            const th = document.createElement('th');
            th.textContent = h.charAt(0).toUpperCase() + h.slice(1);
            tableHeadRow.appendChild(th);
        });

        // Build Body
        data.forEach(item => {
            const tr = document.createElement('tr');
            headers.forEach(h => {
                const td = document.createElement('td');
                const val = item ? item[h] : '';
                td.textContent = (val !== null && val !== undefined) ? String(val) : '-';
                tr.appendChild(td);
            });
            tableBody.appendChild(tr);
        });
    }

    function showError(msg) {
        errorMsg.textContent = msg;
        errorMsg.classList.remove('hidden');
    }

    function hideError() {
        errorMsg.classList.add('hidden');
    }
});
