# Include native line and fill calls

Declared before helper compilation or GUI execution. The pinned public RGraphicsViewImage implementation
can split a painter path into individual worker drawLine calls when screen-based linetypes/draft/printing
are off. Observing only drawPath would omit those strokes. Observe and forward QPainter::drawLines(QLineF*,
int) and fillPath as well. Retain the call type; do not substitute a joined path for separate line strokes.
This is a source-backed hypothesis about the earlier failed path-only replay, not a measured GUI cause yet.

Use a separately provisioned Ubuntu builder for Qt headers/compiler; link helper/replayer against the
frozen native package libraries and test loading in that package. Header/runtime ABI compatibility is a
control to verify, not assumed from an exit status. Keep the original native image unchanged.
