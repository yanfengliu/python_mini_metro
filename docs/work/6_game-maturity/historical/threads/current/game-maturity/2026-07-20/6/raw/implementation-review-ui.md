# GM-06b controls/Pixel implementation review

Initial verdict: two substantive medium findings.

- Queued Metros were forced to brake and stop at synthetic padding endpoints because the facade returned true for every current segment. A three-station reproducer stopped with `current_station=None`, zero speed, and `just_arrived_and_stopped=True` before the next real station.
- Default fleet-control circles overlapped and painted over both lines of the existing locked-slot Buy/price affordance.

Disposition: both findings were accepted and fixed test-first. The queue override now forces a stop only when the current segment endpoint resolves to a real station, with a three-station padding regression. The config-owned purchase-text bottom gap now clears both control bounds, with a deterministic geometry regression.

Final verdict: `CLEAN`.

Independent probes reproduced the corrected outcomes: the queued Metro crosses nonzero padding without an artificial stop and then targets the next real segment endpoint; both purchase-text rectangles have zero intersection with both controls. Gesture precedence, rebinding, marker/render purity, fast/fidelity pixels, privileged demonstrator isolation, and legacy rendering migrations remained coherent. The reviewer passed 153 focused and adjacent tests without editing files.
