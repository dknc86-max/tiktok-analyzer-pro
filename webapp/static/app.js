document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('analyzeForm');
    const targetInput = document.getElementById('targetInput');
    const apiKeyInput = document.getElementById('apiKeyInput');
    const toggleKeyBtn = document.getElementById('toggleKeyBtn');
    const maxVideosSelect = document.getElementById('maxVideosSelect');
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

    // Infographics & Mind Map Selectors
    const viewCardsBtn = document.getElementById('viewCardsBtn');
    const viewInfographicsBtn = document.getElementById('viewInfographicsBtn');
    const viewMindmapBtn = document.getElementById('viewMindmapBtn');
    
    const cardsView = document.getElementById('cardsView');
    const infographicsView = document.getElementById('infographicsView');
    const mindmapView = document.getElementById('mindmapView');
    
    const metricTotalVideos = document.getElementById('metricTotalVideos');
    const metricTotalCompounds = document.getElementById('metricTotalCompounds');
    const metricTopCategory = document.getElementById('metricTopCategory');
    
    const slotsMorning = document.getElementById('slotsMorning');
    const slotsAfternoon = document.getElementById('slotsAfternoon');
    const slotsNight = document.getElementById('slotsNight');
    const slotsBed = document.getElementById('slotsBed');
    
    const mindmapNetwork = document.getElementById('mindmapNetwork');
    const mindmapSidebar = document.getElementById('mindmapSidebar');
    const closeSidebarBtn = document.getElementById('closeSidebarBtn');
    const sidebarContent = document.getElementById('sidebarContent');

    let currentJobId = null;
    let pollInterval = null;
    let cachedResults = [];
    let activeCategory = 'all';
    let searchQuery = '';
    let activeView = 'cards';
    
    let compoundChartInstance = null;
    let categoryChartInstance = null;
    let mindmapNetworkInstance = null;
    let dynamicTopicsList = [];

    // Predefined categorizations of health, routine, and peptide topics
    const PEPTIDES_AND_HORMONES = [
        'BPC-157', 'TB-500', 'GHK-Cu', 'KPV', 'Pinealon', 'Epitalon', 
        'FOXO4-DRI', 'Selank', 'Semax', 'MOTS-c', 'Retatrutide', 'Tirzepatide', 
        'Semaglutide', 'Tesamorelin', 'Ipamorelin', 'TRT', 'Testosterone', 
        'Glutathione', 'NAD+', 'Sermorelin', 'Dihexa', 'DSIP', 'Melanotan'
    ];

    const NUTRITION_KEYWORDS = [
        'Protein', 'Macros', 'Fasting', 'Intermittent Fasting', 'Diet', 
        'Keto', 'Calorie Deficit', 'Calorie Surplus', 'Eating', 'Carbs', 
        'Fats', 'Supplements', 'Creatine', 'Steak', 'Carbohydrates', 'Calories'
    ];

    const FITNESS_KEYWORDS = [
        'Workout', 'Gym', 'Muscle', 'Cardio', 'Training', 'Weightlifting', 
        'Running', 'Exercise', 'Reps', 'Sets', 'Hypertrophy', 'Strength', 
        'Fitness', 'Physique', 'Warmup', 'Stretch', 'Athletic'
    ];

    const WELLNESS_KEYWORDS = [
        'Cortisol', 'Sleep', 'Recovery', 'Dopamine', 'Stress', 'Anxiety', 
        'Meditation', 'Mindset', 'Habits', 'Cold Plunge', 'Sauna', 'Breathwork', 
        'Therapy', 'Focus', 'Cognitive', 'BDNF', 'L-Theanine'
    ];

    const GENERAL_KEYWORDS = [
        'Industry', 'FDA', 'Medical', 'Science', 'Research', 'Doctors', 
        'Health', 'Longevity', 'Clinics', 'Trial', 'Studies', 'Lab'
    ];

    // Common stop words to filter out in the dynamic term extractor
    const STOP_WORDS = new Set([
        'the', 'and', 'a', 'to', 'of', 'in', 'is', 'that', 'it', 'for', 'you', 'was', 
        'on', 'as', 'with', 'they', 'but', 'he', 'she', 'his', 'her', 'we', 'our', 'us', 
        'i', 'my', 'me', 'this', 'these', 'those', 'at', 'by', 'from', 'an', 'or', 'about', 
        'your', 'how', 'what', 'why', 'who', 'where', 'when', 'which', 'there', 'their', 
        'them', 'then', 'so', 'than', 'up', 'down', 'out', 'into', 'over', 'after', 
        'before', 'some', 'any', 'no', 'not', 'only', 'very', 'just', 'more', 'also', 
        'even', 'other', 'been', 'were', 'have', 'has', 'had', 'having', 'do', 'does', 
        'did', 'doing', 'can', 'could', 'should', 'would', 'will', 'shall', 'may', 
        'might', 'must', 'like', 'video', 'today', 'people', 'using', 'get', 'take', 
        'make', 'know', 'want', 'think', 'recommend', 'helps', 'learned', 'experiments', 
        'thought', 'thing', 'things', 'years', 'really', 'started', 'starting', 'looking', 
        'look', 'find', 'found', 'give', 'needed', 'needs', 'day', 'days', 'week', 
        'weeks', 'month', 'months', 'year', 'lot', 'little', 'much', 'many', 'guys', 
        'someone', 'something', 'gonna', 'wanna', 'gotta', 'done', 'doing', 'talking', 
        'talk', 'said', 'says', 'here', 'back', 'first', 'second', 'third', 'last'
    ]);

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
        const max_videos = parseInt(maxVideosSelect.value, 10);
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
                body: JSON.stringify({ target, api_key, max_videos })
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

        // Initialize view states and visual analytics
        switchView('cards');
        processAnalyticsData();

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

    // --- Infographics & Mind Map Implementation ---

    // Switch between Protocol Cards, Infographics, and Mind Map panels
    function switchView(viewName) {
        activeView = viewName;
        
        // Toggle tab button classes
        document.querySelectorAll('.view-tab-btn').forEach(btn => {
            if (btn.dataset.view === viewName) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // Toggle view visibility
        const views = {
            'cards': cardsView,
            'infographics': infographicsView,
            'mindmap': mindmapView
        };

        Object.entries(views).forEach(([name, panel]) => {
            if (panel) {
                if (name === viewName) {
                    panel.classList.remove('hidden');
                } else {
                    panel.classList.add('hidden');
                }
            }
        });

        // Trigger resize for ApexCharts to render properly
        if (viewName === 'infographics') {
            window.dispatchEvent(new Event('resize'));
        }
        
        // Redraw mind map network
        if (viewName === 'mindmap' && mindmapNetworkInstance) {
            mindmapNetworkInstance.fit();
        }
    }

    // Helper: Dynamic term frequency extractor (filters stop-words, outputs top nouns/proper-nouns)
    function extractDynamicTopics(results) {
        const counts = {};
        results.forEach(video => {
            const text = (video.title || '') + ' ' + (video.topic || '') + ' ' + (video.suggestions || []).join(' ');
            const words = text.toLowerCase().split(/[^a-zA-Z0-9\-]/);
            words.forEach(w => {
                const word = w.trim();
                if (word.length > 3 && isNaN(word) && !STOP_WORDS.has(word)) {
                    const formatted = word.charAt(0).toUpperCase() + word.slice(1);
                    counts[formatted] = (counts[formatted] || 0) + 1;
                }
            });
        });

        // Get top 15 terms with at least 2 occurrences
        return Object.entries(counts)
            .filter(([word, count]) => count >= 2)
            .sort((a, b) => b[1] - a[1])
            .map(item => item[0])
            .slice(0, 15);
    }

    // Helper: Normalize predefined compound & dynamic topics matching
    function parseKeyConceptsFromText(text, dynamicTopics = []) {
        const found = [];
        const lower = text.toLowerCase();
        
        const candidates = [
            ...PEPTIDES_AND_HORMONES,
            ...NUTRITION_KEYWORDS,
            ...FITNESS_KEYWORDS,
            ...WELLNESS_KEYWORDS,
            ...GENERAL_KEYWORDS,
            ...dynamicTopics
        ];

        const uniqueCandidates = Array.from(new Set(candidates));

        uniqueCandidates.forEach(comp => {
            const escaped = comp.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
            let regexStr = '\\b' + escaped + '\\b';
            
            // Hyphen-tolerance overrides
            if (comp === 'BPC-157') regexStr = '\\bbpc(?:\\s*|-)?157\\b';
            if (comp === 'TB-500') regexStr = '\\btb(?:\\s*|-)?500\\b';
            if (comp === 'GHK-Cu') regexStr = '\\bghk(?:\\s*|-)?cu\\b';
            if (comp === 'MOTS-c') regexStr = '\\bmots(?:\\s*|-)?c\\b';
            if (comp === 'FOXO4-DRI') regexStr = '\\bfoxo(?:\\s*|-)?4(?:\\s*|-)?(?:dri)?\\b';
            if (comp === 'NAD+') regexStr = '\\bnad\\+?\\b';
            if (comp === 'Intermittent Fasting') regexStr = '\\b(?:intermittent\\s+)?fasting\\b';
            if (comp === 'Cold Plunge') regexStr = '\\b(?:cold\\s+)?plunge\\b';

            const regex = new RegExp(regexStr, 'i');
            if (regex.test(lower)) {
                found.push(comp);
            }
        });

        return found;
    }

    // Process cachedResults to generate all analytics data
    function processAnalyticsData() {
        if (!cachedResults || cachedResults.length === 0) return;

        // Run dynamic tokenizer to find domain keywords for non-peptide profiles
        dynamicTopicsList = extractDynamicTopics(cachedResults);

        const data = {
            totalVideos: cachedResults.length,
            compoundCounts: {},
            categoryCounts: {},
            timelineSlots: {
                morning: [],
                afternoon: [],
                night: [],
                bed: []
            }
        };

        cachedResults.forEach(video => {
            const cat = video.category || 'general_advice';
            data.categoryCounts[cat] = (data.categoryCounts[cat] || 0) + 1;

            // Extract key concepts using both predefined categories and dynamically tokenized concepts
            const videoText = video.title + ' ' + video.topic + ' ' + video.suggestions.join(' ');
            const compounds = parseKeyConceptsFromText(videoText, dynamicTopicsList);
            
            compounds.forEach(comp => {
                data.compoundCounts[comp] = (data.compoundCounts[comp] || 0) + 1;
            });

            // Timeline parsing (scan suggestions for keyword matches)
            const textToScan = video.suggestions.join(' ').toLowerCase();
            const morningKeywords = ['morning', 'fasting', 'empty stomach', 'am', 'wake up', 'start', 'breakfast'];
            const nightKeywords = ['night', 'evening', 'pm', 'bedtime', 'sleep', 'bed', 'glutathione', 'melanotan', 'sauna', 'dinner'];
            const bedKeywords = ['bed', 'sleep', 'dsip', 'delta wave', 'l-theanine', 'meditation'];
            const afternoonKeywords = ['afternoon', 'post-workout', 'workout', 'daytime', 'lunch', 'cardio', 'gym', 'training'];

            compounds.forEach(comp => {
                let time = null;
                
                // Specific compound overrides based on typical usage log
                if (comp === 'DSIP') {
                    time = 'bed';
                } else if (comp === 'Glutathione' || comp === 'Melanotan' || comp === 'Epitalon' || comp === 'Sauna') {
                    time = 'night';
                } else if (comp === 'MOTS-c' || comp === 'Cardio' || comp === 'Workout' || comp === 'Gym') {
                    time = 'afternoon';
                } else if (comp === 'Retatrutide' || comp === 'BPC-157' || comp === 'TB-500' || comp === 'Fasting') {
                    time = 'morning';
                } else {
                    // Custom keywords matching
                    if (bedKeywords.some(kw => textToScan.includes(kw))) {
                        time = 'bed';
                    } else if (nightKeywords.some(kw => textToScan.includes(kw))) {
                        time = 'night';
                    } else if (afternoonKeywords.some(kw => textToScan.includes(kw))) {
                        time = 'afternoon';
                    } else if (morningKeywords.some(kw => textToScan.includes(kw))) {
                        time = 'morning';
                    }
                }
                
                if (time) {
                    const exists = data.timelineSlots[time].some(item => item.compound === comp);
                    if (!exists) {
                        const detailSug = video.suggestions.find(s => s.toLowerCase().includes(comp.toLowerCase())) || '';
                        data.timelineSlots[time].push({
                            compound: comp,
                            description: detailSug || `Recommended for ${time} routine.`,
                            videoTitle: video.title,
                            videoUrl: video.url
                        });
                    }
                }
            });
        });

        // Set metrics counts in UI
        if (metricTotalVideos) metricTotalVideos.textContent = data.totalVideos;
        
        const uniqueCompounds = Object.keys(data.compoundCounts).length;
        if (metricTotalCompounds) metricTotalCompounds.textContent = uniqueCompounds;

        let topCat = '-';
        let maxCatCount = 0;
        Object.entries(data.categoryCounts).forEach(([cat, count]) => {
            if (count > maxCatCount) {
                maxCatCount = count;
                topCat = cat;
            }
        });
        if (metricTopCategory) {
            metricTopCategory.textContent = CATEGORY_LABELS[topCat]?.replace(/^[^\s]+\s+/, '') || topCat;
        }

        // Render Apex charts
        renderCompoundChart(data.compoundCounts);
        renderCategoryChart(data.categoryCounts);

        // Render dynamic timeline slots
        renderTimeline(data.timelineSlots);

        // Build mind map force directed network
        renderMindmap(data);
    }

    // Render horizontal compound frequency chart
    function renderCompoundChart(compoundCounts) {
        const sorted = Object.entries(compoundCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10);

        const categories = sorted.map(item => item[0]);
        const data = sorted.map(item => item[1]);

        const options = {
            series: [{
                name: 'Mentions',
                data: data
            }],
            chart: {
                type: 'bar',
                height: 320,
                background: 'transparent',
                toolbar: { show: false },
                foreColor: '#111111'
            },
            plotOptions: {
                bar: {
                    borderRadius: 6,
                    horizontal: true,
                    barHeight: '60%',
                    distributed: true
                }
            },
            colors: ['#166534', '#22C55E', '#14532D', '#86EFAC', '#4ADE80', '#064E3B', '#15803D', '#A7F3D0'],
            dataLabels: {
                enabled: true,
                textAnchor: 'start',
                style: {
                    colors: ['#fff'],
                    fontFamily: 'Outfit, sans-serif',
                    fontWeight: 600
                },
                formatter: function (val, opt) {
                    return opt.w.globals.labels[opt.dataPointIndex] + ": " + val;
                },
                offsetX: 10
            },
            grid: {
                borderColor: '#E2E8F0',
                xaxis: { lines: { show: true } }
            },
            xaxis: {
                categories: categories,
                labels: {
                    style: { fontFamily: 'Outfit, sans-serif' }
                }
            },
            yaxis: {
                labels: { show: false }
            },
            tooltip: {
                theme: 'light',
                y: {
                    title: {
                        formatter: () => 'Mentions'
                    }
                }
            },
            legend: { show: false }
        };

        if (compoundChartInstance) {
            compoundChartInstance.destroy();
        }

        const container = document.querySelector("#compoundChart");
        if (container) {
            container.innerHTML = "";
            compoundChartInstance = new ApexCharts(container, options);
            compoundChartInstance.render();
        }
    }

    // Render donut chart for categories
    function renderCategoryChart(categoryCounts) {
        const series = [];
        const labels = [];
        
        Object.entries(categoryCounts).forEach(([cat, count]) => {
            series.push(count);
            labels.push(CATEGORY_LABELS[cat]?.replace(/^[^\s]+\s+/, '') || cat);
        });

        const options = {
            series: series,
            labels: labels,
            chart: {
                type: 'donut',
                height: 320,
                background: 'transparent',
                foreColor: '#111111'
            },
            stroke: {
                show: false
            },
            colors: ['#166534', '#22C55E', '#14532D', '#86EFAC', '#4ADE80', '#064E3B', '#15803D', '#A7F3D0'],
            legend: {
                position: 'bottom',
                fontFamily: 'Outfit, sans-serif',
                labels: {
                    colors: 'var(--text-secondary)'
                }
            },
            dataLabels: {
                enabled: true,
                style: {
                    fontFamily: 'Outfit, sans-serif'
                }
            },
            tooltip: {
                theme: 'light'
            },
            plotOptions: {
                pie: {
                    donut: {
                        size: '70%',
                        background: 'transparent',
                        labels: {
                            show: true,
                            name: {
                                show: true,
                                fontFamily: 'Outfit, sans-serif',
                                color: 'var(--text-secondary)'
                            },
                            value: {
                                show: true,
                                fontFamily: 'Outfit, sans-serif',
                                color: '#111111',
                                formatter: (val) => val
                            },
                            total: {
                                show: true,
                                label: 'Total Videos',
                                fontFamily: 'Outfit, sans-serif',
                                color: '#666666',
                                formatter: function (w) {
                                    return w.globals.seriesTotals.reduce((a, b) => a + b, 0);
                                }
                            }
                        }
                    }
                }
            }
        };

        if (categoryChartInstance) {
            categoryChartInstance.destroy();
        }

        const container = document.querySelector("#categoryChart");
        if (container) {
            container.innerHTML = "";
            categoryChartInstance = new ApexCharts(container, options);
            categoryChartInstance.render();
        }
    }

    // Render schedule timeline slots
    function renderTimeline(timelineSlots) {
        const timeKeys = ['morning', 'afternoon', 'night', 'bed'];
        timeKeys.forEach(time => {
            const containerId = `slots${time.charAt(0).toUpperCase() + time.slice(1)}`;
            const container = document.getElementById(containerId);
            if (!container) return;

            container.innerHTML = '';
            const items = timelineSlots[time];

            if (items.length === 0) {
                container.innerHTML = `<div class="timeline-empty">No protocols compiled</div>`;
                return;
            }

            items.forEach(item => {
                const itemDiv = document.createElement('div');
                itemDiv.className = 'timeline-item';
                
                let desc = item.description;
                if (desc.length > 70) {
                    desc = desc.substring(0, 67) + '...';
                }

                itemDiv.innerHTML = `
                    <div class="timeline-item-title">${item.compound}</div>
                    <div class="timeline-item-desc">${desc}</div>
                `;
                
                itemDiv.addEventListener('click', () => {
                    switchView('cards');
                    searchInput.value = item.compound;
                    searchQuery = item.compound.toLowerCase();
                    filterAndRender();
                });

                container.appendChild(itemDiv);
            });
        });
    }

    // Helper to color code topics dynamically by category in the network map
    function getTopicColors(topic) {
        if (PEPTIDES_AND_HORMONES.includes(topic)) {
            return {
                background: '#831843', border: '#be185d', font: '#fbcfe8',
                highlight: { background: '#9d174d', border: '#db2777' }
            };
        }
        if (NUTRITION_KEYWORDS.includes(topic)) {
            return {
                background: '#064e3b', border: '#059669', font: '#d1fae5',
                highlight: { background: '#065f46', border: '#10b981' }
            };
        }
        if (FITNESS_KEYWORDS.includes(topic)) {
            return {
                background: '#7c2d12', border: '#ea580c', font: '#ffedd5',
                highlight: { background: '#9a3412', border: '#f97316' }
            };
        }
        if (WELLNESS_KEYWORDS.includes(topic)) {
            return {
                background: '#0c4a6e', border: '#0284c7', font: '#e0f2fe',
                highlight: { background: '#075985', border: '#0ea5e9' }
            };
        }
        // General / Dynamic topics
        return {
            background: '#134e4a', border: '#0d9488', font: '#ccfbf1',
            highlight: { background: '#115e59', border: '#14b8a6' }
        };
    }

    // Build force-directed Vis.js Network
    function renderMindmap(analyticsData) {
        const nodes = [];
        const edges = [];

        // 1. Root node
        const targetLabel = targetInput.value.trim() || "@jacobnach";
        nodes.push({
            id: 'root',
            label: targetLabel,
            shape: 'ellipse',
            color: {
                background: '#166534',
                border: '#14532D',
                highlight: { background: '#15803D', border: '#064E3B' }
            },
            font: { size: 18, color: '#FFFFFF', bold: true },
            value: 40,
            title: 'Creator Node'
        });

        // 2. Category nodes and root edges
        const categoryMap = new Map();
        Object.entries(analyticsData.categoryCounts).forEach(([cat, count]) => {
            const label = CATEGORY_LABELS[cat] || cat;
            const cleanLabel = label.replace(/^[^\s]+\s+/, '');
            const nodeId = `cat_${cat}`;
            
            nodes.push({
                id: nodeId,
                label: cleanLabel,
                shape: 'box',
                color: {
                    background: '#FFFFFF',
                    border: '#E5E7EB',
                    highlight: { background: '#F0FDF4', border: '#22C55E' }
                },
                font: { size: 14, color: '#1F2937' },
                value: 20 + count * 2,
                title: `${count} videos in category ${cleanLabel}`
            });

            edges.push({
                from: 'root',
                to: nodeId,
                length: 120
            });

            categoryMap.set(cat, nodeId);
        });

        // 3. Topic nodes
        const compoundMap = new Map();
        
        cachedResults.forEach(video => {
            const cat = video.category || 'general_advice';
            const catNodeId = categoryMap.get(cat);
            if (!catNodeId) return;

            const videoText = video.title + ' ' + video.topic + ' ' + video.suggestions.join(' ');
            const compounds = parseKeyConceptsFromText(videoText, dynamicTopicsList);

            compounds.forEach(comp => {
                const count = analyticsData.compoundCounts[comp] || 1;
                const nodeId = `comp_${comp.toLowerCase()}`;
                
                if (!compoundMap.has(nodeId)) {
                    const colors = getTopicColors(comp);
                    nodes.push({
                        id: nodeId,
                        label: comp,
                        shape: 'dot',
                        color: {
                            background: colors.background,
                            border: colors.border,
                            highlight: colors.highlight
                        },
                        font: { size: 12, color: colors.font },
                        value: 12 + count * 3,
                        title: `${comp}: Mentioned ${count} times`
                    });
                    compoundMap.set(nodeId, {
                        name: comp,
                        categories: new Set(),
                        videos: []
                    });
                }
                
                const compData = compoundMap.get(nodeId);
                compData.categories.add(cat);
                compData.videos.push({
                    title: video.title,
                    url: video.url,
                    suggestions: video.suggestions.filter(s => s.toLowerCase().includes(comp.toLowerCase()))
                });
            });
        });

        // Category -> Compound connections
        compoundMap.forEach((data, nodeId) => {
            data.categories.forEach(cat => {
                const catNodeId = categoryMap.get(cat);
                if (catNodeId) {
                    edges.push({
                        from: catNodeId,
                        to: nodeId,
                        length: 80
                    });
                }
            });
        });

        const visNodes = new vis.DataSet(nodes);
        const visEdges = new vis.DataSet(edges);

        const networkData = {
            nodes: visNodes,
            edges: visEdges
        };

        const networkOptions = {
            nodes: {
                scaling: {
                    min: 10,
                    max: 40
                },
                shadow: {
                    enabled: true,
                    color: 'rgba(0,0,0,0.4)',
                    size: 6,
                    x: 2,
                    y: 2
                }
            },
            edges: {
                width: 2,
                color: {
                    color: '#E2E8F0',
                    highlight: '#111111',
                    hover: '#666666'
                },
                smooth: {
                    type: 'cubicBezier',
                    forceDirection: 'vertical',
                    roundness: 0.4
                }
            },
            physics: {
                barnesHut: {
                    gravitationalConstant: -2000,
                    centralGravity: 0.3,
                    springLength: 150,
                    springConstant: 0.02,
                    damping: 0.5,
                    avoidOverlap: 0.2
                },
                stabilization: {
                    iterations: 200,
                    fit: true
                }
            },
            interaction: {
                hover: true,
                zoomView: true,
                dragView: true
            }
        };

        if (mindmapNetworkInstance) {
            mindmapNetworkInstance.destroy();
        }

        mindmapNetworkInstance = new vis.Network(mindmapNetwork, networkData, networkOptions);

        mindmapNetworkInstance.on("stabilizationIterationsDone", function () {
            mindmapNetworkInstance.setOptions({ physics: false });
        });

        // Click handler for side panel details drawer
        mindmapNetworkInstance.on("click", function (params) {
            if (params.nodes.length > 0) {
                const clickedNodeId = params.nodes[0];
                
                if (clickedNodeId === 'root') {
                    showRootSidebar(targetLabel);
                } else if (clickedNodeId.startsWith('cat_')) {
                    const catName = clickedNodeId.replace('cat_', '');
                    showCategorySidebar(catName, analyticsData.categoryCounts[catName]);
                } else if (clickedNodeId.startsWith('comp_')) {
                    const compData = compoundMap.get(clickedNodeId);
                    if (compData) {
                        showCompoundSidebar(compData);
                    }
                }
            } else {
                if (mindmapSidebar) mindmapSidebar.classList.add('hidden');
            }
        });
    }

    function showRootSidebar(creatorName) {
        if (!mindmapSidebar) return;
        mindmapSidebar.classList.remove('hidden');
        sidebarContent.innerHTML = `
            <div class="sidebar-section">
                <div class="sidebar-title">${creatorName}</div>
                <span class="sidebar-tag">Central Node</span>
                <p class="sidebar-desc" style="margin-top: 0.5rem;">Central profile node representing the source of the analyzed transcripts and compiled health stacks.</p>
            </div>
            <div class="sidebar-section">
                <h4>Total Videos</h4>
                <p class="sidebar-desc"><strong>${cachedResults.length}</strong> videos analyzed successfully.</p>
            </div>
        `;
    }

    function showCategorySidebar(catName, videoCount) {
        if (!mindmapSidebar) return;
        const label = CATEGORY_LABELS[catName] || catName;
        const cleanLabel = label.replace(/^[^\s]+\s+/, '');
        mindmapSidebar.classList.remove('hidden');
        sidebarContent.innerHTML = `
            <div class="sidebar-section">
                <div class="sidebar-title">${cleanLabel}</div>
                <span class="sidebar-tag">Category Node</span>
                <p class="sidebar-desc" style="margin-top: 0.5rem;">This category includes <strong>${videoCount}</strong> video transcripts in the current analysis.</p>
            </div>
            <div class="sidebar-section">
                <h4>Category Navigation</h4>
                <button class="tab-btn active" style="margin-top: 0.5rem; width: 100%; min-width: unset; height: auto;" id="sidebarFilterBtn">
                    View Protocol Cards
                </button>
            </div>
        `;

        document.getElementById('sidebarFilterBtn').addEventListener('click', () => {
            switchView('cards');
            const tabBtn = Array.from(document.querySelectorAll('.tab-btn'))
                .find(b => b.textContent.includes(cleanLabel) || b.textContent.toLowerCase().includes(catName));
            if (tabBtn) {
                tabBtn.click();
            }
        });
    }

    function showCompoundSidebar(compData) {
        if (!mindmapSidebar) return;
        mindmapSidebar.classList.remove('hidden');
        
        let catBadges = Array.from(compData.categories)
            .map(cat => `<span class="sidebar-tag" style="margin-right: 0.3rem;">${CATEGORY_LABELS[cat]?.replace(/^[^\s]+\s+/, '') || cat}</span>`)
            .join(' ');

        let videoListHtml = compData.videos.map(v => {
            let quoteHtml = v.suggestions.length > 0 
                ? `<div style="font-size: 0.8rem; font-style: italic; color: var(--text-secondary); margin-top: 0.25rem;">"${v.suggestions[0]}"</div>` 
                : '';
            return `
                <li style="margin-bottom: 0.75rem;">
                    <a href="${v.url}" target="_blank" style="color: var(--accent-solid); font-weight: 500;">${v.title}</a>
                    ${quoteHtml}
                </li>
            `;
        }).join('');

        sidebarContent.innerHTML = `
            <div class="sidebar-section">
                <div class="sidebar-title">${compData.name}</div>
                <div style="margin-bottom: 1rem; display: flex; flex-wrap: wrap; gap: 0.3rem;">${catBadges}</div>
                <p class="sidebar-desc">Found in <strong>${compData.videos.length}</strong> videos.</p>
            </div>
            <div class="sidebar-section">
                <h4>Extracted Dosing / Context</h4>
                <ul class="sidebar-list">
                    ${videoListHtml}
                </ul>
            </div>
        `;
    }

    // Set up click listeners for view buttons
    if (viewCardsBtn) viewCardsBtn.addEventListener('click', () => switchView('cards'));
    if (viewInfographicsBtn) viewInfographicsBtn.addEventListener('click', () => switchView('infographics'));
    if (viewMindmapBtn) viewMindmapBtn.addEventListener('click', () => switchView('mindmap'));
    if (closeSidebarBtn && mindmapSidebar) {
        closeSidebarBtn.addEventListener('click', () => {
            mindmapSidebar.classList.add('hidden');
        });
    }
});
