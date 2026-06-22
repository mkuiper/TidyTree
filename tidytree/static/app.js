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

    // State Variables
    let currentResult = null;
    let highlightedNodes = [];

    // Sync Depth Slider Value
    maxDepthInput.addEventListener("input", (e) => {
        depthVal.textContent = e.target.value;
    });

    // Setup Quick Try chips
    document.querySelectorAll(".chip").forEach(chip => {
        chip.addEventListener("click", () => {
            dirPathInput.value = chip.dataset.path;
            triggerScan();
        });
    });

    scanBtn.addEventListener("click", triggerScan);

    function triggerScan() {
        const path = dirPathInput.value.trim();
        const maxDepth = parseInt(maxDepthInput.value, 10);
        const taxonomySelect = document.getElementById("taxonomy-select");
        const guidanceInput = document.getElementById("guidance-input");
        const taxonomy = taxonomySelect ? taxonomySelect.value : "generic";
        const customGuidance = guidanceInput ? guidanceInput.value.trim() : "";

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
                custom_guidance: customGuidance || null
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

    function countNodes(node) {
        if (!node) return 0;
        let count = 1; // Count self
        if (node.is_dir && node.children) {
            node.children.forEach(child => {
                count += countNodes(child);
            });
        }
        return count;
    }

    function renderDashboard(result) {
        // Set item counts
        const oCount = countNodes(result.original_tree);
        const sCount = countNodes(result.suggested_tree);
        origCount.textContent = `${oCount} item${oCount !== 1 ? 's' : ''}`;
        sugCount.textContent = `${sCount} item${sCount !== 1 ? 's' : ''}`;
        rationaleCount.textContent = `${result.rationales.length} item${result.rationales.length !== 1 ? 's' : ''}`;

        // Create fast path map for lookups
        const relocations = new Map(); // original_path -> rationale
        const suggestedPaths = new Map(); // suggested_path -> rationale
        
        result.rationales.forEach(rat => {
            relocations.set(rat.original_path, rat);
            suggestedPaths.set(rat.suggested_path, rat);
        });

        // Clear existing trees
        originalTreeRoot.innerHTML = "";
        suggestedTreeRoot.innerHTML = "";

        // Build Trees
        originalTreeRoot.appendChild(buildDOMTree(result.original_tree, relocations, "orig"));
        suggestedTreeRoot.appendChild(buildDOMTree(result.suggested_tree, suggestedPaths, "sug"));

        // Render Rationales Table
        renderRationalesTable(result.rationales);
    }

    function buildDOMTree(node, rationaleMap, treeType) {
        const container = document.createElement("div");
        container.className = "tree-node";

        const header = document.createElement("div");
        header.className = `tree-node-header ${node.is_dir ? 'folder' : 'file'}`;
        header.textContent = node.name;
        header.id = `${treeType}-node-${btoa(encodeURIComponent(node.path))}`;

        // Highlight nodes that undergo action
        if (treeType === "orig" && rationaleMap.has(node.path)) {
            header.classList.add("highlight-relocated");
            header.title = `Optimization: ${rationaleMap.get(node.path).reasoning}`;
        } else if (treeType === "sug" && rationaleMap.has(node.path)) {
            header.classList.add("highlight-renamed");
            header.title = `Optimization: ${rationaleMap.get(node.path).reasoning}`;
        }

        container.appendChild(header);

        if (node.is_dir && node.children && node.children.length > 0) {
            const childrenContainer = document.createElement("div");
            childrenContainer.className = "tree-node-children";

            // Click header to toggle children visibility
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

            // Format action tag
            const actionClass = getActionTagClass(rat.action);
            const origDisp = rat.original_path || "/";
            const sugDisp = rat.suggested_path || "/";

            row.innerHTML = `
                <td><span class="action-tag ${actionClass}">${rat.action}</span></td>
                <td><code>${origDisp}</code></td>
                <td><code>${sugDisp}</code></td>
                <td>${rat.reasoning}</td>
            `;

            // Hover / click handler on table rows to highlight corresponding nodes in trees
            row.addEventListener("click", () => {
                // Clear old active row styling
                document.querySelectorAll(".rationales-table tbody tr").forEach(r => r.classList.remove("active-row"));
                row.classList.add("active-row");

                clearHighlights();

                // Highlight before node
                const origId = `orig-node-${btoa(encodeURIComponent(rat.original_path))}`;
                const origEl = document.getElementById(origId);
                if (origEl) {
                    origEl.style.outline = "2px solid #ef4444";
                    origEl.style.borderRadius = "4px";
                    origEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
                    highlightedNodes.push(origEl);
                }

                // Highlight after node
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
});
