# [SOURCE OF TRUTH] -- Mechanical Dimensions and Specs

**Linear:** [LEV-72](https://linear.app/levitation-project-management/issue/LEV-72/source-of-truth-mechanical-dimensions-and-specs)
**Project:** Full Scale Integration · **Milestone:** Mechanical Integration
**Status:** In Progress · **Priority:** Urgent · **Assignee:** Aditya Matam

## Dimensions

*For mechanical teams — this is how much real-estate I need per yoke*

**Net BOUNDING BOX: 7" x 5.5" x 15"**

- *Yoke: **5" x 3.5" x 9"** — which is already built (Image 1)*
  - *Mass: **14 kg***
- *Sensor: **4" away** (Image 2)*
- *Shielding box (placed on yokes during transport): **+2" on each side***
- *Yoke + Shielding => 7" x 5.5" x 11" + Sensor Clearance => **7" x 5.5" x 15"***

**NOTE:** There are 2 holes on either face of the yoke (Image 1). L-brackets interface the yoke to an **aluminum plate/beam** on the top of the pod (FRAME DEPENDENCY)

## Forcing Notes

**Forcing Approximation** from the script on [GitHub](https://github.com/Levitation-Texas-Guadaloop/Lev-Main/tree/main/Magnetic-Circuit-Model) and methodology described in [LEV-35](https://linear.app/levitation-project-management/issue/LEV-35/general-magnetics-theory)

Pod mass vs. equilibrium gap (6" yoke, 4 identical yokes, i=0, from [`reluctance_model.py`](https://github.com/Levitation-Texas-Guadaloop/Lev-Main/tree/main/Magnetic-Circuit-Model)):

| Equilibrium gap | Pod mass (kg) | Pod mass (lb) |
|---|---|---|
| 5 mm | 315.3 | 695.2 |
| **6 mm** | **275.7** | **607.8** |
| **7 mm** | **241.1** | **531.6** |
| **8 mm** | **211.0** | **465.1** |
| 9 mm | 184.5 | 406.8 |
| 10 mm | 161.3 | 355.6 |

**Result:** 6-8mm is the recommended eq. gap => yielding ideal pod mass range of **211-276 kg.**

*Remark: These forcing figures assume 6" yoke, contradicting the bounding box figure I provided above. I would like mechanical teams to allot real estate for the 9" yoke (which we already have manufactured and might **need** to revert to)...*

### Image 1 (Yoke)

*(placeholder — see Linear ticket for image; signed URL, not embedded here)*

### Image 2 (Sensor worst-case dimension margin — `clearance_dimensioned.png`)

*(placeholder — see Linear ticket for image; signed URL, not embedded here)*
