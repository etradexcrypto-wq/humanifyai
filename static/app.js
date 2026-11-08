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

source.addEventListener('input', () => {
  sourceCount.textContent = `${source.value.length.toLocaleString()} / 5,000`;
});

document.querySelector('#clearButton').addEventListener('click', () => {
  source.value = '';
  source.dispatchEvent(new Event('input'));
  source.focus();
});

rewriteButton.addEventListener('click', async () => {
  const text = source.value.trim();
  if (!text) {
    notice.textContent = 'Add some text first, and I’ll help you rewrite it.';
    source.focus();
    return;
  }
  rewriteButton.disabled = true;
  rewriteButton.innerHTML = '<span class="spinner"></span><span>Rewriting…</span>';
  notice.textContent = 'Finding the right words…';
  badge.textContent = 'WORKING';
  copyButton.disabled = true;
  output.classList.add('muted');
  try {
    const response = await fetch('/api/rewrite', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, region: region.value, tone: tone.value }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'The rewrite could not be completed.');
    output.textContent = data.rewritten_text;
    output.classList.remove('muted');
    badge.textContent = data.engine.toUpperCase();
    resultRegion.textContent = `For ${data.region_name}`;
    notice.textContent = data.notice || 'Done. Your meaning and chosen regional voice are preserved.';
    copyButton.disabled = false;
  } catch (error) {
    output.textContent = 'We couldn’t complete that rewrite. Please try again.';
    notice.textContent = error.message;
    badge.textContent = 'ERROR';
    output.classList.add('muted');
  } finally {
    rewriteButton.disabled = false;
    rewriteButton.innerHTML = '<span>Rewrite my text</span><span aria-hidden="true">↗</span>';
  }
});

copyButton.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(output.textContent);
    copyButton.textContent = 'Copied';
    setTimeout(() => { copyButton.textContent = 'Copy text'; }, 1400);
  } catch {
    notice.textContent = 'Copy is unavailable in this browser. Select the rewritten text to copy it.';
  }
});
