document.addEventListener("DOMContentLoaded", () => {
    // UI Elements
    const scanBtn = document.getElementById("scan-btn");
    const dirPathInput = document.getElementById("directory-path");
    const maxDepthInput = document.getElementById("max-depth");
    const depthVal = document.getElementById("depth-val");
    const errorBox = document.getElementById("error-box");
    const origCount = document.getElementById("orig-count");
    const sugCount = document.getElementById("sug-count");
    const rationaleCount = document.getElementById("rationale-count");
    const originalTreeRoot = document.getElementById("original-tree-root");
    const suggestedTreeRoot = document.getElementById("suggested-tree-root");
    const rationalesTbody = document.getElementById("rationales-tbody");

    // Help Modal Elements
    const helpTrigger = document.getElementById("help-trigger");
    const helpModal = document.getElementById("help-modal");
    const closeModalBtn = document.getElementById("close-modal-btn");

    // Metrics Dashboard Elements
    const statsPanel = document.getElementById("stats-panel");
    const statFilesBefore = document.getElementById("stat-files-before");
    const statFilesAfter = document.getElementById("stat-files-after");
    const statFoldersBefore = document.getElementById("stat-folders-before");
    const statFoldersAfter = document.getElementById("stat-folders-after");
    const statDepthBefore = document.getElementById("stat-depth-before");
    const statDepthAfter = document.getElementById("stat-depth-after");
    const distributionBar = document.getElementById("distribution-bar");
    const distributionLegend = document.getElementById("distribution-legend");
    const searchInput = document.getElementById("search-input");

    // Category Color Maps
    const CATEGORY_COLORS = {
        "Documents": "#3b82f6",
        "Policy & Legislation": "#3b82f6",
        "Research & Publications": "#3b82f6",
        "Finance & Legal": "#10b981",
        "Finance & Procurement": "#10b981",
        "Data & Sheets": "#10b981",
        "Media": "#ef4444",
        "Marketing & Sales": "#ef4444",
        "Communications & Relations": "#ef4444",
        "Teaching & Courses": "#ef4444",
        "Source Code": "#a855f7",
        "Engineering & Tech": "#a855f7",
        "Operations & Public Services": "#a855f7",
        "Student Portfolios & Submissions": "#a855f7",
        "Archives": "#f59e0b",
        "Human Resources": "#f59e0b",
        "Administration & HR": "#f59e0b",
        "Administration & Departmental": "#f59e0b",
        "Product & Operations": "#3b82f6",
        "Other": "#6b7280",
        "Unmapped": "#4b5563"
    };

    function getCategoryColor(name) {
        return CATEGORY_COLORS[name] || "#6b7280";
    }

    // State Variables
    let currentResult = null;
    let highlightedNodes = [];

    // Sync Depth Slider Value
    maxDepthInput.addEventListener("input", (e) => {
        depthVal.textContent = e.target.value;
    });

    // Setup Quick Try chips
    document.querySelectorAll(".chip").forEach(chip => {
        if (chip.id !== "help-trigger") {
            chip.addEventListener("click", () => {
                dirPathInput.value = chip.dataset.path;
                triggerScan();
            });
        }
    });

    // Bind Help Modal Toggles
    if (helpTrigger && helpModal && closeModalBtn) {
        helpTrigger.addEventListener("click", () => {
            helpModal.classList.remove("hidden");
        });
        closeModalBtn.addEventListener("click", () => {
            helpModal.classList.add("hidden");
        });
        helpModal.addEventListener("click", (e) => {
            if (e.target === helpModal) {
                helpModal.classList.add("hidden");
            }
        });
    }

    // Toggle AI Credentials Inputs
    const aiProviderSelect = document.getElementById("ai-provider");
    const aiCredentialsDiv = document.getElementById("ai-credentials");
    const aiKeyInput = document.getElementById("ai-key");
    const aiModelInput = document.getElementById("ai-model");

    if (aiProviderSelect) {
        aiProviderSelect.addEventListener("change", (e) => {
            const provider = e.target.value;
            if (provider === "none") {
                aiCredentialsDiv.classList.add("hidden");
                aiKeyInput.value = "";
                aiModelInput.value = "";
            } else {
                aiCredentialsDiv.classList.remove("hidden");
                if (provider === "gemini") {
                    aiModelInput.placeholder = "e.g. gemini-2.5-flash";
                } else if (provider === "openai") {
                    aiModelInput.placeholder = "e.g. gpt-4o-mini";
                }
            }
        });
    }

    // Search Input Real-Time Filter Listener
    if (searchInput) {
        searchInput.addEventListener("input", (e) => {
            const query = e.target.value.toLowerCase().trim();
            applySearchFilter(query);
        });
    }

    scanBtn.addEventListener("click", triggerScan);

    function triggerScan() {
        const path = dirPathInput.value.trim();
        const maxDepth = parseInt(maxDepthInput.value, 10);
        const taxonomySelect = document.getElementById("taxonomy-select");
        const guidanceInput = document.getElementById("guidance-input");
        const taxonomy = taxonomySelect ? taxonomySelect.value : "generic";
        const customGuidance = guidanceInput ? guidanceInput.value.trim() : "";
        
        const aiProvider = aiProviderSelect ? aiProviderSelect.value : "none";
        const aiKey = aiKeyInput ? aiKeyInput.value.trim() : "";
        const aiModel = aiModelInput ? aiModelInput.value.trim() : "";

        if (!path) {
            showError("Please enter a valid directory path.");
            return;
        }

        clearErrors();
        setLoading(true);

        fetch("/api/scan", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ 
                path, 
                max_depth: maxDepth,
                taxonomy: taxonomy,
                custom_guidance: customGuidance || null,
                ai_provider: aiProvider,
                ai_api_key: aiKey || null,
                ai_model: aiModel || null
            })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.detail || "Server error occurred during scan.");
                });
            }
            return response.json();
        })
        .then(data => {
            currentResult = data;
            renderDashboard(data);
        })
        .catch(err => {
            showError(err.message);
        })
        .finally(() => {
            setLoading(false);
        });
    }

    function setLoading(isLoading) {
        const btnText = scanBtn.querySelector(".btn-text");
        const spinner = scanBtn.querySelector(".spinner");

        if (isLoading) {
            scanBtn.disabled = true;
            spinner.classList.remove("hidden");
            btnText.textContent = "Scanning...";
        } else {
            scanBtn.disabled = false;
            spinner.classList.add("hidden");
            btnText.textContent = "Analyze Structure";
        }
    }

    function showError(msg) {
        errorBox.textContent = msg;
        errorBox.classList.remove("hidden");
    }

    function clearErrors() {
        errorBox.textContent = "";
        errorBox.classList.add("hidden");
    }

    // Helper functions to calculate stats
    function countStats(node, stats = { files: 0, folders: 0 }) {
        if (!node) return stats;
        if (node.is_dir) {
            stats.folders += 1;
            if (node.children) {
                node.children.forEach(child => countStats(child, stats));
            }
        } else {
            stats.files += 1;
        }
        return stats;
    }

    function calculateMaxDepth(node) {
        if (!node) return 0;
        if (!node.is_dir || !node.children || node.children.length === 0) {
            return 1;
        }
        let maxChildDepth = 0;
        node.children.forEach(child => {
            maxChildDepth = Math.max(maxChildDepth, calculateMaxDepth(child));
        });
        return 1 + maxChildDepth;
    }

    function renderDashboard(result) {
        // Calculate Statistics
        const origStats = countStats(result.original_tree, { files: 0, folders: 0 });
        const sugStats = countStats(result.suggested_tree, { files: 0, folders: 0 });
        // Exclude root folder counts if they match root directory node
        origStats.folders = Math.max(0, origStats.folders - 1);
        sugStats.folders = Math.max(0, sugStats.folders - 1);

        const origDepth = calculateMaxDepth(result.original_tree);
        const sugDepth = calculateMaxDepth(result.suggested_tree);

        // Update statistics cards
        statFilesBefore.textContent = origStats.files;
        statFilesAfter.textContent = sugStats.files;
        statFoldersBefore.textContent = origStats.folders;
        statFoldersAfter.textContent = sugStats.folders;
        statDepthBefore.textContent = origDepth;
        statDepthAfter.textContent = sugDepth;

        // Display the panel
        statsPanel.classList.remove("hidden");

        // Update tree headers items count labels
        origCount.textContent = `${origStats.files} file${origStats.files !== 1 ? 's' : ''}, ${origStats.folders} folder${origStats.folders !== 1 ? 's' : ''}`;
        sugCount.textContent = `${sugStats.files} file${sugStats.files !== 1 ? 's' : ''}, ${sugStats.folders} folder${sugStats.folders !== 1 ? 's' : ''}`;
        rationaleCount.textContent = `${result.rationales.length} item${result.rationales.length !== 1 ? 's' : ''}`;

        // Clear Search Box
        if (searchInput) searchInput.value = "";

        // Build mappings of original and suggested paths to their rationales
        const relocations = new Map();
        const suggestedPaths = new Map();
        result.rationales.forEach(rat => {
            relocations.set(rat.original_path, rat);
            suggestedPaths.set(rat.suggested_path, rat);
        });

        // Rebuild Trees
        originalTreeRoot.innerHTML = "";
        suggestedTreeRoot.innerHTML = "";
        originalTreeRoot.appendChild(buildDOMTree(result.original_tree, relocations, "orig"));
        suggestedTreeRoot.appendChild(buildDOMTree(result.suggested_tree, suggestedPaths, "sug"));

        // Render charts & legends
        renderDistributionChart(result.suggested_tree);

        // Render Rationales Table
        renderRationalesTable(result.rationales);
    }

    function renderDistributionChart(suggestedTree) {
        distributionBar.innerHTML = "";
        distributionLegend.innerHTML = "";

        if (!suggestedTree || !suggestedTree.children) return;

        // Traverse suggested tree first-level subdirectories to count files
        const categories = {};
        let totalFiles = 0;

        suggestedTree.children.forEach(node => {
            if (node.is_dir) {
                const stats = countStats(node, { files: 0, folders: 0 });
                if (stats.files > 0) {
                    categories[node.name] = stats.files;
                    totalFiles += stats.files;
                }
            } else {
                // Files sitting loose in the root
                categories["Loose Files"] = (categories["Loose Files"] || 0) + 1;
                totalFiles += 1;
            }
        });

        if (totalFiles === 0) {
            distributionBar.innerHTML = `<div style="padding: 0.25rem 1rem; font-size: 0.8rem; color: var(--text-muted);">No files found in directory.</div>`;
            return;
        }

        // Draw horizontal segments and legends
        Object.entries(categories).forEach(([name, count]) => {
            const percentage = (count / totalFiles) * 100;
            const color = getCategoryColor(name);

            // Bar Segment
            const segment = document.createElement("div");
            segment.className = "dist-bar-segment";
            segment.style.width = `${percentage}%`;
            segment.style.backgroundColor = color;
            segment.title = `${name}: ${count} file(s) (${percentage.toFixed(1)}%)`;
            distributionBar.appendChild(segment);

            // Legend item
            const legendItem = document.createElement("div");
            legendItem.className = "legend-item";
            legendItem.innerHTML = `
                <span class="legend-color" style="background-color: ${color};"></span>
                <span><strong>${name}</strong>: ${count} (${percentage.toFixed(0)}%)</span>
            `;
            distributionLegend.appendChild(legendItem);
        });
    }

    function buildDOMTree(node, rationaleMap, treeType) {
        const container = document.createElement("div");
        container.className = "tree-node";

        const header = document.createElement("div");
        header.className = `tree-node-header ${node.is_dir ? 'folder' : 'file'}`;
        header.textContent = node.name;
        header.id = `${treeType}-node-${btoa(encodeURIComponent(node.path))}`;

        if (treeType === "orig" && rationaleMap.has(node.path)) {
            header.classList.add("highlight-relocated");
            header.title = `Relocation: ${rationaleMap.get(node.path).reasoning}`;
        } else if (treeType === "sug" && rationaleMap.has(node.path)) {
            header.classList.add("highlight-renamed");
            header.title = `Relocation: ${rationaleMap.get(node.path).reasoning}`;
        }

        container.appendChild(header);

        if (node.is_dir && node.children && node.children.length > 0) {
            const childrenContainer = document.createElement("div");
            childrenContainer.className = "tree-node-children";

            header.addEventListener("click", (e) => {
                e.stopPropagation();
                childrenContainer.classList.toggle("collapsed");
                header.classList.toggle("collapsed");
            });

            node.children.forEach(child => {
                childrenContainer.appendChild(buildDOMTree(child, rationaleMap, treeType));
            });

            container.appendChild(childrenContainer);
        }

        return container;
    }

    function renderRationalesTable(rationales) {
        rationalesTbody.innerHTML = "";

        if (rationales.length === 0) {
            const row = document.createElement("tr");
            row.innerHTML = `<td colspan="4" class="table-placeholder">No modifications recommended. Your directory is already tidy!</td>`;
            rationalesTbody.appendChild(row);
            return;
        }

        rationales.forEach(rat => {
            const row = document.createElement("tr");
            const actionClass = getActionTagClass(rat.action);
            const origDisp = rat.original_path || "/";
            const sugDisp = rat.suggested_path || "/";

            row.innerHTML = `
                <td><span class="action-tag ${actionClass}">${rat.action}</span></td>
                <td><code>${origDisp}</code></td>
                <td><code>${sugDisp}</code></td>
                <td>${rat.reasoning}</td>
            `;

            row.addEventListener("click", () => {
                document.querySelectorAll(".rationales-table tbody tr").forEach(r => r.classList.remove("active-row"));
                row.classList.add("active-row");

                clearHighlights();

                const origId = `orig-node-${btoa(encodeURIComponent(rat.original_path))}`;
                const origEl = document.getElementById(origId);
                if (origEl) {
                    origEl.style.outline = "2px solid #ef4444";
                    origEl.style.borderRadius = "4px";
                    origEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
                    highlightedNodes.push(origEl);
                }

                const sugId = `sug-node-${btoa(encodeURIComponent(rat.suggested_path))}`;
                const sugEl = document.getElementById(sugId);
                if (sugEl) {
                    sugEl.style.outline = "2px solid #10b981";
                    sugEl.style.borderRadius = "4px";
                    sugEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
                    highlightedNodes.push(sugEl);
                }
            });

            rationalesTbody.appendChild(row);
        });
    }

    function clearHighlights() {
        highlightedNodes.forEach(node => {
            node.style.outline = "none";
        });
        highlightedNodes = [];
    }

    function getActionTagClass(action) {
        switch(action) {
            case "FLATTEN": return "tag-flatten";
            case "GROUP": return "tag-group";
            case "RENAME":
            case "RENAME_AND_MOVE": return "tag-rename";
            default: return "tag-move";
        }
    }

    function applySearchFilter(query) {
        function checkNodeMatch(element) {
            const header = element.querySelector(":scope > .tree-node-header");
            const childrenContainer = element.querySelector(":scope > .tree-node-children");
            
            const nodeName = header.textContent.toLowerCase();
            const selfMatches = nodeName.includes(query);
            
            let childMatches = false;
            if (childrenContainer) {
                const childElements = childrenContainer.querySelectorAll(":scope > .tree-node");
                childElements.forEach(childEl => {
                    if (checkNodeMatch(childEl)) {
                        childMatches = true;
                    }
                });
            }
            
            const isVisible = selfMatches || childMatches;
            
            if (query === "") {
                header.classList.remove("faded", "search-match");
                if (childrenContainer) {
                    // Do not force collapse, just let user toggle or keep collapsed state
                }
            } else {
                if (selfMatches) {
                    header.classList.add("search-match");
                    header.classList.remove("faded");
                } else if (childMatches) {
                    header.classList.remove("faded", "search-match");
                } else {
                    header.classList.remove("search-match");
                    header.classList.add("faded");
                }
                
                // Auto-expand folder matches
                if (childMatches && childrenContainer) {
                    childrenContainer.classList.remove("collapsed");
                    header.classList.remove("collapsed");
                }
            }
            
            return isVisible;
        }

        // Apply filters to both trees side by side
        const origNodes = originalTreeRoot.querySelectorAll(":scope > .tree-node");
        origNodes.forEach(node => checkNodeMatch(node));

        const sugNodes = suggestedTreeRoot.querySelectorAll(":scope > .tree-node");
        sugNodes.forEach(node => checkNodeMatch(node));
    }
});
