# First receiver failure, before pixel comparison

The first receiver refused the original air/water job because it hashed a new
LF JSON serialization of the source basis against the original CRLF file digest.
The parsed basis agrees exactly; its original bytes agree with the already
published cohort inventory. The failed command/output and receiver are retained.
No native input, image, source digest, tolerance or result was changed.

The repair retains each original basis file byte for byte, checks its digest
against the original inventory, then compares its parsed values to the actual
receiving job (only the explicit role is added). This avoids deriving evidence
identity from a platform-specific new serialization. The revised receiver is
frozen before its first pixel comparison; altered basis values still refuse.
