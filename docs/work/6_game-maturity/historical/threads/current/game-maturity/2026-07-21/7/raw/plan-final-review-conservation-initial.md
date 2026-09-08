NOT CLEAN

PLAN.md:25 calls its snapshot the “exact late-validator footprint,” but PLAN.md:24 validates `host.is_game_over` and the snapshot does not include that flag. A factory/list callback can set terminal state, trigger postcondition failure, and leave it changed after rollback. Add the exact terminal flag to snapshot/restoration. Also scope PLAN.md:79’s “all rejected or failed transitions” to carriage attach/detach, because PLAN.md:29 explicitly permits malformed late line-removal failure pending GM-06d.
