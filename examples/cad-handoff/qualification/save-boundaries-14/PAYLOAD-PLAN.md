# Test registered application names, used XDATA and an opaque dictionary record

Declared after attempt-1 finished all 22 exports and 22 fresh public-inventory reads, before generating or
executing the new payload controls. The explicit R15/R21/R24 requests preserved actual source ACADVER;
default requests used AC1024. All source/full-save strict failures remain. Initial native inventories already
contain many linetype names absent from the source. Public inventories have no custom properties on these
base sources, so they cannot establish how a used application payload would behave.

Create two new authored fixtures per exposed source, with the original source retained. Both register
ICT_BOUND14_USED and ICT_BOUND14_UNUSED, add a named root-dictionary XRECORD with fixed string/integer/real
sentinels, and set USERI5 to a case-specific integer. The second fixture differs by attaching ordered XDATA
(string, real, integer) under ICT_BOUND14_USED to the existing profiled asset INSERT. The first leaves both
applications unused. These are authored diagnostic revisions, not untouched upstream or fresh validation.
Freeze generator, exact generated inputs, candidates, plans and expected sentinels before native execution.

Export all twelve no-edit fixtures at their explicit source version, close/reopen, and read in a fresh native
process. Extend the public inventory to retain observed attribute values and USERI5 as well as every custom
property title/key/value. Retain any unsupported native value representation explicitly, rather than treating
it as an exact scalar. Compare the literal saved APPID registrations, full ordered XDATA and complete foreign
XRECORD against each source, alongside unchanged strict and independent raw candidate checks.

Expected diagnostic distinctions, not assumed outcomes: use of XDATA may determine whether its registered
application is imported/exported; an arbitrary dictionary object may be preserved, lost or changed. Absence
from public RObjects does not prove absence from opaque importer state. Actual omission from returned DXF
establishes a round-trip loss, but its exact internal stage stays unknown unless directly observed. Never
waive such a loss or infer that unused registrations are disposable. Keep all twelve outcomes and any errors.

Planted receiving controls must detect a changed sentinel, missing application/XDATA/object, changed USERI5
or native attribute, missing jobs and false zero-difference reports. These controls diagnose preservation;
they do not make full native saves safe or replace the outstanding native UI/readability/revision gates.
