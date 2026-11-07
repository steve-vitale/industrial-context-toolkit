# Retain an interrupted default-profile replay

The first default process completed its original 18-view batch. The corrected
batch was still live when the agent incorrectly sent native Ctrl+Q: its last poll
returned session 26298, not a terminal result. Native app/container exited normally
at 2026-11-07T23:55:12.283468281Z; the separate capture process then returned exit 1.
Receipts and images through sequence 113 remain. The interrupted controller has no
completed actions.json. This is an orchestration failure, not a CAD acceptance result.

Do not restart the old container or overwrite its files. Before repeating, use a
fresh container and work directory with the same image, local configuration, inputs,
native observer and corrected capture method. The host must observe capture-process
terminal exit 0 in a separate tool result before sending native Quit. Only a complete
new serial batch may enter the matched profile comparison. Retain all earlier files.
