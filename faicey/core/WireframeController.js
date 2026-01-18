/**
 * WireframeController - Manages wireframe rendering styles and effects
 * Provides advanced wireframe customization for faces
 */

import * as THREE from 'three';

export default class WireframeController {
  constructor(faceMesh, thickness = 1) {
    this.faceMesh = faceMesh;
    this.thickness = thickness;
    this.originalMaterial = faceMesh.material;
    this.wireframeLines = null;
  }

  /**
   * Enable basic wireframe mode
   */
  enableBasicWireframe() {
    if (this.faceMesh.material) {
      this.faceMesh.material.wireframe = true;
    }
  }

  /**
   * Disable wireframe mode
   */
  disableWireframe() {
    if (this.faceMesh.material) {
      this.faceMesh.material.wireframe = false;
    }
  }

  /**
   * Create enhanced wireframe with custom line thickness
   * Uses LineSegments for more control
   */
  createEnhancedWireframe() {
    const geometry = this.faceMesh.geometry;
    const wireframeGeometry = new THREE.WireframeGeometry(geometry);

    const lineMaterial = new THREE.LineBasicMaterial({
      color: this.faceMesh.material.color,
      linewidth: this.thickness,
    });

    this.wireframeLines = new THREE.LineSegments(wireframeGeometry, lineMaterial);

    // Copy position and rotation from face mesh
    this.wireframeLines.position.copy(this.faceMesh.position);
    this.wireframeLines.rotation.copy(this.faceMesh.rotation);

    return this.wireframeLines;
  }

  /**
   * Update wireframe color
   * @param {number} color - Hex color value
   */
  setColor(color) {
    if (this.faceMesh.material) {
      this.faceMesh.material.color.setHex(color);
    }
    if (this.wireframeLines) {
      this.wireframeLines.material.color.setHex(color);
    }
  }

  /**
   * Set wireframe opacity
   * @param {number} opacity - Opacity value (0-1)
   */
  setOpacity(opacity) {
    if (this.faceMesh.material) {
      this.faceMesh.material.opacity = opacity;
      this.faceMesh.material.transparent = opacity < 1.0;
    }
    if (this.wireframeLines) {
      this.wireframeLines.material.opacity = opacity;
      this.wireframeLines.material.transparent = opacity < 1.0;
    }
  }

  /**
   * Animate wireframe color with glow effect
   * @param {number} baseColor - Base color
   * @param {number} glowColor - Glow color
   * @param {number} frequency - Pulse frequency
   */
  animateGlow(baseColor, glowColor, frequency = 1.0) {
    const baseRGB = new THREE.Color(baseColor);
    const glowRGB = new THREE.Color(glowColor);

    const animate = () => {
      const time = Date.now() / 1000;
      const pulse = (Math.sin(time * frequency * Math.PI * 2) + 1) / 2;

      const currentColor = new THREE.Color();
      currentColor.r = baseRGB.r + (glowRGB.r - baseRGB.r) * pulse;
      currentColor.g = baseRGB.g + (glowRGB.g - baseRGB.g) * pulse;
      currentColor.b = baseRGB.b + (glowRGB.b - baseRGB.b) * pulse;

      this.setColor(currentColor.getHex());
    };

    setInterval(animate, 16); // ~60fps
  }

  /**
   * Create scanline effect (retro style)
   */
  createScanlineEffect() {
    // This would add horizontal scanlines to the wireframe
    // Implementation would depend on shader materials
    console.log('Scanline effect would require custom shaders');
  }

  /**
   * Apply matrix/cyber aesthetic
   */
  applyCyberStyle() {
    this.setColor(0x00ff00); // Matrix green
    this.animateGlow(0x00ff00, 0x00ff88, 2.0);
  }

  /**
   * Apply neon style
   */
  applyNeonStyle(color = 0xff00ff) {
    this.setColor(color);
    this.animateGlow(color, 0xffffff, 1.5);
  }

  /**
   * Dispose wireframe resources
   */
  dispose() {
    if (this.wireframeLines) {
      this.wireframeLines.geometry.dispose();
      this.wireframeLines.material.dispose();
    }
  }
}
