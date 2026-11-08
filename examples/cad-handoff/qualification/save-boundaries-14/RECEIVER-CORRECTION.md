# Preserve raw header values in the empty-document diagnostic

The first offline receive correctly refused a changing report. Only four
empty-control `$TDCREATE` values changed; file hashes, strict reports, resource
diagnostics and other results were equal. `ezdxf` substitutes current time
when a loaded header creation time is zero. The first `analysis/diagnosis.json`
and `diagnosis-recheck.json` retain those differing synthetic times.

The successor helper retains the literal complete HEADER section as raw hex,
including original line endings. It neither changes nor masks any source
byte. Regenerate separately as `analysis-raw-header`, keeping the first
diagnostic and its reports. The existing strict comparator is untouched;
its established save-metadata policy is unchanged. No native execution is
repeated or qualified through this receiving correction.
