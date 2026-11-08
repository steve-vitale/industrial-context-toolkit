# Event-driven transport: two normal cases and eleven intended refusals

Method `4ba46e1` was frozen before execution. Both exposed normal cases complete
controller/native/container exit 0: air/water has 373 helper calls, template 365.
Each retains 14 exact request/reply pairs, the supplied native fields, three
absolute camera frames and a final acknowledged seal before normal UI close.
These runs open and close the source without editing or saving it.

All11 predeclared fault cases retain controller/host/container exit1 and native
exit 0. They are successful evidence of refusal, never clean normal CAD runs.
Nine retain a helper/native error. Missing-reply uses an intentionally paused
actual Qt child; no AT-SPI request is made while paused, and separate cleanup
publishes a stop marker before resuming the same child. Native-exit closes the UI
normally before the refused request. Other failed attempts separately stop/drain
and close their original native process without restarting it.

| Retained packet | Required finding |
|---|---|
| normal-air, normal-template | Complete native fields/frames and exact bound replies; normal seal |
| fault-malformed | Malformed JSON refused |
| fault-wrong-sequence | Filename/envelope sequence refused |
| fault-wrong-run | Foreign run identity refused |
| fault-unsupported | Unavailable mutation action refused |
| fault-read-open | Actual Python I/O owner errno 13/read-open retained |
| fault-reply-collision | Original collision bytes remain; no replacement |
| fault-reply-write | Actual errno 13/write-open retained |
| fault-error-write | Primary error and errno 13 error-publication failure on native console |
| fault-missing-reply | Client timeout retains same process; controlled unavailable snapshot |
| fault-changed-request | Changed published bytes refused |
| fault-native-exit | Actual native exit refused; no restart |

The 13 lossless packets retain 3715 files, 35,280,068 raw bytes, 1,330,860 compressed
bytes and 1123 complete helper invocations. [Packing records](../BRIDGE-PACKING-2.json)
and [complete results](../BRIDGE-RESULTS-2.json) give per-case counts. Every packet
retains actual sources/configuration/method freeze, console, private mailbox,
actions, terminal receipts, original host execution and receiving commands/results.
Empty protocol directories are reconstructed by the offline replay.

```sh
python -S examples/cad-handoff/qualification/observer-transport-21/recheck_bridge.py
python -S examples/cad-handoff/qualification/observer-transport-21/test_bridge_receiving.py -v
```

Seven regression methods include every original packet, removed/extra/changed
replies, missing errors, self-repinned sources/methods, lost seal, unbound native
observations and promoted failed exits. They recompute inner inventories and
bypass outer hashes to challenge the semantic checks. All pass locally without
skips. These are exposed software controls, not an independent observer or plant
test. Earlier failures remain alongside the successor; no native full-save loss
or original strict/byte criterion is waived. Full CAD qualification stays open.
