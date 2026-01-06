document.addEventListener('DOMContentLoaded', () => {
    const startBtn = document.getElementById('startBtn');

    startBtn.addEventListener('click', () => {
        chrome.tabs.create({ url: 'recorder.html' });
        window.close();
    });

    // Check if recorder tab is already open? 
    // Optional Enhancement: focus existing tab instead of opening new one.
    chrome.tabs.query({ title: "Pace - Recording Session" }, (tabs) => {
        if (tabs.length > 0) {
            startBtn.textContent = "Switch to Recorder Tab";
            startBtn.onclick = () => {
                chrome.tabs.update(tabs[0].id, { active: true });
                window.close();
            };
        }
    });

});
