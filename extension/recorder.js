// Recorder Tab Logic (Full Screen Support)
let recorder;
let data = [];
let timer;
let currentSessionId = null;
const CHUNK_DURATION_MS = 20 * 60 * 1000; // 20 mins

const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const statusText = document.getElementById('statusText');

startBtn.addEventListener('click', startCapture);
stopBtn.addEventListener('click', stopCapture);

async function startCapture() {
    try {
        const stream = await navigator.mediaDevices.getDisplayMedia({
            video: { cursor: "always" },
            audio: false
        });

        currentSessionId = `sess_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        console.log("Starting Session:", currentSessionId);

        updateUI(true);

        recorder = new MediaRecorder(stream, { mimeType: 'video/webm;codecs=vp9' });

        recorder.ondataavailable = (e) => {
            if (e.data.size > 0) data.push(e.data);
        };

        recorder.onstop = async () => {
            const blob = new Blob(data, { type: 'video/webm' });
            data = [];
            await uploadChunk(blob);
        };

        stream.getVideoTracks()[0].onended = () => {
            stopCapture();
        };

        recorder.start();
        startTimer();

    } catch (err) {
        console.error("Error selecting screen:", err);
        statusText.textContent = "Selection cancelled.";
    }
}

function startTimer() {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
        cycleRecording();
    }, CHUNK_DURATION_MS);
}

function cycleRecording() {
    if (recorder && recorder.state === 'recording') {
        recorder.stop();
    }
}

let isLooping = true;
let chunkCounter = 0;

async function uploadChunk(blob) {
    statusText.textContent = "Uploading chunk...";

    const formData = new FormData();
    const filename = `recording_${Date.now()}.webm`;
    formData.append('files', blob, filename);
    formData.append('session_id', currentSessionId);

    try {
        await fetch('http://localhost:8000/analyze', {
            method: 'POST',
            body: formData
        });
        console.log("Chunk uploaded");
    } catch (e) {
        console.error("Upload failed", e);
    }

    if (isLooping && recorder.stream && recorder.stream.active) {
        recorder.start();
        chunkCounter++;
        statusText.textContent = "Recording Active (Chunk " + (chunkCounter + 1) + ")...";
        startTimer();
    } else {
        statusText.textContent = "Session Ended.";
        updateUI(false);
    }
}

function stopCapture() {
    isLooping = false;
    if (timer) clearTimeout(timer);
    if (recorder && recorder.state === 'recording') {
        recorder.stop();
    }
    if (recorder && recorder.stream) {
        recorder.stream.getTracks().forEach(t => t.stop());
    }
    updateUI(false);
}

function updateUI(recording) {
    if (recording) {
        startBtn.classList.add('hidden');
        stopBtn.classList.remove('hidden');
        statusText.innerHTML = '<span class="status-dot"></span>Recording Active...';
    } else {
        startBtn.classList.remove('hidden');
        stopBtn.classList.add('hidden');
        statusText.textContent = "Ready to Record";
    }
}
