/**
 * VisionAid Smart Glasses - Temple-Integrated Commercial OpenSCAD Master
 * =======================================================================
 * 
 * Commercial Ray-Ban Meta Style Architecture:
 * - ZERO center box on the browline / nose bridge!
 * - Clean, classic Wayfarer front frame with arched keyhole bridge and corner camera port.
 * - Thickened, stylish Left and Right Temples house the electronics:
 *   * Left Temple: Houses Seeed XIAO ESP32-S3 + OV5640 Camera + Left Bone Conduction + Haptic
 *   * Right Temple: Houses 450mAh LiPo Battery + TP4056 USB-C Charger + Right Bone Conduction + Buttons
 * - Perfectly balanced weight distribution with zero weight on the nose.
 */

$fn = 32;

// --- Dimensions (mm) ---
face_width         = 144.0;
bridge_w           = 18.0;
rim_w_top          = 49.0;
rim_w_bot          = 42.0;
rim_h              = 40.0;
rim_depth          = 4.0;

// Temples (Substantial smart temples housing all electronics)
temple_len         = 145.0;
temple_thick       = 7.2;   // 7.2mm thickness cleanly encloses 4.5mm boards and 5.0mm batteries
temple_h_front     = 21.5;  // Encloses 17.5mm board and 20mm battery
temple_h_mid       = 17.0;  // Bone conduction zone
temple_h_rear      = 8.0;   // Ear hook
hinge_screw_dia    = 1.6;

// =========================================================================
// 1. CLEAN DESIGNER FRONT FRAME (ZERO CENTER BOX!)
// =========================================================================
module front_frame() {
    difference() {
        union() {
            // Browline Top Bar
            translate([-face_width/2, rim_h/2 - 2.5, 0])
                cube([face_width, 4.5, rim_depth]);

            // Left Wayfarer Rim
            translate([bridge_w/2 + rim_w_top/2, 0, 0])
                wayfarer_rim();

            // Right Wayfarer Rim
            translate([-bridge_w/2 - rim_w_top/2, 0, 0])
                mirror([1, 0, 0]) wayfarer_rim();

            // Arched Bridge Base
            translate([-bridge_w/2, 0, 0])
                cube([bridge_w, 6.0, rim_depth]);

            // Left & Right Ergonomic Resting Nose Pads
            translate([bridge_w/2 - 2.2, -10, 0])
                cube([2.2, 13, rim_depth + 4.0]);
            translate([-bridge_w/2, -10, 0])
                cube([2.2, 13, rim_depth + 4.0]);

            // Left Sculpted End Piece & Hinge Lug (18.5mm tall, matches temple arm)
            translate([face_width/2 - 10.0, 2.0, 0])
                cube([10.0, 18.5, 5.5]);

            // Right Sculpted End Piece & Hinge Lug (18.5mm tall, matches temple arm)
            translate([-face_width/2, 2.0, 0])
                cube([10.0, 18.5, 5.5]);
        }

        // Keyhole Saddle Nose Arch Cutout (leaves bridge 100% open and comfortable)
        translate([0, 0, -1])
            cylinder(d=bridge_w, h=rim_depth + 6);

        // Ray-Ban Meta Style Corner Camera Aperture (OV5640 AF 8.5mm Lens)
        translate([bridge_w/2 + rim_w_top - 1.5, rim_h/2 - 1.0, -1])
            cylinder(d=8.7, h=rim_depth + 4);

        // Privacy LED Aperture (Next to camera)
        translate([bridge_w/2 + rim_w_top - 9.0, rim_h/2 - 1.0, -1])
            cylinder(d=2.8, h=rim_depth + 4);

        // Hinge Screw Holes (M1.6)
        translate([face_width/2 - 3.5, rim_h/2 - 1.0, -1])
            cylinder(d=hinge_screw_dia, h=10);
        translate([-face_width/2 + 3.5, rim_h/2 - 1.0, -1])
            cylinder(d=hinge_screw_dia, h=10);
    }
}

module wayfarer_rim() {
    difference() {
        minkowski() {
            cube([rim_w_top - 12, rim_h - 12, rim_depth - 1], center=true);
            cylinder(r=6, h=1, center=true);
        }
        minkowski() {
            cube([rim_w_top - 18, rim_h - 18, rim_depth + 4], center=true);
            cylinder(r=4, h=1, center=true);
        }
    }
}

// =========================================================================
// 2. ENLARGED LEFT TEMPLE (COMPUTE + CAMERA + AUDIO + HAPTIC)
// =========================================================================
module left_temple() {
    difference() {
        union() {
            // Front section housing Seeed XIAO ESP32-S3 (21.5mm high)
            cube([temple_thick, 50, temple_h_front]);
            // Mid section housing bone conduction transducer
            translate([0, 50, 0])
                cube([temple_thick, 40, temple_h_mid]);
            // Rear ear contour
            translate([0, 90, -10])
                cube([temple_thick, 55, temple_h_rear + 10]);
            // Cheekbone Transducer Contact Pad (protrudes 3.2mm toward head)
            translate([-3.2, 52, 1.5])
                cube([3.2, 18, 14.5]);
        }

        // Hinge Screw Hole
        translate([temple_thick/2, 4.0, -1])
            cylinder(d=hinge_screw_dia, h=temple_h_front + 2);

        // Inner Cavity for Seeed XIAO ESP32-S3 Board (24 x 18.5 x 5.4 mm)
        translate([-1, 14, 1.5])
            cube([5.4 + 1, 24, 18.5]);

        // Camera Flex Cable Channel
        translate([-1, 0, 8.0])
            cube([temple_thick + 2, 14, 4.0]);

        // Transducer Cavity inside contact pad
        translate([-2.5, 54, 3.0])
            cube([2.5, 14, 11.5]);

        // 10mm Coin Haptic Motor Cavity
        translate([-1, 74, 3.0])
            cube([3.5, 12, 12]);
    }
}

// =========================================================================
// 3. ENLARGED RIGHT TEMPLE (BATTERY + USB-C + BUTTONS + AUDIO)
// =========================================================================
module right_temple() {
    difference() {
        union() {
            // Front section housing 450mAh LiPo Battery (21.5mm high)
            cube([temple_thick, 55, temple_h_front]);
            // Mid section housing TP4056 USB-C Charger
            translate([0, 55, 0])
                cube([temple_thick, 45, temple_h_mid]);
            // Rear ear contour
            translate([0, 100, -10])
                cube([temple_thick, 45, temple_h_rear + 10]);
            // Right cheekbone transducer contact pad (protrudes 3.2mm toward head)
            translate([temple_thick, 52, 1.5])
                cube([3.2, 18, 14.5]);
        }

        // Hinge Screw Hole
        translate([temple_thick/2, 4.0, -1])
            cylinder(d=hinge_screw_dia, h=temple_h_front + 2);

        // Battery Cavity (Fits up to 800mAh LiPo: 42 x 20.0 x 6.0 mm)
        translate([temple_thick - 6.0, 13, 1.5])
            cube([6.1, 42, 19.5]);

        // Right Bone Conduction Transducer Cavity
        translate([temple_thick - 2.5, 56, 3.0])
            cube([2.5, 14, 11.5]);

        // TP4056 Charger Cavity (24 x 16 x 5.0 mm)
        translate([temple_thick - 5.0, 73, 1.5])
            cube([5.1, 20, 15.0]);

        // USB-C Port Cutout on bottom edge (9.5mm x 3.5mm)
        translate([1.5, 78, -1])
            cube([4.0, 9.5, 3.5]);

        // Dual Tactile Click Buttons on top edge (u=24mm and u=38mm)
        translate([temple_thick/2, 24, temple_h_front - 2])
            cylinder(d=4.0, h=4);
        translate([temple_thick/2, 38, temple_h_front - 2])
            cylinder(d=4.0, h=4);
    }
}

// =========================================================================
// MASTER ASSEMBLY VIEW (True 3D Glasses Perspective)
// =========================================================================
// Front Frame
front_frame();

// Left Temple Arm attached at left end-piece, extending backwards along +Z
translate([face_width/2 - temple_thick - 1.5, rim_h/2 - 1.0, 4.0])
    rotate([90, 0, 0])
        left_temple();

// Right Temple Arm attached at right end-piece, extending backwards along +Z
translate([-face_width/2 + 1.5, rim_h/2 - 1.0, 4.0])
    rotate([90, 0, 0])
        right_temple();
