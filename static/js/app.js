document.addEventListener("DOMContentLoaded", () => {
    // UI Elements
    const wsIdDisplay = document.getElementById("ws-id-display");
    const wsTitleDisplay = document.getElementById("workspace-title-display");
    const btnNewWs = document.getElementById("btn-new-ws");
    const btnCopyWs = document.getElementById("btn-copy-ws");
    const btnDeleteWs = document.getElementById("btn-delete-ws");
    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("file-input");
    const uploadProgressContainer = document.getElementById("upload-progress-container");
    const docsList = document.getElementById("docs-list");
    const chatPane = document.getElementById("chat-pane");
    const chatForm = document.getElementById("chat-form");
    const queryInput = document.getElementById("query-input");
    const btnSendChat = document.getElementById("btn-send-chat");

    let currentWorkspaceId = localStorage.getItem("current_workspace_id");
    let hasDocuments = false;

    // Initialize Workspace
    async function initWorkspace() {
        if (currentWorkspaceId) {
            // Check if workspace actually exists by pulling documents
            try {
                const response = await fetch(`/documents?workspace_id=${currentWorkspaceId}`);
                if (response.status === 404) {
                    // Workspace doesn't exist, create a new one
                    await createNewWorkspace();
                } else if (response.ok) {
                    updateWorkspaceUI(currentWorkspaceId);
                    await loadDocuments();
                } else {
                    await createNewWorkspace();
                }
            } catch (err) {
                console.error("Error validating workspace:", err);
                showToast("Connection error, using offline ID", "error");
                updateWorkspaceUI(currentWorkspaceId);
            }
        } else {
            await createNewWorkspace();
        }
    }

    // Create New Workspace
    async function createNewWorkspace() {
        try {
            const response = await fetch("/workspace/create", { method: "POST" });
            if (!response.ok) throw new Error("Failed to create workspace on server");
            
            const data = await response.json();
            currentWorkspaceId = data.workspace_id;
            localStorage.setItem("current_workspace_id", currentWorkspaceId);
            
            updateWorkspaceUI(currentWorkspaceId);
            clearChatPane();
            renderDocumentsList([]);
            showToast("Created a new workspace!", "success");
        } catch (err) {
            console.error(err);
            showToast("Failed to create a workspace session.", "error");
        }
    }

    // Delete Workspace
    async function deleteWorkspace() {
        if (!currentWorkspaceId) return;
        if (!confirm("Are you sure you want to delete this workspace? This will purge all uploaded files, Pinecone vectors, and chat history. This action is irreversible.")) return;

        try {
            const response = await fetch(`/workspace/${currentWorkspaceId}`, { method: "DELETE" });
            if (!response.ok) throw new Error("Failed to delete workspace");

            showToast("Workspace deleted successfully.", "success");
            localStorage.removeItem("current_workspace_id");
            currentWorkspaceId = null;
            await initWorkspace();
        } catch (err) {
            console.error(err);
            showToast("Failed to delete workspace.", "error");
        }
    }

    // Update Workspace UI Display
    function updateWorkspaceUI(wsId) {
        wsIdDisplay.textContent = wsId;
        wsTitleDisplay.textContent = `Workspace: ${wsId}`;
    }

    // Copy Workspace ID
    btnCopyWs.addEventListener("click", () => {
        if (!currentWorkspaceId) return;
        navigator.clipboard.writeText(currentWorkspaceId).then(() => {
            showToast("Workspace ID copied to clipboard!", "success");
        }).catch(err => {
            console.error("Clipboard copy failed:", err);
        });
    });

    btnNewWs.addEventListener("click", () => {
        if (confirm("Create a new workspace? Your current workspace files will remain saved under the old ID, but you will switch to a fresh workspace session.")) {
            createNewWorkspace();
        }
    });

    btnDeleteWs.addEventListener("click", deleteWorkspace);

    // Load Documents
    async function loadDocuments() {
        if (!currentWorkspaceId) return;
        try {
            const response = await fetch(`/documents?workspace_id=${currentWorkspaceId}`);
            if (!response.ok) throw new Error("Failed to load documents");
            
            const data = await response.json();
            renderDocumentsList(data.documents);
        } catch (err) {
            console.error(err);
            showToast("Failed to load documents list", "error");
        }
    }

    // Render list of documents
    function renderDocumentsList(documents) {
        docsList.innerHTML = "";
        if (!documents || documents.length === 0) {
            docsList.innerHTML = '<li class="empty-list-msg">No files uploaded yet.</li>';
            hasDocuments = false;
            toggleChatControls(false);
            return;
        }

        hasDocuments = true;
        toggleChatControls(true);

        documents.forEach(doc => {
            const li = document.createElement("li");
            li.className = "doc-item";
            li.innerHTML = `
                <i class="fa-solid fa-file-pdf"></i>
                <div class="doc-details">
                    <span class="doc-name" title="${doc.filename}">${doc.filename}</span>
                    <span class="doc-meta">${doc.total_pages} pages • ${formatDate(doc.upload_time)}</span>
                </div>
            `;
            docsList.appendChild(li);
        });
    }

    function toggleChatControls(enable) {
        queryInput.disabled = !enable;
        btnSendChat.disabled = !enable;
        if (enable) {
            queryInput.placeholder = "Ask a question about your uploaded documents...";
        } else {
            queryInput.placeholder = "Upload a PDF first to enable chat assistant...";
        }
    }

    // Drag and Drop File Handlers
    dropzone.addEventListener("click", () => fileInput.click());

    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("dragover");
    });

    dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("dragover");
    });

    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            uploadFiles(files);
        }
    });

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            uploadFiles(fileInput.files);
            fileInput.value = ""; // Reset value
        }
    });

    // Upload Files via AJAX
    function uploadFiles(files) {
        if (!currentWorkspaceId) return;
        
        // Filter out non-PDF files
        const pdfFiles = Array.from(files).filter(f => f.name.toLowerCase().endsWith(".pdf"));
        if (pdfFiles.length === 0) {
            showToast("Only PDF files are supported.", "error");
            return;
        }

        const formData = new FormData();
        formData.append("workspace_id", currentWorkspaceId);
        
        // Create upload progress displays
        pdfFiles.forEach(file => {
            formData.append("files", file);
            createProgressBar(file.name);
        });

        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/upload", true);

        // Upload progress listener
        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const percentComplete = Math.round((e.loaded / e.total) * 100);
                updateAllProgressBars(percentComplete);
            }
        };

        xhr.onload = async () => {
            clearProgressBars();
            if (xhr.status === 200) {
                const result = JSON.parse(xhr.responseText);
                showToast("Documents ingested successfully!", "success");
                await loadDocuments();
                if (result.warnings && result.warnings.length > 0) {
                    showToast(`Warning: ${result.warnings.join("; ")}`, "error");
                }
            } else {
                let errMsg = "Failed to upload files.";
                try {
                    const errRes = JSON.parse(xhr.responseText);
                    errMsg = errRes.error || errMsg;
                } catch (e) {}
                showToast(errMsg, "error");
            }
        };

        xhr.onerror = () => {
            clearProgressBars();
            showToast("Network connection error during upload.", "error");
        };

        xhr.send(formData);
    }

    // Progress Bar UI Helpers
    function createProgressBar(filename) {
        const div = document.createElement("div");
        div.className = "progress-item";
        div.innerHTML = `
            <div class="progress-info">
                <span class="doc-name" style="max-width: 180px; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;">${filename}</span>
                <span class="percent">0%</span>
            </div>
            <div class="progress-bar-container">
                <div class="progress-bar-fill"></div>
            </div>
        `;
        uploadProgressContainer.appendChild(div);
    }

    function updateAllProgressBars(percent) {
        const items = uploadProgressContainer.querySelectorAll(".progress-item");
        items.forEach(item => {
            item.querySelector(".percent").textContent = `${percent}%`;
            item.querySelector(".progress-bar-fill").style.width = `${percent}%`;
        });
    }

    function clearProgressBars() {
        uploadProgressContainer.innerHTML = "";
    }

    // Chat Submission
    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const query = queryInput.value.trim();
        if (!query || !currentWorkspaceId || !hasDocuments) return;

        // Clear input field
        queryInput.value = "";

        // Remove welcome screen if present
        const welcome = chatPane.querySelector(".welcome-message-container");
        if (welcome) welcome.remove();

        // 1. Render User message bubble
        appendMessageBubble(query, "user");

        // 2. Render Typing indicator bubble
        const typingIndicator = appendTypingIndicator();

        try {
            const response = await fetch("/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    workspace_id: currentWorkspaceId,
                    message: query
                })
            });

            // Remove typing indicator
            typingIndicator.remove();

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || "Failed to fetch response");
            }

            const data = await response.json();
            
            // 3. Render Assistant message bubble with citations
            appendMessageBubble(data.answer, "assistant", data.citations);

        } catch (err) {
            if (typingIndicator) typingIndicator.remove();
            console.error(err);
            appendMessageBubble(`Error: ${err.message}`, "assistant");
            showToast("Failed to generate response", "error");
        }
    });

    // Append Chat Bubble to Pane
    function appendMessageBubble(text, sender, citations = "") {
        const row = document.createElement("div");
        row.className = `message-row ${sender}`;
        
        const bubble = document.createElement("div");
        bubble.className = "message-bubble";
        
        const textPara = document.createElement("p");
        textPara.textContent = text;
        bubble.appendChild(textPara);

        // Add citations dropdown if assistant message has them
        if (sender === "assistant" && citations && citations.trim() !== "") {
            const citationsDiv = document.createElement("details");
            citationsDiv.className = "citations-wrapper";
            
            const summary = document.createElement("summary");
            summary.textContent = "View Sources";
            citationsDiv.appendChild(summary);

            const ul = document.createElement("ul");
            ul.className = "citations-list";

            // Parse formatted citation string (split by lines)
            const lines = citations.split("\n");
            lines.forEach(line => {
                const cleanLine = line.replace(/^\*\s*/, "").trim();
                // Skip title lines like 'Sources:'
                if (cleanLine && !cleanLine.startsWith("Sources")) {
                    const li = document.createElement("li");
                    li.className = "citation-item";
                    li.innerHTML = `<i class="fa-solid fa-quote-left"></i> <span>${cleanLine}</span>`;
                    ul.appendChild(li);
                }
            });

            citationsDiv.appendChild(ul);
            bubble.appendChild(citationsDiv);
        }

        row.appendChild(bubble);
        chatPane.appendChild(row);
        scrollChatToBottom();
    }

    // Append Typing Indicator Bubble
    function appendTypingIndicator() {
        const row = document.createElement("div");
        row.className = "message-row assistant";
        
        const bubble = document.createElement("div");
        bubble.className = "message-bubble loading-bubble";
        bubble.innerHTML = `
            <div class="dot"></div>
            <div class="dot"></div>
            <div class="dot"></div>
        `;
        row.appendChild(bubble);
        chatPane.appendChild(row);
        scrollChatToBottom();
        return row;
    }

    // Scroll Chat to bottom helper
    function scrollChatToBottom() {
        chatPane.scrollTop = chatPane.scrollHeight;
    }

    function clearChatPane() {
        chatPane.innerHTML = `
            <div class="welcome-message-container">
                <div class="welcome-icon">
                    <i class="fa-solid fa-wand-magic-sparkles"></i>
                </div>
                <h2>Welcome to your fresh RAG Workspace!</h2>
                <p>Upload PDFs to start querying information across documents.</p>
            </div>
        `;
    }

    // Helper: Date Formatter
    function formatDate(dateStr) {
        if (!dateStr) return "Just now";
        try {
            // Parse SQLite timestamp (UTC format)
            const date = new Date(dateStr + " UTC");
            return date.toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit"
            });
        } catch (e) {
            return dateStr;
        }
    }

    // Helper: Toast Message Alerts
    function showToast(message, type = "success") {
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        
        const icon = type === "success" 
            ? '<i class="fa-solid fa-circle-check"></i>' 
            : '<i class="fa-solid fa-circle-exclamation"></i>';
            
        toast.innerHTML = `${icon} <span>${message}</span>`;
        document.body.appendChild(toast);

        // Slide out and remove toast after 3 seconds
        setTimeout(() => {
            toast.style.animation = "slide-in 0.25s reverse ease-in forwards";
            setTimeout(() => toast.remove(), 250);
        }, 3000);
    }

    // Run Startup Initialization
    initWorkspace();
});
