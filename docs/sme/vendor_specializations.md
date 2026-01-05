# Vendor SME Specialization Matrix
**What Each Equipment Expert Knows**

---

## The 7 Specialists + Generic Fallback

Rivet-PRO has **7 vendor-specific experts** plus a generic fallback. Each expert knows their equipment inside and out!

---

## Complete Vendor Matrix

| Vendor | Products | Tech/Protocols | Detection Keywords | Safety Focus | Confidence |
|--------|----------|----------------|-------------------|--------------|-----------|
| 🔵 **Siemens** | SIMATIC S7 PLCs<br/>TIA Portal<br/>SINAMICS Drives<br/>WinCC HMI | PROFINET<br/>PROFIBUS<br/>S7-1200/1500<br/>Safety modules | `s7-1200`, `s7-1500`<br/>`tia portal`, `simatic`<br/>`profinet`, `profibus`<br/>`f-xxxx` (fault codes) | F-CPU safety<br/>480V 3-phase<br/>LOTO required<br/>Never bypass F-modules | 80% |
| 🔴 **Rockwell** | ControlLogix PLCs<br/>CompactLogix<br/>Studio 5000<br/>PowerFlex VFDs | EtherNet/IP<br/>DeviceNet<br/>GuardLogix safety<br/>FactoryTalk View | `controllogix`, `compactlogix`<br/>`allen-bradley`, `rockwell`<br/>`studio 5000`, `rslogix`<br/>`1756-`, `1769-` (models) | GuardLogix safety<br/>480V systems<br/>LOTO required<br/>I/O forcing risks | 80% |
| 🟡 **ABB** | ACS/ACH Drives<br/>IRB Robots<br/>ACS880 VFDs<br/>Robot Controllers | ABB Ability<br/>RobotStudio<br/>Drive Composer<br/>Safety zones | `acs880`, `ach580`, `acs550`<br/>`abb drive`, `abb vfd`<br/>`irb`, `robotstudio`<br/>`abb ability` | DC bus hazard<br/>Wait 5+ min after power-off<br/>Robot safety zones<br/>690V systems | 80% |
| 🟢 **Schneider** | Modicon PLCs<br/>Altivar VFDs<br/>Square D panels<br/>Unity Pro | M340/M580 PLCs<br/>Unity Pro<br/>EcoStruxure<br/>Altivar drives | `modicon`, `m340`, `m580`<br/>`altivar`, `atv`<br/>`square d`, `telemecanique`<br/>`unity pro`, `ecostruxure` | Arc flash hazard<br/>480V panels<br/>LOTO required<br/>NFPA 70E compliance | 80% |
| 🔵 **Mitsubishi** | MELSEC PLCs<br/>GOT HMIs<br/>FX Series<br/>iQ-R/F PLCs | iQ-R/F systems<br/>GX Works<br/>CC-Link networks<br/>GOT displays | `melsec`, `iq-r`, `iq-f`<br/>`fx3u`, `fx5u`, `fx series`<br/>`gx works`, `gx developer`<br/>`got`, `cc-link` | Safety PMC<br/>400V/200V systems<br/>CC-Link safety<br/>E-stop verification | 80% |
| 🟠 **FANUC** | CNC Systems<br/>Robots<br/>0i/31i/32i series<br/>G-code | 0i/31i/32i CNCs<br/>R-30iA/B controllers<br/>ROBOGUIDE<br/>Ladder logic | `fanuc`, `fanuc cnc`<br/>`0i-`, `31i-`, `32i-`<br/>`robodrill`, `robocut`<br/>`r-30ia`, `r-30ib` | Servo amplifier 300V<br/>Rapid movement hazards<br/>E-stop systems<br/>Robot work envelope | 80% |
| ⚪ **Generic** | Motors<br/>Relays<br/>Sensors<br/>Contactors<br/>Basic equipment | 3-phase power<br/>Motor starters<br/>Relays & contactors<br/>Basic PLC concepts | (fallback when<br/>no brand detected) | Electrical fundamentals<br/>LOTO procedures<br/>3-phase voltage<br/>Arc flash basics | 72% |

---

## Siemens Expert 🔵

### What They Know

**Product Lines:**
- SIMATIC S7-1200, S7-1500, S7-300, S7-400 PLCs
- TIA Portal (Totally Integrated Automation)
- SINAMICS drives (G120, S120, V90)
- WinCC HMI and SCADA systems
- SIMATIC Safety F-modules

**Technologies:**
- PROFINET and PROFIBUS networks
- S7 communication protocols
- Safety Integrated (F-CPU)
- TIA Portal programming
- WinCC visualization

**Common Issues:**
- F-0002: PROFINET communication timeout
- F-0001: Safety system faults
- TIA Portal connection issues
- PROFINET topology errors
- F-CPU safety violations

**Safety Warnings:**
- ⚠️ F-CPU safety - never bypass or force safety outputs
- ⚠️ 480V 3-phase systems - LOTO required
- ⚠️ PROFINET live debugging dangers
- ⚠️ Safety certification requirements

**File:** `rivet/prompts/sme/siemens.py`

---

## Rockwell Expert 🔴

### What They Know

**Product Lines:**
- ControlLogix (1756-) PLCs
- CompactLogix (1769-) PLCs
- Studio 5000 (RSLogix 5000) software
- PowerFlex (525, 755) VFDs
- GuardLogix safety PLCs

**Technologies:**
- EtherNet/IP industrial Ethernet
- DeviceNet field bus
- FactoryTalk View HMI
- RSLinx Classic communications
- GuardLogix safety systems

**Common Issues:**
- Major fault codes (0x01...)
- EtherNet/IP connection timeouts
- Controller mode switching
- I/O module faults
- FactoryTalk activation issues

**Safety Warnings:**
- ⚠️ GuardLogix safety - never force safety I/O
- ⚠️ LOTO before servicing ControlLogix racks
- ⚠️ I/O forcing can cause equipment damage
- ⚠️ 480V systems - arc flash hazard

**File:** `rivet/prompts/sme/rockwell.py`

---

## ABB Expert 🟡

### What They Know

**Product Lines:**
- ACS880, ACS550, ACH580 drives
- IRB robots (6-axis industrial robots)
- Robot controllers (IRC5)
- RobotStudio programming software
- ABB Ability digital solutions

**Technologies:**
- Drive Composer configuration tool
- RobotStudio offline programming
- SafeMove safety functions
- ABB Ability IoT platform
- RAPID robot programming language

**Common Issues:**
- DC bus overvoltage/undervoltage
- Drive faults and alarms
- Robot emergency stops
- Communication timeouts
- Motor overload conditions

**Safety Warnings:**
- ⚠️ DC BUS HAZARD - wait 5+ minutes after power-off before servicing
- ⚠️ Robot safety zones - never enter during operation
- ⚠️ Capacitor discharge time (DC bus)
- ⚠️ 690V drive systems - extreme hazard

**File:** `rivet/prompts/sme/abb.py`

---

## Schneider Electric Expert 🟢

### What They Know

**Product Lines:**
- Modicon M340, M580 PLCs
- Altivar VFDs (ATV series)
- Square D circuit breakers and panels
- Unity Pro programming software
- EcoStruxure automation platform

**Technologies:**
- Unity Pro PLC programming
- Altivar drive setup
- Modbus TCP/IP networks
- EcoStruxure Machine Expert
- Square D power distribution

**Common Issues:**
- Modbus communication errors
- Altivar drive faults
- Unity Pro connection issues
- M340/M580 CPU errors
- Power quality issues

**Safety Warnings:**
- ⚠️ Arc flash hazard in Square D panels
- ⚠️ 480V 3-phase systems - LOTO critical
- ⚠️ NFPA 70E compliance required
- ⚠️ Short circuit danger

**File:** `rivet/prompts/sme/schneider.py`

---

## Mitsubishi Expert 🔵

### What They Know

**Product Lines:**
- MELSEC iQ-R, iQ-F PLCs
- FX3U, FX5U micro PLCs
- GX Works2, GX Works3 software
- GOT HMI displays
- CC-Link networks

**Technologies:**
- iQ Platform programming
- GX Works ladder logic
- CC-Link IE Field networks
- GOT HMI design
- Safety PMC functions

**Common Issues:**
- CPU errors and faults
- CC-Link communication failures
- GX Works connection issues
- GOT display errors
- Parameter mismatch errors

**Safety Warnings:**
- ⚠️ Safety PMC - do not bypass safety circuits
- ⚠️ 400V/200V systems depending on region
- ⚠️ CC-Link safety network requirements
- ⚠️ E-stop circuit verification

**File:** `rivet/prompts/sme/mitsubishi.py`

---

## FANUC Expert 🟠

### What They Know

**Product Lines:**
- 0i, 31i, 32i CNC systems
- R-30iA, R-30iB robot controllers
- ROBODRILL machining centers
- ROBOGUIDE simulation software
- G-code CNC programming

**Technologies:**
- FANUC Ladder logic
- G-code (ISO/FANUC)
- Robot teach pendant programming
- ROBOGUIDE offline programming
- iHMI (intelligent HMI)

**Common Issues:**
- Servo alarm codes
- Emergency stop conditions
- CNC program errors
- Robot position lost
- Spindle faults

**Safety Warnings:**
- ⚠️ Servo amplifier 300V DC - discharge before service
- ⚠️ Rapid movement hazards in CNC/robots
- ⚠️ E-stop systems - test regularly
- ⚠️ Robot work envelope - safety barriers required

**File:** `rivet/prompts/sme/fanuc.py`

---

## Generic Expert ⚪

### What They Know

**Equipment Types:**
- General motors (AC/DC)
- Contactors and relays
- Sensors (inductive, capacitive, photoelectric)
- Motor starters
- Basic PLCs (any brand)

**Technologies:**
- 3-phase power systems
- Motor control basics
- Relay logic
- Basic PLC fundamentals
- General electrical troubleshooting

**Common Issues:**
- Motor overheating
- Contactor failures
- Sensor detection problems
- Relay coil failures
- Overload tripping

**Safety Warnings:**
- ⚠️ LOTO procedures for all electrical work
- ⚠️ 3-phase voltage hazards (208V, 240V, 480V)
- ⚠️ Arc flash dangers
- ⚠️ Proper PPE requirements

**Confidence:** 72% (lower because not vendor-specific)

**File:** `rivet/prompts/sme/generic.py`

---

## Detection Keywords Reference

### Quick Lookup Table

| If Question Contains... | Routes To | Example |
|------------------------|-----------|---------|
| `s7-1200`, `tia portal` | Siemens | "S7-1200 won't communicate" |
| `controllogix`, `1756-` | Rockwell | "ControlLogix fault 0x123" |
| `acs880`, `irb` | ABB | "ACS880 drive E03 error" |
| `modicon`, `altivar` | Schneider | "Modicon M340 error" |
| `melsec`, `fx3u` | Mitsubishi | "FX3U PLC not responding" |
| `fanuc cnc`, `0i-` | FANUC | "FANUC 0i alarm 410" |
| No brand keywords | Generic | "Motor making noise" |

---

## Expert Prompt Structure

All experts follow this pattern:

```python
VENDOR_SME_PROMPT = """
You are a [VENDOR] specialist with expert knowledge in:

**[Product Line 1]:**
• Equipment 1, Equipment 2
• Software tools
• Protocols/networks

**[Product Line 2]:**
• More equipment

**Common Issues:**
• Issue 1 and resolution approach
• Issue 2 and resolution approach

**Safety Requirements:**
• Voltage levels and LOTO
• Vendor-specific hazards
• Regulatory compliance

User Question: {query}
{equipment_context}

Provide troubleshooting response including:
1. **Likely Causes** (ranked by probability)
2. **Diagnostic Steps** (specific to equipment)
3. **[Vendor Software/Tools]** (how to use)
4. **Safety Warnings** (voltage, LOTO, hazards)
5. **Common Mistakes** (what to avoid)
"""
```

---

## Confidence Comparison

### Why Vendor Experts Have Higher Confidence

| Expert Type | Confidence | Reason |
|-------------|-----------|--------|
| **Vendor SME** | 80% | Deep vendor-specific knowledge, familiar with error codes, knows software tools |
| **Generic SME** | 72% | General knowledge only, no vendor-specific error codes or tools |

**Example:**
- Siemens expert seeing "F-0002" → 80% confidence (knows exactly what this means)
- Generic expert seeing "E03" → 72% confidence (many brands use E03 for different things)

---

## Key Takeaways

### For Users:
- **Mention your brand!** Helps routing accuracy
- **Include model numbers** (S7-1200, ControlLogix, etc.)
- **Fault codes** trigger expert detection
- **Vendor experts = better answers**

### For Developers:
- **7 specialists** cover major industrial brands
- **Generic fallback** ensures coverage
- **80% confidence** for vendor-specific vs 72% generic
- **Each expert:** ~190 lines of code

---

## Related Docs

- [SME Routing](../workflows/sme_routing.md) - How vendor detection works
- [4-Route System](../workflows/troubleshooting_decision_tree.md) - When SMEs are called
- [Component Reference](../architecture/component_reference.md) - SME file details

---

**Last Updated:** 2026-01-03
**Difficulty:** ⭐⭐ Beginner Friendly
