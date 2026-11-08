# Copied settings are not selected settings

The phase-10 settings-path failure prompted a read-only audit of the earlier font
experiment. Both accepted font-9 batches retain `absConfigFile: "/work/qcad-config"`
in `raw/default-replay-2/native.stderr` and `raw/substitute/native.stderr` of the
[unchanged font archive](../font-views-9/INVENTORY.json). Their SETUP records bind
the copied run-7 configuration hash, not the native-selected filename or the exact
contents selected there. That hash alone is therefore **not evidence that CAD
loaded those settings**. The old checker verifies the declared copy receipt; it
does not establish selected-file identity. Do not infer full configuration
reproduction or a controlled verified-settings comparison from that check.

Keep all earlier code, freezes, setup records, images and numerical observations
unchanged. Actual native font/Qt coverage probes, attribute values, measured
frames, stable images, inspected labels and pixel counts remain observations of
the actual recorded processes. This correction narrows configuration provenance;
it neither reruns those GUI observations nor promotes them to new qualification.
In particular the default 62-pixel discrepancy remains unresolved.

The same distinction applies to any earlier installed/copied settings receipt
without native-selected-file proof. The actual run-7 edit/save/reopen and run-8
within-process pointer controls retain their recorded outcomes; a copied settings
hash must not be used to infer their complete loaded configuration either.

Phase-10's fourth receiving batch uses a different, explicitly verified recipe:
the command selects the installed absolute file; native `RSettings.getFileName()`
reports it; every command's stderr confirms it; and before/after settings digests
form an uninterrupted chain without resets. This verifies that batch only. It
does not retroactively verify any earlier process or establish fresh validation,
typography fidelity, full-save equivalence or company acceptance.
