let sessionId = null;
let uploadedDocuments = [];

// DOM Elements
const dropZone = document.getElementById("dropZone");
const pdfInput = document.getElementById("pdfInput");
const docList = document.getElementById("docList");
const noDocsText = document.getElementById("noDocsText");
const sessionIdDisplay = document.getElementById("sessionIdDisplay");
const clearSessionBtn = document.getElementById("clearSessionBtn");
const messagesViewport = document.getElementById("messagesViewport");
const emptyState = document.getElementById("emptyState");
const chatInput = document.getElementById("chatInput");
const sendBtn = document.getElementById("sendBtn");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");

// Initialize Session
async function getOrCreateSession() {
    sessionId = localStorage.getItem("session_id");
    
    if (!sessionId) {
        try {
            updateStatus("Initializing session...", "loading");
            const response = await fetch("/api/upload/create-session", { method: "POST" });
            const data = await response.json();
            sessionId = data.session_id;
            localStorage.setItem("session_id", sessionId);
            updateStatus("Ready", "ready");
        } catch (e) {
            console.error("Failed to create session:", e);
            updateStatus("Connection Error", "error");
            return;
        }
    }
    
    sessionIdDisplay.innerText = sessionId;
    
    // Load historical state if page was refreshed
    await loadSessionHistory();
}

// Update Status indicators
function updateStatus(text, type) {
    statusText.innerText = text;
    statusDot.className = "status-dot";
    
    if (type === "loading") {
        statusDot.classList.add("loading");
    } else if (type === "ready") {
        statusDot.style.backgroundColor = "var(--success)";
        statusDot.style.boxShadow = "0 0 8px var(--success)";
    } else if (type === "error") {
        statusDot.style.backgroundColor = "var(--error)";
        statusDot.style.boxShadow = "0 0 8px var(--error)";
    }
}

// Load session's files & conversations
async function loadSessionHistory() {
    try {
        updateStatus("Loading session history...", "loading");
        
        // 1. Fetch ingested documents for the session
        const docsResponse = await fetch(`/api/upload/documents/${sessionId}`);
        if (docsResponse.status === 404) {
            // Invalid session in localStorage, clear it
            localStorage.removeItem("session_id");
            await getOrCreateSession();
            return;
        }
        
        const docsData = await docsResponse.json();
        let hasCompletedDoc = false;
        
        if (docsData.success && docsData.documents && docsData.documents.length > 0) {
            noDocsText.style.display = "none";
            docsData.documents.forEach(doc => {
                addDocToList(doc);
                if (doc.ingestion) {
                    if (doc.ingestion.status === "processing") {
                        pollIngestionStatus(doc.document_id);
                    } else if (doc.ingestion.status === "completed") {
                        hasCompletedDoc = true;
                    }
                }
            });
        }
        
        // 2. Fetch conversation history
        const response = await fetch(`/api/chat/history/${sessionId}`);
        const data = await response.json();
        if (data.success && data.history && data.history.length > 0) {
            emptyState.style.display = "none";
            data.history.forEach(turn => {
                appendMessage(turn.question, "user");
                appendMessage(turn.answer, "assistant");
            });
        }
        
        // Enable chat input if at least one document is completed
        if (hasCompletedDoc) {
            enableChat();
            updateStatus("Ready", "ready");
        } else {
            disableChat();
            updateStatus("Upload PDFs to begin", "ready");
        }
    } catch (e) {
        console.error("Failed to load history:", e);
        updateStatus("Error loading history", "error");
    }
}

// Enable inputs
function enableChat() {
    chatInput.disabled = false;
    sendBtn.disabled = false;
    chatInput.placeholder = "Ask a question across uploaded PDFs...";
}

// Disable inputs
function disableChat() {
    chatInput.disabled = true;
    sendBtn.disabled = true;
    chatInput.placeholder = "Upload PDFs in the sidebar to start chat...";
}

// Setup drag and drop events
dropZone.addEventListener("click", () => pdfInput.click());

dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.style.borderColor = "var(--accent)";
    dropZone.style.background = "rgba(99, 102, 241, 0.08)";
});

dropZone.addEventListener("dragleave", () => {
    dropZone.style.borderColor = "rgba(255, 255, 255, 0.1)";
    dropZone.style.background = "rgba(255, 255, 255, 0.02)";
});

dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.style.borderColor = "rgba(255, 255, 255, 0.1)";
    dropZone.style.background = "rgba(255, 255, 255, 0.02)";
    
    if (e.dataTransfer.files.length > 0) {
        uploadPDFs(e.dataTransfer.files);
    }
});

pdfInput.addEventListener("change", () => {
    if (pdfInput.files.length > 0) {
        uploadPDFs(pdfInput.files);
    }
});

// File Upload Handler
async function uploadPDFs(files) {
    updateStatus("Uploading PDFs...", "loading");
    
    const formData = new FormData();
    formData.append("session_id", sessionId);
    for (let file of files) {
        formData.append("files", file);
    }
    
    try {
        const response = await fetch("/api/upload/pdfs", {
            method: "POST",
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            data.documents.forEach(doc => {
                addDocToList(doc);
                if (doc.ingestion && doc.ingestion.status === "processing") {
                    pollIngestionStatus(doc.document_id);
                }
            });
            updateStatus("Processing documents...", "loading");
        } else {
            alert("Upload failed: " + data.message);
            updateStatus("Upload Failed", "error");
        }
    } catch (e) {
        console.error("Upload error:", e);
        alert("An error occurred during file upload.");
        updateStatus("Upload Failed", "error");
    }
}

// Render Document Item in Sidebar
function addDocToList(doc) {
    noDocsText.style.display = "none";
    
    const item = document.createElement("div");
    item.className = "doc-item";
    item.id = `doc_${doc.document_id}`;
    item.dataset.documentId = doc.document_id;
    
    const status = doc.ingestion ? doc.ingestion.status : "unknown";
    const message = doc.ingestion ? doc.ingestion.message : "";
    const pages = doc.ingestion ? (doc.ingestion.pages || 0) : 0;
    const parentChunks = doc.ingestion ? (doc.ingestion.parents || 0) : 0;
    
    let metaText = "";
    let icon = "📄";
    if (status === "processing") {
        metaText = `<span style="color: var(--accent); font-weight: 500;">⏳ ${message}</span>`;
    } else if (status === "completed") {
        metaText = `${pages} pgs • ${parentChunks} chunks`;
    } else if (status === "failed") {
        metaText = `<span style="color: var(--error);">❌ Ingestion failed</span>`;
    } else {
        metaText = `${pages} pgs • ${parentChunks} chunks`;
    }
    
    item.innerHTML = `
        <div class="doc-item-icon">${icon}</div>
        <div class="doc-item-info">
            <div class="doc-item-name" title="${doc.filename}">${doc.filename}</div>
            <div class="doc-item-meta" id="meta_${doc.document_id}">${metaText}</div>
        </div>
        <button class="doc-delete-btn" title="Delete PDF">🗑️</button>
    `;
    
    // Attach delete button handler
    const deleteBtn = item.querySelector(".doc-delete-btn");
    deleteBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        if (confirm(`Are you sure you want to delete "${doc.filename}"?`)) {
            await deleteDocument(doc.document_id, doc.filename, item);
        }
    });
    
    docList.appendChild(item);
}

// Delete individual document
async function deleteDocument(documentId, filename, itemElement) {
    updateStatus(`Deleting ${filename}...`, "loading");
    
    try {
        const response = await fetch(`/api/upload/document/${documentId}`, {
            method: "DELETE"
        });
        
        const data = await response.json();
        
        if (data.success) {
            itemElement.remove();
            
            // Re-evaluate documents list
            const remainingDocs = docList.querySelectorAll(".doc-item");
            if (remainingDocs.length === 0) {
                noDocsText.style.display = "block";
                disableChat();
            } else {
                // Check if at least one remaining doc is completed
                let hasCompleted = false;
                for (let docItem of remainingDocs) {
                    const docId = docItem.dataset.documentId;
                    const metaElem = document.getElementById(`meta_${docId}`);
                    if (metaElem && !metaElem.innerHTML.includes("⏳") && !metaElem.innerHTML.includes("❌")) {
                        hasCompleted = true;
                    }
                }
                if (hasCompleted) {
                    enableChat();
                } else {
                    disableChat();
                }
            }
            updateStatus("Ready", "ready");
        } else {
            alert("Failed to delete document: " + data.message);
            updateStatus("Error", "error");
        }
    } catch (e) {
        console.error("Delete document error:", e);
        alert("An error occurred during document deletion.");
        updateStatus("Error", "error");
    }
}

// Poll status of an ingestion
function pollIngestionStatus(document_id) {
    const interval = setInterval(async () => {
        const metaElem = document.getElementById(`meta_${document_id}`);
        if (!metaElem) {
            clearInterval(interval);
            return;
        }
        
        try {
            const response = await fetch(`/api/upload/status/${document_id}`);
            const data = await response.json();
            
            if (data.status === "processing") {
                metaElem.innerHTML = `<span style="color: var(--accent); font-weight: 500;">⏳ ${data.message}</span>`;
            } else if (data.status === "completed") {
                clearInterval(interval);
                metaElem.innerText = `${data.pages} pgs • ${data.parents} chunks`;
                enableChat();
                updateStatus("Ready", "ready");
            } else if (data.status === "failed") {
                clearInterval(interval);
                metaElem.innerHTML = `<span style="color: var(--error);" title="${data.message}">❌ Failed: ${data.message}</span>`;
                alert(`Ingestion failed: ${data.message}`);
                updateStatus("Processing Failed", "error");
            }
        } catch (e) {
            console.error("Polling error:", e);
        }
    }, 2000);
}

// Send Message Flow
async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;
    
    // Clear input & disable UI
    chatInput.value = "";
    chatInput.style.height = "44px";
    chatInput.disabled = true;
    sendBtn.disabled = true;
    
    emptyState.style.display = "none";
    
    // Append user message
    appendMessage(text, "user");
    
    // Append typing indicator
    const typingIndicator = appendTypingIndicator();
    updateStatus("Thinking...", "loading");
    
    try {
        const response = await fetch("/api/chat/message", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: sessionId,
                message: text
            })
        });
        
        const data = await response.json();
        
        // Remove typing indicator
        typingIndicator.remove();
        
        if (data.success) {
            appendMessage(data.answer, "assistant", data.citations);
            updateStatus("Ready", "ready");
        } else {
            appendMessage("Sorry, I encountered an error. " + data.message, "assistant");
            updateStatus("Error", "error");
        }
    } catch (e) {
        console.error("Message error:", e);
        typingIndicator.remove();
        appendMessage("Network error: Failed to reach the server.", "assistant");
        updateStatus("Error", "error");
    } finally {
        chatInput.disabled = false;
        sendBtn.disabled = false;
        chatInput.focus();
    }
}

// Append chat bubbles
function appendMessage(text, sender, citations = []) {
    const wrapper = document.createElement("div");
    wrapper.className = `message-wrapper ${sender}`;
    
    const avatar = document.createElement("div");
    avatar.className = `avatar ${sender}`;
    avatar.innerText = sender === "user" ? "U" : "AI";
    
    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    
    // Escape and format newlines
    let formattedText = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\n/g, "<br>");
    
    bubble.innerHTML = formattedText;
    
    // Append citations if any
    if (sender === "assistant" && citations && citations.length > 0) {
        const citationsBox = document.createElement("div");
        citationsBox.className = "citations-box";
        
        const title = document.createElement("div");
        title.className = "citations-header";
        title.innerText = "Sources Referenced:";
        citationsBox.appendChild(title);
        
        const list = document.createElement("div");
        list.className = "citations-list";
        
        citations.forEach(cit => {
            const badge = document.createElement("div");
            badge.className = "citation-badge";
            badge.innerHTML = `📄 ${cit.filename} (Page ${cit.page_number})`;
            list.appendChild(badge);
        });
        
        citationsBox.appendChild(list);
        bubble.appendChild(citationsBox);
    }
    
    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
    messagesViewport.appendChild(wrapper);
    messagesViewport.scrollTop = messagesViewport.scrollHeight;
}

// Typing Indicator
function appendTypingIndicator() {
    const wrapper = document.createElement("div");
    wrapper.className = "message-wrapper assistant";
    
    const avatar = document.createElement("div");
    avatar.className = "avatar assistant";
    avatar.innerText = "AI";
    
    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    
    bubble.innerHTML = `
        <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    
    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
    messagesViewport.appendChild(wrapper);
    messagesViewport.scrollTop = messagesViewport.scrollHeight;
    
    return wrapper;
}

// Reset / Clear Session
clearSessionBtn.addEventListener("click", async () => {
    if (!confirm("Are you sure you want to clear this session? All uploaded PDFs, conversation history, and vectors will be permanently deleted.")) {
        return;
    }
    
    updateStatus("Clearing session...", "loading");
    
    try {
        const response = await fetch(`/api/chat/session/${sessionId}`, {
            method: "DELETE"
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Reset state
            localStorage.removeItem("session_id");
            sessionId = null;
            docList.innerHTML = `<div style="font-size: 0.85rem; color: var(--text-muted); text-align: center; margin-top: 10px;" id="noDocsText">No documents uploaded yet.</div>`;
            messagesViewport.innerHTML = `
                <div class="empty-state" id="emptyState">
                    <div class="empty-state-icon">🤖</div>
                    <div class="empty-state-title">Welcome to RAG Assistant</div>
                    <div class="empty-state-desc">
                        Upload your PDF documents in the sidebar, and I will parse, chunk, and embed them. Then you can ask questions across all documents in this session!
                    </div>
                </div>
            `;
            disableChat();
            
            // Re-initialize a clean session
            await getOrCreateSession();
        } else {
            alert("Failed to clear session: " + data.message);
            updateStatus("Error", "error");
        }
    } catch (e) {
        console.error("Clear session error:", e);
        updateStatus("Error", "error");
    }
});

// Chat Input Auto-resize & submit on enter
chatInput.addEventListener("input", () => {
    chatInput.style.height = "auto";
    chatInput.style.height = (chatInput.scrollHeight) + "px";
});

chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

sendBtn.addEventListener("click", sendMessage);

// Page Load Lifecycle
window.onload = async () => {
    await getOrCreateSession();
};