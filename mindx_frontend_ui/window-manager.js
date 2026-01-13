// ===== mindX Window Management System =====
// Provides drag-and-drop, resizable windows, and multi-panel support

class WindowManager {
    constructor() {
        this.windows = new Map();
        this.windowCounter = 0;
        this.zIndexCounter = 1000;
        this.activeWindow = null;
        this.windowContainer = null;
        this.isDragging = false;
        this.isResizing = false;
        this.dragOffset = { x: 0, y: 0 };
        this.resizeHandle = null;
        this.resizeStartPos = { x: 0, y: 0 };
        this.resizeStartSize = { width: 0, height: 0 };
        
        this.init();
    }
    
    init() {
        this.windowContainer = document.getElementById('window-container');
        if (!this.windowContainer) {
            console.error('Window container not found');
            return;
        }
        
        // Initialize menu buttons
        this.initMenuButtons();
        
        // Load saved layout
        this.loadLayout();
        
        // Setup drag and drop for agent items
        this.setupAgentDragDrop();
    }
    
    initMenuButtons() {
        const newWindowBtn = document.getElementById('menu-new-window');
        const tileBtn = document.getElementById('menu-tile-windows');
        const cascadeBtn = document.getElementById('menu-cascade-windows');
        const closeAllBtn = document.getElementById('menu-close-all');
        const saveLayoutBtn = document.getElementById('menu-save-layout');
        const loadLayoutBtn = document.getElementById('menu-load-layout');
        const newAgentWindowBtn = document.getElementById('new-agent-window-btn');
        
        if (newWindowBtn) {
            newWindowBtn.addEventListener('click', () => this.createWindow({
                title: 'New Window',
                content: '<div class="window-content-placeholder">Drag content here or use context menu</div>',
                width: 400,
                height: 300
            }));
        }
        
        if (tileBtn) {
            tileBtn.addEventListener('click', () => this.tileWindows());
        }
        
        if (cascadeBtn) {
            cascadeBtn.addEventListener('click', () => this.cascadeWindows());
        }
        
        if (closeAllBtn) {
            closeAllBtn.addEventListener('click', () => this.closeAllWindows());
        }
        
        if (saveLayoutBtn) {
            saveLayoutBtn.addEventListener('click', () => this.saveLayout());
        }
        
        if (loadLayoutBtn) {
            loadLayoutBtn.addEventListener('click', () => this.loadLayout());
        }
        
        if (newAgentWindowBtn) {
            newAgentWindowBtn.addEventListener('click', () => this.createAgentWindow());
        }
    }
    
    createWindow(options = {}) {
        const windowId = `window-${++this.windowCounter}`;
        const {
            title = 'Window',
            content = '',
            width = 400,
            height = 300,
            x = 50 + (this.windowCounter * 30),
            y = 50 + (this.windowCounter * 30),
            minWidth = 200,
            minHeight = 150,
            resizable = true,
            draggable = true,
            closable = true,
            maximizable = true,
            onClose = null
        } = options;
        
        const window = document.createElement('div');
        window.className = 'draggable-window';
        window.id = windowId;
        window.style.width = `${width}px`;
        window.style.height = `${height}px`;
        window.style.left = `${x}px`;
        window.style.top = `${y}px`;
        window.style.zIndex = this.zIndexCounter++;
        
        window.innerHTML = `
            <div class="window-header" data-draggable="${draggable}">
                <div class="window-title">${title}</div>
                <div class="window-controls">
                    ${maximizable ? '<button class="window-btn maximize-btn" title="Maximize">□</button>' : ''}
                    ${closable ? '<button class="window-btn close-btn" title="Close">×</button>' : ''}
                </div>
            </div>
            <div class="window-body">
                ${content}
            </div>
            ${resizable ? '<div class="window-resize-handle"></div>' : ''}
        `;
        
        this.windowContainer.appendChild(window);
        
        // Setup window functionality
        this.setupWindow(window, { draggable, resizable, onClose });
        
        // Store window data
        this.windows.set(windowId, {
            element: window,
            title,
            content,
            width,
            height,
            x,
            y,
            minWidth,
            minHeight,
            resizable,
            draggable,
            onClose,
            isMaximized: false,
            originalState: null
        });
        
        this.updateWindowCount();
        this.bringToFront(window);
        
        return windowId;
    }
    
    setupWindow(window, options) {
        const { draggable, resizable, onClose } = options;
        const windowId = window.id;
        const windowData = this.windows.get(windowId);
        
        // Make window draggable
        if (draggable) {
            const header = window.querySelector('.window-header');
            if (header && header.getAttribute('data-draggable') === 'true') {
                header.addEventListener('mousedown', (e) => this.startDrag(e, window));
            }
        }
        
        // Make window resizable
        if (resizable) {
            const resizeHandle = window.querySelector('.window-resize-handle');
            if (resizeHandle) {
                resizeHandle.addEventListener('mousedown', (e) => this.startResize(e, window));
            }
        }
        
        // Close button
        const closeBtn = window.querySelector('.close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeWindow(windowId));
        }
        
        // Maximize button
        const maximizeBtn = window.querySelector('.maximize-btn');
        if (maximizeBtn) {
            maximizeBtn.addEventListener('click', () => this.toggleMaximize(windowId));
        }
        
        // Click to bring to front
        window.addEventListener('mousedown', () => this.bringToFront(window));
    }
    
    startDrag(e, window) {
        if (e.target.closest('.window-btn')) return;
        
        this.isDragging = true;
        this.activeWindow = window;
        const rect = window.getBoundingClientRect();
        this.dragOffset.x = e.clientX - rect.left;
        this.dragOffset.y = e.clientY - rect.top;
        
        this.bringToFront(window);
        
        document.addEventListener('mousemove', this.handleDrag);
        document.addEventListener('mouseup', this.stopDrag);
        
        e.preventDefault();
    }
    
    handleDrag = (e) => {
        if (!this.isDragging || !this.activeWindow) return;
        
        const containerRect = this.windowContainer.getBoundingClientRect();
        let x = e.clientX - containerRect.left - this.dragOffset.x;
        let y = e.clientY - containerRect.top - this.dragOffset.y;
        
        // Constrain to container bounds
        x = Math.max(0, Math.min(x, containerRect.width - this.activeWindow.offsetWidth));
        y = Math.max(0, Math.min(y, containerRect.height - this.activeWindow.offsetHeight));
        
        this.activeWindow.style.left = `${x}px`;
        this.activeWindow.style.top = `${y}px`;
        
        // Update window data
        const windowId = this.activeWindow.id;
        const windowData = this.windows.get(windowId);
        if (windowData) {
            windowData.x = x;
            windowData.y = y;
        }
    }
    
    stopDrag = () => {
        this.isDragging = false;
        this.activeWindow = null;
        document.removeEventListener('mousemove', this.handleDrag);
        document.removeEventListener('mouseup', this.stopDrag);
    }
    
    startResize(e, window) {
        this.isResizing = true;
        this.resizeHandle = window;
        const rect = window.getBoundingClientRect();
        this.resizeStartPos.x = e.clientX;
        this.resizeStartPos.y = e.clientY;
        this.resizeStartSize.width = rect.width;
        this.resizeStartSize.height = rect.height;
        
        this.bringToFront(window);
        
        document.addEventListener('mousemove', this.handleResize);
        document.addEventListener('mouseup', this.stopResize);
        
        e.preventDefault();
        e.stopPropagation();
    }
    
    handleResize = (e) => {
        if (!this.isResizing || !this.resizeHandle) return;
        
        const windowId = this.resizeHandle.id;
        const windowData = this.windows.get(windowId);
        if (!windowData) return;
        
        const deltaX = e.clientX - this.resizeStartPos.x;
        const deltaY = e.clientY - this.resizeStartPos.y;
        
        let newWidth = this.resizeStartSize.width + deltaX;
        let newHeight = this.resizeStartSize.height + deltaY;
        
        // Apply minimum size constraints
        newWidth = Math.max(windowData.minWidth, newWidth);
        newHeight = Math.max(windowData.minHeight, newHeight);
        
        // Constrain to container bounds
        const containerRect = this.windowContainer.getBoundingClientRect();
        const rect = this.resizeHandle.getBoundingClientRect();
        const maxWidth = containerRect.width - rect.left + containerRect.left;
        const maxHeight = containerRect.height - rect.top + containerRect.top;
        
        newWidth = Math.min(newWidth, maxWidth);
        newHeight = Math.min(newHeight, maxHeight);
        
        this.resizeHandle.style.width = `${newWidth}px`;
        this.resizeHandle.style.height = `${newHeight}px`;
        
        // Update window data
        windowData.width = newWidth;
        windowData.height = newHeight;
    }
    
    stopResize = () => {
        this.isResizing = false;
        this.resizeHandle = null;
        document.removeEventListener('mousemove', this.handleResize);
        document.removeEventListener('mouseup', this.stopResize);
    }
    
    bringToFront(window) {
        window.style.zIndex = this.zIndexCounter++;
        this.activeWindow = window;
    }
    
    toggleMaximize(windowId) {
        const windowData = this.windows.get(windowId);
        if (!windowData) return;
        
        const window = windowData.element;
        
        if (windowData.isMaximized) {
            // Restore
            window.style.width = `${windowData.originalState.width}px`;
            window.style.height = `${windowData.originalState.height}px`;
            window.style.left = `${windowData.originalState.x}px`;
            window.style.top = `${windowData.originalState.y}px`;
            window.classList.remove('maximized');
            windowData.isMaximized = false;
        } else {
            // Maximize
            windowData.originalState = {
                width: window.offsetWidth,
                height: window.offsetHeight,
                x: parseInt(window.style.left),
                y: parseInt(window.style.top)
            };
            
            const containerRect = this.windowContainer.getBoundingClientRect();
            window.style.width = `${containerRect.width}px`;
            window.style.height = `${containerRect.height}px`;
            window.style.left = '0px';
            window.style.top = '0px';
            window.classList.add('maximized');
            windowData.isMaximized = true;
        }
    }
    
    closeWindow(windowId) {
        const windowData = this.windows.get(windowId);
        if (!windowData) return;
        
        if (windowData.onClose) {
            windowData.onClose(windowId);
        }
        
        windowData.element.remove();
        this.windows.delete(windowId);
        this.updateWindowCount();
    }
    
    closeAllWindows() {
        const windowIds = Array.from(this.windows.keys());
        windowIds.forEach(id => this.closeWindow(id));
    }
    
    tileWindows() {
        if (this.windows.size === 0) return;
        
        const containerRect = this.windowContainer.getBoundingClientRect();
        const windows = Array.from(this.windows.values());
        const cols = Math.ceil(Math.sqrt(windows.length));
        const rows = Math.ceil(windows.length / cols);
        
        const windowWidth = (containerRect.width - 20) / cols;
        const windowHeight = (containerRect.height - 20) / rows;
        
        windows.forEach((windowData, index) => {
            const col = index % cols;
            const row = Math.floor(index / cols);
            
            const x = col * windowWidth + 10;
            const y = row * windowHeight + 10;
            
            windowData.element.style.width = `${windowWidth - 20}px`;
            windowData.element.style.height = `${windowHeight - 20}px`;
            windowData.element.style.left = `${x}px`;
            windowData.element.style.top = `${y}px`;
            
            windowData.width = windowWidth - 20;
            windowData.height = windowHeight - 20;
            windowData.x = x;
            windowData.y = y;
            
            if (windowData.isMaximized) {
                windowData.element.classList.remove('maximized');
                windowData.isMaximized = false;
            }
        });
    }
    
    cascadeWindows() {
        if (this.windows.size === 0) return;
        
        const windows = Array.from(this.windows.values());
        const offset = 30;
        const defaultWidth = 400;
        const defaultHeight = 300;
        
        windows.forEach((windowData, index) => {
            const x = 50 + (index * offset);
            const y = 50 + (index * offset);
            
            windowData.element.style.width = `${defaultWidth}px`;
            windowData.element.style.height = `${defaultHeight}px`;
            windowData.element.style.left = `${x}px`;
            windowData.element.style.top = `${y}px`;
            
            windowData.width = defaultWidth;
            windowData.height = defaultHeight;
            windowData.x = x;
            windowData.y = y;
            
            if (windowData.isMaximized) {
                windowData.element.classList.remove('maximized');
                windowData.isMaximized = false;
            }
        });
    }
    
    updateWindowCount() {
        const countElement = document.getElementById('active-window-count');
        if (countElement) {
            countElement.textContent = this.windows.size;
        }
    }
    
    saveLayout() {
        const layout = {
            windows: Array.from(this.windows.entries()).map(([id, data]) => ({
                id,
                title: data.title,
                content: data.content,
                width: data.width,
                height: data.height,
                x: data.x,
                y: data.y,
                minWidth: data.minWidth,
                minHeight: data.minHeight
            })),
            timestamp: Date.now()
        };
        
        localStorage.setItem('mindx-window-layout', JSON.stringify(layout));
        console.log('Layout saved:', layout);
        alert('Layout saved successfully!');
    }
    
    loadLayout() {
        const saved = localStorage.getItem('mindx-window-layout');
        if (!saved) return;
        
        try {
            const layout = JSON.parse(saved);
            if (layout.windows && layout.windows.length > 0) {
                // Close existing windows
                this.closeAllWindows();
                
                // Restore windows
                layout.windows.forEach(windowConfig => {
                    this.createWindow(windowConfig);
                });
                
                console.log('Layout loaded:', layout);
            }
        } catch (error) {
            console.error('Failed to load layout:', error);
        }
    }
    
    setupAgentDragDrop() {
        // This will be called when agents are loaded
        // Agents can be dragged to create new windows
    }
    
    createAgentWindow(agentId = null, agentData = null) {
        const title = agentData ? `Agent: ${agentData.name || agentId}` : 'Agent Monitor';
        const content = agentData ? this.generateAgentContent(agentData) : '<div class="window-content-placeholder">Select an agent to monitor</div>';
        
        return this.createWindow({
            title,
            content,
            width: 500,
            height: 400,
            minWidth: 300,
            minHeight: 200
        });
    }
    
    generateAgentContent(agentData) {
        return `
            <div class="agent-window-content">
                <div class="agent-window-header">
                    <h3>${agentData.name || agentData.agent_id}</h3>
                    <span class="agent-status-badge ${agentData.status || 'inactive'}">${agentData.status || 'Unknown'}</span>
                </div>
                <div class="agent-window-details">
                    <div class="detail-row">
                        <span class="detail-label">Type:</span>
                        <span class="detail-value">${agentData.agent_type || 'N/A'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Status:</span>
                        <span class="detail-value">${agentData.status || 'N/A'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Created:</span>
                        <span class="detail-value">${agentData.created_at ? new Date(parseFloat(agentData.created_at) * 1000).toLocaleString() : 'N/A'}</span>
                    </div>
                </div>
                <div class="agent-window-actions">
                    <div class="action-log" id="agent-action-log-${agentData.agent_id}">
                        <h4>Recent Actions</h4>
                        <div class="action-list"></div>
                    </div>
                </div>
            </div>
        `;
    }
    
    updateAgentWindow(windowId, agentData) {
        const windowData = this.windows.get(windowId);
        if (!windowData) return;
        
        const body = windowData.element.querySelector('.window-body');
        if (body) {
            body.innerHTML = this.generateAgentContent(agentData);
        }
    }
}

// Initialize window manager when DOM is ready
let windowManager = null;

document.addEventListener('DOMContentLoaded', () => {
    // Wait a bit to ensure all DOM elements are ready
    setTimeout(() => {
        windowManager = new WindowManager();
        window.windowManager = windowManager; // Make globally accessible
        console.log('Window Manager initialized and ready');
    }, 100);
});

