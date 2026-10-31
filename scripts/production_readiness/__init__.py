"""Production-readiness gate harness (PR-1).

Runs Helix Prime's six engines against the two external tenant fixtures
(`callcenterclient`, `sportacademyclient`) and emits a machine-readable
evidence pack. Every gate is fail-closed: an absent fixture, an unparsable
table, an engine error, an empty sample or a mislabelled data mode fails the
run rather than producing a green summary.

The harness is deliberately outside the governed core: it imports the engine
adapters, it does not modify them, and it writes only under the run directory.
"""
