// Pure process logic for the interactive tour. The page inlines this file (build.mjs strips the `export`
// keywords) and drafts/interactive-tour/verify.mjs imports it, so the readouts the page shows and the checks the
// verifier makes come from the same functions. No DOM, no randomness, no clock.
//
// Proof of concept: written with AI assistance from the repository's data files; not reviewed by an operator.

// One replay value -> display state. Same rule as scripts/build_3d_scene.py classify(): only published setpoints
// make an alarm; normal bands are display aids, not limits; a missing or non-finite value is never "normal".
export function classify(value, band, setpoints) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "unknown";
  if ((setpoints || []).some((s) => value > s)) return "alarm";
  if (band && !(band.lo <= value && value <= band.hi)) return "outside_band";
  return "normal";
}

export function setpointsOf(tag) {
  return ((tag.alarms && tag.alarms.all) || []).map((a) => a.setpointA);
}

// Every connected tag's state at one replay sample.
export function statesAt(data, run, sample) {
  const values = data.replay.runs[run].values;
  const out = {};
  for (const tag of data.tags) {
    if (!tag.connected || !values[tag.tag]) { out[tag.tag] = { state: "not_connected", value: null }; continue; }
    const value = values[tag.tag][sample];
    out[tag.tag] = { state: classify(value, tag.band, setpointsOf(tag)), value };
  }
  return out;
}

// Tags above a published high alarm at one sample (what the alarm list shows).
export function alarmsAt(data, run, sample) {
  const states = statesAt(data, run, sample);
  return data.tags.filter((t) => states[t.tag].state === "alarm").map((t) => ({ tag: t.tag, value: states[t.tag].value }));
}

export function firstAlarm(data, run) {
  const n = data.replay.runs[run].samples;
  for (let k = 0; k < n; k++) {
    const hits = alarmsAt(data, run, k);
    if (hits.length) return { sample: k, tags: hits.map((h) => h.tag) };
  }
  return null;
}

// Pulse speed per stream: the recorded flow over its normal-band mean, where the stream has a flow tag; streams
// without one move at a constant, labelled "illustrative" rate. Clamped to 0..2.5 so a spike stays readable.
export function flowShare(data, run, sample, stream) {
  if (!stream.flow_tag) return { share: 1, basis: "illustrative (no flow tag on this stream)" };
  const tag = data.tags.find((t) => t.tag === stream.flow_tag);
  const series = data.replay.runs[run].values[stream.flow_tag];
  const value = series ? series[sample] : null;
  if (!tag || !tag.band || !tag.band.mean || typeof value !== "number" || !Number.isFinite(value)) {
    return { share: 1, basis: "illustrative (no usable replay value)" };
  }
  return { share: Math.max(0, Math.min(2.5, value / tag.band.mean)), basis: `${stream.flow_tag} / normal-band mean`, value, tag: stream.flow_tag };
}

// Minutes after the fault start for a sample (negative before it).
export function minutesAfterFault(data, sample) {
  return (sample - data.replay.fault_start_sample) * data.replay.minutes_per_sample;
}

export function fmt(v) {
  if (typeof v !== "number" || !Number.isFinite(v)) return "n/a";
  const a = Math.abs(v);
  if (a >= 1000) return Math.round(v).toLocaleString("en-US");
  if (a >= 100) return v.toFixed(1);
  if (a >= 10) return v.toFixed(2);
  if (a >= 1) return v.toFixed(3);
  return v.toPrecision(3);
}
