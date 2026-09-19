# Maglev - Magnet Manufacture and Shielding

*Master doc for **S6**. Owner: **Keerthi Chandran** · Support: **Aarush Upadhya** · Linear: `Two Yoke Test Rig / Magnetics` + label `S6`.*

> **STUB.** Scoping and open questions only — numbers here are placeholders pulled from sibling docs, not decisions. Fill in as the trade studies land.

Companion to [[Maglev - PM Bias and Force Linearization]] (what the PM has to deliver), [[Maglev - Coupling and Geometry]] (yoke geometry and inter-yoke effects), [[Maglev - Hardware and Implementation]] (how it mounts).

---

## 1. Why this is a stream and not a purchase order

The PM is not a component choice, it is the operating point. Per [[Maglev - PM Bias and Force Linearization]], the permanent magnet carries the static load so the coil only has to handle the *deviation* — that is the whole reason the actuator is PM-biased rather than pure reluctance. Getting the PM wrong moves the zero-power gap, changes `k_i` and `k_s`, and rescales every gain in the control stack.

Three properties have to be decided together, and they trade against each other:

- **Grade / remanence `B_r`** — sets the bias flux and therefore where zero-power sits.
- **Geometry** — 1" per leg × 2 legs in the current yoke (`L_PM` in `params.py`). Length in the magnetic loop sets the PM's share of total reluctance (η ≈ 0.11 today), which scales both stiffnesses.
- **Manufacturability** — grade availability, tolerance, coating, and whether the part can actually be handled and potted without chipping or demagnetising.

## 2. Open questions

1. **What grade, and why?** Current sim assumes NdFeB N42, `B_r = 1.3 T`, `μ_rec = 1.05`. Nobody has justified N42 specifically against cost, temperature coefficient, or availability.
2. **Temperature.** NdFeB remanence drifts roughly **−0.11%/°C**. That moves the zero-power point directly. Does the operating envelope need a grade with a better tempco (SmCo trades remanence for stability), or is the drift small enough to reject in the loop?
3. **Yoke-to-yoke matching.** The dual rig will measure this for free — at nulled roll, a systematic `c0`/`c1` force difference *is* PM mismatch. **Set a matching tolerance before the sweep runs** so the result means something.
4. **Shielding: what are we actually protecting?** Stray field affecting nearby sensors (Hall placement — see [[Maglev - Hall Sensor Selection]]), the pod electronics, or people? The answer picks the material and the geometry.
5. **Shielding material.** Mu-metal (high µ, saturates low, needs annealing after forming) vs. silicon steel vs. simple mild-steel return path. A high-µ shield near a working gap can steal flux from the circuit — **shielding must be designed with the magnetic circuit, not bolted on afterwards.**
6. **Potting and retention.** How is the magnet held against an attractive load that peaks at the smallest gap? What happens on a hard stop?

## 3. Near-term scope

Specification and trade-study work; does **not** block on the rig being finished.

- [ ] Grade trade study — `B_r`, tempco, cost, availability, lead time.
- [ ] Geometry sensitivity — sweep `L_PM` through the existing model and report how zero-power gap, `k_i`, `k_s` move. `lev_sim` and `Code/maglev/` already support this; no new physics needed.
- [ ] Define the yoke-matching tolerance, and hand it to S2′ as an acceptance criterion.
- [ ] Shielding requirement — write down what is being protected and to what field level, *before* choosing a material.
- [ ] First-pass shielding concept for the big yoke, coordinated with S5 fixturing.

## 4. Deliverables into other streams

| To | What |
| --- | --- |
| **S2′** | PM matching tolerance as a sweep acceptance criterion; expected zero-power gap to sanity-check the measured `F(z)`. |
| **S5** | Shield geometry and mounting envelope; magnet retention scheme. |
| **S3** | Stray-field map near candidate Hall locations — feeds placement in [[Maglev - Hall Sensor Selection]]. |
| **Sim** | Confirmed `B_r`, `μ_rec`, `L_PM` for `params.py`, replacing the current illustrative values. |
