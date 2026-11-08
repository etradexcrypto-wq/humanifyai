const source = document.querySelector('#source');
const region = document.querySelector('#region');
const tone = document.querySelector('#tone');
const output = document.querySelector('#output');
const notice = document.querySelector('#notice');
const badge = document.querySelector('#engineBadge');
const resultRegion = document.querySelector('#resultRegion');
const rewriteButton = document.querySelector('#rewriteButton');
const copyButton = document.querySelector('#copyButton');
const sourceCount = document.querySelector('#sourceCount');
const optionTabs = document.querySelector('#optionTabs');
const detectorScore = document.querySelector('#detectorScore');
const detectorBand = document.querySelector('#detectorBand');
const detectorDetail = document.querySelector('#detectorDetail');
const detectorMarker = document.querySelector('#detectorMarker');
const detectorScale = document.querySelector('#detectorScale');
let rewriteOptions = [];
let activeOption = 0;
let detectorTimer;
let detectorRequest = 0;

source.addEventListener('input', () => {
  detectorRequest += 1;
  sourceCount.textContent = `${source.value.length.toLocaleString()} / 5,000`;
  clearTimeout(detectorTimer);
  detectorTimer = setTimeout(analyzeText, 450);
});

document.querySelector('#clearButton').addEventListener('click', () => {
  source.value = '';
  source.dispatchEvent(new Event('input'));
  source.focus();
  resetDetector();
});

function resetDetector() {
  detectorRequest += 1;
  detectorScore.textContent = '—';
  detectorBand.textContent = 'Waiting for text';
  detectorBand.className = 'detector-band';
  detectorDetail.textContent = 'Enter at least 25 words for a rough estimate. This checker does not prove who wrote the text.';
  detectorMarker.hidden = true;
  detectorScale.setAttribute('aria-valuenow', '0');
  detectorScale.setAttribute('aria-valuetext', 'Waiting for text');
}

async function analyzeText() {
  const text = source.value.trim();
  const wordCount = (text.match(/[\w’'-]+/g) || []).length;
  if (wordCount < 25) {
    resetDetector();
    detectorDetail.textContent = `${wordCount} word${wordCount === 1 ? '' : 's'} so far. Enter at least 25 words for a rough estimate.`;
    return;
  }
  const requestId = ++detectorRequest;
  detectorBand.textContent = 'Checking…';
  detectorDetail.textContent = 'Comparing a few writing-style patterns…';
  try {
    const response = await fetch('/api/detect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Estimate unavailable.');
    if (requestId !== detectorRequest) return;
    if (data.score === null) {
      resetDetector();
      detectorDetail.textContent = data.detail;
      return;
    }
    detectorScore.textContent = `${data.score}%`;
    detectorBand.textContent = data.label;
    detectorBand.className = `detector-band ${data.band}`;
    detectorDetail.textContent = `${data.detail} Analysed ${data.word_count} words.`;
    detectorMarker.hidden = false;
    detectorMarker.style.left = `${data.score}%`;
    detectorScale.setAttribute('aria-valuenow', String(data.score));
    detectorScale.setAttribute('aria-valuetext', `${data.score} percent: ${data.label}`);
  } catch (error) {
    if (requestId !== detectorRequest) return;
    detectorBand.textContent = 'Unavailable';
    detectorDetail.textContent = error.message;
  }
}

function selectOption(index) {
  if (!rewriteOptions[index]) return;
  activeOption = index;
  output.textContent = rewriteOptions[index].text;
  output.classList.remove('muted');
  document.querySelectorAll('.option-tab').forEach((tab) => {
    const selected = Number(tab.dataset.index) === index;
    tab.classList.toggle('active', selected);
    tab.setAttribute('aria-selected', String(selected));
  });
  copyButton.disabled = false;
}

document.querySelectorAll('.option-tab').forEach((tab) => {
  tab.addEventListener('click', () => selectOption(Number(tab.dataset.index)));
});

rewriteButton.addEventListener('click', async () => {
  const text = source.value.trim();
  if (!text) {
    notice.textContent = 'Add some text first, and I’ll help you rewrite it.';
    source.focus();
    return;
  }
  rewriteButton.disabled = true;
  rewriteButton.innerHTML = '<span class="spinner"></span><span>Building options…</span>';
  notice.textContent = 'Checking the regional dictionary and preparing three versions…';
  badge.textContent = 'WORKING';
  copyButton.disabled = true;
  output.classList.add('muted');
  optionTabs.hidden = true;
  try {
    const response = await fetch('/api/rewrite', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, region: region.value, tone: tone.value }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'The rewrite could not be completed.');
    rewriteOptions = data.options || [{ label: 'Natural', text: data.rewritten_text }];
    document.querySelectorAll('.option-tab').forEach((tab, index) => {
      tab.textContent = rewriteOptions[index]?.label || `Option ${index + 1}`;
    });
    optionTabs.hidden = false;
    badge.textContent = data.engine.toUpperCase();
    resultRegion.textContent = `For ${data.region_name} · choose a version`;
    notice.textContent = data.notice || 'Choose the version that best preserves your intended meaning.';
    selectOption(0);
    analyzeText();
  } catch (error) {
    output.textContent = 'We couldn’t complete those rewrites. Please try again.';
    notice.textContent = error.message;
    badge.textContent = 'ERROR';
    output.classList.add('muted');
  } finally {
    rewriteButton.disabled = false;
    rewriteButton.innerHTML = '<span>Show 3 rewrite options</span><span aria-hidden="true">↗</span>';
  }
});

copyButton.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(output.textContent);
    copyButton.textContent = 'Copied';
    setTimeout(() => { copyButton.textContent = 'Copy selected'; }, 1400);
  } catch {
    notice.textContent = 'Copy is unavailable in this browser. Select the rewritten text to copy it.';
  }
});
