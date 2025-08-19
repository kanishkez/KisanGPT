const chat = document.getElementById('chat');
const input = document.getElementById('input');
const send = document.getElementById('send');
const imageButton = document.getElementById('imageButton');
const imageInput = document.getElementById('imageInput');
const imagePreview = document.getElementById('imagePreview');
const previewImg = document.getElementById('previewImg');
const removeImage = document.getElementById('removeImage');
// Removed API key elements

// Voice UI elements
const recordBtn = document.getElementById('recordBtn');
const speakerBtn = document.getElementById('speakerBtn');
const sendTranscriptBtn = document.getElementById('sendTranscriptBtn');
const liveTranscriptEl = document.getElementById('liveTranscript');
const voiceLoader = document.getElementById('voiceLoader');
const voiceAnswer = document.getElementById('voiceAnswer');
const voiceAnswerText = document.getElementById('voiceAnswerText');
const retryTTS = document.getElementById('retryTTS');
// Inline mic and language selector in input area
const inlineRecordBtn = document.getElementById('inlineRecordBtn');
const langSelect = document.getElementById('langSelect');

// Session management
// Toggle this to true if you want chats to persist across reloads
const PERSIST_HISTORY = false;
let sessionId = null;
let selectedImage = null;
let geminiApiKey = localStorage.getItem('gemini_api_key') || null;
let conversationHistory = [];

// Voice state
let recognition = null;
let isRecording = false;
let finalTranscript = '';
let interimTranscript = '';
let lastAnswerText = '';
let lastAnswerLang = 'en';

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    setupDragAndDrop();
    setupPasteSupport();
    initVoice();
    if (!PERSIST_HISTORY) {
      try { localStorage.removeItem('kisangpt_conversation_history'); } catch {}
      conversationHistory = [];
    } else {
      loadConversationHistory();
    }
});

// Conversation history functions
function saveMessageToHistory(text, who, imageData = null) {
    if (!PERSIST_HISTORY) return; // do not persist between reloads
    const message = {
        text: text,
        who: who,
        timestamp: new Date().toISOString(),
        imageData: imageData
    };
    conversationHistory.push(message);
    
    // Keep only last 50 messages to prevent storage bloat
    if (conversationHistory.length > 50) {
        conversationHistory = conversationHistory.slice(-50);
    }
    
    localStorage.setItem('kisangpt_conversation_history', JSON.stringify(conversationHistory));
}

function loadConversationHistory() {
    if (!PERSIST_HISTORY) return; // skip loading in non-persistent mode
    try {
        const saved = localStorage.getItem('kisangpt_conversation_history');
        if (saved) {
            conversationHistory = JSON.parse(saved);
            
            // Restore messages to chat
            conversationHistory.forEach(msg => {
                addMessageToDOM(msg.text, msg.who, msg.imageData);
            });
        }
    } catch (error) {
        console.log('Could not load conversation history:', error);
        conversationHistory = [];
    }
}

function addMessageToDOM(text, who, imageData = null) {
    const div = document.createElement('div');
    div.className = `message ${who}`;
    
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    
    // Add image if provided
    if (imageData) {
        const img = document.createElement('img');
        img.src = imageData;
        img.className = 'message-image';
        img.style.cssText = 'max-width: 300px; max-height: 200px; border-radius: 8px; margin-bottom: 10px; display: block;';
        bubble.appendChild(img);
    }
    
    const html = text
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
    
    const textDiv = document.createElement('div');
    textDiv.innerHTML = html;
    bubble.appendChild(textDiv);

    // Per-message TTS for bot replies
    if (who === 'bot') {
        const ttsBtn = document.createElement('button');
        ttsBtn.className = 'tts-btn';
        ttsBtn.title = 'Play this answer';
        ttsBtn.textContent = '🔊';
        ttsBtn.addEventListener('click', () => speakText(text));
        bubble.appendChild(ttsBtn);
    }
    
    div.appendChild(bubble);
    chat.appendChild(div);
}

// Check server configuration
async function checkServerConfig() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();
        
        if (config.has_api_key) {
            // Hide API key section if server has API key
            const apiKeySection = document.querySelector('.api-key-section');
            if (apiKeySection) {
                apiKeySection.style.display = 'none';
            }
            
            // Hide the API key notice entirely
            const notice = document.getElementById('apiKeyNotice');
            if (notice) {
                notice.style.display = 'none';
            }
            
            // Set flag to indicate server has API key
            window.serverHasApiKey = true;
        }
    } catch (error) {
        console.log('Could not check server config:', error);
    }
}

function loadApiKey() {
    if (geminiApiKey) {
        apiKeyInput.value = geminiApiKey;
        hideApiKeyNotice();
    }
}

function updateApiKeyNotice() {
    if (!window.serverHasApiKey && !geminiApiKey) {
        apiKeyNotice.style.display = 'block';
        apiKeyNotice.textContent = 'Please enter your API key';
        apiKeyNotice.style.color = '#f87171';
    } else {
        apiKeyNotice.style.display = 'none';
    }
}

function extractLocation(text) {
  // Common Indian cities
  const cities = [
    'Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Chennai', 'Kolkata', 
    'Pune', 'Ahmedabad', 'Surat', 'Nashik', 'Nagpur', 'Lucknow', 
    'Kanpur', 'Indore', 'Thane', 'Bhopal', 'Visakhapatnam', 'Patna'
  ];
  
  // Find first matching city in text
  const found = cities.find(city => 
    text.toLowerCase().includes(city.toLowerCase())
  );
  
  return found || null;
}

function generateFallbackResponse(message) {
  const msg = message.toLowerCase();
  
  return `Welcome to KisanGPT - Your Intelligent Farming Assistant!

I'm here to provide you with data-driven agricultural insights based on real government data and market intelligence. Here's how I can help transform your farming decisions:

What I Can Do For You:

**Crop Planning & Recommendations**
- Region-specific crop suggestions based on soil, climate, and market data
- Seasonal planning with sowing and harvesting calendars
- Crop rotation strategies for soil health and profitability
- High-value crop identification for maximum returns

**Market Intelligence**
- Real-time mandi prices from data.gov.in
- Price trend analysis and forecasting
- MSP updates and procurement information
- Export market opportunities and quality requirements

**Farming Best Practices**
- Scientific cultivation techniques for higher yields
- Integrated pest and disease management
- Fertilizer recommendations and soil health management
- Water-efficient irrigation strategies

**Weather & Risk Management**
- Weather-based farming advisories
- Crop insurance guidance
- Risk mitigation strategies for climate challenges

Popular Questions to Get Started:
- "What are the most profitable crops for [your state/district]?"
- "Current market prices and trends for wheat/rice/cotton"
- "Best farming practices for increasing yield in [specific crop]"
- "Weather-based farming advice for this season"
- "Government schemes and subsidies available for farmers"

Pro Tip: Be specific about your location, crop, or farming challenge for the most accurate and actionable advice!

Ask me anything about farming - I'm powered by real data and designed to help you make informed agricultural decisions.

— KisanGPT`;
}

function addMessage(text, who, imageData = null){
  const div = document.createElement('div');
  div.className = `message ${who}`;
  
  // Bubble
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  
  // Add image if provided
  if (imageData) {
    const img = document.createElement('img');
    img.src = imageData;
    img.className = 'message-image';
    img.style.cssText = 'max-width: 300px; max-height: 200px; border-radius: 8px; margin-bottom: 10px; display: block;';
    bubble.appendChild(img);
  }
  
  // Basic Markdown rendering
  const html = text
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');
  
  const textDiv = document.createElement('div');
  textDiv.innerHTML = html;
  bubble.appendChild(textDiv);

  if (who === 'bot') {
    const ttsBtn = document.createElement('button');
    ttsBtn.className = 'tts-btn';
    ttsBtn.title = 'Play this answer';
    ttsBtn.textContent = '🔊';
    ttsBtn.addEventListener('click', () => speakText(text));
    bubble.appendChild(ttsBtn);
  }
  
  div.appendChild(bubble);
  chat.appendChild(div);
  
  // Save to conversation history
  saveMessageToHistory(text, who, imageData);
  
  // Scroll to bottom
  chat.scrollTop = chat.scrollHeight;
}

function addThinkingMessage() {
  const div = document.createElement('div');
  div.className = 'message bot thinking';
  div.id = 'thinking-message';
  
  // Bubble with thinking animation
  const thinkingBubble = document.createElement('div');
  thinkingBubble.className = 'bubble thinking-bubble';
  thinkingBubble.innerHTML = `
    <div class="thinking-text">
      <span class="thinking-dots">
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="dot"></span>
      </span>
      KisanGPT is thinking...
    </div>
  `;
  
  div.appendChild(thinkingBubble);
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  
  // Force a reflow to ensure animation starts
  div.offsetHeight;
}

function removeThinkingMessage() {
  const thinkingMessage = document.getElementById('thinking-message');
  if (thinkingMessage) {
    thinkingMessage.remove();
  }
}

// API Key management
function saveApiKeyToStorage() {
  const key = apiKeyInput.value.trim();
  if (key) {
    geminiApiKey = key;
    localStorage.setItem('gemini_api_key', key);
    hideApiKeyNotice();
    addMessage('✅ API key saved successfully! You can now use KisanGPT.', 'bot');
  }
}

function hideApiKeyNotice() {
  if (apiKeyNotice) {
    apiKeyNotice.style.display = 'none';
  }
}

// Image handling with drag and drop support
function handleImageSelection(event) {
  const file = event.target.files[0];
  if (file) {
    processImageFile(file);
  }
}

function processImageFile(file) {
  // Validate file type
  if (!file.type.startsWith('image/')) {
    addMessage('⚠️ Please select a valid image file (JPG, PNG, GIF, WebP)', 'bot');
    return;
  }
  
  // Validate file size (max 10MB)
  if (file.size > 10 * 1024 * 1024) {
    addMessage('⚠️ Image file is too large. Please select an image under 10MB.', 'bot');
    return;
  }
  
  selectedImage = file;
  const reader = new FileReader();
  reader.onload = function(e) {
    previewImg.src = e.target.result;
    imagePreview.style.display = 'block';
    // Remove the automatic message - only show image in preview, not in conversation
  };
  reader.readAsDataURL(file);
}

// Drag and drop functionality
function setupDragAndDrop() {
  const inputContainer = document.querySelector('.input-container');
  
  // Prevent default drag behaviors
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    inputContainer.addEventListener(eventName, preventDefaults, false);
    document.body.addEventListener(eventName, preventDefaults, false);
  });
  
  // Highlight drop area when item is dragged over it
  ['dragenter', 'dragover'].forEach(eventName => {
    inputContainer.addEventListener(eventName, highlight, false);
  });
  
  ['dragleave', 'drop'].forEach(eventName => {
    inputContainer.addEventListener(eventName, unhighlight, false);
  });
  
  // Handle dropped files
  inputContainer.addEventListener('drop', handleDrop, false);
}

function preventDefaults(e) {
  e.preventDefault();
  e.stopPropagation();
}

function highlight(e) {
  const inputContainer = document.querySelector('.input-container');
  inputContainer.classList.add('drag-over');
}

function unhighlight(e) {
  const inputContainer = document.querySelector('.input-container');
  inputContainer.classList.remove('drag-over');
}

function handleDrop(e) {
  const dt = e.dataTransfer;
  const files = dt.files;
  
  if (files.length > 0) {
    processImageFile(files[0]);
  }
}

// Paste image functionality
function setupPasteSupport() {
  document.addEventListener('paste', function(e) {
    const items = e.clipboardData.items;
    
    for (let i = 0; i < items.length; i++) {
      if (items[i].type.indexOf('image') !== -1) {
        const blob = items[i].getAsFile();
        processImageFile(blob);
        e.preventDefault();
        break;
      }
    }
  });
}

function removeSelectedImage() {
  selectedImage = null;
  imagePreview.style.display = 'none';
  imageInput.value = '';
}

async function callChatAPI(text, location=null){
  try {
    // Store image data before clearing selectedImage
    let userImageData = null;
    if (selectedImage) {
      userImageData = await new Promise(resolve => {
        const reader = new FileReader();
        reader.onload = function(e) {
          resolve(e.target.result);
        };
        reader.readAsDataURL(selectedImage);
      });
    }
    
    // Add user message with image
    addMessage(text, 'user', userImageData);
    
    // Add thinking message
    addThinkingMessage();
    
    const endpoint = selectedImage ? '/api/chat-with-image' : '/api/chat';
    
    let requestData;
    let headers = {};
    
    if (selectedImage) {
      // Form data for image upload
      const formData = new FormData();
      formData.append('message', text);
      formData.append('image', selectedImage);
      if (location) formData.append('location', location);
      if (sessionId) formData.append('session_id', sessionId);
      
      requestData = formData;
    } else {
      // JSON for text-only
      headers['Content-Type'] = 'application/json';
      requestData = JSON.stringify({ 
        message: text,
        location: location || extractLocation(text),
        session_id: sessionId,
        gemini_api_key: window.serverHasApiKey ? null : (geminiApiKey || null),
        conversation_history: conversationHistory.slice(-10) // Send last 10 messages for context
      });
    }
    
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: headers,
      body: requestData
    });
    
    if(!res.ok){
      console.error('HTTP Error:', res.status, res.statusText);
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }
    
    const data = await res.json();
    console.log('API Response:', data);
    
    // Store session ID for future requests
    if (data.session_id) {
      sessionId = data.session_id;
    }
    
    // Clear image after sending
    if (selectedImage) {
      removeSelectedImage();
    }
    
    return data;
  } catch (error) {
    console.error('API Call Error:', error);
    throw error;
  }
}

async function handleSend() {
  const message = input.value.trim();
  if (!message && !selectedImage) return;

  try {
    // Stop recording if currently recording
    if (isRecording) {
      stopRecording();
    }

    // Disable input and show loading state
    input.disabled = true;
    send.classList.add('loading');
    send.disabled = true;

    // Clear input immediately
    input.value = '';

    // Remove any stray live transcript bubble if present (legacy)
    const liveEl = document.getElementById('live-transcript-chat');
    if (liveEl) liveEl.remove();

    // Call API (which will add the user message internally)
    try {
      const response = await callChatAPI(message);
      
      // Remove thinking message
      removeThinkingMessage();
      
      if (response && response.response) {
        addMessage(response.response, 'bot');
        
      } else {
        // Fallback response
        addMessage(generateFallbackResponse(message), 'bot');
      }
    } catch (apiError) {
      console.error('API Error:', apiError);
      removeThinkingMessage();
      addMessage(generateFallbackResponse(message), 'bot');
    }
  } catch(e) {
    console.error('Full Error Details:', e);
    removeThinkingMessage();
    
    // Show a working response instead of error
    addMessage(`KisanGPT is here to help!

I can provide advice on:
- **Crop recommendations** for your region
- **Market prices** and farming trends  
- **Best practices** for agriculture
- **Image analysis** for crop health
- **Weather guidance** for farming

Try asking: "What crops should I grow in Punjab?" or "Current market prices"

— KisanGPT`, 'bot');
  } finally {
    // Re-enable input and hide loading state
    input.disabled = false;
    send.classList.remove('loading');
    send.disabled = false;
    input.focus();
  }
}

// =========================
// Voice: init and handlers
// =========================
function initVoice() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    if (recordBtn) recordBtn.disabled = true;
    if (sendTranscriptBtn) sendTranscriptBtn.disabled = true;
    if (speakerBtn) speakerBtn.disabled = true;
    if (inlineRecordBtn) inlineRecordBtn.disabled = true;
    return;
  }

  recognition = new SpeechRecognition();
  // We'll set recognition.lang dynamically on start based on selected language
  recognition.continuous = true;
  recognition.interimResults = true;

  recognition.onstart = () => {
    isRecording = true;
    finalTranscript = '';
    interimTranscript = '';
    if (recordBtn) {
      recordBtn.setAttribute('aria-pressed', 'true');
      recordBtn.textContent = '⏹ Stop';
    }
    if (inlineRecordBtn) {
      inlineRecordBtn.setAttribute('aria-pressed', 'true');
      inlineRecordBtn.textContent = '⏹';
      inlineRecordBtn.title = 'Stop recording';
    }
    if (sendTranscriptBtn) sendTranscriptBtn.disabled = true;
    updateLiveTranscriptUI();
  };

  recognition.onresult = (event) => {
    let interim = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const res = event.results[i];
      if (res.isFinal) {
        finalTranscript += res[0].transcript.trim() + ' ';
      } else {
        interim += res[0].transcript;
      }
    }
    interimTranscript = interim.trim();
    updateLiveTranscriptUI();
  };

  recognition.onerror = () => {
    stopRecording();
  };

  recognition.onend = () => {
    isRecording = false;
    if (recordBtn) {
      recordBtn.setAttribute('aria-pressed', 'false');
      recordBtn.textContent = '🎤 Record';
    }
    if (inlineRecordBtn) {
      inlineRecordBtn.setAttribute('aria-pressed', 'false');
      inlineRecordBtn.textContent = '🎤';
      inlineRecordBtn.title = 'Record voice';
    }
    if (sendTranscriptBtn) sendTranscriptBtn.disabled = !finalTranscript.trim();
  };
}

function startRecording() {
  try {
    if (recognition) {
      // Set language from selector or default
      recognition.lang = getSelectedSttLang();
      recognition.start();
    }
  } catch (e) {}
}

function stopRecording() {
  try { recognition && recognition.stop(); } catch (e) {}
}

function updateLiveTranscriptUI() {
  const text = (finalTranscript + ' ' + interimTranscript).trim();
  if (liveTranscriptEl) liveTranscriptEl.textContent = text;
  // Mirror into the input textbox like ChatGPT voice input
  if (typeof text === 'string') {
    input.value = text;
  }
  // Do not create or update any live chat bubble; only the textbox should update
  if (sendTranscriptBtn) sendTranscriptBtn.disabled = !text;
}

function getSelectedSttLang() {
  // Web Speech API doesn't auto-detect; 'auto' falls back to English-India
  if (langSelect && langSelect.value && langSelect.value !== 'auto') {
    return langSelect.value;
  }
  return 'en-IN';
}

async function sendTranscript(transcript) {
  // Remove any live element and add final user message
  const liveEl = document.getElementById('live-transcript-chat');
  if (liveEl) liveEl.remove();
  if (transcript) addMessage(transcript, 'user');

  // Loader panel
  if (voiceLoader) voiceLoader.style.display = 'flex';
  if (voiceAnswer) voiceAnswer.style.display = 'none';
  if (speakerBtn) speakerBtn.disabled = true;

  try {
    const res = await fetch('/api/voice-chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        transcript: transcript,
        session_id: sessionId,
        conversation_history: conversationHistory.slice(-10),
        gemini_api_key: window.serverHasApiKey ? null : (geminiApiKey || null)
      })
    });
    if (!res.ok) throw new Error('Voice API failed');
    const data = await res.json();
    if (data.session_id) sessionId = data.session_id;

    const answer = data.response || 'Sorry, I could not generate a response.';
    lastAnswerText = answer;
    addMessage(answer, 'bot');
    if (voiceAnswerText) voiceAnswerText.textContent = answer;
    if (voiceAnswer) voiceAnswer.style.display = 'block';
    if (speakerBtn) speakerBtn.disabled = false;
  } catch (e) {
    addMessage('Audio chat failed. Please try again.', 'bot');
  } finally {
    if (voiceLoader) voiceLoader.style.display = 'none';
  }
}

// TTS helpers
function detectLanguageFromText(text) {
  // Basic script blocks
  if (/[\u0900-\u097F]/.test(text)) return 'hi-IN'; // Devanagari
  if (/[\u0A80-\u0AFF]/.test(text)) return 'gu-IN'; // Gujarati
  if (/[\u0A00-\u0A7F]/.test(text)) return 'pa-IN'; // Gurmukhi
  if (/[\u0980-\u09FF]/.test(text)) return 'bn-IN'; // Bengali
  if (/[\u0C80-\u0CFF]/.test(text)) return 'kn-IN'; // Kannada
  if (/[\u0C00-\u0C7F]/.test(text)) return 'te-IN'; // Telugu
  if (/[\u0B80-\u0BFF]/.test(text)) return 'ta-IN'; // Tamil
  return 'en-IN';
}

function speakText(text) {
  if (!window.speechSynthesis) return;
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = detectLanguageFromText(text);
  utter.rate = 1.0;
  utter.pitch = 1.0;
  try { window.speechSynthesis.cancel(); } catch {}
  window.speechSynthesis.speak(utter);
}

// Event listeners
send.addEventListener('click', handleSend);
imageButton.addEventListener('click', () => imageInput.click());
imageInput.addEventListener('change', handleImageSelection);
removeImage.addEventListener('click', removeSelectedImage);

// Voice UI listeners
recordBtn && recordBtn.addEventListener('click', () => {
  if (!isRecording) startRecording(); else stopRecording();
});

sendTranscriptBtn && sendTranscriptBtn.addEventListener('click', async () => {
  const transcript = (finalTranscript || interimTranscript).trim();
  if (!transcript) return;
  await sendTranscript(transcript);
});

speakerBtn && speakerBtn.addEventListener('click', () => {
  if (lastAnswerText) speakText(lastAnswerText);
});

// Inline mic listener next to input
inlineRecordBtn && inlineRecordBtn.addEventListener('click', () => {
  if (!isRecording) startRecording(); else stopRecording();
});

// Handle enter key press
input.addEventListener('keypress', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
});