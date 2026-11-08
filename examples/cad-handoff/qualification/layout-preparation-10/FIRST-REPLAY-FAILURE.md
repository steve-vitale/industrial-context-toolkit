# First offline replay failure

The first `check_layout10.py` execution exited 1 at the complete comparison-object
equality check for the public-adapted `text_in_viewports` exact no-op. Its retained
`save_metadata_changed` was false; one later observation was true. All strict
fields matched and both inputs were pinned byte-identical. No source/native record
was changed or repackaged to hide this failure.

A 15-pair repeated inspection of the same bytes reproduced one differing loaded
`$TDCREATE`: 2461352.787916667 versus 2461352.787928241. The existing frozen recheck
already documents ezdxf's on-read replacement of zero creation dates with the
current time (`../recheck.py`). This affects the informational metadata boolean;
the frozen comparator already excludes the named save fields from strict equality.

Retain this failing checker in Git before correcting its receiving replay. The
correction must reproduce every other comparison field, including every strict
difference, and explicitly retain/report the saved and newly observed boolean.
Independent byte reconstruction and exact original/prepared no-op equality remain
mandatory. This is no new strict exclusion, waiver or source-passing result.
