// ===== CHARGE LED sign — global config =====
// Edit this file; then run ./build.sh to regenerate every STL.

$fn = 72;

// ---- calibrated collar (press-fit for 12mm bullet pixel) ----
collar_stl    = "../../assets/bullet-collar.stl"; // path resolved from src/parts/ entry files
collar_h      = 2.0;     // Z span of the collar STL
collar_od     = 16.0;    // collar outer diameter
collar_cx     = 43.0;    // STL native X center (Y center is 0)
pixel_through = 12.3;    // clearance hole through the plate (just over bore Ø12.19)
dome_clear    = 9.0;     // lit dome protrusion above the rear plate — MEASURE on your pixel

// ---- shell ----
plate_t    = 2.0;        // rear plate thickness (== collar_h, so the collar sits flush)
wall_t     = 2.5;        // chimney wall thickness
cell_inner = 30;         // square interior of each test cell (the press-fit opening)

// ---- diffuser panels (press-fit straight into the cell opening) ----
panel_press_clear = 0.25; // panel is this much SMALLER than the opening (total) -> friction fit
panel_thicks      = [1, 2, 3];

// ---- coupon depth ladder ----
led_gaps = [20, 35, 50]; // clear LED-tip -> panel distance, per cell (mm)

// ---- derived ----
cell_pitch = cell_inner + 2 * wall_t;      // outer cell footprint (35)
n_cells    = len(led_gaps);
plate_w    = n_cells * cell_pitch;
plate_d    = cell_pitch;
panel_side = cell_inner - panel_press_clear;
function cell_x(i)     = i * cell_pitch + cell_pitch / 2;
function chimney_H(i)  = plate_t + dome_clear + led_gaps[i];
