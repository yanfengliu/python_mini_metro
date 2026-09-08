# GM-06b conservation plan review - first pass

Status: `NOT CLEAN`

1. `HIGH` - The legacy post-create replay adapter is positioned too late to preserve one historical operation. `MiniMetroEnv.step` applies the action and then advances time, while the draft only promises a post-create call. An adapter after `step` introduces one unserved tick. Select a pre-tick boundary and pin action-result/failure semantics.

2. `HIGH` - The no-boarding promise does not cover both live seams. `move_passengers` receives candidates directly and can board without consulting `can_board_at_station`. Require queued metros to receive no boarding candidates in mutating and nonmutating modes and test that eligible waiting riders remain at the station without dwell.

3. `MEDIUM` - Same-tick settlement relative to game-over evaluation is unspecified. Current passenger flow moves passengers before updating game over. Select whether an empty train that reaches a station on a terminal-producing tick detaches.

4. `MEDIUM` - Immediate station detachment is ambiguous for a freshly assigned metro. `Path.add_metro` initializes position at a segment endpoint while `current_station` remains `None`. Define real-station presence by identity rather than coordinate and test immediate plus-then-minus behavior.

5. `MEDIUM` - Acceptance requires `available + assigned == total`, which contradicts the selected clamped over-cap compatibility rule. Scope equality to within-cap states and require the clamped formula universally.

Evidence inspected: `src/env.py:63-84`, `src/recursive_playtest.py:306-329`, `src/agent_play.py:300-322`, the passenger movement/boarding call chain, `src/path.py` metro initialization, and the candidate iteration-6 plan.
