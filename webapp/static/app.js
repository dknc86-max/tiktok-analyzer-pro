document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('analyzeForm');
    const targetInput = document.getElementById('targetInput');
    const apiKeyInput = document.getElementById('apiKeyInput');
    const toggleKeyBtn = document.getElementById('toggleKeyBtn');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = submitBtn.querySelector('.btn-text');
    const loader = submitBtn.querySelector('.loader');
    
    const progressSection = document.getElementById('progressSection');
    const progressTitle = document.getElementById('progressTitle');
    const progressPercentage = document.getElementById('progressPercentage');
    const progressFill = document.getElementById('progressFill');
    const progressMessage = document.getElementById('progressMessage');
    
    const resultsSection = document.getElementById('resultsSection');
    const cardsGrid = document.getElementById('cardsGrid');
    const downloadBtn = document.getElementById('downloadBtn');
    const synthesizeBtn = document.getElementById('synthesizeBtn');
    const searchInput = document.getElementById('searchInput');
    const categoryTabs = document.getElementById('categoryTabs');

    let currentJobId = null;
    let pollInterval = null;
    let cachedResults = [];
    let activeCategory = 'all';
    let searchQuery = '';

    const CATEGORY_LABELS = {
        'all': '📋 Show All',
        'peptide_protocol': '💉 Protocols',
        'peptide_info': '💊 Peptide Info',
        'glp1_fat_loss': '🔥 Fat Loss',
        'hormones': '🧬 Hormones & TRT',
        'mitochondria': '⚡ Mitochondria',
        'nutrition': '🥩 Nutrition',
        'wellness_mindset': '🧠 Mindset',
        'fitness': '💪 Fitness',
        'industry_news': '📰 Industry News',
        'general_advice': '💡 General Advice',
    };

    // Load saved API key from localStorage
    if (localStorage.getItem('gemini_api_key')) {
        apiKeyInput.value = localStorage.getItem('gemini_api_key');
    }

    // Toggle API Key visibility
    toggleKeyBtn.addEventListener('click', () => {
        if (apiKeyInput.type === 'password') {
            apiKeyInput.type = 'text';
            toggleKeyBtn.textContent = 'Hide';
        } else {
            apiKeyInput.type = 'password';
            toggleKeyBtn.textContent = 'Show';
        }
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const target = targetInput.value.trim();
        const api_key = apiKeyInput.value.trim();
        if(!target) return;

        // Save API key to localStorage
        if (api_key) {
            localStorage.setItem('gemini_api_key', api_key);
        } else {
            localStorage.removeItem('gemini_api_key');
        }

        // Reset UI
        resultsSection.classList.add('hidden');
        cardsGrid.innerHTML = '';
        
        // Button Loading state
        btnText.classList.add('hidden');
        loader.classList.remove('hidden');
        submitBtn.disabled = true;

        try {
            const res = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target, api_key })
            });
            const data = await res.json();
            
            if (data.job_id) {
                currentJobId = data.job_id;
                progressSection.classList.remove('hidden');
                pollStatus();
            } else {
                throw new Error("Failed to start job");
            }
        } catch (error) {
            console.error(error);
            resetBtn();
            alert('Failed to start analysis. Please check console.');
        }
    });

    function pollStatus() {
        if(pollInterval) clearInterval(pollInterval);
        
        pollInterval = setInterval(async () => {
            try {
                const res = await fetch(`/api/status/${currentJobId}`);
                const data = await res.json();
                
                updateProgressUI(data);

                if (data.status === 'completed') {
                    clearInterval(pollInterval);
                    renderResults(data.results);
                    resetBtn();
                } else if (data.status === 'error') {
                    clearInterval(pollInterval);
                    progressTitle.textContent = "Error";
                    progressMessage.textContent = data.message;
                    progressFill.style.backgroundColor = "var(--accent-glow-secondary)";
                    resetBtn();
                }

            } catch(e) {
                console.error("Polling error", e);
            }
        }, 1000);
    }

    function updateProgressUI(data) {
        if (data.total > 0) {
            const pct = Math.round((data.progress / data.total) * 100);
            progressPercentage.textContent = `${pct}%`;
            progressFill.style.width = `${pct}%`;
            progressTitle.textContent = "Analyzing Videos...";
        } else {
            progressPercentage.textContent = "0%";
            progressFill.style.width = "0%";
            progressTitle.textContent = "Initializing...";
        }
        progressMessage.textContent = data.message || "Working...";
    }

    // Setup Search input listener
    searchInput.addEventListener('input', (e) => {
        searchQuery = e.target.value.toLowerCase().trim();
        filterAndRender();
    });

    function setupCategoryTabs() {
        categoryTabs.innerHTML = '';
        
        // Count cards in each category
        const counts = { 'all': cachedResults.length };
        cachedResults.forEach(item => {
            const cat = item.category || 'general_advice';
            counts[cat] = (counts[cat] || 0) + 1;
        });

        // Generate tab buttons
        Object.keys(counts).forEach(cat => {
            const btn = document.createElement('button');
            btn.className = `tab-btn ${activeCategory === cat ? 'active' : ''}`;
            btn.type = 'button';
            
            const label = CATEGORY_LABELS[cat] || cat;
            btn.textContent = `${label} (${counts[cat]})`;
            
            btn.addEventListener('click', () => {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                activeCategory = cat;
                filterAndRender();
            });
            
            categoryTabs.appendChild(btn);
        });
    }

    function filterAndRender() {
        cardsGrid.innerHTML = '';
        
        const filtered = cachedResults.filter(item => {
            // Category filter
            const matchesCategory = (activeCategory === 'all' || (item.category || 'general_advice') === activeCategory);
            
            // Search query filter
            let matchesSearch = true;
            if (searchQuery) {
                const titleMatch = item.title.toLowerCase().includes(searchQuery);
                const topicMatch = item.topic.toLowerCase().includes(searchQuery);
                const bulletMatch = item.suggestions.some(sug => sug.toLowerCase().includes(searchQuery));
                matchesSearch = titleMatch || topicMatch || bulletMatch;
            }
            
            return matchesCategory && matchesSearch;
        });

        if (filtered.length === 0) {
            cardsGrid.innerHTML = "<p class='no-results'>No matching protocols or suggestions found.</p>";
            return;
        }

        filtered.forEach((item, index) => {
            const card = document.createElement('div');
            card.className = 'result-card';
            card.style.animationDelay = `${index * 0.05}s`;

            const ul = document.createElement('ul');
            ul.className = 'suggestion-list';
            item.suggestions.forEach(sug => {
                const li = document.createElement('li');
                li.innerHTML = highlightKeywords(sug);
                ul.appendChild(li);
            });

            card.innerHTML = `
                <div class="result-card-header">
                    <h3><a href="${item.url}" target="_blank" onclick="event.stopPropagation()">${item.title}</a></h3>
                    <span class="chevron-icon">▼</span>
                </div>
                <div class="topic-tag">${item.topic}</div>
            `;
            card.appendChild(ul);
            
            // Accordion toggle on click
            card.addEventListener('click', () => {
                card.classList.toggle('expanded');
            });

            cardsGrid.appendChild(card);
        });
    }

    function renderResults(results) {
        progressSection.classList.add('hidden');
        resultsSection.classList.remove('hidden');
        
        cachedResults = results || [];
        activeCategory = 'all';
        searchQuery = '';
        searchInput.value = '';
        
        setupCategoryTabs();
        filterAndRender();

        // Setup download button functionality for current results
        downloadBtn.onclick = () => downloadMarkdown(cachedResults);

        // Setup synthesize button functionality
        synthesizeBtn.onclick = async () => {
            const api_key = apiKeyInput.value.trim();
            const originalText = synthesizeBtn.textContent;
            synthesizeBtn.disabled = true;
            synthesizeBtn.textContent = '⚡ Synthesizing Master Stacks...';
            
            try {
                const res = await fetch('/api/synthesize', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ api_key })
                });
                const data = await res.json();
                
                if (data.markdown) {
                    const blob = new Blob([data.markdown], { type: 'text/markdown' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `Synthesized_Master_Protocols.md`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                } else if (data.error) {
                    alert('Synthesis failed: ' + data.error);
                } else {
                    alert('Synthesis failed with unknown error.');
                }
            } catch (err) {
                console.error(err);
                alert('Connection to server failed.');
            } finally {
                synthesizeBtn.disabled = false;
                synthesizeBtn.textContent = originalText;
            }
        };
    }

    function highlightKeywords(text) {
        const keywords = ['peptide', 'stack', 'mg', 'mcg', 'diet', 'fasting', 'testosterone', 'melanotan', 'bpc', 'tb500'];
        let highlighted = text;
        keywords.forEach(kw => {
            const regex = new RegExp(`\\b${kw}\\b`, 'gi');
            highlighted = highlighted.replace(regex, `<strong>$&</strong>`);
        });
        return highlighted;
    }

    function downloadMarkdown(results) {
        let md = "# Detailed Video Protocols & Suggestions\n\n";
        results.forEach(item => {
            md += `### [${item.title}](${item.url})\n`;
            md += `**Topic**: ${item.topic}\n\n`;
            md += `**Key Suggestions / Takeaways**:\n`;
            item.suggestions.forEach(sug => {
                md += `- ${sug}\n`;
            });
            md += "\n";
        });

        const blob = new Blob([md], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${currentJobId}_analysis.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    function resetBtn() {
        btnText.classList.remove('hidden');
        loader.classList.add('hidden');
        submitBtn.disabled = false;
    }
});
