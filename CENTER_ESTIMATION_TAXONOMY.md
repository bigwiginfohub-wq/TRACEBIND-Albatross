\# TRACEBIND-Albatross: Center Estimation Taxonomy



This document provides a scientifically grounded guide for selecting the appropriate center estimation strategy based on the atmospheric flow regime under analysis.



\*\*Core Principle:\*\* The frozen Cφ operator is center-dependent (Property P4). The choice of center estimator determines \*what\* the descriptor measures. Different flow regimes require different estimators to answer the intended scientific question.



\---



\## Taxonomy



| Flow Regime                  | Recommended Center Strategy | Scientific Question Answered                          | Evidence Base      |

|------------------------------|-----------------------------|-------------------------------------------------------|--------------------|

| Single cyclone               | Max absolute vorticity      | "How coherent is this cyclone?"                       | A2d benchmark      |

| Hurricane eye                | Max absolute vorticity      | "How coherent is the eyewall rotation?"               | A2d benchmark      |

| Isolated mesoscale vortex    | Max absolute vorticity      | "How coherent is this vortex?"                        | A2d benchmark      |

| Jet stream                   | Geometric / local window    | "How coherent is this regional flow?"                 | A2b response lib.  |

| Frontal shear zone           | Local window                | "How coherent is this shear region?"                  | A2b response lib.  |

| Double / multiple vortices   | Multi-center analysis       | "How coherent is each vortex individually?"           | A2d counterexample |

| Non-rotational flow          | Geometric center            | "What is the background coherence level?" (\~0.65)     | A2b response lib.  |

| Global domain                | Hierarchical centers        | "Where are the coherent regions globally?"            | Future derived proc|



\---



\## Physical Reasoning



\### Why Max Vorticity Works for Single Vortices

In a coherent vortex, vorticity (ζ = ∂v/∂x − ∂u/∂y) peaks at the geometric center of rotation. This is a fundamental property of rotational flow. The A2d benchmark confirmed this with sub-grid accuracy across multiple vortex configurations.



\### Why Max Vorticity Fails for Multiple Vortices

When two comparable vortices exist, max |ζ| locks onto the stronger one. The resulting Cφ measures the coherence of \*that vortex\*, not the system. This is not an error—it is a different measurement. For system-level analysis, geometric center or multi-center analysis is required.



\### Why Geometric Center is the Background Baseline

For non-rotational flows (jets, shear, uniform translation), there is no "true center." The geometric center yields Cφ ≈ 0.65, which is the operator's baseline for organized non-rotational flow (A2b). This is the correct physical behavior, not a failure.



\---



\## Future Extensions



\### Derived Procedure A2: Multi-Center Analysis

For systems with multiple comparable vortices, a future derived procedure will:

1\. Identify all local maxima of |ζ| above a significance threshold

2\. Apply the frozen Cφ operator independently to each vortex-centered sub-domain

3\. Aggregate results into a multi-center coherence profile



\*\*Frozen mathematics:\*\* UNCHANGED. Only the evaluation protocol changes.



\### Derived Procedure A3: Hierarchical Global Analysis

For global domains, a future derived procedure will:

1\. Partition the globe into regional tiles

2\. Apply appropriate center estimation per tile (per this taxonomy)

3\. Generate a global coherence map



\*\*Frozen mathematics:\*\* UNCHANGED. Only the evaluation protocol changes.



\---



\## Operational Guidance



When analyzing a new atmospheric dataset:

1\. \*\*Identify the flow regime\*\* (visual inspection, synoptic context)

2\. \*\*Select the appropriate center estimator\*\* from this taxonomy

3\. \*\*Document the choice\*\* in the provenance

4\. \*\*Interpret the Cφ value\*\* in the context of the chosen estimator



Example:

\- Analyzing Hurricane Ian → Max vorticity → Cφ = 0.94 → "The eyewall rotation is highly coherent"

\- Analyzing the North Atlantic jet → Geometric center → Cφ = 0.67 → "The regional flow exhibits moderate shear coherence"



Both are valid scientific statements. The taxonomy ensures they are not conflated.

