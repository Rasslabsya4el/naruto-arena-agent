# Synergy Patterns

These patterns are downstream planning guidance built on the project-owned tags in `references/tags.json`. They are not hardcoded teams and they are not new mechanics claims. Use them as retrieval and comparison hints, then confirm exact skills from local evidence before recommending a team.

## Core Patterns

- `character.capability.conditional_effects` + `character.capability.combo_dependency` + `character.capability.damage_effects`
  Use this when a character needs setup windows before their pressure matters. Pair setup-heavy characters with allies that buy time or stabilize the board while the gated skill comes online.

- `character.capability.protect_effects` or `character.capability.damage_reduction` + `character.capability.heal_effects`
  This is the safest baseline for streak-style planning. Protection reduces loss risk and healing helps preserve tempo across repeated wins.

- `character.capability.stun_effects` + `character.capability.damage_effects`
  Control plus pressure creates cleaner kill windows than either tag family alone. Prefer this pattern when a mission requires a named carry character to survive long enough to close games.

- `character.capability.drain_effects` or `character.capability.removal_effects` + `character.capability.stun_effects`
  This is a tempo-denial pattern. It is useful when the goal is to slow enemy turns rather than race immediately.

- `character.capability.gain_effects` + `character.capability.conditional_effects`
  Resource gain and setup tags together suggest a character can fuel their own follow-up windows or keep future skill chains online longer.

## Mission-Facing Patterns

- `mission.objective.streak`
  Favor safer compositions first: protection, healing, and reliable control are better default filters than pure damage tags.

- `mission.objective.win_with_character`
  Start from the required character or character group, then look for allies with protection, healing, or stun tags that preserve that win path. If the mission only has group text and carries `mission.data.character_group_not_modeled`, keep the recommendation broad and cite the unresolved group condition.

- `mission.objective.use_skill`
  Center the required user and the named skill refs. Protection, gain, and combo/setup tags are the best first-pass support filters because they increase the odds that the required skill can be activated repeatedly.

- `mission.objective.unknown`
  Do not collapse this into a fake solved objective. Branch recommendations by generally safe team shapes, surface the unknown tag family in the answer, and treat later mission-refresh work as the correct way to improve confidence.

## Uncertainty Rules

- `character.data.*` tags are not cosmetic. They mark places where downstream reasoning must stay conservative.
- `mission.data.*` tags are evidence-backed blockers or partial-structure markers, not parser noise.
- If a candidate comparison depends on a tag with uncertainty evidence, quote the underlying skill or mission text before making the recommendation stronger than the data supports.
