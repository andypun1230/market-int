# Stage 6 Relationship Engine

## Purpose

The Relationship Engine explains how a qualified research subject is connected to its benchmark, taxonomy, constituent securities, and the user's saved list. Its output is a typed, evidence-linked graph used by the Research Chain figure and by the frontend preview.

The graph describes validated structure. It does not explain why prices moved, predict how a move will propagate, or imply that one node caused another node to rise or fall.

## Trust boundary

Every visible edge must come from a frozen, identified mapping in the report input. The engine may normalize IDs and arrange nodes for display, but it may not infer a missing hierarchy or translate co-movement into a business relationship.

The following distinction is mandatory:

- **Relationship:** an explicit benchmark comparison, taxonomy membership, hierarchy, theme definition, saved-list overlap, or separately validated structured supply-chain mapping.
- **Analytical observation:** a return, rank, breadth, participation, or relative-strength value associated with a node.
- **Causal claim:** an assertion that one node caused another market outcome. Stage 6 does not generate causal claims.

Arrows in the Research Chain mean “is connected by this typed mapping.” They are not forecast arrows and do not represent capital flow, price direction, transmission strength, or causality.

## Graph contract

`ResearchRelationshipGraph` contains:

- `nodes`: unique `node_id`, display `label`, `node_type`, and display `depth` from 0 through 8;
- `edges`: unique `relationship_id`, known source and target node IDs, typed relationship, display label, mapping source, structured-data flag, and one or more evidence IDs.

Document validation rejects duplicate node IDs, duplicate edge IDs, dangling source or target references, and relationship edges whose evidence IDs are empty or unknown. A supply-chain edge has an additional hard gate described below.

The graph is additive to the established V7 `taxonomy_chain`. The legacy chain remains available for compatibility; Stage 6 consumers should prefer the typed graph because it preserves edge semantics and provenance.

## Supported relationship types

| Type | Meaning | Accepted source in the current builder | Non-claim |
| --- | --- | --- | --- |
| `sector_hierarchy` | Sector-to-industry or sector-to-member structure | Security master or validated sector membership | Does not mean the sector caused the security's return. |
| `theme_hierarchy` | Parent sector/theme or theme/member structure | Reviewed, versioned theme definition | Does not mean a theme is an economic supply chain. |
| `relative_performance` | Typed performance comparison between supported nodes | Reserved by the v2 contract for an explicit comparative series | Does not establish business dependence. |
| `benchmark_relationship` | Subject compared with a named benchmark | Frozen one-month benchmark-relative metric | Does not mean benchmark movement caused subject movement. |
| `user_watchlist_overlap` | A graph security is explicitly saved by the user | Frozen research preferences | Does not infer ownership or portfolio exposure. |
| `validated_taxonomy` | Security or industry membership in a validated classification | Security master | Does not imply supplier/customer status. |
| `validated_supply_chain` | Explicit supplier/customer or similar business mapping | Separately supplied structured relationship record | Does not establish market causality or current materiality by itself. |

The current builder emits hierarchy, benchmark, taxonomy, and saved-overlap edges when their source inputs are present. `relative_performance` is part of the typed contract but is not synthesized from proximity or chart correlation. It should be emitted only when the implementation has an explicit node-to-node comparative measure.

## Deterministic construction

### Common subject node

Every graph starts with one focus node derived from the selected candidate. Group subjects are typed as their candidate category; an individual candidate is typed as a security. Normalized IDs provide deterministic deduplication while the original label remains visible.

### Benchmark relationship

Theme and sector candidates with a supported current benchmark-relative value receive a `SPY benchmark` node and a `benchmark_relationship` edge labeled as one-month relative performance. Individual-security candidates do not receive this group-relative edge because their current `relative_strength` field is an RS rank from the stock snapshot, not percentage-point performance versus SPY.

### Theme graph

For a theme candidate, the builder may add:

1. up to three validated parent-sector nodes from member taxonomy or the theme definition;
2. a `theme_hierarchy` edge from each parent sector to the theme;
3. industry nodes from validated member taxonomy;
4. `validated_taxonomy` edges from the theme to those industries;
5. `validated_taxonomy` edges from each industry to its member securities;
6. a direct `theme_hierarchy` member edge when no industry mapping exists but reviewed theme membership is explicit.

This creates a branching graph. It is not flattened into a narrative chain that would conceal multiple parent sectors or industries.

### Sector graph

For a sector candidate, the builder may add:

1. industry nodes from security-master membership;
2. `sector_hierarchy` edges from the sector focus to industries;
3. `validated_taxonomy` edges from industries to securities;
4. direct `sector_hierarchy` member edges only when explicit sector membership exists and no industry layer is available.

### Individual-security graph

For an individual security, the builder may add its validated sector and industry path from the security master:

`sector -> industry -> security`

The sector-to-industry edge is `sector_hierarchy`; the industry-to-security or sector-to-security edge is `validated_taxonomy`. No peer, supplier, customer, or theme edge is inferred from the security symbol alone.

### Saved-list overlap

When an explicit saved security already exists in the graph, the builder adds one `User Saved Stocks` node and a `user_watchlist_overlap` edge. Only the intersection between validated focus members and frozen saved symbols is shown. The graph does not add unseen saved securities merely to enlarge the diagram.

The overlap means the security is saved for monitoring. It never means the user owns it, has exposure to it, or should act on the group conclusion.

## Supply-chain gate

Supply-chain relationships are prohibited by default. A `validated_supply_chain` edge is eligible only when every condition below is true:

1. the report input contains a record in `validated_relationships`;
2. `relationship_type` is exactly `validated_supply_chain`;
3. `structured_data` is true;
4. `mapping_source` is a non-empty explicit source identifier;
5. `source_symbol` and `target_symbol` resolve to security nodes already present in the focus graph;
6. the generated relationship evidence is registered in the document.

The model independently rejects a supply-chain edge whose `structured_data` flag is false or whose mapping source is blank. This is defense in depth: the builder filters invalid payloads, and the document contract refuses an invalid serialized edge.

Free text, analyst intuition, theme adjacency, shared sector membership, price correlation, news text, and model-generated associations are not sufficient sources for a supply-chain edge. If the structured mapping is absent, the relationship is omitted and the focus limitation states that the diagram represents taxonomy or membership rather than supplier/customer flows.

## Evidence registration

Each emitted edge creates an evidence point whose metric names the two connected nodes, whose current value is the relationship type, whose unit is `mapping`, and whose timeframe is the current validated relationship graph. The evidence source is the frozen theme, sector, or watchlist research source used by the selected candidate.

This edge-level evidence is included in `research_focus.evidence_ids`. Consumers can therefore audit both the topology and the provenance without parsing diagram labels.

Node presence alone is not evidence of performance. Market claims about a node must use separate return, rank, breadth, participation, relative-strength, volume, or stock-snapshot evidence IDs.

## Research Chain rendering

The Research Chain is generated only when the graph contains both nodes and edges. It renders the node and typed-edge registries as a branching diagram. The visual should:

- group nodes by depth without implying time sequence;
- label or visually distinguish relationship types;
- preserve branches instead of forcing a false single chain;
- show benchmark, hierarchy, membership, and saved overlap as different semantics;
- reserve directional arrowheads for the declared source-to-target mapping only;
- avoid decorative future arrows, price targets, flow weights, or causal captions;
- remain readable when optional industry or saved-list layers are absent.

The figure's observation reports node and edge counts. Its interpretation explicitly says that arrows encode typed structure and not a price forecast or causal relationship.

## Relationship Engine versus leadership evidence

Leading and lagging securities are separate from graph topology. Stage 6 ranks supported constituent observations by one-month return when available. If a constituent return is absent, a matching frozen watchlist RS rank can serve as a current stock-snapshot measure. Each leader or laggard stores its metric label, value, timeframe, saved flag, reason, and evidence IDs.

A security's position in the graph does not make it a leader or laggard. Conversely, a relative leader is not assigned a taxonomy or supply-chain edge unless the corresponding mapping exists.

## Partial-data behavior

The engine degrades by omission:

| Missing input | Behavior |
| --- | --- |
| Benchmark-relative value | Omit the benchmark node and edge. |
| Parent sector | Keep the focus and supported member structure; do not invent a parent. |
| Industry mapping | Use only explicit direct membership when available. |
| Security taxonomy | Omit unsupported taxonomy levels. |
| Saved overlap | Omit the saved-list node. |
| Structured supply-chain source | Omit all supply-chain edges. |
| All usable edges | Keep the qualified focus but do not render a Research Chain; disclose the mapping limitation. |

Partial graphs are valid when every remaining edge is supported. A visually fuller graph is never preferred over a smaller auditable graph.

## Extension requirements

New relationship types or sources must not be added only in a renderer. An extension requires all of the following:

1. a versioned structured source contract;
2. a typed value in `RelationshipType`;
3. builder logic that emits deterministic nodes and edges;
4. exact evidence registration and freshness semantics;
5. model validation for any type-specific trust rule;
6. PDF and frontend rendering that preserves the declared semantics;
7. focused tests for valid, missing, malformed, and unsupported inputs;
8. an update to the data-gap document stating what the new source does and does not prove.

No extension may use a relationship diagram to bypass evidence, candidate qualification, or the no-focus policy.

