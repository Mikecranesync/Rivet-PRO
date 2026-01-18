# YCB Asset Creation Guide

This guide explains how to create and add new visual assets to the YCB v3 video generation system.

## Asset Types

### 1. SVG Symbols

SVG files are used for 2D technical diagrams and can be animated in Manim.

**Location:** `ycb/assets/<category>/`

**Categories:**
- `electrical/` - IEC electrical symbols
- `plc/` - PLC hardware and ladder logic symbols
- (Add new categories as needed)

### 2. Manim Templates

Python dataclasses that generate Manim animation code.

**Location:** `ycb/rendering/templates.py`

---

## Creating SVG Assets

### File Requirements

1. **Format:** SVG (Scalable Vector Graphics)
2. **Size:** 100x100 viewBox recommended
3. **Colors:** Use hex colors, preferably from the color scheme
4. **Stroke:** Use consistent stroke widths (2-4 for main elements)

### Color Scheme

```python
INDUSTRIAL_COLORS = {
    "background": "#1A1A2E",
    "primary": "#0066CC",
    "secondary": "#00CC66",
    "accent": "#FF6600",
    "text": "#FFFFFF",
    "grid": "#333344",
}

PLC_COLORS = {
    "cpu": "#3B82F6",      # Blue
    "io_digital": "#22C55E", # Green
    "io_analog": "#8B5CF6",  # Purple
    "power": "#F59E0B",     # Amber
    "comm": "#06B6D4",      # Cyan
}
```

### SVG Template

```xml
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 100 100"
     width="100" height="100">
  <!-- Background (optional) -->
  <rect fill="none" width="100" height="100"/>

  <!-- Main symbol elements -->
  <circle cx="50" cy="50" r="30"
          fill="none" stroke="#3B82F6" stroke-width="3"/>

  <!-- Connection points (for wiring) -->
  <circle cx="50" cy="5" r="3" fill="#3B82F6"/>
  <circle cx="50" cy="95" r="3" fill="#3B82F6"/>
</svg>
```

### Manifest File

Each category needs a `manifest.json` file:

```json
{
  "name": "My Symbol Library",
  "version": "1.0.0",
  "description": "Description of this symbol collection",
  "author": "YCB Video Generator",
  "symbols": {
    "symbol_name": {
      "file": "symbol_name.svg",
      "category": "subcategory",
      "description": "What this symbol represents",
      "color": "#3B82F6",
      "size": {"width": 100, "height": 100},
      "anchor": {"x": 50, "y": 50},
      "connections": [
        {"name": "top", "x": 50, "y": 5},
        {"name": "bottom", "x": 50, "y": 95}
      ]
    }
  },
  "categories": {
    "subcategory": {
      "description": "Category description",
      "color": "#3B82F6"
    }
  }
}
```

### Manifest Fields

| Field | Type | Description |
|-------|------|-------------|
| `file` | string | SVG filename |
| `category` | string | Subcategory for grouping |
| `description` | string | Human-readable description |
| `color` | string | Primary color (hex) |
| `size` | object | Width and height |
| `anchor` | object | Center point for positioning |
| `connections` | array | Connection points for wiring |

---

## Creating New Categories

### Step 1: Create Directory

```bash
mkdir ycb/assets/my_category
```

### Step 2: Add SVG Files

Place your SVG files in the directory:
```
ycb/assets/my_category/
├── symbol1.svg
├── symbol2.svg
├── symbol3.svg
└── manifest.json
```

### Step 3: Create Manifest

Create `manifest.json` with all symbols:

```json
{
  "name": "My Symbol Library",
  "version": "1.0.0",
  "description": "Description",
  "author": "Your Name",
  "symbols": {
    "symbol1": { ... },
    "symbol2": { ... }
  }
}
```

### Step 4: Validate

```bash
python -m ycb.cli.assets validate
```

---

## Example: Creating a Sensor Symbol

### 1. Create the SVG

`ycb/assets/electrical/temperature_sensor.svg`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <!-- Sensor body -->
  <rect x="30" y="25" width="40" height="50" rx="5"
        fill="none" stroke="#8B5CF6" stroke-width="3"/>

  <!-- Thermometer icon -->
  <circle cx="50" cy="60" r="8"
          fill="none" stroke="#8B5CF6" stroke-width="2"/>
  <rect x="47" y="35" width="6" height="20"
        fill="none" stroke="#8B5CF6" stroke-width="2"/>

  <!-- Connection wires -->
  <line x1="40" y1="25" x2="40" y2="10"
        stroke="#8B5CF6" stroke-width="2"/>
  <line x1="60" y1="25" x2="60" y2="10"
        stroke="#8B5CF6" stroke-width="2"/>

  <!-- Connection points -->
  <circle cx="40" cy="10" r="3" fill="#8B5CF6"/>
  <circle cx="60" cy="10" r="3" fill="#8B5CF6"/>
</svg>
```

### 2. Update Manifest

Add to `ycb/assets/electrical/manifest.json`:

```json
{
  "symbols": {
    "temperature_sensor": {
      "file": "temperature_sensor.svg",
      "category": "sensors",
      "description": "Temperature sensor (RTD/Thermocouple)",
      "color": "#8B5CF6",
      "size": {"width": 100, "height": 100},
      "anchor": {"x": 50, "y": 50},
      "connections": [
        {"name": "wire1", "x": 40, "y": 10},
        {"name": "wire2", "x": 60, "y": 10}
      ]
    }
  }
}
```

### 3. Verify

```bash
python -m ycb.cli.assets list --category electrical
python -m ycb.cli.assets preview temperature_sensor
```

---

## Best Practices

### 1. Consistent Sizing

Use 100x100 viewBox for all symbols to ensure consistent scaling.

### 2. Clear Connection Points

Mark connection points explicitly for automated wiring in diagrams.

### 3. Minimal Detail

Keep symbols simple - they'll be animated and may be small on screen.

### 4. Standard Colors

Use the defined color schemes for visual consistency.

### 5. Descriptive Names

Use clear, descriptive filenames: `motor.svg`, `relay_nc.svg`, `plc_cpu.svg`

### 6. Test in Manim

Verify symbols render correctly:

```python
from manim import *
from pathlib import Path

class TestSVG(Scene):
    def construct(self):
        svg = SVGMobject("ycb/assets/electrical/motor.svg")
        svg.scale(2)
        self.add(svg)
```

---

## Existing Assets

### Electrical Symbols (11)

| Symbol | Description |
|--------|-------------|
| motor | 3-phase AC motor |
| relay | Relay coil |
| contactor | Motor contactor |
| overload | Thermal overload |
| transformer | Single-phase transformer |
| fuse | Fuse |
| switch | Manual switch (NO) |
| digital_input | PLC digital input |
| digital_output | PLC digital output |
| analog_input | PLC analog input |
| analog_output | PLC analog output |

### PLC Symbols (17)

| Symbol | Description |
|--------|-------------|
| plc_rack | PLC backplane with slots |
| cpu_module | CPU with status LEDs |
| io_module | 8-channel I/O module |
| power_supply | 24VDC PSU |
| ladder_xic | XIC - Examine If Closed |
| ladder_xio | XIO - Examine If Open |
| ladder_ote | OTE - Output Energize |
| ladder_otl | OTL - Output Latch |
| ladder_otu | OTU - Output Unlatch |
| ladder_ton | TON - Timer On Delay |
| ladder_tof | TOF - Timer Off Delay |
| ladder_ctu | CTU - Count Up |
| ladder_ctd | CTD - Count Down |
| comm_ethernet | Ethernet port |
| comm_serial | Serial RS-232/485 |
| comm_modbus | Modbus protocol |
| comm_profinet | PROFINET interface |

---

## Troubleshooting

### Symbol Not Appearing

1. Check file path is correct
2. Verify manifest.json is valid JSON
3. Run `validate` command to check for errors

### Colors Wrong

1. SVGs use hex colors (#RRGGBB)
2. Check for fill vs stroke attributes
3. Manim may override some colors

### Scaling Issues

1. Ensure viewBox is 100x100
2. Don't use absolute units (px, pt)
3. Use relative positioning within viewBox

### Animation Problems

1. Keep paths simple (avoid complex gradients)
2. Use explicit stroke-width values
3. Test with Manim's SVGMobject
