/**
 * Project Ouroboros Web Visualizer Logic
 * Author: Brayan Osinaka
 */

// Core Constants
const CACHE_LINE_SIZE = 64;

// Shannon Entropy Estimator
function calculateEntropy(bytes) {
  if (!bytes || bytes.length === 0) return 0;
  const counts = new Array(256).fill(0);
  for (let i = 0; i < bytes.length; i++) {
    counts[bytes[i]]++;
  }
  let entropy = 0;
  for (let i = 0; i < 256; i++) {
    if (counts[i] > 0) {
      const p = counts[i] / bytes.length;
      entropy -= p * Math.log2(p);
    }
  }
  return entropy;
}

// BDI Compression Engine JS Implementation
function compressBDI(bytes) {
  // Ensure exactly 64 bytes
  const line = new Uint8Array(64);
  line.set(bytes.slice(0, 64));

  // 1. Check Zero Pattern (Zer)
  let isZero = true;
  for (let i = 0; i < 64; i++) {
    if (line[i] !== 0) { isZero = false; break; }
  }
  if (isZero) {
    return { pattern: 'Zer', compressedSize: 1, ratio: 64.0, embedded: true, payload: line.slice(0, 1) };
  }

  // 2. Check Repeated Pattern (Rep - 8B words)
  const view = new DataView(line.buffer);
  const base0_int64 = view.getBigInt64(0, true);
  let isRep = true;
  for (let i = 8; i < 64; i += 8) {
    if (view.getBigInt64(i, true) !== base0_int64) { isRep = false; break; }
  }
  if (isRep) {
    return { pattern: 'Rep', compressedSize: 8, ratio: 8.0, embedded: true, payload: line.slice(0, 8) };
  }

  // Helper to check B8D1, B8D2, B8D4
  const tryBaseDelta8 = (deltaMax) => {
    const base = view.getBigInt64(0, true);
    const deltas = [];
    for (let i = 0; i < 64; i += 8) {
      const val = view.getBigInt64(i, true);
      const diff = val - base;
      if (diff < -deltaMax || diff > deltaMax - 1n) return null;
      deltas.push(diff);
    }
    return deltas;
  };

  // B8D1 (8-bit deltas)
  const deltasB8D1 = tryBaseDelta8(128n);
  if (deltasB8D1) {
    const sz = 8 + 8; // 8B base + 8*1B deltas = 16B
    return { pattern: 'B8D1', compressedSize: sz, ratio: 64 / sz, embedded: true, payload: line.slice(0, sz) };
  }

  // B8D2 (16-bit deltas)
  const deltasB8D2 = tryBaseDelta8(32768n);
  if (deltasB8D2) {
    const sz = 8 + 16; // 8B base + 8*2B deltas = 24B
    return { pattern: 'B8D2', compressedSize: sz, ratio: 64 / sz, embedded: false, payload: line.slice(0, sz) };
  }

  // Helper to check B4D1, B4D2
  const tryBaseDelta4 = (deltaMax) => {
    const base = view.getInt32(0, true);
    for (let i = 0; i < 64; i += 4) {
      const val = view.getInt32(i, true);
      const diff = val - base;
      if (diff < -deltaMax || diff > deltaMax - 1) return null;
    }
    return true;
  };

  // B4D1 (4B base, 1B deltas)
  if (tryBaseDelta4(128)) {
    const sz = 4 + 16; // 20B
    return { pattern: 'B4D1', compressedSize: sz, ratio: 64 / sz, embedded: false, payload: line.slice(0, sz) };
  }

  // B4D2 (4B base, 2B deltas)
  if (tryBaseDelta4(32768)) {
    const sz = 4 + 32; // 36B
    return { pattern: 'B4D2', compressedSize: sz, ratio: 64 / sz, embedded: false, payload: line.slice(0, sz) };
  }

  // Uncompressed Fallback
  return { pattern: 'Uncompressed', compressedSize: 64, ratio: 1.0, embedded: false, payload: line };
}

// Preset Trace Generators
const PRESETS = {
  pointers: () => {
    const buf = new ArrayBuffer(64);
    const view = new DataView(buf);
    const basePtr = 0x00007FFF00100000n;
    for (let i = 0; i < 8; i++) {
      view.setBigInt64(i * 8, basePtr + BigInt(i * 4), true);
    }
    return new Uint8Array(buf);
  },
  gaming: () => {
    const buf = new ArrayBuffer(64);
    const view = new DataView(buf);
    const baseCoord = 100;
    for (let i = 0; i < 16; i++) {
      view.setInt32(i * 4, baseCoord + (i % 3), true);
    }
    return new Uint8Array(buf);
  },
  llm: () => {
    const buf = new ArrayBuffer(64);
    const view = new DataView(buf);
    for (let i = 0; i < 32; i++) {
      view.setInt16(i * 2, (i % 4) * 2, true);
    }
    return new Uint8Array(buf);
  },
  encrypted: () => {
    const arr = new Uint8Array(64);
    window.crypto.getRandomValues(arr);
    return arr;
  }
};

// UI Elements & State
let currentLine = PRESETS.pointers();

function updateUI() {
  const entropy = calculateEntropy(currentLine);
  const isBypassed = entropy >= 5.4;
  const result = isBypassed 
    ? { pattern: 'Bypassed (High Entropy)', compressedSize: 64, ratio: 1.0, embedded: false, payload: currentLine }
    : compressBDI(currentLine);

  // Update Metric Boxes
  document.getElementById('val-ratio').innerText = `${result.ratio.toFixed(2)}x`;
  document.getElementById('val-size').innerText = `${result.compressedSize} Bytes`;
  document.getElementById('val-entropy').innerText = `${entropy.toFixed(2)} bits`;

  // Status Pill
  const pill = document.getElementById('status-pill');
  if (isBypassed) {
    pill.className = 'status-pill bypassed';
    pill.innerText = '⚠️ High Entropy Bypassed (0% Size Expansion)';
  } else if (result.embedded) {
    pill.className = 'status-pill embedded';
    pill.innerText = `✨ Direct Payload Embedded in HIT Entry (0 DRAM Sectors Allocated!) Pattern: ${result.pattern}`;
  } else if (result.ratio > 1.0) {
    pill.className = 'status-pill compressed';
    pill.innerText = `⚡ Compressed via BDI (${result.pattern}) -> ${result.compressedSize}B (${Math.ceil(result.compressedSize / 16)} DRAM Sectors)`;
  } else {
    pill.className = 'status-pill bypassed';
    pill.innerText = `Uncompressed Raw Line (64 Bytes)`;
  }

  // Render Hex Grid
  const hexGrid = document.getElementById('hex-grid');
  hexGrid.innerHTML = '';
  for (let i = 0; i < 64; i++) {
    const cell = document.createElement('div');
    const byteVal = currentLine[i];
    cell.className = 'hex-cell' + (i < result.compressedSize && result.ratio > 1.0 ? ' compressed' : '');
    cell.innerText = byteVal.toString(16).padStart(2, '0').toUpperCase();
    hexGrid.appendChild(cell);
  }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
  // Preset buttons
  document.getElementById('btn-preset-pointers').addEventListener('click', () => {
    currentLine = PRESETS.pointers();
    updateUI();
  });
  document.getElementById('btn-preset-gaming').addEventListener('click', () => {
    currentLine = PRESETS.gaming();
    updateUI();
  });
  document.getElementById('btn-preset-llm').addEventListener('click', () => {
    currentLine = PRESETS.llm();
    updateUI();
  });
  document.getElementById('btn-preset-encrypted').addEventListener('click', () => {
    currentLine = PRESETS.encrypted();
    updateUI();
  });

  // Custom text input
  const textInput = document.getElementById('custom-input');
  textInput.addEventListener('input', (e) => {
    const enc = new TextEncoder();
    const bytes = enc.encode(e.target.value);
    const padded = new Uint8Array(64);
    padded.set(bytes.slice(0, 64));
    currentLine = padded;
    updateUI();
  });

  // Initial render
  updateUI();
});
