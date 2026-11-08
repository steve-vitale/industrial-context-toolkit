# Isolate the operation's current-attributes default

Declared after attempt-1 terminated normally and before attempt-2. Attempt-1 and its freeze remain intact.
All six source -> no-operation comparisons have the same strict counts as source -> edited comparisons.
But their matched returns differ at the edited ATTRIB layer: the source's ICT_QUAL_TEST_ONLY becomes the
imported drawing's current layer (0, main or another source-selected name). R15 also has a separate
DWGPROPS COOKIE XRECORD difference in groups 41/42. Second saves are not a fixed point.

Primary public QCAD source at 897079c2d11aaa0869f839a6cf5df8a937dbddbe:
RModifyObjectsOperation inherits RAddObjectsOperation; addObject defaults useCurrentAttributes=true;
apply passes that setting to the transaction. The first probe copied the historical native-batch.js call.

Attempt-2 changes only that call to addObject(a,false), plus observes layer IDs with the existing native
attribute properties. Repeat the same 48 matched exports / fresh-process reads on the same sources, image
and initial settings. Expected intervention: the attribute-only difference between no-operation and edited
returns disappears. Do not predict that whole saves or R15 timestamps pass. Every residual is retained.
The new probe is a separately named successor; the original native-batch.js and attempt-1 probe are unchanged.
