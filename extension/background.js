// Background Service Worker
// MV3 requires offscreen document for DOM-based MediaRecorder

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'START_RECORDING') {
        startRecording(sendResponse);
        return true; // async response
    } else if (message.action === 'STOP_RECORDING') {
        stopRecording(sendResponse);
        return true;
    }
});

async function startRecording(sendResponse) {
    // Check if offscreen document exists, if not create it
    const existingContexts = await chrome.runtime.getContexts({});
    const offscreenDocument = existingContexts.find(c => c.contextType === 'OFFSCREEN_DOCUMENT');

    if (!offscreenDocument) {
        await chrome.offscreen.createDocument({
            url: 'offscreen.html',
            reasons: ['USER_MEDIA'],
            justification: 'Recording screen for process mining'
        });
    }

    // Get active tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    // Get stream ID
    // targetTabId: The tab we want to RECORD (the user's work)
    // consumerTabId: The tab that will VIEW/RECORD the stream (our offscreen doc). 
    // If we omit consumerTabId, it defaults to the extension, so offscreen doc can use it.
    const streamId = await chrome.tabCapture.getMediaStreamId({
        targetTabId: tab.id
    });

    // Send stream ID to offscreen document to start MediaRecorder
    chrome.runtime.sendMessage({
        action: 'INIT_RECORDER',
        streamId: streamId
    }, (response) => {
        chrome.storage.local.set({ isRecording: true });
        sendResponse({ success: true });
    });
}

function stopRecording(sendResponse) {
    chrome.runtime.sendMessage({ action: 'STOP_RECORDER_AND_UPLOAD' }, (response) => {
        chrome.storage.local.set({ isRecording: false });
        // Close offscreen doc to save resources? 
        // Maybe keep it open if we want to loop. 
        // For now, let's keep it simple.
        sendResponse({ success: true });
    });
}
