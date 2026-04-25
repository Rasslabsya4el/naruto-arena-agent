# TASK-E2E-ANSWER-SAMPLES-01 Answer Samples

These samples are representative final answers for the MVP request classes. They are grounded only in the accepted skill-local bundle at `skills/naruto-arena-team-builder/references` and helper/planner outputs from `scripts/search_characters.py`, `scripts/team_candidate_report.py`, and `scripts/optimize_mission_pool.py`.

The samples intentionally separate confirmed bundle facts from strategic inference and data gaps. They are not static best-team tables.

## Sample 1 - Build Around A Character

Prompt: `Build a practical ladder team around Uzumaki Naruto.`

### Recommendation

Use `Uzumaki Naruto / Uchiha Sasuke / Haruno Sakura`.

I am resolving this as base `Uzumaki Naruto`, not `Uzumaki Naruto (S)`. The local search finds both records for the text "Uzumaki Naruto", but base `Uzumaki Naruto` is the exact name match. This Team 7 shell is chosen because the team report shows a `Control-Pressure Shell`, `Pressure With Stabilizers`, and `Setup-Support Shell`. I would reject the `Uchiha Sasuke (S)` variant for this specific answer because the diagnosis evidence shows that version creates high shared `nin` chakra pressure with Naruto and Sakura.

### Team Identity

This is a practical control-pressure team with stabilizers. The win condition is to use Naruto and Sasuke as pressure pieces while Sakura keeps the shell from becoming a pure race. The pacing is midrange: the team has low-cost options, but it is still sensitive to shared `tai`, `nin`, and `random` chakra pressure.

### Why These Characters Fit

Confirmed from local data:

- `Uzumaki Naruto` has role hints for pressure, control, sustain, setup, and protection. His effect buckets include damage, increase_damage, stun, reduce_damage, heal, protect, conditional, and apply_state.
- `Uchiha Sasuke` contributes pressure, sustain, setup, and protection role hints.
- `Haruno Sakura` contributes pressure, control, sustain, setup, and protection role hints.
- The combined team has all three identity hints reported by the helper: control-pressure, pressure with stabilizers, and setup-support.

Strategic inference:

- Naruto is the build-around piece because he is the only member in this trio with all five non-resource role hints, including both pressure and control.
- Sasuke gives a second damage lane, while Sakura gives the team a more stable support/control profile than a third pure attacker.

### Game Plan

Use Naruto as the main pressure-control pivot, then commit Sasuke or Sakura into the window that looks least chakra-constrained. When `nin` is available, Naruto's `Rasengan` and Sasuke's higher-pressure turns compete for the same color, so do not assume both premium lines happen together. If chakra is awkward, keep the turn functional with low-cost or random-cost options and preserve the setup-support shell until a kill window opens.

### First Turns

Confirmed from local data:

- Naruto has low-cost `Sexy Technique`, `Shadow Clones`, and `Uzumaki Naruto Combo`.
- Team 7 has medium shared `tai`, `nin`, and `random` pressure.

Strategic inference:

- Early turns should identify the chakra draw first. If `nin` is scarce, avoid planning around simultaneous Naruto/Sasuke premium pressure. If random chakra is available, use the stabilizing/setup options to keep the team from losing tempo before the better color draw arrives.

### Good Matchups

Strategic inference from role and chakra surfaces:

- Teams that give setup time or rely on linear pressure can be punished because this team combines pressure, control, sustain, and protection hints.
- Teams that cannot quickly force bad chakra trades are more comfortable, because Team 7 can shift between pressure and stabilization.

### Bad Matchups / What Beats This

Confirmed from local data:

- The helper reports medium shared `tai`, `nin`, and `random` chakra pressure.
- All selected records carry accepted data-quality warnings, including target uncertainty.

Strategic inference:

- Opponents that punish slow setup or deny the right color turns can make the team feel clunky.
- Heavy disruption into Naruto is dangerous because he is the team identity piece and the only member with pressure, control, sustain, setup, and protection all together in the helper surface.

### Failure Modes

- `nin` or `tai` draw does not line up and the team has to spend low-impact turns.
- The team tries to run Naruto and Sasuke as simultaneous premium pressure instead of sequencing them.
- The user needs exact mission guarantees outside the listed mission evidence; this answer is mainly ladder-style unless the mission pool explicitly matches Team 7 requirements.
- Data-quality tags mean some exact targeting and effect semantics remain uncertain in the structured bundle.

### Mission Coverage

This trio has proven mission-pool value for `Survival`, `A Girl Grown Up`, and `Medical Training` in the accepted planner output:

- `Survival`: requires wins with `Uzumaki Naruto`, `Uchiha Sasuke`, and `Haruno Sakura` on the same team.
- `A Girl Grown Up`: requires wins and a streak with `Haruno Sakura`.
- `Medical Training`: requires wins with `Haruno Sakura`.

This does not mean Team 7 covers all missions. It means this exact team has local evidence for that specific pool.

### Substitutions

If the mission does not require Team 7 and the problem is shared `nin` pressure, replace `Uchiha Sasuke` with a no-`nin` control/resource candidate from the helper search. `Akadou Yoroi` is one example surfaced by `python scripts/search_characters.py --role-hint control --exclude-chakra-type nin --limit 5`; he has control, resource, sustain, setup, and protection hints with `random`/`tai` top chakra. That swap reduces `nin` pressure but gives up Team 7 mission coverage and changes the team into a slower denial shell.

### Confidence / Data Gaps

Confirmed mechanics are limited to the local bundle and helper outputs. Strategic claims about pacing, matchup comfort, and sequencing are inference from role hints, effect buckets, chakra pressure, and low-cost skill surfaces.

Data gaps:

- `Uzumaki Naruto`, `Uchiha Sasuke`, and `Haruno Sakura` all have `character.data.effect_target_unknown`.
- `Uzumaki Naruto` and `Uchiha Sasuke` also have `character.data.effect_type_heuristic`.
- The source for the character records resolves to `https://www.naruto-arena.site/characters-and-skills`.

## Sample 2 - Build For A Mission

Prompt: `Build a team for A Dishonored Shinobi.`

### Mission Resolution

Resolved exact mission: `A Dishonored Shinobi` (`mission:a-dishonored-shinobi`), B Rank Missions.

Source resolution:

- `https://www.naruto-arena.site/mission/a-dishonored-shinobi`
- `https://www.naruto-arena.site/missions/b-rank-missions`

### Requirement Summary

Confirmed mission requirements:

- `Win 8 battles with Uzumaki Naruto.`
- `Win 3 battles in a row with Umino Iruka.`

Confirmed planning facts:

- The planner found one exact coverage bucket with `Umino Iruka` and `Uzumaki Naruto`.
- That bucket has one flex slot.
- The mission has no unknown requirement ids and no soft-fit requirement ids in the planner output.

Data gap:

- The mission rank has a label (`Chuunin`) but the numeric rank value is not provided by the snapshot.

### Recommended Team

Use `Umino Iruka / Uzumaki Naruto / Haruno Sakura`.

`Umino Iruka` and `Uzumaki Naruto` are the required core. `Haruno Sakura` is the flex choice, not a mission requirement.

### Why This Covers The Mission

Confirmed from local data:

- The planner maps `Win 8 battles with Uzumaki Naruto` to `character:uzumaki-naruto`.
- The planner maps `Win 3 battles in a row with Umino Iruka` to `character:umino-iruka`.
- Both exact requirements fit within one three-character team.

Strategic inference:

- Sakura is a reasonable flex because the concrete `Uzumaki Naruto / Umino Iruka / Haruno Sakura` team report has pressure, control, protection, setup, and sustain across the trio. She is not required for mission completion and should be swapped if the user's roster or chakra comfort points elsewhere.

### Play Plan

Prioritize the `Umino Iruka` streak requirement when the matchup looks stable, because a lost game resets that progress. Keep Naruto active in the team while collecting his eight wins. Use Sakura as a stabilizer/flex member to reduce the chance that the Iruka streak attempt collapses before Naruto's pressure and Iruka's protection/pressure surfaces matter.

### Weaknesses / Failure Modes

Confirmed from the team report:

- The concrete Iruka/Naruto/Sakura team has medium shared `tai`, `nin`, and `random` pressure.
- It carries data-quality warnings for effect magnitude, target, and heuristic effect typing across the selected records.

Strategic inference:

- The team can fail the streak if it overcommits damage while the opponent is pressuring Iruka.
- If `nin` or random chakra is awkward, both the mission core and Sakura flex can lose tempo.

### Substitutions

The third slot is flexible. If Sakura makes the curve feel too crowded, use the helper substitution paths:

- Search for a flex that excludes `nin` if shared `nin` pressure is the problem.
- Search for a flex that excludes `random` if random-cost congestion is the problem.

Do not remove `Umino Iruka` or `Uzumaki Naruto` unless you are no longer answering this mission's exact known requirements.

### Confidence / Unknowns

Confidence is high for the two known mission requirements and the required two-member core. Confidence is lower for the best third slot because the mission planner intentionally leaves that slot open. Character mechanics still carry accepted data-quality warnings, so exact targeting and some effect semantics should not be overstated.

## Sample 3 - Optimize A Mission Pool

Prompt: `Optimize teams for Survival, A Girl Grown Up, and Medical Training.`

### Mission Pool Resolution

All three mission names resolved exactly:

- `Survival` (`mission:survival`), B Rank Missions.
- `A Girl Grown Up` (`mission:a-girl-grown-up`), Shippuuden Missions.
- `Medical Training` (`mission:medical-training`), B Rank Missions.

### Grouped Plan

Use one team group:

- `bucket:01`: `Uzumaki Naruto / Uchiha Sasuke / Haruno Sakura`
- Flex slots: `0`
- Assigned missions: `Survival`, `A Girl Grown Up`, `Medical Training`

### Coverage Explanation

Confirmed from local planner output:

- `Survival` requires `Win 5 battles with Uzumaki Naruto, Uchiha Sasuke and Haruno Sakura on the same team.`
- `A Girl Grown Up` requires `Win 3 battles in a row with Haruno Sakura` and `Win 10 battles with Haruno Sakura.`
- `Medical Training` requires `Win 10 battles with Haruno Sakura.`
- All four exact requirement units fit inside the same three-member Team 7 bucket.

Strategic inference:

- This is efficient because Survival already forces the full Team 7 shell, and the other two missions are Sakura-centered. You can collect Sakura progress while keeping the Survival-valid team intact.

### Conflict Explanation

No split is needed. The planner's split rationale says all exact mission requirements fit within one practical team bucket with three required characters and team size three.

The only caution is that `Survival` has a `multi_character_condition_not_structured` data-quality marker. The planner preserved the condition text and kept the three character refs together because the mission text says "on the same team"; it did not silently split them into alternatives.

### Coverage Matrix

| Mission | Required condition surface | Assigned group | Coverage status | Uncertainty |
| --- | --- | --- | --- | --- |
| Survival | Win 5 battles with Uzumaki Naruto, Uchiha Sasuke and Haruno Sakura on the same team. | bucket:01 - Naruto / Sasuke / Sakura | fully_covered_by_one_bucket | Multi-character condition preserved in text; refs are resolved and kept together. |
| A Girl Grown Up | Win 3 battles in a row with Haruno Sakura; Win 10 battles with Haruno Sakura. | bucket:01 - Naruto / Sasuke / Sakura | fully_covered_by_one_bucket | No unknown requirement ids in planner output. |
| Medical Training | Win 10 battles with Haruno Sakura. | bucket:01 - Naruto / Sasuke / Sakura | fully_covered_by_one_bucket | No unknown requirement ids in planner output. |

### Play Priorities

Strategic inference:

- Keep Team 7 intact while running this pool, because replacing any member breaks the Survival requirement.
- Prioritize Sakura streak attempts when the matchup is favorable, because two of the three missions depend on Sakura progress and one requires a streak.
- Treat this as a mission-efficiency team, not a claim that Team 7 is the best ladder team in all contexts.

### Confidence / Data Gaps

Confirmed:

- The planner returned `coverage_bucket_count=1`, `exact_requirement_unit_count=4`, and no impossible exact units.
- Each coverage matrix row is `fully_covered_by_one_bucket`.

Data gaps:

- Numeric rank values are not provided for the mission rank labels in the snapshot.
- Character records still carry accepted data-quality warnings, so precise targeting or effect semantics should not be overclaimed.
- This grouped plan only proves the named mission pool.

## Sample 4 - Diagnose Or Improve An Existing Team

Prompt: `Diagnose Uzumaki Naruto / Uchiha Sasuke (S) / Haruno Sakura and suggest the smallest fix.`

### Verdict

The team is coherent, but greedy. It has pressure, control, protection, setup, sustain, and a resource-denial identity surface, so it is not a fake or empty shell. The main problem is not lack of roles; it is the chakra curve.

### Biggest Problem

Confirmed from local data:

- The team report marks shared `nin` chakra pressure as `high`.
- Total `nin` component amount is 6 across Naruto, Uchiha Sasuke (S), and Sakura.
- `Uchiha Sasuke (S)` is the largest contributor to that `nin` load, with `Flying Corrupt Chidori`, `Great Dragon Flame Jutsu`, `Lightning Blade`, and `Lightning Shockwave` in the `nin` pressure evidence.
- The team also has medium shared `random` pressure.

Strategic inference:

- This team can look strong when the right colors arrive, but it risks losing turns because its best pressure/control lines compete for the same `nin` supply.

### Minimal Fix

Replace `Uchiha Sasuke (S)` with a no-`nin` control/resource option when the goal is a smoother general-purpose team. One grounded candidate path is `Akadou Yoroi`, who appears in the no-`nin` control search with control, resource, sustain, setup, and protection hints, `0` `nin` components, and `random`/`tai` top chakra.

This is a minimal one-slot fix. It is not an authoritative best-team claim.

### Why The Fix Helps

Confirmed from local data:

- The helper search command `python scripts/search_characters.py --role-hint control --exclude-chakra-type nin --limit 5` returns 63 candidates and includes `Akadou Yoroi`.
- `Akadou Yoroi` has `0` `nin` components and control/resource tags from drain effects.

Strategic inference:

- Swapping out `Uchiha Sasuke (S)` removes the biggest `nin` contributor while preserving a control/resource role. The tradeoff is that the team becomes less direct-damage oriented and may lean more on denial/setup.

### Broader Rebuild

Not required for a normal diagnosis because the original team has a coherent role shell. A broader rebuild is only needed if the user insists on keeping `Uchiha Sasuke (S)` as the carry; in that case, rebuild the other two slots around lower-`nin` partners instead of stacking Naruto and Sakura beside him.

### Mission Fit

This exact team is not the proven Team 7 mission-pool team, because `Survival` requires base `Uchiha Sasuke`, not `Uchiha Sasuke (S)`. If the goal is the accepted `Survival / A Girl Grown Up / Medical Training` pool, use base `Uchiha Sasuke` with Naruto and Sakura.

### Confidence / Data Gaps

Confirmed mechanics come from the team report and no-`nin` control search. Strategic claims about smoothness and matchup comfort are inference from chakra pressure and role surfaces.

Data gaps:

- The original team has warnings for effect magnitude, effect target, and heuristic effect typing.
- The proposed `Akadou Yoroi` path also carries data-quality warnings, so do not present it as a solved matchup answer without testing it against the user's roster and goal.

## Sample 5 - Explain Mechanics Or Character Difference

Prompt: `What is the practical difference between Uzumaki Naruto and Uzumaki Naruto (S)?`

### Question Resolution

The local bundle has two separate records:

- `Uzumaki Naruto`
- `Uzumaki Naruto (S)`

Both resolve to canonical character records from `https://www.naruto-arena.site/characters-and-skills`.

### Confirmed From Data

`Uzumaki Naruto`:

- Role hints: pressure, control, sustain, setup, protection.
- Top chakra types: random, nin, tai.
- Component totals: `random=3`, `nin=1`, `tai=1`.
- Effect buckets include damage, conditional, increase_damage, reduce_damage, apply_state, heal, protect, and stun.

`Uzumaki Naruto (S)`:

- Role hints: pressure, control, sustain, setup, resource, protection.
- Top chakra types: random, nin, tai.
- Component totals: `random=6`, `nin=2`, `tai=1`.
- Effect buckets include damage, stun, protect, conditional, apply_state, reduce_damage, and remove_state.

### Strategic Inference

Base Naruto is the simpler pressure/control/stabilizer profile and has a lighter visible chakra footprint. Naruto (S) has a wider role surface because the helper adds `resource`, and it has more offense/control/protection density in the effect buckets, but it also asks for more `random` and `nin` components.

In practical team building, I would treat base Naruto as easier to fit into low-commitment or early mission shells. I would treat Naruto (S) as a more demanding version that can offer extra utility if the rest of the team can support the heavier random/nin profile.

### Data Gaps / Unknowns

Both records carry:

- `character.data.effect_target_unknown`
- `character.data.effect_type_heuristic`

So the safe answer is not "one is strictly better." The bundle proves different role/chakra/effect surfaces, but matchup superiority and exact targeting behavior remain inference unless a specific skill text and source ref are inspected.

### Source Resolution

Resolved local source refs:

- `source:character:uzumaki-naruto:character` -> `https://www.naruto-arena.site/characters-and-skills`, section `character:Uzumaki Naruto`.
- `source:character:uzumaki-naruto-s:character` -> `https://www.naruto-arena.site/characters-and-skills`, section `character:Uzumaki Naruto (S)`.

No non-canonical domains, mirrors, or model-memory mechanics are used.
