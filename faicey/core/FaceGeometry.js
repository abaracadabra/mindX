/**
 * FaceGeometry - Creates 3D geometry for humanoid face
 * Defines vertices, faces, and morph targets for expressions
 */

import * as THREE from 'three';

export default class FaceGeometry {
  constructor() {
    this.morphTargets = [];
  }

  /**
   * Create face geometry with eyes, nose, mouth, and head outline
   */
  createFaceGeometry() {
    const geometry = new THREE.BufferGeometry();

    // Define face vertices (simplified humanoid face)
    const vertices = new Float32Array([
      // Head outline (ellipse)
      0.0, 1.2, 0.0,    // 0: top
      0.7, 1.0, 0.0,    // 1: top-right
      1.0, 0.5, 0.0,    // 2: right-top
      1.0, 0.0, 0.0,    // 3: right-middle
      1.0, -0.5, 0.0,   // 4: right-bottom
      0.5, -1.0, 0.0,   // 5: bottom-right
      0.0, -1.2, 0.0,   // 6: bottom
      -0.5, -1.0, 0.0,  // 7: bottom-left
      -1.0, -0.5, 0.0,  // 8: left-bottom
      -1.0, 0.0, 0.0,   // 9: left-middle
      -1.0, 0.5, 0.0,   // 10: left-top
      -0.7, 1.0, 0.0,   // 11: top-left

      // Left eye (circle)
      -0.5, 0.4, 0.0,   // 12: left eye center
      -0.3, 0.4, 0.0,   // 13: left eye right
      -0.5, 0.6, 0.0,   // 14: left eye top
      -0.7, 0.4, 0.0,   // 15: left eye left
      -0.5, 0.2, 0.0,   // 16: left eye bottom

      // Right eye (circle)
      0.5, 0.4, 0.0,    // 17: right eye center
      0.7, 0.4, 0.0,    // 18: right eye right
      0.5, 0.6, 0.0,    // 19: right eye top
      0.3, 0.4, 0.0,    // 20: right eye left
      0.5, 0.2, 0.0,    // 21: right eye bottom

      // Nose (simple triangle)
      0.0, 0.2, 0.1,    // 22: nose tip
      -0.1, 0.0, 0.0,   // 23: nose left
      0.1, 0.0, 0.0,    // 24: nose right

      // Mouth (ellipse)
      0.0, -0.4, 0.0,   // 25: mouth center
      0.3, -0.4, 0.0,   // 26: mouth right
      0.2, -0.3, 0.0,   // 27: mouth top-right
      0.0, -0.3, 0.0,   // 28: mouth top
      -0.2, -0.3, 0.0,  // 29: mouth top-left
      -0.3, -0.4, 0.0,  // 30: mouth left
      -0.2, -0.5, 0.0,  // 31: mouth bottom-left
      0.0, -0.5, 0.0,   // 32: mouth bottom
      0.2, -0.5, 0.0,   // 33: mouth bottom-right

      // Eyebrows
      -0.7, 0.7, 0.0,   // 34: left eyebrow left
      -0.3, 0.7, 0.0,   // 35: left eyebrow right
      0.3, 0.7, 0.0,    // 36: right eyebrow left
      0.7, 0.7, 0.0,    // 37: right eyebrow right
    ]);

    // Define faces (lines for wireframe)
    const indices = [
      // Head outline
      0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6,
      6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 0,

      // Left eye
      13, 14, 14, 15, 15, 16, 16, 13,
      12, 13, 12, 14, 12, 15, 12, 16,

      // Right eye
      18, 19, 19, 20, 20, 21, 21, 18,
      17, 18, 17, 19, 17, 20, 17, 21,

      // Nose
      22, 23, 22, 24, 23, 24,

      // Mouth
      26, 27, 27, 28, 28, 29, 29, 30,
      30, 31, 31, 32, 32, 33, 33, 26,

      // Mouth interior lines
      25, 26, 25, 28, 25, 30, 25, 32,

      // Eyebrows
      34, 35, 36, 37,
    ];

    geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
    geometry.setIndex(indices);
    geometry.computeBoundingSphere();

    // Create morph targets for expressions
    this.createMorphTargets(geometry, vertices);

    return geometry;
  }

  /**
   * Create morph targets for facial expressions
   */
  createMorphTargets(geometry, baseVertices) {
    const vertexCount = baseVertices.length / 3;

    // Helper to create morph target
    const createMorph = (name, modifications) => {
      const morphVertices = new Float32Array(baseVertices);

      modifications.forEach(({ index, x, y, z }) => {
        if (x !== undefined) morphVertices[index * 3] = x;
        if (y !== undefined) morphVertices[index * 3 + 1] = y;
        if (z !== undefined) morphVertices[index * 3 + 2] = z;
      });

      return {
        name,
        vertices: morphVertices,
      };
    };

    // Smile expression
    this.morphTargets.push(createMorph('smile', [
      { index: 27, y: -0.25 }, // mouth corners up
      { index: 33, y: -0.45 },
      { index: 29, y: -0.25 },
      { index: 31, y: -0.45 },
      { index: 26, x: 0.35 },  // mouth wider
      { index: 30, x: -0.35 },
    ]));

    // Frown expression
    this.morphTargets.push(createMorph('frown', [
      { index: 27, y: -0.35 }, // mouth corners down
      { index: 33, y: -0.55 },
      { index: 29, y: -0.35 },
      { index: 31, y: -0.55 },
    ]));

    // Open mouth
    this.morphTargets.push(createMorph('mouth_open', [
      { index: 28, y: -0.25 }, // top of mouth
      { index: 32, y: -0.6 },  // bottom of mouth
      { index: 25, y: -0.425 }, // center
      { index: 27, y: -0.25 },
      { index: 29, y: -0.25 },
      { index: 31, y: -0.6 },
      { index: 33, y: -0.6 },
    ]));

    // Blink (both eyes)
    this.morphTargets.push(createMorph('blink', [
      { index: 14, y: 0.4 }, // left eye top down
      { index: 16, y: 0.4 }, // left eye bottom up
      { index: 19, y: 0.4 }, // right eye top down
      { index: 21, y: 0.4 }, // right eye bottom up
    ]));

    // Wink left
    this.morphTargets.push(createMorph('wink_left', [
      { index: 14, y: 0.4 }, // left eye top down
      { index: 16, y: 0.4 }, // left eye bottom up
    ]));

    // Wink right
    this.morphTargets.push(createMorph('wink_right', [
      { index: 19, y: 0.4 }, // right eye top down
      { index: 21, y: 0.4 }, // right eye bottom up
    ]));

    // Raised eyebrows (surprised)
    this.morphTargets.push(createMorph('eyebrows_raised', [
      { index: 34, y: 0.8 },
      { index: 35, y: 0.8 },
      { index: 36, y: 0.8 },
      { index: 37, y: 0.8 },
    ]));

    // Furrowed eyebrows (thinking/confused)
    this.morphTargets.push(createMorph('eyebrows_furrowed', [
      { index: 34, y: 0.65, x: -0.6 },
      { index: 35, y: 0.65, x: -0.35 },
      { index: 36, y: 0.65, x: 0.35 },
      { index: 37, y: 0.65, x: 0.6 },
    ]));

    // Store morph targets on geometry
    geometry.morphAttributes.position = this.morphTargets.map(m =>
      new THREE.BufferAttribute(m.vertices, 3)
    );
    geometry.morphTargetsRelative = false;

    console.log(`Created ${this.morphTargets.length} morph targets`);
  }

  /**
   * Get list of available morph targets
   */
  getMorphTargets() {
    return this.morphTargets.map(m => m.name);
  }
}
