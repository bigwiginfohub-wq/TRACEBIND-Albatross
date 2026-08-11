\# B6 AMENDMENT 001: Control Identity Definition Correction



\*\*Date:\*\* 2026-08-11  

\*\*Amends:\*\* `v1.0-phase-b6-protocol`, Section 6.1  

\*\*Proposed version:\*\* `v1.1-phase-b6-protocol`



\## Reason for Amendment



A forensic audit of the frozen B2.1 control-selection implementation and audit

artifacts established that the B2.1 algorithm does not define a persistent

non-storm atmospheric-system identifier for control cases.



The authoritative B2.1 implementation is:



`b2.1\_select\_controls\_v5.1.py`



with SHA-256:



`7a5dc65683aac22281462a640bbaeffa8b77f2d351659984edc24bd3d833e0d8`



The B2.1 atomic candidate identity is the tuple:



`(basin, month, lmc, timestamp, latitude, longitude)`



The `ControlID` is assigned sequentially after deterministic ranking and is

therefore an artifact identifier rather than a physical atmospheric-system

identifier.



No persistent `parent\_system\_id` is defined for B2.1 controls.



\---



\## Corrected Section 6.1 — Event/System Independence Hierarchy



\### TC Events



For tropical-cyclone events:



\- `parent\_system\_id` = IBTrACS Storm Identifier (`SID`).

\- The SID represents the persistent tropical-cyclone system.

\- All observations/events belonging to the same SID constitute one parent

&#x20; system for B6 partitioning purposes.

\- A given SID may appear in only one B6 partition.

\- If a SID is represented in the frozen B1–B5 analysis population, the entire

&#x20; SID is excluded from the B6 candidate population.



\### Control Events



For control events:



\- No persistent `parent\_system\_id` is defined.

\- `source\_case\_id` = the frozen B2.1 `ControlID`.

\- `source\_identity\_type` = `B2.1\_CONTROL\_SNAPSHOT`.

\- The underlying atomic B2.1 candidate identity is:

&#x20; `(basin, month, lmc, timestamp, latitude, longitude)`.

\- `ControlID` is an artifact-level identifier assigned after deterministic

&#x20; candidate ranking.

\- No broader atmospheric-system identity may be inferred from the ControlID,

&#x20; timestamp, coordinates, or B2.1 ranking procedure.

\- Each B2.1 control case is treated as a distinct identified sampling unit

&#x20; for B6 cohort construction and partition bookkeeping.

\- \*\*This identification is an artifact/sampling identity only and does not

&#x20; assert physical independence between atmospheric states.\*\*



\### Partition Independence Rule



The following rules apply:



1\. \*\*TC events:\*\* all events associated with the same IBTrACS SID must belong

&#x20;  to exactly one B6 partition.



2\. \*\*Control events:\*\* the same frozen B2.1 `source\_case\_id` must not occur in

&#x20;  more than one B6 partition.



3\. No control may be assigned an inferred or synthetic physical

&#x20;  `parent\_system\_id`.



4\. Additional temporal or spatial exclusion of control candidates shall not

&#x20;  be inferred merely from the existence of a B2.1 ControlID. Any such

&#x20;  exclusion must be explicitly defined by the applicable frozen B6 rule and

&#x20;  recorded in the exclusion audit.



\---



\## Impact on B6 Implementation



The B6 implementation shall therefore use separate identity fields:



\- `parent\_system\_id` for TC events;

\- `source\_case\_id` for B2.1 control events;

\- `source\_identity\_type` to distinguish the identity semantics.



The exclusion manifest shall preserve the distinction between:



\- persistent TC system exclusion; and

\- previously represented B2.1 control-case exclusion.



No physical atmospheric-system identity shall be fabricated for control cases.



\---



\## Governance



This amendment corrects an implementation/specification mismatch discovered

through forensic inspection of the frozen predecessor artifacts.



The amendment does not alter:



\- the B6 scientific hypothesis;

\- the primary endpoint;

\- the TRACEBIND feature definition;

\- the target definition;

\- the model family;

\- the test-set methodology;

\- the bootstrap procedure; or

\- the three-tier outcome framework.



It corrects only the identity semantics required for deterministic,

leakage-controlled B6 cohort construction and partitioning.

