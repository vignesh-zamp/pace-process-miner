// Offscreen Recorder Logic
let recorder;
let data = [];
let timer;
// Default to 20 mins (1200000 ms). For testing we might want shorter.
const CHUNK_DURATION_MS = 20 * 60 * 1000;

chrome.runtime.onMessage.addListener(async (message) => {
    if (message.action === 'INIT_RECORDER') {
        startRecording(message.streamId);
    } else if (message.action === 'STOP_RECORDER_AND_UPLOAD') {
        stopRecording();
    }
});

async function startRecording(streamId) {
    if (recorder && recorder.state === 'recording') {
        return;
    }

    const mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
            mandatory: {
                chromeMediaSource: 'tab',
                chromeMediaSourceId: streamId
            }
        },
        video: {
            mandatory: {
                chromeMediaSource: 'tab',
                chromeMediaSourceId: streamId
            }
        }
    });

    // Continue recording audio even if tab is muted by user? 
    // For now standard settings.

    recorder = new MediaRecorder(mediaStream, { mimeType: 'video/webm;codecs=vp9' });

    recorder.ondataavailable = (event) => data.push(event.data);

    recorder.onstop = async () => {
        // This triggers when we manually stop OR when 20 mins is up and we restart
        const blob = new Blob(data, { type: 'video/webm' });
        data = []; // Clear buffer

        await uploadChunk(blob);

        // Logic for "Looping"
        // If we are still in "Active Mode", we should restart.
        // However, handling seamless restart in offscreen with same streamId might be tricky if stream ended.
        // Actually, MediaRecorder.start(timeslice) might be better?
        // "timeslice": This returns data every X ms. We can accumulate until 20 mins.
        // But user wants "Every 20 mins save... discard... keep looping".
        // So distinct files are better.
    };

    recorder.start();

    // Start the 20-minute automated loop
    // Reset any existing timer
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
        cycleRecording();
    }, CHUNK_DURATION_MS);
}

function stopRecording() {
    if (recorder && recorder.state === 'recording') {
        clearTimeout(timer);
        recorder.stop();
        // Stop tracks to release camera/tab
        recorder.stream.getTracks().forEach(t => t.stop());
    }
}

function cycleRecording() {
    if (recorder && recorder.state === 'recording') {
        // Stopping triggers 'onstop' which handles upload
        // We need to RESTART after upload.
        // BUT 'recorder.stop()' usually kills the stream? 
        // No, stream tracks might stay alive. Let's try.
        // Actually, safer pattern is:
        // requestData() -> upload -> continue.
        // But user wants "20 minute content increments".
        // requestData() gives current blob.

        recorder.requestData();
        // Wait for dataavailable?
        // Actually simplicity:
        // 1. recorder.stop() -> onstop uploads.
        // 2. record.start() again?
        // If stream is active, we can re-use it.

        recorder.stop();
        // We need to restart immediately in onstop? 
        // Let's modify onstop logic below.
    }
}

// Modify onstop to handle looping if still active
// We'll use a global flag
let isLooping = true;

async function uploadChunk(blob) {
    const formData = new FormData();
    // Name it with timestamp
    const filename = `recording_${Date.now()}.webm`;
    formData.append('files', blob, filename);
    // Add Session Context if needed (TODO)

    try {
        console.log('Uploading chunk...', filename, blob.size);
        const response = await fetch('http://localhost:8000/analyze', {
            method: 'POST',
            body: formData
        });
        console.log('Upload complete', response.status);
    } catch (err) {
        console.error('Upload failed', err);
    }

    // If we want to loop, we restart here
    if (isLooping && recorder.stream.active) {
        recorder.start();
        timer = setTimeout(cycleRecording, CHUNK_DURATION_MS);
    }
}

// Update stopRecording to kill loop
function stopRecording() {
    isLooping = false; // Kill loop
    if (recorder && recorder.state === 'recording') {
        clearTimeout(timer);
        recorder.stop();
        recorder.stream.getTracks().forEach(t => t.stop());
    }
}
