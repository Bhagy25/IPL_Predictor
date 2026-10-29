# Derived event tables

Small supplementary tables built directly from the committed raw Cricsheet JSON in
`data/raw/ipl_json/`. They add facts that Stage 1's `data/processed/deliveries.csv`
does not carry (dismissal kind, player out, fielders, bowler registry IDs, the
non-boundary flag) and a registry-ID player table. Stage 1 code and outputs are
unchanged. This file is generated; do not edit it by hand.

Build (from the repository root):

    python -m cricketlens.derived_events --raw data/raw/ipl_json --output data/derived

## Keys

`match_id`, `innings`, `over_index`, `delivery_index` use the same convention as
`deliveries.csv`: `match_id` is the JSON file name, `innings` is the 1-based
position of the innings in the file, `over_index` is Cricsheet's 0-based `over`,
and `delivery_index` is the 1-based position in that over's delivery list
(wides and no-balls included). Ordinary innings are 1 and 2; super-over innings
keep their position (3, 4, ...) and are flagged `is_super_over`. `season` is the
year of the first match date, as in Stage 1. Team names use Stage 1's franchise
mapping (`pipeline.RENAMES`).

## dismissals.csv

One row per wicket event, including super overs.

- `match_id`, `season`, `date`, `innings`, `over_index`, `delivery_index`: delivery key (see above)
- `is_super_over`: True for super-over innings; exclude these rows for career statistics
- `batting_team`, `bowling_team`: canonical franchise names
- `batter`, `batter_id`: striker on the delivery and Cricsheet registry ID
- `non_striker`, `non_striker_id`: non-striker and registry ID
- `player_out`, `player_out_id`: dismissed player (may be the non-striker) and registry ID
- `kind`: Cricsheet dismissal kind, lower case
- `bowler`, `bowler_id`: bowler of the delivery and registry ID
- `fielders`, `fielder_ids`: fielders involved, semicolon-separated, in matching order (substitutes included)
- `bowler_credited`: True when the wicket counts for the bowler
- `counts_as_batting_dismissal`: True when the batter's innings ends as a dismissal

## non_boundary_events.csv

Deliveries Cricsheet flags with `runs.non_boundary` (for example an all-run four).
The flag is the only source; nothing is inferred from run values.

- delivery key columns and `is_super_over`, as above
- `batter`, `batter_id`, `bowler`, `bowler_id`: players on the delivery
- `runs_batter`: runs credited to the batter, which are not a boundary

## batting_appearances.csv

One row per player per ordinary innings in which they were at the crease, as
striker or non-striker (or dismissed), in order of first appearance. A batting
innings is one row, so a non-striker run out without facing a ball still counts
as an innings and a dismissal. Super overs are excluded.

- `match_id`, `season`, `date`, `innings`: innings key (see above)
- `batting_team`: canonical franchise name
- `player_id`, `player_name`: registry ID and the name used in that match
- `balls_faced`: deliveries faced as striker, excluding wides (no-balls count)
- `runs`: runs off the bat
- `dismissed`: True when a wicket event for this player counts as a batting dismissal
- `dismissal_kind`: kind of that dismissal, or of a non-dismissal event such as retired hurt; empty if none
- `faced_a_ball`: True when `balls_faced` > 0
- `on_strike`: True when the player was the striker on at least one delivery
  (including wides); these rows are exactly Stage 1's `batter_innings.csv` rows

## match_players.csv

One row per player per match from `info.players` (official squad lists, including
listed impact or replacement players) and `info.registry.people`.

- `match_id`, `season`, `date`: match key
- `team`: canonical franchise name
- `player_name`: name as listed for that match
- `player_id`: Cricsheet registry ID

## match_replacements.csv

One row per match-level substitution recorded in a delivery's
`replacements.match` list: Impact Player substitutions and concussion
substitutes. Both players are in `info.players`, so both have a
match_players.csv row for that match: a team's list is its starting eleven
plus every player who came in. Mid-over bowler or batter changes
(`replacements.role`) do not change the squad and are not included.

- `match_id`, `season`, `date`, `innings`, `over_index`, `delivery_index`: the
  delivery where the substitution is recorded (see Keys)
- `is_super_over`: True when it is recorded in a super-over innings
- `team`: canonical franchise name
- `reason`: Cricsheet reason, e.g. `impact_player` or `concussion_substitute`
- `player_in`, `player_in_id`: player who came into the match and registry ID
- `player_out`, `player_out_id`: player replaced and registry ID

## people.csv

One row per registry ID seen as a listed player or as a fielder.

- `player_id`: Cricsheet registry ID
- `names`: every name variant seen for this ID, semicolon-separated
- `first_season`, `last_season`: first and last season in an official player list
- `matches`: matches in an official player list
- `teams`: canonical franchises in those lists, semicolon-separated

Substitute fielders who never appear in an official player list have
`matches` = 0 and empty season and team fields.

## Rules

- `bowler_credited` is True for: bowled, caught, caught and bowled, lbw, stumped,
  hit wicket. It is False for run out, retired hurt, retired out, obstructing the
  field and any other kind (handled the ball, timed out).
- `counts_as_batting_dismissal` is True for every kind except retired hurt and
  retired not out. This is the same rule Stage 1 uses for team wickets
  (`pipeline.NO_TEAM_WICKET`), so retired out counts as a dismissal.
- Super overs: rows are kept and flagged, never mixed into ordinary innings.

## Files

CSV files are UTF-8 with LF line endings; `.gitattributes` keeps git from
converting them, so the hashes below match a checkout.

| File | Rows | Bytes | SHA256 |
|---|---:|---:|---|
| dismissals.csv | 14,705 | 2,714,066 | `b626f43307a927cc03b2fd8a7c8a2a1ea8d2f4737bb8d0a29db58af968877220` |
| non_boundary_events.csv | 29 | 2,385 | `65cbbb65826e7a55371c82d6f8adb89e8cf16576dacdd0d38a40a75eb6498c5a` |
| batting_appearances.csv | 19,111 | 1,715,390 | `595265dc49da227fed158529adb34eb1288daecd95496e8ce43e50b47458f340` |
| match_players.csv | 27,909 | 1,723,500 | `525f2513f7cc429e259e7834fa9e0b5e00185cc6c3b3e374a9674ebfab4d2f26` |
| match_replacements.csv | 563 | 62,160 | `001be472ddcf16f12f02aaafd13e317e616bb7312f654e8a67e960503247423b` |
| people.csv | 816 | 55,784 | `ed0f498789641750a7422471fa86581c085a278e2496fb3e6719423c28f2eb4a` |
